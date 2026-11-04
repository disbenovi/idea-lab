---
id: "001"
slug: repo-brief
title: repo-brief — repo to one page
status: in-pr
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

Date: 2026-11-04
PR: (owner applies)

Implemented as `repo_brief.py`; run `python3 repo_brief.py PATH` or add `--json`.
Tests: `python3 -B -m unittest discover -s tests -v` (6 regression tests).
Both output modes carry the same fields. Language ranking is file count, then
bytes, then name; unknown extensions are `Other`. Paths are relative and sorted.
No network, dependency installation, or repository writes are required.

Scope cuts: entry points and frameworks are filename/config heuristics, not code
execution or import analysis. Test counts exclude Python package/config helpers.
Git metadata, common dependency/cache dirs, symlinks and common secret filenames
are skipped. This is not a secret detector. Only root README, package.json and
Makefile contents are read, capped at 65,536 characters each with warnings.
README parsing supports simple Markdown/setext headings and plain paragraphs,
not full Markdown rendering. Makefile targets are static, not expanded.
Follow-ups: richer framework detection and Markdown parsing if needed.
BACKLOG.md is unchanged under the explicit file allowlist; the owner can reconcile
its queued row when applying the patch.

## History

| date | run | outcome |
|---|---|---|
| 2026-11-04 | 1 | Local patch prepared; tests pass; pending owner apply. |
