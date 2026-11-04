# Delivery log

One file per ISO week: `<YYYY-Www>.md`. One line per run, appended by the agent.

Format:

```
<idea id> — <one line> — <PR link or "no PR"> — <status>
```

Rules:

- append, never rewrite history
- a run with no output still gets a line: `— no work — nothing queued`
- absence of a line is a signal: it means the run did not happen

## Weekly review (Friday)

The dot reads the last two weeks of this directory and answers, in one screen:

1. what shipped, with links
2. what is open and who it waits on
3. what stalled — idea id, days since last touch, the exact next action
4. the one decision the owner owes

If nothing happened, say so in one line. An empty week is information; a silent
week is a fault.
