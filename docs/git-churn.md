# git-churn

Run `python3 git_churn.py` from the repository to inspect. Python 3.11+ and local
Git are the only requirements. Nothing is fetched, installed or written by the
CLI. Use `--json`, `-n N` / `--commits N` (default 200), `--since DATE`, and
`--exclude 'glob,glob'`. The date is passed to Git unchanged.

JSON contains `commits_analysed`, `hotspots` and `pairs`. Every eligible file is
listed in hotspots, sorted by churn descending then path. Each row reports
commits, distinct author email count, added/removed lines, churn, latest
committer date, directory_ratio and directory_hotspot. Author identities are
not printed. Directory ratios count commits touching the file divided by
commits touching any eligible file in its immediate parent directory; root
files share the root directory. Excluded-only and empty commits still count
in commits_analysed. Merge commits do not. History is reachable from HEAD.

Directory hotspots require strictly more than 60%. Pairs require at least
five shared commits and together / min(file commit counts) >= 0.6. Top ten
pairs sort by shared commits descending, ratio descending, then path pair.
These defaults favor repeated coupling over coincidence, but are heuristics,
not evidence of causation or universal maintenance thresholds.

Default exclusions cover *.lock, package-lock.json, npm-shrinkwrap.json,
yarn.lock, pnpm-lock.yaml, and dist/, vendor/, build/, node_modules/ and
__pycache__/ at any depth. Custom comma-separated globs add to the defaults.
Patterns use case-sensitive fnmatch (including '*' matching '/').

Renames are intentionally treated as a deletion and addition, without linking
identities across names. Binary files count as touched with zero measurable
line churn. Tab/newline/non-UTF-8 paths are preserved and JSON-escaped. The text
report escapes paths too. No commits matching a filter yields empty lists;
an unborn or non-repository directory exits nonzero with a diagnostic.

## Verification

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`

Tests create local throwaway repositories in the system temporary directory.
They leave fixtures for inspection rather than deleting data. Tests cover
known hotspots and pairs, filters, binary files, odd paths, rename accounting,
empty commits, thresholds, stable sorting and unchanged repository state.

```sh
python3 git_churn.py --json | python3 -c "import json,sys; d=json.load(sys.stdin); \
assert d['commits_analysed'] > 0; \
assert d['hotspots'][0]['path']; \
assert all(p['ratio'] >= 0.6 for p in d['pairs']); print('OK')"
```

Pair enumeration is quadratic in the number of eligible files in each commit;
use -n and --exclude to narrow unusually broad histories. No history cache,
rename tracking, configurable thresholds or remote access is included.
