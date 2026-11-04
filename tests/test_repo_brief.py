"""Run with: python3 -B -m unittest discover -s tests -v."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import repo_brief


class RepoBriefTests(unittest.TestCase):
    def setUp(self):
        # Leave generated fixtures for inspection; no data deletion is needed.
        self.root = Path(tempfile.mkdtemp(prefix='repo-brief-test-'))

    def write(self, path, text=''):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', repo_brief.__file__, *map(str, args)],
                              capture_output=True, text=True)

    def test_complete_brief(self):
        self.write('README.md', '# Demo\n\nFirst paragraph\ncontinued.\n\nSecond.\n')
        self.write('main.py', 'print("hello")\n')
        self.write('src/__main__.py')
        self.write('src/cli.py')
        self.write('bin/run')
        self.write('tests/test_main.py')
        self.write('tests/__init__.py')
        self.write('tests/conftest.py')
        self.write('package.json', '{"bin": {"demo": "cli.js"}}')
        self.write('Makefile', 'build test: dep\n\techo hi\n.PHONY: build\nVAR := value\n')
        for name in ('requirements.txt', 'pyproject.toml', 'go.mod'):
            self.write(name)
        result = repo_brief.scan(self.root)
        self.assertEqual(result['readme'], {'path': 'README.md', 'heading': 'Demo',
                                           'paragraph': 'First paragraph continued.'})
        self.assertEqual(result['test_files'], 1)
        self.assertEqual(result['test_dirs'], ['tests'])
        self.assertEqual(result['test_frameworks'], ['pytest'])
        self.assertEqual(result['entry_points'], ['Makefile target: build', 'Makefile target: test',
                         'bin/run', 'main.py', 'package.json bin demo: cli.js',
                         'src/__main__.py', 'src/cli.py'])
        self.assertEqual(result['dependency_files'], sorted(repo_brief.DEPENDENCIES))
        self.assertEqual(len(result['largest_files']), 10)
        python = next(item for item in result['languages'] if item['language'] == 'Python')
        self.assertEqual(python, {'language': 'Python', 'files': 6, 'bytes': 15})
        self.assertEqual(self.cli('--json', self.root).returncode, 0)
        self.assertEqual(json.loads(self.cli('--json', self.root).stdout), result)
        text = self.cli(self.root).stdout.splitlines()[1:]
        self.assertEqual({key: json.loads(value) for key, value in
                          (line.split(': ', 1) for line in text)}, result)

    def test_absent_readme_and_empty_directory(self):
        (self.root / 'tests').mkdir()
        before = sorted((p.relative_to(self.root).as_posix(), p.stat().st_mtime_ns)
                        for p in self.root.rglob('*'))
        result = self.cli(self.root)
        self.assertEqual(before, sorted((p.relative_to(self.root).as_posix(), p.stat().st_mtime_ns)
                                        for p in self.root.rglob('*')))
        self.assertEqual(result.returncode, 0)
        self.assertIn('absent', result.stdout)
        brief = repo_brief.scan(self.root)
        self.assertEqual(brief['test_dirs'], ['tests'])
        self.assertEqual(brief['languages'], [])
        self.assertEqual(brief['test_files'], 0)

    def test_skips_metadata_secrets_and_symlinks(self):
        for name in ('.git/config', '.env', '.env.local', 'private.key',
                     '.ssh/config', 'node_modules/main.js', '__pycache__/cached.pyc'):
            self.write(name, 'excluded fixture')
        self.write('real.py', 'ok')
        (self.root / 'link.py').symlink_to(self.root / 'real.py')
        (self.root / 'loop').symlink_to(self.root, target_is_directory=True)
        brief = repo_brief.scan(self.root)
        self.assertEqual(brief['largest_files'], [{'path': 'real.py', 'bytes': 2}])

    def test_deterministic_top_five_and_ties(self):
        for name in ('b.py', 'a.py', 'x.js', 'x.go', 'x.rs', 'x.c', 'x.java'):
            self.write(name, 'é')
        first = self.cli('--json', self.root).stdout
        self.assertEqual(first, self.cli('--json', self.root).stdout)
        brief = json.loads(first)
        self.assertEqual(len(brief['languages']), 5)
        self.assertEqual(brief['languages'][0], {'language': 'Python', 'files': 2, 'bytes': 4})
        self.assertEqual(brief['largest_files'][0]['path'], 'a.py')

    def test_malformed_and_bounded_text(self):
        self.write('package.json', '{broken')
        self.write('README', 'Title\n=====\n\n' + 'x' * (repo_brief.READ_LIMIT + 1))
        brief = repo_brief.scan(self.root)
        self.assertEqual(brief['readme']['heading'], 'Title')
        self.assertEqual(len(brief['warnings']), 2)
        self.write('package.json', '[]')
        self.assertEqual(repo_brief.scan(self.root)['entry_points'], [])

    def test_errors_and_frameworks(self):
        self.assertNotEqual(self.cli(self.root / 'missing').returncode, 0)
        for name in ('jest.config.js', 'vitest.config.ts', 'src/a_test.go', 'spec/a_spec.rb'):
            self.write(name)
        self.assertEqual(repo_brief.scan(self.root)['test_frameworks'],
                         ['Go testing', 'Jest', 'RSpec', 'Vitest'])
        warnings = set()
        with patch.object(Path, 'open', side_effect=PermissionError):
            self.assertEqual(repo_brief.read_text(self.root / 'README', warnings, 'README'), '')
        self.assertEqual(warnings, {'README: cannot read text'})


if __name__ == '__main__':
    unittest.main()
