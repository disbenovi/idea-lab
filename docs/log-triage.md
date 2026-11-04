# log-triage

Run with Python 3.8+; no dependencies or network access.

```
python3 log_triage.py fixtures/noisy.log
python3 log_triage.py --json --top 10 --samples 2 fixtures/noisy.log
cat fixtures/noisy.log | python3 log_triage.py --json
python3 -m unittest discover -s tests -v
```

The dominant template is usually the symptom; the rare one is usually the cause.
Templates rank by count descending, then template text ascending. Text mode has
that reminder as its header; JSON mode emits only JSON, without a text header.
Input is UTF-8; line endings are removed, but other whitespace is preserved.
Empty lines count. Missing files and invalid UTF-8 fail with exit code 2.

## Normalization and output

- Calendar-valid ISO date-times with seconds, optional fractions and timezone
  normalize to `<timestamp>` (T/t or space separators, Z/z or numeric offsets).
- UUIDs normalize to `<uuid>`, valid IPv4 addresses with optional valid ports
  to `<ipv4>`, and hexadecimal IDs of at least eight digits to `<hex>`.
- 10/13-digit integers, optionally fractional, normalize to `<epoch>`.
  Other numbers with five or more digits normalize to `<number>`.
- Single/double-quoted strings with more than 40 characters inside the quotes
  normalize to `<quoted>`. Escapes count as source characters. Short quotes
  remain, while variable tokens inside them still normalize.

JSON contains `total_lines`, `total_templates` (before truncation) and `templates`.
Each group has `template`, `count`, `first_line`, `last_line`, `sample` (the first
raw line at full length), and `samples` (the first N occurrences, duplicates
included). Optional `first_timestamp` and `last_timestamp` preserve original
ISO spelling and encounter order, not chronological minimum/maximum. Multiple
timestamps on a line are considered left to right. No timestamp fields appear
for a group without valid ISO timestamps.

`--top` defaults to 20 and `--samples` to 1; both accept nonnegative integers.
Zero top emits no groups; zero samples emits an empty samples list, while the
required first/last/sample fields remain. Stdin is selected by omitting the
file or using `-`. The same input and options produce identical output bytes.

## Deliberate limits

This is heuristic grouping, not secret redaction. Raw examples may contain
sensitive log content; do not publish output without reviewing it. Numeric IDs
can look like epochs; genuinely different messages differing only in a
normalized token will collapse. IPv6, multiline events, ISO week/ordinal dates,
live tailing, ML, cross-file correlation and custom regexes are not supported.
Memory scales with distinct templates, retained examples and their line lengths.
