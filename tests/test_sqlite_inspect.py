import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import sqlite_inspect as app

ROOT = Path(__file__).resolve().parents[1]


class InspectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sample ?#%.db"
        shutil.copyfile(ROOT / "fixtures/sample.db", self.path)

    def run_cli(self, path=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "sqlite_inspect.py"), "--json",
             str(path or self.path)], text=True, capture_output=True)

    def test_cli_hash_and_metadata(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        files = sorted(p.name for p in self.path.parent.iterdir())
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        d = json.loads(result.stdout)
        t = {x["name"]: x for x in d["tables"]}
        self.assertEqual(t["users"]["rows"], 3)
        self.assertEqual(t["empty_table"]["rows"], 0)
        self.assertIn("empty_table", d["no_primary_key"])
        self.assertIn("empty_table", d["empty_tables"])
        self.assertTrue(t["settings"]["without_rowid"])
        self.assertEqual(t["users"]["pii_columns"],
                         [{"name": "email", "non_null": 2},
                          {"name": "name", "non_null": 3}])
        self.assertEqual(t["orders"]["foreign_keys"][0]["table"], "users")
        self.assertEqual(d["views"][0]["name"], "user_ids")
        self.assertEqual(d["triggers"][0]["name"], "users_updated")
        self.assertTrue(any(i["columns"] == ["email"] for i in d["indexes"]))
        self.assertEqual(d["largest_tables"][0], {"name": "users", "rows": 3})
        self.assertEqual(d["user_version"], 7)
        self.assertGreater(d["page_size"], 0)
        self.assertGreater(d["page_count"], 0)
        self.assertEqual(d["file_size"], self.path.stat().st_size)
        for value in ("fixture-one", "Alice", "Bob", "Cara"):
            self.assertNotIn(value, result.stdout + result.stderr)
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(files, sorted(p.name for p in self.path.parent.iterdir()))

    def test_write_guards(self):
        db = app.connect_readonly(self.path)
        self.addCleanup(db.close)
        for sql in ("CREATE TABLE nope(x)", "PRAGMA user_version=42",
                    "PRAGMA query_only=OFF", "ATTACH ':memory:' AS other"):
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute(sql)
        db.set_authorizer(None)
        db.execute("PRAGMA query_only=OFF")
        with self.assertRaises(sqlite3.OperationalError):
            db.execute("CREATE TABLE nope(x)")  # URI itself enforces read-only.

    def test_guard_failure_closes_connection(self):
        with patch.object(app.sqlite3, "connect") as connect:
            connect.return_value.execute.return_value.fetchone.return_value = (0,)
            with self.assertRaises(RuntimeError):
                app.connect_readonly(self.path)
            connect.return_value.close.assert_called_once()

    def test_quoted_identifiers_and_expression_index(self):
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE "odd"" name"(id INT, "phone number" TEXT);
                INSERT INTO "odd"" name" VALUES(1, 'DO_NOT_PRINT');
                CREATE INDEX expr_idx ON "odd"" name"(lower("phone number"));
                CREATE TABLE sqliteXcustom(x);
            """)
        d = app.inspect(self.path)
        self.assertIn('odd" name', d["no_primary_key"])
        self.assertIn("sqliteXcustom", d["empty_tables"])
        self.assertEqual(next(i for i in d["indexes"] if i["name"] == "expr_idx")
                         ["columns"], [None])
        self.assertNotIn("DO_NOT_PRINT", json.dumps(d))

    def test_missing_and_corrupt_fail_without_creating_file(self):
        missing = self.path.parent / "absent.db"
        self.assertNotEqual(self.run_cli(missing).returncode, 0)
        self.assertFalse(missing.exists())
        self.path.write_bytes(b"not a database")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("not a database", result.stderr)

    def test_recovery_sidecars_refused(self):
        for suffix in ("-wal", "-journal"):
            with self.subTest(suffix=suffix):
                database = self.path.parent / (suffix + ".db")
                shutil.copyfile(self.path, database)
                sidecar = Path(str(database) + suffix)
                sidecar.write_bytes(b"pending state")
                result = self.run_cli(database)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(sidecar.read_bytes(), b"pending state")

    def test_virtual_tables_skipped(self):
        with sqlite3.connect(self.path) as db:
            try:
                db.execute("CREATE VIRTUAL TABLE search USING fts5(body)")
            except sqlite3.OperationalError:
                self.skipTest("SQLite build has no FTS5")
        d = app.inspect(self.path)
        self.assertIn({"name": "search", "type": "virtual"}, d["skipped_tables"])
        self.assertNotIn("search", [t["name"] for t in d["tables"]])


if __name__ == "__main__":
    unittest.main()
