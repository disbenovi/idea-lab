# secret-scan-lite

Python 3.8+ standard library only. Run only against directories you are authorized
 to inspect. This tool makes no network requests and does not validate tokens.

```
python3 secret_scan_lite.py path/to/directory
python3 secret_scan_lite.py --json --allowlist allow.txt path/to/directory
python3 -m unittest discover -s tests -v
```

Exit status: 0 clean, 1 findings, 2 incomplete scan or invalid arguments. JSON is
an object with `findings`; incomplete scans add `error` and discard partial
results. Errors never echo paths or exception messages. Text findings are
`relative/path:line  SL001  AKI…00 (20)`. JSON contains only path, line, rule and
shape. Paths containing detected values or recognizable shapes are redacted.
Line numbers start at 1. Multiple rules can flag the same value independently.

Allowlist files contain root-relative POSIX path globs, one per line. Blank
lines and lines starting with `#` are ignored. Matching is case-sensitive;
Python fnmatch wildcards can cross `/`. Example: `fixtures/*` skips all fixtures.
Keep allowlists outside the scan root, or explicitly exclude their own path.

Skips `.git`, `node_modules`, `__pycache__`, symlinks, nonregular files, files
larger than 1,000,000 bytes, NUL-containing files and non-UTF-8 files. Enumeration
is deterministic. POSIX no-follow protects file opens from symlink replacement;
this is not a sandbox for adversarial concurrent filesystem changes.

Rules are heuristics: SL001 requires exactly 16 uppercase letters/digits after
AKIA; SL002 recognizes the five specified GitHub prefixes plus one or more alphanumeric
or underscore characters; SL003 recognizes sk- plus 20+ letters/digits/_/-;
SL004 recognizes uppercase private-key headers; SL005 requires three base64url
nonempty segments; SL006 recognizes xox[abpos]- plus
one or more letters/digits/hyphens; SL007 matches the five exact names, case-insensitively,
with = or : and a single-line, single- or double-quoted value of 12+ characters.

False positives and false negatives are expected. Escaped quotes, multiline assignments, arbitrary binary encodings, git history and
entropy-based detection are outside this slice. A clean result is not proof
that a directory contains no secrets. Redaction intentionally reveals first
three/last two characters and length; do not publish findings carelessly.
All bundled fixtures are fictional and inert, never issued credentials.
