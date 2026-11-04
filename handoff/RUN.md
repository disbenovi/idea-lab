# Run file — idea-lab

**This file is your entire instruction set for this run.** Read it fully
before acting. Nothing else is needed.

## State of play — this supersedes anything you remember

- **You have no network.** Do not clone, fetch, pull, push, install or
  call an API. Every connection is refused. A run that retries
  connections has failed.
- **This run file replaces the old pasted pack.** If you remember a large
  pack being pasted in, that workflow is retired: this file is delivered
  by path at a named commit. Do not ask for a pack.
- **You build in your own cloud computer and hand back a patch.** You do
  not push, you hold no credential, and you never ask for one.
- **One run, one idea, one patch.** The idea file and the delivery-log
  line go inside the same patch.
- Order of trust: this file, then `AGENTS.md` below, then the idea file.
  Nothing else — not a summary of a previous conversation.

repo: disbenovi/idea-lab (public)
branch: main
base: the commit that contains this file
generated: 2026-11-04 15:20 MST
queued: 003 routine-lint, 004 log-triage, 005 jsonl-profile, 006 dockerfile-audit, 007 sqlite-inspect, 008 secret-scan-lite, 009 git-churn
delivery-log: delivery-log/2026-W45.md (included below — append to it, do not rewrite it)

Deliver: the full `git format-patch <base>..HEAD` output, the acceptance
command you ran, and its real output.

## Files in this run

total bytes: 11852 across 5 files. Every block carries its
byte count and sha256 — write it verbatim, then check both. If the
original ends with a newline the block keeps it; if it did not, the block
adds one so the closing fence starts a line. Accept whichever candidate
matches the sha256, and if neither does, stop and say so instead of
guessing.

| path | bytes | sha256 |
| --- | --- | --- |
| `AGENTS.md` | 6008 | `5195db002e16bc5902ffacca5e8b9f39f4d1b603d3d9783dd4056b3f2b8a6f28` |
| `BACKLOG.md` | 1686 | `3764b2ca25a500474f714b12d8569929510495fbad5dce57ce5ea1d52dbf3854` |
| `ideas/_template.md` | 909 | `0902946c35cb7c2956efb5b64564de0e68c0815fcd6e7f664dfd8a5cc190163b` |
| `ideas/008-secret-scan-lite.md` | 2344 | `e9b3051d836c01f64b51e049b59c5908ba092ddcfccf1b1291d2a9bf53dd389f` |
| `delivery-log/2026-W45.md` | 905 | `83cdef5d32b2f1778847e7378f718f94639903fe3c534d824275bf7834d43d0a` |

## AGENTS.md

bytes: 6008  sha256: 5195db002e16bc5902ffacca5e8b9f39f4d1b603d3d9783dd4056b3f2b8a6f28

````markdown
# Agent contract — read fully before acting

You are the builder in residence for this repository. One run produces at most
one pull request. You optimise for a change a human can review in ten minutes,
not for the largest change you can make.

## 0. Preconditions

- **Repository allowlist: `disbenovi/idea-lab` and nothing else.** Other
  repositories on the same account are off limits — do not clone, list, read,
  fork or modify them, not even to look. If a task seems to need one, stop and
  report instead.
- **You have no outbound network.** Every connection is refused, including
  github.com and example.com. Do not attempt `git clone`, `fetch`, `push`,
  `pip`, `npm install` or any API call: they cannot succeed, and a run that
  spends its time retrying connections has failed. Local git still works —
  `init`, `branch`, `commit`, `format-patch` — and that is all you need.
- **You receive a run file, not a repository.** At the start of the run you are
  given `handoff/RUN.md` — read by path, or attached — which holds this
  contract, the backlog and the idea files, each with its byte count and sha256.
  Reconstruct only what you need and check it against those hashes. If a file
  you need is not in it, say which file and stop; do not reconstruct it from
  memory or invent its contents. An older workflow pasted the entire repository
  as a pack; that is retired.
- **Standard library only.** Nothing can be installed, so a dependency is not an
  option, however small. Python stdlib, or Node built-ins if the idea says so.
