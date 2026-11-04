---
id: "008"
slug: secret-scan-lite
title: secret-scan-lite — find secret-shaped strings, never print them
status: in-pr
priority: 8
created: 2026-11-04
language: python
---

# secret-scan-lite

## Problem

Before a repository goes public, or a directory gets pasted into a chat, there
should be one cheap check for credentials. Most scanners solve it by printing
the secret they found, which puts it in a terminal, a scrollback, a log and
often a ticket — the finding becomes the leak. The tool has to be useful without
ever echoing a value.

## Shape

Single-file Python CLI, stdlib only. Walks a directory (default `.`).

- Skip `.git`, `node_modules`, `__pycache__`, binaries, and files over 1 MB.
- Match shapes, each with a stable rule id:
  - `SL001` AWS access key id (`AKIA` + 16 upper alnum)
  - `SL002` GitHub token (`ghp_`, `gho_`, `ghs_`, `ghu_`, `github_pat_`)
  - `SL003` OpenAI-style key (`sk-` + 20 or more)
  - `SL004` private key header (`-----BEGIN ... PRIVATE KEY-----`)
  - `SL005` JWT (three base64url segments)
  - `SL006` Slack token (`xox[abpos]-`)
  - `SL007` assignment to a key-shaped name (`password`, `secret`, `token`,
    `api_key`, `apikey`) with a quoted value of 12+ chars
- Output one line per finding: `path:line  RULE  shape`, where `shape` is the
  first three and last two characters with the middle replaced by `…` and the
  total length. **Never the value, in any mode, including `--json`.**
- Exit 1 if anything is found, 0 if clean.
- `--json`, `--allowlist FILE` (one path glob per line, for known-safe fixtures
  and documentation examples).

## Acceptance check

```
python3 secret_scan_lite.py --json fixtures/leaky/ > out.json; code=$?; \
python3 -c "import json; d=json.load(open('out.json')); \
assert len(d['findings'])==4, len(d['findings']); \
assert not any('AKIAFAKE' in json.dumps(d) for _ in [0]); print('OK')"; \
[ "$code" = "1" ] && echo EXIT1
```

Plus a test asserting every planted value appears nowhere in stdout, and that a
clean fixture exits 0 with an empty finding list.

## Out of scope

Entropy scoring, git history, remote scans, auto-rotation, anything that fixes
what it finds.

## Notes

The redaction rule is the whole idea. If a test can be written that catches the
tool printing a value, write it.

## History

| date | run | outcome |
|---|---|---|
| 2026-11-04 | 008 | Built and verified offline; pending owner apply. |

PR: (owner applies)

Implemented all seven rules, redacted text/JSON, bounded UTF-8 scanning and
allowlists. Heuristic thresholds and limitations are in docs/secret-scan-lite.md.
