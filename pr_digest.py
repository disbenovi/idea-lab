#!/usr/bin/env python3
"""Offline unified-diff survey. Heuristics, not a language-aware security audit."""
import argparse
import json
from pathlib import PurePosixPath
import re
import sys

SECRET = re.compile(r'(?<![A-Za-z0-9_])(?:[0-9a-fA-F]{32,}|[A-Za-z0-9+/=_-]{40,})(?![A-Za-z0-9_])')
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
PAIRS = [('package.json', ('package-lock.json', 'yarn.lock', 'pnpm-lock.yaml')),
         ('pyproject.toml', ('poetry.lock', 'uv.lock')),
         ('Cargo.toml', ('Cargo.lock',)), ('Gemfile', ('Gemfile.lock',)),
         ('composer.json', ('composer.lock',)), ('go.mod', ('go.sum',))]
RULES = [
    ('auth', r'\b(auth\w*|session\w*|token\w*|password\w*)\b', 'Check changed authentication/session/token behavior'),
    ('sql-concat', r'\b(SELECT|INSERT|UPDATE|DELETE)\b.*[+]|[+].*\b(SELECT|INSERT|UPDATE|DELETE)\b', 'Replace SQL concatenation with bound parameters'),
    ('dynamic-code', r'\b(eval|exec|pickle\.loads)\s*\(', 'Verify dynamic execution or deserialization inputs'),
    ('broad-except', r'\bexcept\s*:', 'Narrow the bare exception handler'),
    ('todo', r'\b(TODO|FIXME)\b', 'Resolve or track the added TODO/FIXME'),
]


def redact(text):
    return SECRET.sub('[REDACTED]', text)


def classify(path):
    p = PurePosixPath(path.lower())
    if any(x in ('test', 'tests', '__tests__') for x in p.parts) or p.name.startswith('test_') or p.stem.endswith(('_test', '.test', '.spec')):
        return 'tests'
    if any('migration' in x for x in p.parts):
        return 'migration'
    if 'docs' in p.parts or p.suffix in ('.md', '.rst', '.txt') or p.name.startswith(('readme', 'license')):
        return 'docs'
    if p.suffix in ('.json', '.toml', '.yaml', '.yml', '.ini', '.cfg', '.lock') or p.name in ('dockerfile', 'makefile', '.gitignore', 'go.mod', 'go.sum', 'gemfile'):
        return 'config'
    if p.suffix in ('.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.c', '.h', '.cpp', '.java', '.rb', '.sh', '.sql'):
        return 'source'
    return 'other'


def path_from_header(text):
    path = text.split('\t', 1)[0]
    if path.startswith('"'):
        try:
            path = json.loads(path)
        except ValueError:
            raise ValueError('unsupported quoted diff path') from None
    return path[2:] if path.startswith(('a/', 'b/')) else path


def parse_diff(text):
    files, changes = {}, []
    old_path = path = None
    old = new = left = right = 0
    group = 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HUNK.match(line)
        if match:
            if left or right:
                raise ValueError('truncated unified diff hunk')
            if not path:
                raise ValueError('hunk has no file headers')
            old, new = int(match[1]), int(match[3])
            left, right = int(match[2] or 1), int(match[4] or 1)
            group += 1
            continue
        if left or right:
            if line.startswith('\\ No newline'):
                continue
            kind = line[:1]
            if kind not in (' ', '+', '-'):
                raise ValueError('invalid unified diff hunk')
            number = old if kind == '-' else new
            changes.append((path, number, kind, line[1:], group))
            if kind in (' ', '-'):
                old += 1
                left -= 1
            if kind in (' ', '+'):
                new += 1
                right -= 1
            if min(left, right) < 0:
                raise ValueError('hunk line count mismatch')
            if kind != ' ':
                files[path]['added' if kind == '+' else 'removed'] += 1
            continue
        if line.startswith('--- ') and index + 1 < len(lines) and lines[index + 1].startswith('+++ '):
            old_path = path_from_header(line[4:])
        elif line.startswith('+++ ') and old_path is not None:
            new_path = path_from_header(line[4:])
            path = old_path if new_path == '/dev/null' else new_path
            files.setdefault(path, dict(path=path, added=0, removed=0, change_class=classify(path)))
            old_path = None
        elif line.startswith(('Binary files ', 'GIT binary patch', 'rename from ', 'old mode ')):
            raise ValueError('binary, rename-only and mode-only diffs are not supported')
    if left or right:
        raise ValueError('truncated unified diff hunk')
    return files, changes


