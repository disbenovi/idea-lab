---
id: "002"
slug: pr-digest
title: pr-digest — diff to reviewer checklist
status: queued
priority: 2
created: 2026-11-04
language: python
---

# pr-digest

## Problem

Reviewing a pull request starts with diff archaeology: which files, how much
churn, what kind of change, which parts carry risk. That survey is mechanical,
it is repeated for every PR, and skipping it is how a risky line slips through.

## Shape

Single-file Python CLI, stdlib only. Reads a unified diff on stdin (or
`--file`), prints:

- files changed, with added/removed line counts, sorted by churn
- change class per file: `tests`, `docs`, `config`, `migration`, `source`, `other`
- risk flags, each with the line that triggered it:
  - auth / session / token handling
  - SQL string built by concatenation
  - `eval`, `exec`, `pickle.loads`, `subprocess` with `shell=True`
  - broad `except:` or bare `except Exception: pass`
  - deleted tests
  - a lockfile changed without its manifest, or vice versa
  - `TODO`/`FIXME` added
  - secret-shaped strings (long hex/base64) — report location only, **never the value**
- a reviewer checklist: 3–7 items derived from what was found, not generic advice
- `--json`

No network. Never prints a matched secret, only file and line.

## Acceptance check

```
$ python3 pr_digest.py --file fixtures/risky.diff | grep -q 'shell=True' && echo OK
OK
```

Plus a fixture test asserting that a secret-shaped string appears nowhere in the
output except as `file:line`, and a clean-diff case producing an empty risk list.

## Out of scope

Fetching PRs from an API, posting comments, scoring with a model, HTML.

## Notes

## History

| date | run | outcome |
|---|---|---|
| | | |