- **Where the work runs: your own cloud computer.** That is deliberate — you
  hold no git credential and must never acquire one, so this is the only place
  you build. Do not attach a computer for this.
- **You do not push. You hand over a patch.** When the work is done and the
  acceptance check passes, produce `git format-patch main..HEAD` output and
  report it. The owner applies it and opens the pull request. This is not a
  restriction to work around — a run that tries to push, or that asks for a
  credential, has failed the run.
- The GitHub plugin is for reading, searching and understanding code. It does not
  push, and it is not an execution environment.
- **Never ask the owner for a token, and never write one into a file, commit,
  log or PR body.** There is no credential path by design.
- Read `BACKLOG.md`, then the idea file you intend to pick. Do not work from
  memory of a previous run; the run file you were given is the truth for that
  run.

## 1. Picking work

1. Highest priority item with `status: queued`.
2. Skip anything marked `blocked-needs-host`, `parked` or `in-pr`.
3. If an idea needs the owner's machines, private network, private git host,
   credentials, payments or publishing, set `status: blocked-needs-host` with
   one line of reason and pick the next item. Do not try to reach around it.
4. If nothing is queued, say so in one line and stop. Do not invent work.

## 2. How to build

- Branch from `main`: `idea/<slug>`, e.g. `idea/002-pr-digest`.
- Never commit to `main`. Never force-push. Never rebase a branch someone else
  may have based work on.
- Keep the change under roughly 400 changed lines. If the idea is bigger, cut
  the smallest useful slice, ship that, and write the remainder back into the
  idea file as a follow-up.
- Language: prefer Python (stdlib first) or Node, whichever the idea file
  names. No build toolchain that needs more than 2 GB.
- There is no dependency installation: no network, so no virtualenv that needs
  to fetch, no `node_modules`. Standard library, or code you write yourself.
- There is no egress at all. If an idea turns out to need a network call, set
  `status: blocked-needs-host` with that reason and stop.
- No secrets in any file, fixture, test, log or PR body. Never print environment
  variables. Never read or copy `.env`, `~/.ssh`, `~/.config` or credential files.

## 3. Tests are the deliverable

Every PR must contain something that can be run and that fails when the code is
wrong: a test file, a fixture-driven check, or a script with a non-zero exit on
failure. State the exact command.

If a test is genuinely impossible, that fact belongs in the PR body and in the
idea file. "No tests" without a reason is a rejected PR.

- **Placement:** the module at the repository root, tests in `tests/`, docs in `docs/`. A test file anywhere else is not discovered by `unittest discover -s tests`, so it can pass review while never running.
## 4. The PR

Title: `idea: <slug> — <one line>`

Body, these headings only:

```
## Goal
one sentence, from the idea file

## What changed
files and behaviour, not a narrative

## How to verify
exact commands, in order, from a clean clone

## Tests
command run + result summary

## What I deliberately did not do
scope cuts, known gaps, follow-ups

## Risks and rollback
what could break, and how to revert
```

## 5. Records, always

- Update the idea file: `status: in-pr`, and add the date. The PR link is filled
  in by the owner after applying the patch — leave the field as
  `PR: (owner applies)`.
- Append exactly one line to `delivery-log/<YYYY-Www>.md`:
  `<idea id> — <one line> — pending owner apply — in-pr`

Both go in the patch, so they land in the same commit as the work. An idea that
shipped without a log line did not happen.

## 6. Stop conditions

Stop, leave the branch in place, and report — do not thrash:

- tests fail and cannot be fixed within this run → `status: blocked-tests`
- the work needs credentials, payments, publishing, or the owner's machine →
  `status: blocked-needs-host`
- the same idea has now failed twice → `status: parked`, do not retry
- anything that would merge, approve, release, delete or spend

## 7. Report

Ten lines maximum: idea id, branch, **the patch** (or where to download it),
the exact acceptance command and its real output, what is next, the one decision
the owner owes you. No preamble, no restating this contract.
````

## BACKLOG.md

bytes: 1686  sha256: 3764b2ca25a500474f714b12d8569929510495fbad5dce57ce5ea1d52dbf3854

