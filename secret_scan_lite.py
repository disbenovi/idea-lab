"""Offline shape scanner. Findings contain redacted previews, never values."""
import argparse
import fnmatch
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 1_000_000
SKIP = {'.git', 'node_modules', '__pycache__'}
RULES = [
    ('SL001', re.compile(r'(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}(?![A-Za-z0-9])')),
    ('SL002', re.compile(r'\b(?:gh[pous]_|github_pat_)[A-Za-z0-9_]+')),
    ('SL003', re.compile(r'\bsk-[A-Za-z0-9_-]{20,}')),
    ('SL004', re.compile(r'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----')),
    ('SL005', re.compile(r'(?<![A-Za-z0-9_.-])[A-Za-z0-9_-]+\.'
                         r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
                         r'(?![A-Za-z0-9_.-])')),
    ('SL006', re.compile(r'\bxox[abpos]-[A-Za-z0-9-]+')),
    ('SL007', re.compile(r'''(?i)(?<![\w])(?:password|secret|token|api_key|apikey)
        ["']?\s*[:=]\s*(["'])(?P<value>[^\r\n]*?)\1''', re.X)),
]


def matches(text):
    for rule, pattern in RULES:
        for match in pattern.finditer(text):
            value = match.group('value') if rule == 'SL007' else match.group()
            if rule != 'SL007' or len(value) >= 12:
                yield rule, value


def shape(value):
    return f'{value[:3]}…{value[-2:]} ({len(value)})'


def safe_path(path, values):
    # A filename can itself contain a planted value; do not leak via metadata.
    label = path.as_posix()
    for value in sorted(values, key=len, reverse=True):
        label = label.replace(value, '[redacted]')
    for _, pattern in RULES:
        label = pattern.sub('[redacted]', label)
    return ''.join(c if c.isprintable() else '?' for c in label)


def scan(root, allowlist=()):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise OSError('invalid scan root')
    findings, values = [], set()

    def failed(_):
        raise OSError('directory unavailable')

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=failed):
        dirs[:] = sorted(d for d in dirs if d not in SKIP
                         and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root)
            if any(fnmatch.fnmatchcase(relative.as_posix(), g) for g in allowlist):
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                continue
            # Refuse symlinks even if a path is swapped after lstat (POSIX).
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, 'rb') as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    continue
                data = source.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES or b'\0' in data:
                continue
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                for rule, value in matches(line):
                    values.add(value)
                    findings.append({'path': relative, 'line': number,
                                     'rule': rule, 'shape': shape(value)})
    for finding in findings:
        finding['path'] = safe_path(finding['path'], values)
    return findings


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error echoes arbitrary arguments.
        self.exit(2, 'secret-scan-lite: invalid arguments; use --help\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('directory', nargs='?', default='.')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--allowlist', metavar='FILE')
    args = parser.parse_args(argv)
    try:
        globs = []
        if args.allowlist:
            with open(args.allowlist, encoding='utf-8') as source:
                globs = [s for line in source if (s := line.strip())
                         and not s.startswith('#')]
        findings = scan(args.directory, globs)
    except (OSError, UnicodeError, ValueError):
        if args.json:
            print(json.dumps({'findings': [], 'error': 'scan incomplete'}))
        else:
            print('secret-scan-lite: scan incomplete', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({'findings': findings}, ensure_ascii=True))
    else:
        for item in findings:
            print('{path}:{line}  {rule}  {shape}'.format(**item))
    return int(bool(findings))


if __name__ == '__main__':
    sys.exit(main())
