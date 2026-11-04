import json
from pathlib import Path
import subprocess
import sys
import unittest

import log_triage as lt


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/noisy.log'


def run(*args, input=None):
    return subprocess.run([sys.executable, str(ROOT / 'log_triage.py'), *args],
                          input=input, text=True, capture_output=True)


class LogTriageTests(unittest.TestCase):
    def test_fixture_and_determinism(self):
        first = run('--json', str(FIXTURE))
        second = run('--json', str(FIXTURE))
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout.encode(), second.stdout.encode())
        result = json.loads(first.stdout)
        self.assertEqual([g['count'] for g in result['templates']], [4, 2, 1])
        self.assertEqual(result['total_lines'], 7)

    def test_distinct_lines_and_ties(self):
        result = lt.triage(['zebra\n', 'alpha\n', 'beta\n'])
        self.assertEqual([g['template'] for g in result['templates']], ['alpha', 'beta', 'zebra'])
        self.assertTrue(all(g['count'] == 1 for g in result['templates']))

    def test_normalization(self):
        cases = {
            '2026-11-04T12:34:56.123Z': '<timestamp>',
            '2026-11-04 12:34:56+01:00': '<timestamp>',
            '2026-11-04t12:34:56z': '<timestamp>',
            '1730736000 1730736000123 1730736000.25': '<epoch> <epoch> <epoch>',
            'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee': '<uuid>',
            'abcdef12 0xDEADBEEF': '<hex> <hex>',
            '192.0.2.4:8080 203.0.113.5': '<ipv4> <ipv4>',
            '12345 -67890 +54321.5 12345678.9': '<number> <number> <number> <number>',
            '"' + 'x' * 41 + '"': '<quoted>',
            "'" + 'x' * 41 + "'": '<quoted>',
            '"' + 'x' * 40 + '"': '"' + 'x' * 40 + '"',
            '"192.0.2.4"': '"<ipv4>"',
            'status=404 id=12 abcdefg12': 'status=404 id=12 abcdefg12',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(lt.normalize(raw), expected)

    def test_invalid_ip_and_timestamp(self):
        for line in ['999.0.0.1', '192.0.2.1:99999', '2026-99-04T12:34:56Z']:
            self.assertEqual(lt.normalize(line), line)
            self.assertNotIn('first_timestamp', lt.triage([line])['templates'][0])

    def test_raw_samples_and_encounter_order(self):
        lines = [f'2026-11-04T10:00:0{i}Z "' + 'x' * 100 + '"' for i in [2, 0, 1]]
        group = lt.triage(lines, samples=2)['templates'][0]
        self.assertEqual(group['count'], 3)
        self.assertEqual(group['first_line'], lines[0])
        self.assertEqual(group['last_line'], lines[-1])
        self.assertEqual(group['sample'], lines[0])
        self.assertEqual(group['samples'], lines[:2])
        self.assertEqual(group['first_timestamp'], '2026-11-04T10:00:02Z')
        self.assertEqual(group['last_timestamp'], '2026-11-04T10:00:01Z')

    def test_absent_timestamps_empty_and_limits(self):
        self.assertNotIn('first_timestamp', lt.triage(['hello'])['templates'][0])
        self.assertEqual(lt.triage([])['templates'], [])
        self.assertEqual(lt.triage(['a', 'b'], top=0)['templates'], [])
        result = lt.triage(['a', 'a', 'b'], top=1, samples=0)
        self.assertEqual(result['total_templates'], 2)
        self.assertEqual(result['templates'][0]['samples'], [])
        self.assertEqual(result['templates'][0]['sample'], 'a')

    def test_cli_stdin_text_errors(self):
        result = run('--json', '-', input='hello\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['total_lines'], 1)
        result = run(input='hello\n')
        self.assertTrue(result.stdout.startswith(lt.HEADER + '\n'))
        self.assertIn('sample: hello', result.stdout)
        self.assertEqual(run('--top', '-1').returncode, 2)
        self.assertEqual(run('--samples', '-1').returncode, 2)
        self.assertEqual(run(str(ROOT / 'fixtures/missing.log')).returncode, 2)


if __name__ == '__main__':
    unittest.main()
