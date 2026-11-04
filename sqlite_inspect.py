"""Read-only SQLite metadata and aggregate counts; never return row values."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys

PII = re.compile(r"email|phone|address|name|token|secret|password|ssn|dob", re.I)
READ_PRAGMAS = {
    "query_only", "page_size", "page_count", "journal_mode", "user_version",
    "table_list", "table_xinfo", "index_list", "index_xinfo", "foreign_key_list",
}


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def authorize(action, arg1, arg2, database, source):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                  sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_TRANSACTION):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and arg1 in READ_PRAGMAS:
        # Metadata pragmas take identifiers; scalar pragmas must be read-only.
        if arg1 in {"table_xinfo", "index_list", "index_xinfo",
                    "foreign_key_list"} or arg2 is None:
            return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect_readonly(path):
    # as_uri escapes ?, # and % so a filename cannot replace mode=ro.
    # immutable prevents SQLite from creating WAL/shm sidecars. Only accept
    # offline snapshots without recovery state; immutable would ignore a WAL.
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal")):
        raise RuntimeError("use a checkpointed, offline snapshot")
    db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        # mode=ro is enforced by SQLite; query_only is a second, checked guard.
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA query_only").fetchone() != (1,):
            raise RuntimeError("read-only guard unavailable")
        db.set_authorizer(authorize)
        db.row_factory = sqlite3.Row
        return db
    except Exception:
        db.close()
        raise


def inspect(path):
    path = Path(path).resolve()
    db = connect_readonly(path)
    try:
        db.execute("BEGIN")  # Consistent snapshot across counts and schema reads.
        scalar = lambda key: db.execute("PRAGMA " + key).fetchone()[0]
        report = {"file_size": path.stat().st_size}
        report.update({key: scalar(key) for key in
                       ("page_size", "page_count", "journal_mode", "user_version")})
        table_info = db.execute("PRAGMA main.table_list").fetchall()
        if not table_info:
            raise RuntimeError("SQLite 3.37 or newer is required")
        kinds = {r["name"]: r for r in table_info if r["schema"] == "main"}
        schema = db.execute(
            "SELECT type, name, tbl_name FROM main.sqlite_schema "
            "WHERE name NOT GLOB 'sqlite_*' ORDER BY name").fetchall()
        report.update(tables=[], views=[], triggers=[], indexes=[],
                      skipped_tables=[])
        for obj in schema:
            name, kind = obj["name"], obj["type"]
            if kind in ("view", "trigger"):
                report[kind + "s"].append({"name": name, "table": obj["tbl_name"]})
            if kind != "table":
                continue
            info = kinds[name]
            # Virtual tables can invoke extension code; do not query them.
            if info["type"] != "table":
                report["skipped_tables"].append({"name": name, "type": info["type"]})
                continue
            columns = [dict(r) for r in db.execute(
                "PRAGMA main.table_xinfo(" + quote(name) + ")")]
            columns = [{"name": c["name"], "type": c["type"],
                        "not_null": bool(c["notnull"]), "pk": c["pk"],
                        "hidden": c["hidden"]} for c in columns]
            pii = [c["name"] for c in columns if PII.search(c["name"])]
            counts = ["count(*)"] + ["count(" + quote(c) + ")" for c in pii]
            values = db.execute("SELECT " + ", ".join(counts) +
                                " FROM main." + quote(name)).fetchone()
            table = {"name": name, "rows": values[0], "columns": columns,
                     "without_rowid": bool(info["wr"]),
                     "no_primary_key": not any(c["pk"] for c in columns),
                     "pii_columns": [{"name": c, "non_null": values[i + 1]}
                                     for i, c in enumerate(pii)],
                     "foreign_keys": [dict(r) for r in db.execute(
                         "PRAGMA main.foreign_key_list(" + quote(name) + ")")]}
            report["tables"].append(table)
            for idx in db.execute("PRAGMA main.index_list(" + quote(name) + ")"):
                report["indexes"].append({
                    "name": idx["name"], "table": name, "unique": bool(idx["unique"]),
                    "origin": idx["origin"], "partial": bool(idx["partial"]),
                    "columns": [r["name"] for r in db.execute(
                        "PRAGMA main.index_xinfo(" + quote(idx["name"]) + ")")
                                if r["key"]]})
        report["indexes"].sort(key=lambda i: (i["table"], i["name"]))
        report["no_primary_key"] = [t["name"] for t in report["tables"]
                                    if t["no_primary_key"]]
        report["empty_tables"] = [t["name"] for t in report["tables"] if not t["rows"]]
        report["largest_tables"] = [
            {"name": t["name"], "rows": t["rows"]} for t in sorted(
                report["tables"], key=lambda t: (-t["rows"], t["name"]))[:5]]
        return report
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="compact JSON report")
    parser.add_argument("database")
    args = parser.parse_args(argv)
    try:
        report = inspect(args.database)
    except (OSError, sqlite3.Error, RuntimeError):
        # Database errors may contain data or schema expressions: do not echo.
        print("sqlite-inspect: cannot inspect database safely", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=None if args.json else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
