---
id: "003"
slug: routine-lint
title: routine-lint — catch schedule mistakes before they fire
status: shipped
priority: 3
created: 2026-11-04
language: python
---

# routine-lint

## Problem

A scheduled task that is wrong is worse than one that does not exist, because it
looks fine until it silently never runs. The failure modes repeat: cron in the
wrong timezone, a time already in the past, a missing delivery destination, a
missing end date, an event routine with no event source. All of them are
mechanically detectable.

## Shape

Single-file Python CLI, stdlib only. Input: a JSON or YAML-free markdown table
matching the routine shape used by the owner:

```
name | schedule | cron | timezone | end_date | notify | deliver
```

Checks, each producing file/row + reason:

- `cron` has 5 fields, each in range; wildcards and lists accepted
- `timezone` is an IANA name, or the row is rejected for ambiguous offset
- the UTC equivalent is computed and printed next to the local equivalent, so a
  human can see the conversion rather than trust it
- the next fire time is in the future; a one-time schedule in the past is an error
- `end_date` present and in the future
- `deliver` non-empty
- `notify` present; warns when `notify` means "only on change" without a
  separate liveness signal, because silence then cannot be distinguished from
  failure
- event routines: no `cron`, and `trigger` names a source that is actually
  connected — otherwise error, since connecting alone creates no monitoring

Output: table of rows, then errors, then warnings, then exit 1 if any error.
`--json` for the same.

## Acceptance check

```
$ python3 routine_lint.py fixtures/bad.md; echo "exit=$?"
exit=1
$ python3 routine_lint.py fixtures/good.md; echo "exit=$?"
exit=0
```

Fixtures must include: a 4-field cron (reject), a timezone-abbreviation
`PST` (reject), a past one-time schedule (reject), a silent-notification row
(warn), and a row whose `0 16 * * 5` converts to `0 0 * * 6` UTC (must print both).

## Out of scope

Actually creating schedules, reading any provider API, YAML dependency.

## Notes

The timezone conversion is the point. It is the check that was missed by hand.

PR: (owner applies)

2026-11-04: Added the stdlib CLI, Markdown/JSON fixtures, and regression tests.
Verify: `python3 -m unittest -v tests.test_routine_lint`, then the acceptance
commands above. UTC cron projections use only the next fire's offset; see
`docs/routine-lint.md` for DST behavior, input schema, and the eight-year bound.
Event source connectivity is a caller-supplied offline inventory, not an API
check. Follow-up: provider-verified connectivity requires a separately
host-enabled run. No schedules or provider connections were created.

## History

| date | run | outcome |
|---|---|---|
| 2026-11-04 | 003 | in-pr; acceptance passes, pending owner apply |
