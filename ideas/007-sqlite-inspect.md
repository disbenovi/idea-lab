---
id: "007"
slug: sqlite-inspect
title: sqlite-inspect — describe an unknown database without touching it
status: queued
priority: 7
created: 2026-11-06
language: python
---

# sqlite-inspect

## Problem

An unfamiliar SQLite file — from an app's data directory, a backup, a snapshot —
needs a dozen ad-hoc queries before you know what you are looking at: which
tables matter, which are empty, what the indexes are, whether there are foreign
keys, and whether a column named `email` holds something you should not print.
Doing that by hand is slow and the first query is often the one that mutates.

## Shape

Single-file Python CLI, stdlib only. Opens the database read-only by URI
(`file:{path}?mode=ro`) and refuses to proceed if the connection is not
read-only.

Report:

- file size, page size, page count, journal mode, `user_version`
- tables: name, row count, column names with declared types, `WITHOUT ROWID`
- views, triggers, indexes (with the columns each covers), foreign keys
- tables with no primary key — these break upserts
- tables with zero rows — usually schema left behind by a removed feature
- columns whose name matches a PII shape (`email`, `phone`, `address`, `name`,
  `token`, `secret`, `password`, `ssn`, `dob`) — **names and counts only, never
  values**
- largest five tables by row count

`--json`. No DDL, no `VACUUM`, no writes.

## Acceptance check

```
python3 sqlite_inspect.py --json fixtures/sample.db \
  | python3 -c "import json,sys; d=json.load(sys.stdin); t={x['name']:x for x in d['tables']}; \
assert t['users']['rows']==3; \
assert t['empty_table']['rows']==0; \
assert any(c['name']=='email' for c in t['users']['columns']); print('OK')"
```

Plus a test asserting the file's sha256 is unchanged before and after a run, and
that a table with no primary key is flagged.

## Out of scope

Query execution, migrations, attaching other databases, `EXPLAIN` advice,
encrypted databases.

## Notes

Read-only is the deliverable, not a nicety: this tool will be pointed at other
people's data directories. Make the read-only assertion the first thing that can
fail.

## History

| date | run | outcome |
|---|---|---|
| | | |
