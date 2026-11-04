import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

import dockerfile_audit as audit

ROOT = Path(__file__).resolve().parents[1]


class AuditTests(unittest.TestCase):
    def rules(self, text):
        return {f['rule'] for f in audit.audit(text)['findings']}

    def test_bad_all_rules(self):
        text = (ROOT / 'fixtures/bad.Dockerfile').read_text()
        self.assertEqual(self.rules(text), {f'DF{i:03}' for i in range(1, 11)})

    def test_good_cli(self):
        run = subprocess.run([sys.executable, 'dockerfile_audit.py', '--json', 'fixtures/good.Dockerfile'],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), dict(findings=[], counts=dict(high=0, medium=0, low=0)))

    def test_bad_cli(self):
        run = subprocess.run([sys.executable, 'dockerfile_audit.py', '--json', 'fixtures/bad.Dockerfile'],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertGreater(json.loads(run.stdout)['counts']['high'], 0)

    def test_continuation_and_comments(self):
        text = 'FROM debian:12\nRUN apt-get update \\\n# comment\n && apt-get install curl\n'
        findings = audit.audit(text)['findings']
        self.assertEqual([f['line'] for f in findings if f['rule'] in {'DF003', 'DF004'}], [2, 2])

    def test_apt_clean(self):
        rules = self.rules('RUN apt-get install --no-install-recommends curl && rm -rf /var/lib/apt/lists/*')
        self.assertFalse({'DF003', 'DF004'} & rules)
        self.assertIn('DF004', self.rules('RUN apt-get install curl\nRUN rm -rf /var/lib/apt/lists/*'))

    def test_cleanup_must_follow_install(self):
        self.assertIn('DF004', self.rules('RUN rm -rf /var/lib/apt/lists/* && apt-get install curl'))

    def test_user_final_and_inherited(self):
        self.assertNotIn('DF002', self.rules('FROM alpine:3 AS base\nUSER app\nFROM base'))
        self.assertIn('DF002', self.rules('FROM alpine:3 AS base\nUSER app\nFROM alpine:3'))
        for user in ('root', '0', '0:0', 'root:app'):
            self.assertIn('DF002', self.rules('FROM scratch\nUSER ' + user))
        self.assertNotIn('DF002', self.rules('FROM scratch\nUSER root\nUSER app'))

    def test_from_variants(self):
        for base in ('alpine', 'localhost:5000/alpine', 'alpine:latest'):
            self.assertIn('DF001', self.rules('FROM ' + base))
        for base in ('scratch', 'alpine:3', 'alpine@sha256:abc', '${BASE}'):
            self.assertNotIn('DF001', self.rules('FROM --platform=linux/amd64 ' + base))

    def test_names_only(self):
        text = 'ARG API_TOKEN=placeholder\nENV PUBLIC=yes PASSWORD=placeholder\nENV SECRET placeholder'
        result = json.dumps(audit.audit(text))
        self.assertNotIn('placeholder', result)
        self.assertEqual(result.count('DF007'), 3)
        self.assertNotIn('DF007', self.rules('ENV PUBLIC="API_TOKEN=placeholder"'))

    def test_copy_order_and_stage(self):
        self.assertIn('DF008', self.rules('FROM node:22\nCOPY [".", "."]\nRUN npm ci'))
        self.assertNotIn('DF008', self.rules('FROM node:22\nRUN npm ci\nCOPY . .'))
        self.assertNotIn('DF008', self.rules('FROM node:22\nCOPY . .\nFROM node:22\nRUN npm ci'))

    def test_add_exceptions(self):
        for source in ('https://example.invalid/a', 'source.tar.gz', '${SOURCE}'):
            self.assertNotIn('DF006', self.rules('ADD ' + source + ' /app/'))
        self.assertIn('DF006', self.rules('ADD ["app.py", "/app/"]'))

    def test_shell_and_exec(self):
        self.assertIn('DF005', self.rules('RUN wget -qO- https://example.invalid/a | /bin/bash'))
        self.assertNotIn('DF005', self.rules("RUN curl '|' sh"))
        self.assertNotIn('DF005', self.rules('RUN echo "curl x | sh"'))
        self.assertNotIn('DF005', self.rules('RUN ["curl", "x", "|", "sh"]'))
        self.assertNotIn('DF010', self.rules('RUN echo sudo'))
        self.assertIn('DF010', self.rules('RUN ["sudo", "echo", "ok"]'))

    def test_heredoc_and_escape(self):
        self.assertEqual(list(audit.instructions('RUN <<EOF\nFROM bad\nEOF\nUSER app')), [(4, 'USER', 'app')])
        self.assertEqual(list(audit.instructions('# escape=`\nRUN echo `\n hello')), [(2, 'RUN', 'echo  hello')])

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(audit.main(['definitely-missing.Dockerfile']), 2)
        self.assertIn('cannot read', error.getvalue())

    def test_low_only(self):
        result = audit.audit('FROM scratch\nUSER app')
        self.assertEqual(result['counts'], dict(high=0, medium=0, low=1))


if __name__ == '__main__':
    unittest.main()
