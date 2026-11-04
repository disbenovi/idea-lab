# dockerfile-audit

Run `python3 dockerfile_audit.py [--json] [Dockerfile]` with Python 3.9+.
The default input is `./Dockerfile`. No Docker daemon, registry, network or
third-party packages are used. Exit codes: 1 for any high finding, 0 otherwise,
2 for unreadable/non-UTF-8 input or argument errors. JSON includes findings
(rule, severity, physical start line, message) and high/medium/low counts.
Messages never include ARG/ENV values. Input is never executed.

Checks DF001–DF010 correspond to the idea specification. Final USER overrides
previous USER settings; an earlier named stage passes its USER to derived
stages. External base-image users cannot be resolved offline, so an explicit
non-root USER is required. Numeric UID 0 and root groups are handled by UID.
A HEALTHCHECK instruction anywhere satisfies DF009, including NONE, per the
literal instruction-presence rule. COPY ordering checks are stage-local.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 dockerfile_audit.py --json fixtures/bad.Dockerfile \
  | python3 -c "import json,sys; d=json.load(sys.stdin); r={f['rule'] for f in d['findings']}; \
assert {'DF001','DF002','DF005','DF007'} <= r, r; print('OK')"
```

The bad fixture intentionally exits 1; the acceptance pipeline's final process
exits 0 and prints OK. Tests independently assert the CLI exit codes, that the
good fixture has zero findings, and continuation source-line attribution.

## Limits

This is a small heuristic linter, not a Dockerfile or shell validator. It skips
heredoc instructions/bodies, quoted shell operators, unresolved FROM variables
and malformed token lists.
It does not expand variables, inspect remote metadata, resolve filesystem
archives, or evaluate shell conditionals. ADD archive suffixes/URLs are exempt;
COPY cache checks target exactly `COPY . .` (including JSON form). Dependency
checks recognize direct apt-get, pip, npm, yarn, pnpm, bundle and poetry commands.
Nested shells, wrappers (including sudo), substitutions and complex shell syntax
may be missed. Cleanup checks require a recursive rm after installation in the
same RUN but do not prove that conditional paths execute it. Treat findings as
review prompts, not proof of image security. Follow-up: richer shell parsing and
Dockerfile validation, without changing the offline/std-library constraint.
