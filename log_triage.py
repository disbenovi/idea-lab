#!/usr/bin/env python3
"""Deterministic, offline log template ranking (Python standard library only)."""
import argparse
from contextlib import nullcontext
from datetime import datetime
import ipaddress
import json
import re
import sys


ISO = r'\b\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:?\d{2})?(?![\w:+.-])'
PATTERN = re.compile(
    r'(?P<quoted>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
    r'|(?P<timestamp>' + ISO + r')'
    r'|(?P<uuid>\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b)'
    r'|(?P<ipv4>(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?(?![\w.:]))'
    r'|(?P<epoch>\b(?:\d{13}|\d{10})(?:\.\d+)?\b)'
    r'|(?P<number>(?<![\w.])[+-]?\d{5,}(?:\.\d+)?(?![\w.]))'
    r'|(?P<hex>\b(?:0x)?[0-9a-f]{8,}\b)',
    re.IGNORECASE,
)
TIMESTAMPS = re.compile(ISO)
HEADER = 'Ranked by count: the dominant template is usually the symptom; the rare one is usually the cause.'


def valid_timestamp(value):
    try:
        datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def normalize(line):
    def replace(match):
        kind, value = match.lastgroup, match.group()
        if kind == 'quoted':
            if len(value[1:-1]) > 40:
                return '<quoted>'
            # Short quotes remain, but variable tokens inside still normalize.
            return value[0] + normalize(value[1:-1]) + value[-1]
        if kind == 'timestamp' and not valid_timestamp(value):
            return value
        if kind == 'ipv4':
            host, _, port = value.partition(':')
            try:
                ipaddress.IPv4Address(host)
                if port and int(port) > 65535:
                    return value
            except ipaddress.AddressValueError:
                return value
        if kind == 'hex' and value.isdigit():
            kind = 'number'
        return '<' + kind + '>'
    return PATTERN.sub(replace, line)


def triage(lines, top=20, samples=1):
    groups = {}
    total = 0
    for raw in lines:
        line = raw.rstrip('\r\n')
        total += 1
        template = normalize(line)
        if template not in groups:
            groups[template] = dict(template=template, count=0, first_line=line,
                                    last_line=line, sample=line, samples=[])
        group = groups[template]
        group['count'] += 1
        group['last_line'] = line
        if len(group['samples']) < samples:
            group['samples'].append(line)
        for match in TIMESTAMPS.finditer(line):
            timestamp = match.group()
            if valid_timestamp(timestamp):
                group.setdefault('first_timestamp', timestamp)
                group['last_timestamp'] = timestamp
    ranked = sorted(groups.values(), key=lambda g: (-g['count'], g['template']))
    return dict(total_lines=total, total_templates=len(groups), templates=ranked[:top])


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError('must be nonnegative')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', default='-', help='UTF-8 file, or - for stdin')
    parser.add_argument('--top', type=nonnegative, default=20)
    parser.add_argument('--samples', type=nonnegative, default=1)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        source = nullcontext(sys.stdin) if args.file == '-' else open(args.file, encoding='utf-8')
        with source as lines:
            result = triage(lines, args.top, args.samples)
    except (OSError, UnicodeError) as error:
        parser.exit(2, f'log-triage: {error}\n')
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(HEADER)
        for group in result['templates']:
            print(f"{group['count']:>7}  {group['template']}")
            if 'first_timestamp' in group:
                print(f"         timestamps: {group['first_timestamp']} .. {group['last_timestamp']}")
            for sample in group['samples']:
                print(f'         sample: {sample}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
