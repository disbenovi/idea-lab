---
id: "009"
slug: git-churn
title: git-churn — which files change most, and which change together
status: queued
priority: 9
created: 2026-11-04
language: python
---

# git-churn

## Problem

In a repository with years of history, the files that matter are not the
largest, they are the ones that keep changing. And the second-order fact is more
useful still: which files change *together*, because that coupling is usually an
undocumented dependency. Both are invisible in a file listing and tedious to
extract by hand.

## Shape

Single-file Python CLI, stdlib only, shelling out to `git` in the current
repository (read-only commands only).

- Walk `git log --numstat --no-merges -n N` (default 200 commits).
- Per file: commits touching it, distinct authors, added and removed lines,
  churn = added + removed, last changed date.
- Hotspots: files with the highest churn, and files changed in more than 60% of
  the commits that touched their directory.
- Coupling: pairs of files appearing in the same commit at least 5 times, with
  `co-change ratio = together / min(commits_a, commits_b)`, only when the ratio
  is at least 0.6. Report the top 10 pairs.
- Skip lockfiles, generated directories, and any path matching `--exclude`
  (comma-separated globs; defaults include `*.lock`, `dist/*`, `vendor/*`).
- `--json`, `--since DATE` passed through to `git log`.

Deterministic ordering: churn descending, then path.

## Acceptance check

```
python3 git_churn.py --json | python3 -c "import json,sys; d=json.load(sys.stdin); \
assert d['commits_analysed'] > 0; \
assert d['hotspots'][0]['path']; \
assert all(p['ratio'] >= 0.6 for p in d['pairs']); print('OK')"
```

Plus a test that builds a throwaway repository with known commits in a temp
directory, and asserts the top hotspot is the file changed in every one of them,
and that a file touched once never appears in `pairs`.

## Out of scope

Blame, authorship statistics, branch comparison, remote repositories, blame
graphs, anything that writes to the repository.

## Notes

Coupling is the interesting output; churn alone is just a bigger `du`. In the PR
body, state the threshold choices and why they are defaults rather than truths.

## History

| date | run | outcome |
|---|---|---|
| | | |
