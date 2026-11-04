"""Only fictional, inert strings generated locally are scanned by these tests."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import secret_scan_lite as scanner

SCRIPT = Path(scanner.__file__).resolve()


class ScannerTests(unittest.TestCase):
    def setUp(self):
        # Intentionally retain fixtures: no deletion is required by the run.
        self.root = Path(tempfile.mkdtemp(prefix='secret-scan-lite-fictional-'))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, check=False)

    def plant(self, text, name='fictional.txt'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_every_rule_and_no_value_in_either_mode(self):
        values = ['AKIAFAKE' + '0' * 12,
                  *[prefix + 'FAKE' + '0' * 24 for prefix in
                    ('ghp_', 'gho_', 'ghs_', 'ghu_', 'github_pat_')],
                  'sk-FAKE' + '0' * 24, '-----BEGIN FICTIONAL PRIVATE KEY-----',
                  'FAKE0000.FAKE1111.FAKE2222',
                  *['xox' + c + '-FAKE' + '0' * 20 for c in 'abpos'],
                  'fictional-only-value']
        self.plant('\n'.join(values[:-1]) + '\npassword = "' + values[-1] + '"')
        for mode in ([], ['--json']):
            result = self.run_cli(*mode, self.root)
            self.assertEqual(result.returncode, 1)
            for value in values:
                self.assertNotIn(value, result.stdout + result.stderr)
        found = json.loads(result.stdout)['findings']
        self.assertEqual({f['rule'] for f in found},
                         {f'SL00{i}' for i in range(1, 8)})
        self.assertEqual(len(found), len(values))
        self.assertEqual(found[0]['shape'], 'AKI…00 (20)')
        self.assertEqual(found[0]['line'], 1)

    def test_short_shapes(self):
        for value in ("a.b.c", "ghp_a", "xoxb-a"):
            found = list(scanner.matches(value))
            self.assertEqual(len(found), 1)
            self.assertNotIn(value, scanner.shape(value))

    def test_clean(self):
        result = self.run_cli('--json', SCRIPT.parent / 'fixtures/clean')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {'findings': []})

    def test_acceptance_fixture(self):
        result = self.run_cli('--json', SCRIPT.parent / 'fixtures/leaky')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(json.loads(result.stdout)['findings']), 4)
        self.assertNotIn('AKIAFAKE', result.stdout)

    def test_assignment_names_and_threshold(self):
        for key in ('password', 'SECRET', 'token', 'api_key', 'apikey'):
            self.assertEqual(len(list(scanner.matches(f'"{key}": "fictional00"'))), 0)
            self.assertEqual(len(list(scanner.matches(f"{key}='fictional0000'"))), 1)
        self.assertFalse(list(scanner.matches('notpassword="fictional0000"')))

    def test_skips_and_allowlist(self):
        value = 'AKIAFAKE' + '0' * 12
        for directory in scanner.SKIP:
            self.plant(value, directory + '/example.txt')
        self.plant(value + 'x' * scanner.MAX_BYTES, 'large.txt')
        (self.root / 'binary.bin').write_bytes(b'\0' + value.encode())
        (self.root / 'invalid.txt').write_bytes(b'\xff' + value.encode())
        self.plant(value, 'examples/safe.txt')
        allow = self.plant('# comment\n\nexamples/*\n', 'allow.txt')
        result = self.run_cli('--json', '--allowlist', allow, self.root)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['findings'], [])

    def test_symlinks_not_followed(self):
        target = self.plant('AKIAFAKE' + '0' * 12, '.git/inert.txt')
        (self.root / 'link.txt').symlink_to(target)
        (self.root / 'loop').symlink_to(self.root, target_is_directory=True)
        self.assertEqual(scanner.scan(self.root), [])

    def test_path_metadata_redacted(self):
        value = 'fictional-value-only'
        self.plant(f'password="{value}"', value + '.txt')
        result = self.run_cli('--json', self.root)
        self.assertNotIn(value, result.stdout)
        self.assertIn('[redacted]', result.stdout)

    def test_errors_do_not_echo_input(self):
        value = 'sk-FAKE' + '0' * 24
        for args in [('--json', self.root / value), ('--unknown=' + value,)]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(value, result.stdout + result.stderr)

    def test_read_failure_is_not_clean(self):
        with patch.object(scanner, 'scan', side_effect=OSError('private content')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = scanner.main(['--json', str(self.root)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'scan incomplete')
        self.assertNotIn('private content', output.getvalue())

    def test_order_is_deterministic_and_root_defaults(self):
        self.plant('AKIAFAKE' + '0' * 12, 'b.txt')
        self.plant('AKIAFAKE' + '0' * 12, 'a.txt')
        first = scanner.scan(self.root)
        self.assertEqual(first, scanner.scan(self.root))
        self.assertEqual([f['path'] for f in first], ['a.txt', 'b.txt'])
        result = subprocess.run([sys.executable, str(SCRIPT), '--json'],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['findings'], first)


if __name__ == '__main__':
    unittest.main()
