from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import git_churn


SCRIPT = Path(git_churn.__file__).resolve()


class ChurnTests(unittest.TestCase):
    def setUp(self):
        # Retain fixtures: no user data is removed by the test suite.
        self.root = Path(tempfile.mkdtemp(prefix='git-churn-test-'))
        self.env = dict(os.environ, GIT_AUTHOR_NAME='Test',
                        GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.git('init', '-b', 'main')

    def git(self, *args):
        return subprocess.run(['git', '-c', 'commit.gpgsign=false', *args],
                              cwd=self.root, env=self.env, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def commit(self, day, author='test@example.invalid'):
        self.env.update(GIT_AUTHOR_DATE=f'2026-01-{day:02}T12:00:00+00:00',
                        GIT_COMMITTER_DATE=f'2026-01-{day:02}T12:00:00+00:00',
                        GIT_AUTHOR_EMAIL=author)
        self.git('add', '.')
        self.git('commit', '--allow-empty', '-m', 'fixture')

    def cli(self, *args, check=True):
        return subprocess.run(['python3', '-B', str(SCRIPT), '--json', *args],
                              cwd=self.root, env=self.env, check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def history(self):
        for day in range(1, 7):
            self.write('src/hot.py', b'hot\n' * (day * 10))
            self.write('src/peer.py', b'peer\n' * day)
            self.write('nested/dist/output', b'generated\n' * day)
            self.write('package-lock.json', b'lock\n' * day)
            if day == 1:
                self.write('once.txt', b'once\n')
            self.commit(day, 'other@example.invalid' if day == 6 else 'test@example.invalid')

    def test_known_history_and_read_only(self):
        self.history()
        before = (self.git('rev-parse', 'HEAD').stdout, self.git('status', '--porcelain').stdout)
        report = json.loads(self.cli().stdout)
        self.assertEqual(report['commits_analysed'], 6)
        hot = report['hotspots'][0]
        self.assertEqual((hot['path'], hot['commits'], hot['authors'], hot['churn']),
                         ('src/hot.py', 6, 2, 60))
        self.assertEqual(datetime.fromisoformat(hot['last_changed']),
                         datetime.fromisoformat('2026-01-06T12:00:00+00:00'))
        self.assertTrue(hot['directory_hotspot'])
        self.assertEqual(report['pairs'], [dict(files=['src/hot.py', 'src/peer.py'], together=6, ratio=1)])
        self.assertEqual(len(report['hotspots']), 3)
        self.assertEqual(before, (self.git('rev-parse', 'HEAD').stdout,
                                 self.git('status', '--porcelain').stdout))
        self.assertEqual(self.cli().stdout, self.cli().stdout)

    def test_filters_and_limit(self):
        self.history()
        report = json.loads(self.cli('-n', '2', '--exclude', 'src/peer.*').stdout)
        self.assertEqual(report['commits_analysed'], 2)
        self.assertEqual([f['path'] for f in report['hotspots']], ['src/hot.py'])
        self.assertEqual(report['pairs'], [])
        self.assertEqual(json.loads(self.cli('--since', '2026-01-05T00:00:00Z').stdout)['commits_analysed'], 2)
        self.assertEqual(json.loads(self.cli('--since', '2027-01-01').stdout)['hotspots'], [])
        self.assertNotEqual(self.cli('-n', '0', check=False).returncode, 0)

    def test_unusual_names_binary_and_rename(self):
        name = 'odd\tline\n雪.txt'
        self.write(name, b'a\nb\n')
        self.write('blob', b'\0binary')
        self.commit(1)
        self.git('mv', name, 'renamed.txt')
        self.commit(2)
        report = json.loads(self.cli().stdout)
        rows = {f['path']: f for f in report['hotspots']}
        self.assertEqual(rows[name]['removed'], 2)
        self.assertEqual(rows['renamed.txt']['added'], 2)
        self.assertEqual(rows['blob']['churn'], 0)
        self.assertEqual(rows['blob']['commits'], 1)

    def test_empty_commit_and_errors(self):
        self.assertNotEqual(self.cli(check=False).returncode, 0)
        self.commit(1)
        self.assertEqual(json.loads(self.cli().stdout), dict(commits_analysed=1, hotspots=[], pairs=[]))
        self.write('a', b'a\n')
        self.commit(2)
        self.commit(3)
        report = json.loads(self.cli().stdout)
        self.assertEqual(report['commits_analysed'], 3)
        self.assertEqual(report['hotspots'][0]['commits'], 1)

    def test_thresholds_ties_and_top_ten(self):
        date = '2026-01-01T00:00:00+00:00'
        commits = [('a', date, [('d/a', '1', '0')] +
                    ([('d/b', '1', '0')] if i < 6 else [])) for i in range(10)]
        report = git_churn.analyse(commits)
        self.assertFalse(report['hotspots'][1]['directory_hotspot'])  # exactly 60%
        self.assertEqual(report['pairs'][0]['ratio'], 1)
        many = [('a', date, [(str(i), '1', '0') for i in range(6)])] * 5
        report = git_churn.analyse(many)
        self.assertEqual(len(report['pairs']), 10)
        self.assertEqual([f['path'] for f in report['hotspots']], list('012345'))
        self.assertEqual(git_churn.analyse(many[:4])['pairs'], [])
        sparse = [('a', date, [('a', '1', '0'), ('b', '1', '0')])] * 5
        sparse += [('a', date, [('a', '1', '0')])] * 4
        sparse += [('a', date, [('b', '1', '0')])] * 4
        self.assertEqual(git_churn.analyse(sparse)['pairs'], [])


if __name__ == '__main__':
    unittest.main()
