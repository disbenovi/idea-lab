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
