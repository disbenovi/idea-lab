"""Offline schedule linting. See docs/routine-lint.md for the input contract."""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc


def cron_fields(text):
    parts = text.split()
    if len(parts) != 5:
        raise ValueError('cron must have 5 fields')
    fields = []
    for part, (lo, hi) in zip(parts, [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]):
        if part == '*':
            values = set(range(lo, hi + 1))
        elif re.fullmatch(r'[0-9]+(?:,[0-9]+)*', part):
            values = {int(x) for x in part.split(',')}
            if min(values) < lo or max(values) > hi:
                raise ValueError(f'cron field {part!r} outside {lo}..{hi}')
        else:
            raise ValueError(f'unsupported cron field {part!r}; use *, numbers or lists')
        fields.append(values)
    fields[4] = {n % 7 for n in fields[4]}
    return parts, fields


def local_instants(naive, zone):
    """Reject skipped wall times; retain both distinct repeated-hour instants."""
    values = set()
    for fold in (0, 1):
        utc = naive.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if utc.astimezone(zone).replace(tzinfo=None) == naive:
            values.add(utc)
    return sorted(values)


def timestamp(text, zone):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if value.tzinfo is not None:
        return value.astimezone(UTC)
    instants = local_instants(value, zone)
    if len(instants) != 1:
        raise ValueError('ambiguous or nonexistent local time; supply an explicit offset')
    return instants[0]


def next_cron(parts, fields, zone, now, end):
    minutes, hours, days, months, weekdays = fields
    date = now.astimezone(zone).date()
    for _ in range(366 * 8):
        dom, dow = date.day in days, (date.weekday() + 1) % 7 in weekdays
        day_ok = (dom or dow) if parts[2] != '*' and parts[4] != '*' else dom and dow
        if date.month in months and day_ok:
            candidates = [instant for hour in sorted(hours) for minute in sorted(minutes)
                          for instant in local_instants(datetime(date.year, date.month,
                          date.day, hour, minute), zone) if now < instant <= end]
            if candidates:
                return min(candidates)
        if date >= end.astimezone(zone).date():
            break
        date += timedelta(days=1)
    raise ValueError('no future cron fire before end_date within 8-year search horizon')


def utc_projection(parts, fields, local):
    # Only simple daily/weekly schedules have a safe compact next-offset projection.
    if parts[2:4] != ['*', '*'] or len(fields[0]) != 1 or len(fields[1]) != 1:
        return ''
    offset = local.utcoffset().total_seconds()
    if offset % 60:
        return ''
    shift, minute = divmod(local.hour * 60 + local.minute - int(offset // 60), 1440)
    hour, minute = divmod(minute, 60)
    day = '*' if parts[4] == '*' else ','.join(str(n) for n in sorted(
        {(d + shift) % 7 for d in fields[4]}))
    return f'{minute} {hour} * * {day}'


def read_rows(path):
    text = path.read_text(encoding='utf-8')
    if path.suffix.lower() == '.json':
        rows = json.loads(text)
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError('JSON must be an array of row objects')
        return list(enumerate(rows, 1))
    rows, header = [], None
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
            if line.endswith('|'):
                line = line[:-1]
        cells = [c.strip() for c in line.split('|')]
        if all(re.fullmatch(r':?-+:?', c) for c in cells):
            continue
        if header is None:
            header = cells
            if len(set(header)) != len(header) or 'name' not in header:
                raise ValueError('markdown requires unique column names including name')
        elif len(cells) != len(header):
            raise ValueError(f'row {number}: expected {len(header)} cells, got {len(cells)}')
        else:
            rows.append((number, dict(zip(header, cells))))
    if not rows:
        raise ValueError('input contains no schedule rows')
    return rows


def lint(row, source, now, connected):
    result = dict(source=source, name=str(row.get('name', '')), local='', utc='',
                  local_cron=str(row.get('cron', '')), utc_cron='', errors=[], warnings=[])
    errors, warnings = result['errors'], result['warnings']
    def value(key):
        val = row.get(key)
        return val.strip() if isinstance(val, str) else ''
    for key in ('name', 'schedule', 'timezone', 'end_date', 'notify', 'deliver'):
        if not value(key):
            errors.append(f'{key} must be a non-empty string')
    if value('notify').lower().replace('_', '-').replace(' ', '-') in (
            'only-on-change', 'on-change', 'change-only') and not value('liveness'):
        warnings.append('only-on-change without a separate liveness signal')
    try:
        name = value('timezone')
        if name != 'UTC' and '/' not in name:
            raise ValueError('timezone must be an IANA name, not an abbreviation or offset')
        zone = ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError):
        errors.append('timezone must be an available IANA name, not an abbreviation or offset')
        return result
    try:
        end = timestamp(value('end_date'), zone)
        if end <= now:
            errors.append('end_date must be in the future')
    except ValueError as exc:
        errors.append(f'end_date: {exc}')
        return result
    try:
        schedule = value('schedule')
        if schedule == 'event':
            if value('cron'):
                errors.append('event routines must not have cron')
            if not value('trigger') or value('trigger') not in connected:
                errors.append('event trigger must name a connected source in --connected-source')
            result['local'] = result['utc'] = 'event-driven (no scheduled fire)'
            return result
        if schedule == 'cron':
            parts, fields = cron_fields(value('cron'))
            instant = next_cron(parts, fields, zone, now, end)
            result['utc_cron'] = utc_projection(parts, fields, instant.astimezone(zone))
        else:
            if value('cron'):
                errors.append('one-time schedules must not have cron')
            instant = timestamp(value('at') if schedule == 'once' else schedule, zone)
            if instant <= now:
                errors.append('one-time schedule must be in the future')
            if instant > end:
                errors.append('one-time schedule is after end_date')
        result['local'] = instant.astimezone(zone).isoformat()
        result['utc'] = instant.isoformat()
    except (ValueError, OverflowError) as exc:
        errors.append(str(exc))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--now', help='offset-aware ISO timestamp for reproducible checks')
    parser.add_argument('--connected-source', action='append', default=[])
    args = parser.parse_args(argv)
    try:
        now = datetime.fromisoformat(args.now.replace('Z', '+00:00')) if args.now else datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError('--now requires an explicit offset')
        now = now.astimezone(UTC)
        rows = [lint(row, f'{args.file}:{number}', now, set(args.connected_source))
                for number, row in read_rows(args.file)]
        if not rows:
            raise ValueError('input contains no schedule rows')
    except (OSError, ValueError) as exc:
        rows = [dict(source=str(args.file), name='', local='', utc='', local_cron='',
                     utc_cron='', errors=[str(exc)], warnings=[])]
    errors = [f"{r['source']}: {e}" for r in rows for e in r['errors']]
    warnings = [f"{r['source']}: {w}" for r in rows for w in r['warnings']]
    if args.json:
        print(json.dumps(dict(rows=rows, errors=errors, warnings=warnings), indent=2))
    else:
        print('file/row | name | local | UTC | local cron | UTC cron (next-fire offset only)')
        for row in rows:
            print(' | '.join(row[k] for k in ('source', 'name', 'local', 'utc', 'local_cron', 'utc_cron')))
        print('Errors:\n' + ('\n'.join(errors) or '(none)'))
        print('Warnings:\n' + ('\n'.join(warnings) or '(none)'))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