```markdown
# Backlog

Highest priority `queued` item is picked each run. One item, one PR.
Statuses: `queued`, `in-pr`, `blocked-tests`, `blocked-needs-host`, `parked`, `shipped`.

| # | slug | priority | status | needs | one line |
|---|---|---|---|---|---|
| 001 | repo-brief | 1 | shipped | nothing | summarise any repo into a one-page brief from tree, sizes and README |
| 002 | pr-digest | 2 | shipped | nothing | turn a diff into a reviewer checklist with risk flags |
| 003 | routine-lint | 3 | queued | nothing | validate schedule tables for timezone and missing-field errors |
| 004 | log-triage | 4 | queued | nothing | collapse a noisy log into its few recurring templates, ranked |
| 005 | jsonl-profile | 5 | queued | nothing | derive a schema from a JSONL dump: keys, types, nulls, cardinality |
| 006 | dockerfile-audit | 6 | queued | nothing | lint a Dockerfile for the flaws that show up in every scan |
| 007 | sqlite-inspect | 7 | queued | nothing | describe an unknown SQLite database without writing to it |
| 008 | secret-scan-lite | 8 | queued | nothing | find secret-shaped strings and never print the value |
| 009 | git-churn | 9 | queued | nothing | which files change most, and which change together |

## Adding an idea

Copy `ideas/_template.md`, give it the next number, add a row here. The idea
file must contain an acceptance check that a machine can run. If you cannot
describe how to tell whether it worked, it is not ready to be queued.

## Not accepted here

Anything that needs the home network, the private git host, the owner's
machines, credentials, a paid account, or publishing on the owner's behalf.
Those get `blocked-needs-host` and wait for a human.
```

## ideas/_template.md

bytes: 909  sha256: 0902946c35cb7c2956efb5b64564de0e68c0815fcd6e7f664dfd8a5cc190163b

````markdown
---
id: "000"
slug: template
title: Idea template
status: queued
priority: 99
created: 2026-11-04
language: python
---

# <title>

## Problem

One paragraph. Who has this problem, what they do today, why that is annoying.
If the answer is "nobody, I just think it is neat", say so — that is allowed,
but it sets the bar: this must be small.

## Shape

What the thing is: a CLI, a single script, a library, a static page. Prefer the
smallest shape that solves the problem.

## Acceptance check

The exact command that must exit 0, and what its output must contain. This is
the definition of done and it is what the PR must show.

```
$ <command>
<expected output shape>
```

## Out of scope

Bullet list of things that would be tempting and are deliberately excluded.

## Notes

Anything learned during a run goes here, including why a run failed.

## History

| date | run | outcome |
|---|---|---|
| | | |
````

## ideas/008-secret-scan-lite.md

bytes: 2344  sha256: e9b3051d836c01f64b51e049b59c5908ba092ddcfccf1b1291d2a9bf53dd389f

````markdown
---
id: "008"
slug: secret-scan-lite
title: secret-scan-lite — find secret-shaped strings, never print them
status: queued
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
| | | |
````

## delivery-log/2026-W45.md

bytes: 905  sha256: 83cdef5d32b2f1778847e7378f718f94639903fe3c534d824275bf7834d43d0a

```markdown
001 — deterministic stdlib repository brief with regression tests — https://github.com/disbenovi/idea-lab/pull/1 — shipped
002 — pr-digest: offline diff risks and reviewer checklist — https://github.com/disbenovi/idea-lab/pull/2 — shipped
003 — routine-lint: offline schedule validation and local/UTC previews — https://github.com/disbenovi/idea-lab/pull/3 — shipped
004 — log-triage: deterministic offline template ranking with samples and tests — https://github.com/disbenovi/idea-lab/pull/4 — shipped
005 — jsonl-profile: bounded cardinality and two-level schema summaries with tests — https://github.com/disbenovi/idea-lab/pull/5 — shipped
006 — dockerfile-audit: offline Dockerfile checks with fixtures and regression tests — pending owner apply — in-pr
007 — sqlite-inspect: read-only metadata and counts with regression tests — pending owner apply — in-pr
```

---

total bytes: 11852
