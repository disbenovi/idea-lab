# Backlog

Highest priority `queued` item is picked each run. One item, one PR.
Statuses: `queued`, `in-pr`, `blocked-tests`, `blocked-needs-host`, `parked`, `shipped`.

| # | slug | priority | status | needs | one line |
|---|---|---|---|---|---|
| 001 | repo-brief | 1 | shipped | nothing | summarise any repo into a one-page brief from tree, sizes and README |
| 002 | pr-digest | 2 | shipped | nothing | turn a diff into a reviewer checklist with risk flags |
| 003 | routine-lint | 3 | shipped | nothing | validate schedule tables for timezone and missing-field errors |
| 004 | log-triage | 4 | shipped | nothing | collapse a noisy log into its few recurring templates, ranked |
| 005 | jsonl-profile | 5 | queued | nothing | derive a schema from a JSONL dump: keys, types, nulls, cardinality |
| 006 | dockerfile-audit | 6 | shipped | nothing | lint a Dockerfile for the flaws that show up in every scan |
| 007 | sqlite-inspect | 7 | shipped | nothing | describe an unknown SQLite database without writing to it |
| 008 | secret-scan-lite | 8 | shipped | nothing | find secret-shaped strings and never print the value |
| 009 | git-churn | 9 | shipped | nothing | which files change most, and which change together |

## Adding an idea

Copy `ideas/_template.md`, give it the next number, add a row here. The idea
file must contain an acceptance check that a machine can run. If you cannot
describe how to tell whether it worked, it is not ready to be queued.

## Not accepted here

Anything that needs the home network, the private git host, the owner's
machines, credentials, a paid account, or publishing on the owner's behalf.
Those get `blocked-needs-host` and wait for a human.
