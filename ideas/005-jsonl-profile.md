---
id: "005"
slug: jsonl-profile
title: jsonl-profile — derive a schema from a JSONL dump
status: queued
priority: 5
created: 2026-11-04
language: python
---

# jsonl-profile

## Problem

An event dump arrives as JSON Lines with no schema and no docs. Before querying
it you need to know which keys exist, how often they are missing, whether a key
is always null, which keys are identifiers with tens of thousands of distinct
values, and which are small enumerations worth grouping by. Guessing at that
costs a round of failed queries every time.

## Shape

Single-file Python CLI, stdlib only. Reads a `.jsonl` file or stdin.

Per key, report:

- `present` — lines where the key exists, and `missing` = total - present
- `types` — the set of JSON types seen (object, array, string, number,
  boolean, null), sorted
- `nulls` — count where the value is `null`
- `distinct` — distinct value count, computed exactly up to `--max-card`
  (default 1000) and reported as `>=1000` beyond that, so memory stays bounded
- for numbers: `min`, `max`, and whether every value is integral
- for strings with `distinct <= 20`: the values themselves, sorted, with counts
- `example` — one representative value, truncated to 80 chars

Also: total lines, malformed lines skipped and counted, and duplicate-key
detection is out of scope. Sorted by key. `--json`.

## Acceptance check

```
python3 jsonl_profile.py --json fixtures/events.jsonl \
  | python3 -c "import json,sys; d=json.load(sys.stdin); k=d['keys']; \
assert d['lines']==10; \
assert k['user_id']['distinct']==3; \
assert k['note']['nulls']==4; \
assert k['status']['values']; print('OK')"
```

Plus a test that a malformed line increments `malformed` and does not abort the
run, and that a key present in every line reports `missing: 0`.

## Out of scope

JSON Schema output, type coercion, nested path flattening beyond one level,
streaming gigabytes, network.

## Notes

Nested objects: report first-level keys only, and name the nested key as
`parent.child` up to two levels, then stop. Depth without bound is how these
tools become unusable.

## History

| date | run | outcome |
|---|---|---|
| | | |
