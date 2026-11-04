# idea-lab

An always-on agent's workshop. One idea in, one pull request out, per run.

This repo is the **durable state** of a dot (ChatGPT agent) that builds small
tools in its own cloud computer. The dot has no always-on process: it wakes on a
schedule, reads this repo, ships one change, records it, sleeps. Everything that
must survive lives here, in git — never only in the dot's own machine, which
nothing backs up.

## The loop

```
BACKLOG.md  ──pick──▶  branch idea/<slug>  ──▶  PR  ──▶  human review  ──▶  merge
     ▲                    │                                              │
     └──── status update ─┴──────────── delivery-log/<week>.md ◀─────────┘
```

- `BACKLOG.md` — the queue. Highest-priority `queued` item wins.
- `ideas/` — one file per idea: the spec, the acceptance check, the history.
- `delivery-log/` — one file per ISO week: what actually shipped, what stalled.
- `AGENTS.md` — the contract the agent reads before it touches anything.

## Why git and not the agent's disk

The dot's cloud computer keeps state between periods of use, but there is no
backup, no export and no second copy. A repo is the only place where work is
both durable and reviewable. If it is not in a commit, it does not exist.

## Status values

| status | meaning |
|---|---|
| `queued` | ready to be picked |
| `in-pr` | branch pushed, PR open, waiting on a human |
| `blocked-tests` | tests fail, agent could not fix in one run |
| `blocked-needs-host` | needs the owner's machines, private network or credentials |
| `parked` | two failed attempts, do not retry automatically |
| `shipped` | merged |

## Human gates (do not remove)

The agent opens pull requests. It never merges, never approves, never pushes to
`main`, never publishes, never pays. Those are the owner's decisions and they
stay that way regardless of what the agent's own rules say.
