---
id: "006"
slug: dockerfile-audit
title: dockerfile-audit — lint the flaws scanners report later
status: queued
priority: 6
created: 2026-11-04
language: python
---

# dockerfile-audit

## Problem

The same Dockerfile mistakes recur across every stack: floating base tags, root
user, apt caches left in the layer, `curl | sh`, secrets in `ARG`, and a cache
busting `COPY . .` before dependencies install. A scanner reports them weeks
later as image findings, long after the author has context. A ten-second check
at review time is cheaper than a remediation batch.

## Shape

Single-file Python CLI, stdlib only. Reads a Dockerfile path (default
`./Dockerfile`), handles multi-stage builds and line continuations.

Rules, each with a stable id, severity, line number and one line of why:

- `DF001` high — `FROM` with no tag, or tag `latest`
- `DF002` high — final stage has no `USER`, or `USER root`
- `DF003` medium — `apt-get install` without `--no-install-recommends`
- `DF004` medium — `apt-get install` without cleanup of
  `/var/lib/apt/lists` in the same `RUN`
- `DF005` high — `curl` or `wget` piped into a shell
- `DF006` medium — `ADD` used for a local path where `COPY` would do
- `DF007` high — `ARG` or `ENV` whose name looks like a secret; report the name
  only, never the value
- `DF008` medium — `COPY . .` (or `COPY . `) before a dependency-install step
- `DF009` low — no `HEALTHCHECK` anywhere
- `DF010` low — `RUN` with `sudo`

Exit 1 if any high finding, else 0. `--json` gives `{findings:[{rule,severity,
line,message}], counts:{high,medium,low}}`.

## Acceptance check

```
python3 dockerfile_audit.py --json fixtures/bad.Dockerfile \
  | python3 -c "import json,sys; d=json.load(sys.stdin); r={f['rule'] for f in d['findings']}; \
assert {'DF001','DF002','DF005','DF007'} <= r, r; print('OK')"
```

Plus a test that `fixtures/good.Dockerfile` produces zero findings and exit 0,
and that a continuation line (`RUN apt-get update \\` newline ` && apt-get
install`) is parsed as one instruction.

## Out of scope

Building the image, querying a registry, parsing `.dockerignore` contents, SBOM,
severity scoring against CVEs.

## Notes

A linter that cannot be fooled is better than one that catches everything: when
parsing is ambiguous, prefer missing a finding over reporting a false one, and
say so in the PR body.

## History

| date | run | outcome |
|---|---|---|
| | | |
