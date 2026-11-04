import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

from jsonl_profile import Field, profile

ROOT = Path(__file__).resolve().parents[1]


def analyze(*records, cap=1000):
    return profile(io.StringIO("".join(json.dumps(r) + "\n" for r in records)), cap)


class ProfileTests(unittest.TestCase):
    def test_fixture(self):
        with (ROOT / "fixtures/events.jsonl").open() as stream:
            result = profile(stream)
        self.assertEqual((result["lines"], result["malformed"]), (10, 0))
        self.assertEqual(result["keys"]["user_id"]["missing"], 0)
        self.assertEqual(result["keys"]["user_id"]["distinct"], 3)
        self.assertEqual(result["keys"]["note"]["nulls"], 4)
        self.assertEqual(result["keys"]["status"]["values"], {"error": 2, "ok": 8})

    def test_malformed_and_nonobjects(self):
        result = profile(io.StringIO('{"x":1}\nbad\n\n[]\nnull\n{"x":2}\n'))
        self.assertEqual((result["lines"], result["malformed"]), (6, 4))
        self.assertEqual(result["keys"]["x"]["present"], 2)
        self.assertEqual(result["keys"]["x"]["missing"], 4)

    def test_types_numbers_and_null(self):
        result = analyze(*({"x": v} for v in [None, True, 1, 1.0, 2.5, "a", [], {}]))
        field = result["keys"]["x"]
        self.assertEqual(field["types"], ["array", "boolean", "null", "number", "object", "string"])
        self.assertEqual(field["distinct"], 7)
        self.assertEqual((field["min"], field["max"], field["integral"]), (1, 2.5, False))
        self.assertTrue(analyze({"x": -2}, {"x": 3.0})["keys"]["x"]["integral"])
        self.assertNotIn("min", analyze({"x": True})["keys"]["x"])

    def test_cardinality_boundaries(self):
        field = Field(2)
        for value in [1, 2, 1]:
            field.add(value)
        self.assertEqual(field.result(3)["distinct"], 2)
        for value in range(100):
            field.add(value)
        self.assertEqual(field.result(103)["distinct"], ">=2")
        self.assertEqual(len(field.seen), 2)

    def test_enumeration_limit(self):
        twenty = [{"x": str(i)} for i in range(20)]
        self.assertEqual(len(analyze(*twenty)["keys"]["x"]["values"]), 20)
        self.assertNotIn("values", analyze(*twenty, {"x": "extra"})["keys"]["x"])
        self.assertNotIn("values", analyze(*twenty, cap=2)["keys"]["x"])

    def test_nested_depth_and_collisions(self):
        result = analyze({"a": {"b": {"c": 1}}, "a.b": 2, "a\\b": 3}, {"a": {}})
        self.assertEqual(list(result["keys"]), ["a", "a.b", "a\\.b", "a\\\\b"])
        self.assertEqual(result["keys"]["a.b"]["missing"], 1)
        self.assertEqual(result["keys"]["a.b"]["types"], ["object"])

    def test_structural_distinctness(self):
        result = analyze({"x": {"a": 1, "b": True}}, {"x": {"b": True, "a": 1.0}})
        self.assertEqual(result["keys"]["x"]["distinct"], 1)
        self.assertEqual(analyze({"x": [1, 2]}, {"x": [2, 1]})["keys"]["x"]["distinct"], 2)

    def test_examples_empty_and_invalid_numbers(self):
        self.assertEqual(analyze(), {"lines": 0, "malformed": 0, "keys": {}})
        self.assertEqual(len(analyze({"x": "z" * 200})["keys"]["x"]["example"]), 80)
        result = profile(io.StringIO('{"x":NaN}\n{"x":Infinity}\n{"x":1e999}\n'))
        self.assertEqual((result["malformed"], result["keys"]), (3, {}))
        with self.assertRaises(ValueError):
            profile([], 0)

    def test_cli(self):
        command = [sys.executable, str(ROOT / "jsonl_profile.py")]
        run = subprocess.run(command + ["--json"], input='{"x":1}\n', text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["keys"]["x"]["missing"], 0)
        text = subprocess.run(command, input='{"x":1}\n', text=True, capture_output=True)
        self.assertIn("lines: 1; malformed: 0", text.stdout)
        for args in [["--max-card", "0"], ["--max-card", "bad"], ["/nonexistent-jsonl-profile"]]:
            self.assertEqual(subprocess.run(command + args, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