def digest(text):
    files, changes = parse_diff(text)
    risks = []

    def flag(rule, path, number, kind, source, message):
        risk = dict(rule=rule, file=path, line=number,
                    side='old' if kind == '-' else 'new', message=message)
        if rule != 'secret':
            risk['source'] = redact(source)
        risks.append(risk)

    for i, (path, number, kind, source, group) in enumerate(changes):
        if kind == ' ':
            continue
        if SECRET.search(source):
            flag('secret', path, number, kind, '', 'Secret-shaped string; value withheld')
        if kind == '-':
            if classify(path) == 'tests':
                flag('deleted-test', path, number, kind, source, 'Confirm removed test coverage is replaced or obsolete')
            continue
        for rule, pattern, message in RULES:
            if re.search(pattern, source, re.I):
                flag(rule, path, number, kind, source, message)
        following = [row[3] for row in changes[i:i + 4]
                     if row[0] == path and row[4] == group and row[2] != '-']
        window = '\n'.join(following)
        if re.search(r'\bsubprocess\.', source) and re.search(r'\bshell\s*=\s*True\b', window):
            flag('shell', path, number, kind, source, 'Review subprocess shell=True inputs for injection')
        if re.search(r'\bexcept\s+Exception\s*:', source) and re.search(r':\s*pass\b', window):
            flag('swallowed-exception', path, number, kind, source, 'Do not silently swallow Exception')

    for path in sorted(files):
        p = PurePosixPath(path)
        for manifest, locks in PAIRS:
            expected = locks if p.name == manifest else (manifest,) if p.name in locks else ()
            if expected and not any(str(p.with_name(name)) in files for name in expected):
                touched = next((r for r in changes if r[0] == path and r[2] != ' '), None)
                number, kind, source = (touched[1], touched[2], touched[3]) if touched else (1, '+', '')
                flag('dependency-pair', path, number, kind, source,
                     'Check dependency pair: expected ' + ' or '.join(expected) + ' in this directory')
    ordered = sorted(files.values(), key=lambda f: (-(f['added'] + f['removed']), f['path']))
    checklist = list(dict.fromkeys(r['message'] + ' (' + r['file'] + ')' for r in risks))[:7]
    if ordered:
        total = sum(f['added'] + f['removed'] for f in ordered)
        fallback = [f"Review {len(ordered)} changed file(s), {total} changed line(s)",
                    'Verify behavior in highest-churn file: ' + ordered[0]['path'],
                    'Confirm coverage for changed classes: ' + ', '.join(sorted({f['change_class'] for f in ordered}))]
        for item in fallback:
            if len(checklist) < 3:
                checklist.append(item)
    result = dict(files=ordered, risks=risks, checklist=checklist)
    # Scrub every string, including paths and checklist text, before any output.
    return json.loads(redact(json.dumps(result, ensure_ascii=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', help='unified diff file (default: stdin)')
    parser.add_argument('--json', action='store_true', help='emit JSON')
    args = parser.parse_args()
    try:
        if args.file:
            with open(args.file, encoding='utf-8') as stream:
                text = stream.read()
        else:
            text = sys.stdin.read()
        result = digest(text)
    except (OSError, UnicodeError, ValueError):
        print('pr-digest: cannot read input or unsupported/malformed unified diff', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for f in result['files']:
            print(f"{f['path']}: +{f['added']} -{f['removed']} [{f['change_class']}]")
        print('Risks: ' + str(len(result['risks'])))
        for risk in result['risks']:
            print(f"{risk['file']}:{risk['line']} ({risk['side']}) {risk['rule']}: {risk['message']}")
            if risk.get('source'):
                print('  ' + risk['source'])
        print('Reviewer checklist:')
        for item in result['checklist']:
            print('- ' + item)
    return 0


if __name__ == '__main__':
    sys.exit(main())
