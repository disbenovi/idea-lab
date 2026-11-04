---
id: "001"
slug: repo-brief
title: repo-brief — repo to one page
status: queued
priority: 1
created: 2026-11-04
language: python
---

# repo-brief

## Problem

Opening an unfamiliar repository means reading a tree, guessing what matters
from file names, and reading a README that may be stale. Ten minutes per repo,
every time, and the guesswork is the same each time.

## Shape

Single-file Python CLI, stdlib only. Takes a path, prints a brief:

- language mix by file count and bytes, top 5
- entry points: `main`, `__main__`, `bin/`, `cli`, `package.json` bin, `Makefile` targets
- largest 10 files by byte size
- test layout: detected test dirs, test framework guess, count of test files
- dependency files present (`requirements.txt`, `pyproject.toml`, `package.json`, `go.mod`)
- README first heading + first non-empty paragraph, or `absent`
- a `--json` flag emitting the same data

No network. No writes. Deterministic ordering so output can be diffed.

## Acceptance check

```
$ python3 repo_brief.py --json <this repo> | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['test_files'] >= 1; assert d['languages']; print('OK')"
OK
```

And: running it on a directory with no README must print `absent`, not crash.

## Out of scope

Git history, churn metrics, dependency vulnerability scanning, anything that
needs `pip install`, HTML output.

## Notes

## History

| date | run | outcome |
|---|---|---|
| | | |
