# sqlite-inspect

Python 3 with SQLite 3.37+; standard library only. Run from the repository root:

    python3 sqlite_inspect.py --json fixtures/sample.db
    python3 -m unittest discover -s tests -v

Without --json the same report is pretty-printed JSON. Errors exit 1 with no
partial report. Counts are exact; large databases can take time. Identifiers
are quoted and URI paths escaped. Output contains schema names and aggregate
counts only, not row values, SQL definitions or column defaults.

Use a checkpointed, offline database snapshot, not an actively changing file.
The URI uses mode=ro and immutable=1 to forbid writes and avoid creating
journal/WAL/shared-memory files. Existing -wal or -journal files cause refusal
because immutable would ignore pending changes. Do not remove recovery files
to bypass this check: obtain a consistent snapshot using the owning app.
Concurrent writers are unsupported; immutable assumes the file stays fixed.
A verified query_only guard and an authorizer add protection before any reads.

Report includes file/page metadata, tables, columns, PK positions, WITHOUT ROWID,
foreign keys, indexes (including automatic indexes), views and triggers.
No-PK and empty-table lists and the top five row counts are included. PII name
matching is deliberately broad, case-insensitive substring matching; non_null
counts count populated cells, not distinct values or people. Expression-index
columns are null rather than showing potentially sensitive SQL expressions.
Virtual tables and their shadow tables are listed as skipped, never queried.
Views are listed, not executed. Schema names themselves can contain personal
information; handle the report accordingly.

Encrypted databases, migrations, arbitrary queries and index advice are excluded.
