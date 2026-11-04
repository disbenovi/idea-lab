# routine-lint

Run `python3 routine_lint.py fixtures/good.md` or add `--json`. No installs,
network calls, or schedule creation. Requires Python 3.9+ and system IANA
zoneinfo data. Markdown headers use literal pipes (no escaped pipes); JSON
is an array of objects with the same keys. Diagnostics include path and
Markdown line number or one-based JSON array index.

Required strings: name, schedule, timezone, end_date, notify, deliver.
Schedule is `cron`, `event`, `once` (with an `at` ISO timestamp), or an ISO
one-time timestamp directly. Dates without times mean local midnight.
An explicit timestamp offset takes precedence over the row timezone.
Naive ambiguous/nonexistent local timestamps are rejected. UTC is allowed;
abbreviations such as PST and bare numeric offsets are not.

Cron supports five numeric, comma-list, or wildcard fields; Sunday is 0 or 7.
Ranges, steps, and names are deliberately rejected. Restricted day-of-month
and day-of-week fields use standard cron OR semantics. Search is bounded by
end_date (inclusive) and eight years. Missing DST times are skipped; repeated
wall times can fire twice. `--now 2026-11-04T21:00:00Z` freezes the clock.

Both next-fire timestamps are printed. Simple daily/weekly fixed-time cron
also shows a UTC expression projected using that next fire's offset. It is
NOT a year-round replacement for a DST-observing local cron; complex crons
show exact next-fire timestamps without claiming a UTC cron equivalent.
The fixed-offset IANA fixture Etc/GMT+8 means UTC-08:00, so Friday 16:00
converts to Saturday 00:00 (`0 16 * * 5` -> `0 0 * * 6`).

`only on change`, `only-on-change`, `on-change`, and `change-only` notify
values warn unless the row includes a nonempty `liveness` description.
Event rows require a `trigger`, no cron, and `--connected-source NAME` for
each locally asserted connected source. This is an offline inventory claim,
not provider verification or monitoring; this tool cannot inspect APIs.
An event has no predictable next fire. All rows still require a future end.

Verification: `python3 -m unittest -v test_routine_lint.py`, then the two
acceptance commands from the idea file. Good fixtures intentionally warn;
warnings alone do not fail. Fixed 2099 end dates keep examples useful until
then. To roll back, revert the implementation commit.
