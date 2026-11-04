# jsonl-profile

Python 3, standard library only. No installation or network access required.

```
python3 jsonl_profile.py fixtures/events.jsonl
python3 jsonl_profile.py --json --max-card 1000 fixtures/events.jsonl
cat fixtures/events.jsonl | python3 jsonl_profile.py --json -
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

`lines` counts physical input lines, including blank, malformed and non-object
lines. Those invalid records increment `malformed` without aborting. `missing`
is `lines - present`, so invalid records count as missing for every known key.
Empty input reports zero lines and no keys. Files must be UTF-8; I/O/encoding
errors and invalid CLI arguments exit 2. Nonstandard NaN/Infinity constants,
out-of-range floating point numbers and excessively deep JSON are malformed.

Keys and types are sorted. Top-level object fields and their immediate child
fields are reported, including object-valued parents. Arrays are not flattened.
Dots and backslashes in literal key names are backslash-escaped: `a.b` means a
nested path, whereas `a\.b` means a literal top-level key. Empty keys are allowed.

`distinct` is exact through `--max-card` (default 1000); after another distinct
value appears it becomes `>=1000` (or the selected cap). At most that many
canonical values per field are retained. JSON types remain distinct (true is
not 1), integral numbers such as 1 and 1.0 are equivalent, and object member
order does not matter. Python's normal floating point precision applies.

`min`, `max` and `integral` describe only numeric observations, excluding booleans.
`values` is a sorted string-to-count map when total distinct cardinality is known
and at most 20. Mixed fields count only their string values in that map.
`example` is the first value rendered as JSON, truncated to at most 80 characters
with `...`; it is a display string, not necessarily parseable JSON after truncation.

Memory is bounded by cardinality per key, not total file size: arbitrarily many
keys, very long values or a huge single line can still require substantial memory.
Duplicate JSON keys use the parser's last value; duplicate-key detection, schema
output and deeper flattening are not implemented. Input values appear in output,
so this tool is not a redactor and should not be used on secret-bearing dumps.
