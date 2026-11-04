"""Offline regression checks; planted strings are deliberately fake, not credentials."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pr_digest


def diff(path, before, after):
    return f'--- a/{path}\n+++ b/{path}\n@@ -1,{len(before)} +1,{len(after)} @@\n' + ''.join('-' + x + '\n' for x in before) + ''.join('+' + x + '\n' for x in after)


class DigestTests(unittest.TestCase):
    def run_cli(self, text, *args):
        return subprocess.run([sys.executable, str(ROOT / 'pr_digest.py'), *args],
                              input=text, text=True, capture_output=True)

    def test_fixture_and_redaction(self):
        text = (ROOT / 'fixtures/risky.diff').read_text()
        planted = 'FAKE0123456789abcdef0123456789abcdef0123456789abcdef'
        for args in [(), ('--json',)]:
            result = self.run_cli(text, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(planted, result.stdout + result.stderr)
            self.assertIn('shell=True', result.stdout)
        data = pr_digest.digest(text)
        self.assertEqual(data['files'][0]['added'], 9)
        self.assertEqual(data['files'][0]['removed'], 1)
        self.assertTrue({'shell', 'auth', 'sql-concat', 'dynamic-code', 'broad-except',
                         'deleted-test', 'dependency-pair', 'todo', 'secret'} <= {r['rule'] for r in data['risks']})
        secret = next(r for r in data['risks'] if r['rule'] == 'secret')
        self.assertEqual((secret['file'], secret['line']), ('app.py', 3))
        self.assertNotIn('source', secret)
        self.assertTrue(3 <= len(data['checklist']) <= 7)

    def test_clean_and_empty(self):
        data = pr_digest.digest((ROOT / 'fixtures/clean.diff').read_text())
        self.assertEqual(data['risks'], [])
        self.assertEqual(len(data['checklist']), 3)
        self.assertEqual(pr_digest.digest(''), dict(files=[], risks=[], checklist=[]))

    def test_removed_secret_and_path(self):
        fake = 'abc123' * 8
        text = diff('tests/test_' + fake + '.py', ['token = "' + fake + '"'], ['pass'])
        for args in [(), ('--json',)]:
            result = self.run_cli(text, *args)
            self.assertNotIn(fake, result.stdout + result.stderr)

    def test_pairs_per_directory(self):
        a = diff('web/package.json', ['{}'], ['{"version":2}'])
        b = diff('web/yarn.lock', ['old'], ['new'])
        self.assertFalse(pr_digest.digest(a + b)['risks'])
        self.assertEqual(pr_digest.digest(a + b.replace('web/', 'other/'))['risks'][0]['rule'], 'dependency-pair')

    def test_multiline_and_line_numbers(self):
        text = diff('app.py', [], ['subprocess.run(', '    command,', '    shell=True)', 'except Exception:', '    pass'])
        risks = pr_digest.digest(text)['risks']
        self.assertEqual([(r['rule'], r['line']) for r in risks], [('shell', 1), ('swallowed-exception', 4)])

    def test_hunk_header_like_source(self):
        data = pr_digest.digest(diff('x.py', ['-- old'], ['++ new']))
        self.assertEqual((data['files'][0]['added'], data['files'][0]['removed']), (1, 1))

    def test_classes_and_order(self):
        self.assertEqual([pr_digest.classify(p) for p in ['tests/x.py', 'docs/a.md', 'a.toml', 'migrations/a.sql', 'x.py', 'blob']],
                         ['tests', 'docs', 'config', 'migration', 'source', 'other'])
        data = pr_digest.digest(diff('z.py', [], ['pass']) + diff('a.py', [], ['pass']))
        self.assertEqual([f['path'] for f in data['files']], ['a.py', 'z.py'])

    def test_malformed_is_safe(self):
        for text in ['--- a/a\n+++ b/a\n@@ -1 +1 @@\n+only\n', 'GIT binary patch\n']:
            result = self.run_cli(text)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(result.stdout)

    def test_secret_shapes_in_every_mode(self):
        for fake in ['abcdef0123456789' * 2, 'FakeExampleValue0123456789+/ABCDefghijklmnop=']:
            text = diff('a.py', [], ['token = "' + fake + '" # TODO'])
            for args in [(), ('--json',)]:
                result = self.run_cli(text, *args)
                self.assertEqual(result.returncode, 0)
                self.assertNotIn(fake, result.stdout + result.stderr)
                self.assertIn('secret', result.stdout)

    def test_context_and_multiple_hunks(self):
        text = '--- a/a.py\n+++ b/a.py\n@@ -10,2 +10,2 @@\n context\n-old\n+new\n@@ -20 +20 @@\n-old\n+# TODO verify\n'
        data = pr_digest.digest(text)
        self.assertEqual(data['risks'][0]['line'], 20)
        self.assertEqual(data['files'][0]['added'], 2)
        self.assertEqual(data['files'][0]['removed'], 2)

    def test_file_and_stdin_match(self):
        text = (ROOT / 'fixtures/risky.diff').read_text()
        self.assertEqual(self.run_cli(text, '--json').stdout,
                         self.run_cli('', '--json', '--file', str(ROOT / 'fixtures/risky.diff')).stdout)


if __name__ == '__main__':
    unittest.main()
