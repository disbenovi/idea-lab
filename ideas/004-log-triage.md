---
id: "004"
slug: log-triage
title: log-triage — collapse a noisy log into its recurring templates
status: queued
priority: 4
created: 2026-11-06
language: python
---

# log-triage

## Problem

A log with ten thousand lines usually contains six distinct things, one of them
repeated nine thousand times. Reading top to bottom spends attention on
repetition and misses the rare line that explains the incident. The shape of the
log — how many distinct behaviours, which is dominant, what appeared first and
last — is what an operator wants before reading any single line.

## Shape

Single-file Python CLI, stdlib only. Reads one file or stdin.

- Normalise each line into a template by replacing the variable parts with
  placeholders: ISO timestamps, epoch numbers, UUIDs, hex ids of 8+ chars, IPv4
  with optional port, long numbers, quoted strings over 40 chars.
- Group identical templates, count them, keep the first and last raw line seen
  for each, and one sample at full length.
- Print ranked by count descending, ties broken by template text so output is
  stable and diffable.
- `--top N` (default 20), `--json`, `--samples N` (raw examples per template,
  default 1).
- If lines carry ISO-8601 timestamps, report per-template first and last
  timestamp; skip quietly when they do not.

Deterministic: the same input produces byte-identical output.

## Acceptance check

```
python3 log_triage.py --json fixtures/noisy.log \
  | python3 -c "import json,sys; d=json.load(sys.stdin); \
assert len(d['templates'])==3, len(d['templates']); \
assert d['templates'][0]['count']==4; print('OK')"
```

Plus a test asserting that two runs on the same fixture are byte-identical, and
that a log with no repeated lines keeps every line distinct.

## Out of scope

Live tailing, regex dialects, ML clustering, cross-file correlation, colour.

## Notes

Ranking by count is the point: the dominant template is usually the symptom and
the rare one is usually the cause. Say that in the output header, one line.

## History

| date | run | outcome |
|---|---|---|
| | | |
