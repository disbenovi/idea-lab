"""Conservative, offline Dockerfile checks. Python standard library only."""
import argparse
import json
import re
import shlex
import sys
from pathlib import Path


def instructions(text):
    """Yield start line, opcode and joined argument; skip heredoc bodies."""
    pending, start, escape, heredocs = '', 0, '\\', []
    for line, raw in enumerate(text.splitlines(), 1):
        if heredocs:
            if raw.strip() == heredocs[0]:
                heredocs.pop(0)
            continue
        stripped = raw.strip()
        if stripped.startswith('#'):
            match = re.fullmatch(r'#\s*escape\s*=\s*([`\\])', stripped, re.I)
            if match and not pending:
                escape = match[1]
            continue
        if not stripped:
            continue
        if not pending:
            start = line
        continued = len(stripped) - len(stripped.rstrip(escape))
        pending += (stripped[:-1] + ' ') if continued % 2 else stripped
        if continued % 2:
            continue
        parts = pending.split(None, 1)
        pending = ''
        op, value = parts[0].upper(), parts[1] if len(parts) > 1 else ''
        if op in {'RUN', 'COPY', 'ADD'} and '<<' in value:
            heredocs = re.findall(r"<<-?\s*['\"]?([\w]+)", value)
            continue
        yield start, op, value


def words(value):
    try:
        if value.lstrip().startswith('['):
            result = json.loads(value)
            return result if isinstance(result, list) and all(isinstance(x, str) for x in result) else []
        return shlex.split(value)
    except (ValueError, TypeError):
        return []


def commands(value):
    """Split shell operators without treating quoted operators as commands."""
    if value.lstrip().startswith('['):
        return [words(value)], []
    if re.search(r"(['\"])[;&|]+\1", value):
        return [], []  # Quoted operator tokens lose their provenance in shlex.
    try:
        lexer = shlex.shlex(value, posix=True, punctuation_chars=';&|')
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return [], []
    result, separators, current = [], [], []
    for token in tokens:
        if token in {'&&', '||', ';', '|', '&'}:
            result.append(current)
            separators.append(token)
            current = []
        else:
            current.append(token)
    return result + [current], separators


def audit(text):
    findings, stages, stage, health = [], {}, None, False

    def add(rule, severity, line, message):
        findings.append(dict(rule=rule, severity=severity, line=line, message=message))

    for line, op, value in instructions(text):
        args = words(value)
        if op == 'FROM' and args:
            args = [x for x in args if not x.startswith('--')]
            if not args:
                continue
            base = args[0]
            inherited = stages.get(base.lower())
            stage = dict(user=inherited['user'] if inherited else None, line=line, copies=[])
            if len(args) >= 3 and args[1].upper() == 'AS':
                stages[args[2].lower()] = stage
            if base != 'scratch' and inherited is None and '$' not in base and '@' not in base:
                tail = base.rsplit('/', 1)[-1]
                if ':' not in tail or tail.rsplit(':', 1)[1] == 'latest':
                    add('DF001', 'high', line, 'Base image has no explicit non-latest tag or digest')
        elif op == 'USER' and stage is not None and args:
            stage['user'] = (args[0], line)
        elif op == 'HEALTHCHECK':
            health = True
        elif op in {'ARG', 'ENV'}:
            names = [args[0].split('=', 1)[0]] if args else []
            if op == 'ENV' and args and '=' in args[0]:
                names = [x.split('=', 1)[0] for x in args if '=' in x]
            for name in names:
                if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) and re.search(
                        r'secret|password|passwd|token|api_?key|private_?key|credential', name, re.I):
                    add('DF007', 'high', line, 'Secret-like variable name: ' + name)
        elif op == 'ADD':
            sources = [x for x in args[:-1] if not x.startswith('--')]
            if any(not re.search(r'://|^git@|\$(?:\{|\w)|\.(?:tar(?:\.(?:gz|bz2|xz|zst))?|tgz|tbz2|txz)$', x)
                   for x in sources):
                add('DF006', 'medium', line, 'Use COPY for ordinary local files')
        elif op == 'COPY' and stage is not None:
            if args == ['.', '.']:
                stage['copies'].append(line)
        elif op == 'RUN':
            groups, separators = commands(value)
            executables = [g[0].rsplit('/', 1)[-1] if g else '' for g in groups]
            apt = [g for g, exe in zip(groups, executables) if exe == 'apt-get' and 'install' in g]
            if apt:
                if any('--no-install-recommends' not in g for g in apt):
                    add('DF003', 'medium', line, 'apt-get install lacks --no-install-recommends')
                last_install = max(i for i, g in enumerate(groups) if g in apt)
                cleanup = any(i > last_install and exe == 'rm' and any(x.startswith('-') and 'r' in x for x in g[1:])
                              and any(x.rstrip('/') in {'/var/lib/apt/lists', '/var/lib/apt/lists/*'} for x in g[1:])
                              for i, (g, exe) in enumerate(zip(groups, executables)))
                if not cleanup:
                    add('DF004', 'medium', line, 'Clean /var/lib/apt/lists in the same RUN')
            for i, separator in enumerate(separators):
                if separator == '|' and executables[i] in {'curl', 'wget'} and executables[i + 1] in {'sh', 'bash', 'dash', 'ash', 'zsh'}:
                    add('DF005', 'high', line, 'Download piped directly into a shell')
                    break
            if 'sudo' in executables:
                add('DF010', 'low', line, 'Avoid sudo in image build commands')
            dependency = any(exe in {'apt-get', 'pip', 'pip3', 'npm', 'yarn', 'pnpm', 'bundle', 'poetry'}
                             and any(x in g[1:] for x in {'install', 'ci', 'sync'})
                             for g, exe in zip(groups, executables))
            if dependency and stage is not None:
                for copy_line in stage['copies']:
                    add('DF008', 'medium', copy_line, 'Copy dependency manifests before installing dependencies')
                stage['copies'] = []
    if stage is not None:
        user = stage['user']
        if user is None or user[0].split(':', 1)[0] in {'root', '0'}:
            add('DF002', 'high', user[1] if user else stage['line'], 'Final stage does not select a non-root USER')
    if not health:
        add('DF009', 'low', 1, 'No HEALTHCHECK instruction')
    findings.sort(key=lambda f: (f['line'], f['rule']))
    return dict(findings=findings, counts={s: sum(f['severity'] == s for f in findings)
                                          for s in ('high', 'medium', 'low')})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', default='./Dockerfile')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = audit(Path(args.path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError):
        print('dockerfile-audit: cannot read input as UTF-8', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for f in result['findings']:
            print(f"{f['line']}: {f['rule']} {f['severity']} {f['message']}")
        print(' '.join(f'{s}={n}' for s, n in result['counts'].items()))
    return int(result['counts']['high'] > 0)


if __name__ == '__main__':
    sys.exit(main())
