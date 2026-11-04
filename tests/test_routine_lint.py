import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
import routine_lint as r

NOW = datetime(2026, 11, 4, 21, tzinfo=timezone.utc)


class RoutineTests(unittest.TestCase):
    def row(self, **changes):
        row = dict(name='test', schedule='cron', cron='0 16 * * 5',
                   timezone='Etc/GMT+8', end_date='2099-12-31', notify='always', deliver='console')
        row.update(changes)
        return row

    def lint(self, connected=(), now=NOW, **changes):
        return r.lint(self.row(**changes), 'test:1', now, set(connected))

    def test_rollover_and_sunday_alias(self):
        out = self.lint()
        self.assertEqual(out['errors'], [])
        self.assertEqual(out['utc_cron'], '0 0 * * 6')
        self.assertEqual(out['utc'], '2026-11-07T00:00:00+00:00')
        self.assertEqual(self.lint(cron='0 16 * * 7')['utc_cron'], '0 0 * * 1')

    def test_bad_fields(self):
        for cron in ('0 16 * *', '60 16 * * 5', '0 24 * * 5', '0 0 0 * *',
                     '0 0 * 13 *', '0 0 * * 8', '*/5 * * * *'):
            self.assertTrue(self.lint(cron=cron)['errors'], cron)
        for zone in ('PST', '+08:00', 'Not/AZone'):
            self.assertTrue(self.lint(timezone=zone)['errors'])
        for key in ('name', 'schedule', 'end_date', 'notify', 'deliver'):
            self.assertTrue(self.lint(**{key: ''})['errors'], key)

    def test_once_end_and_event(self):
        self.assertTrue(self.lint(schedule='2000-01-01', cron='')['errors'])
        self.assertFalse(self.lint(schedule='once', at='2027-01-01', cron='')['errors'])
        self.assertTrue(self.lint(end_date='2000-01-01')['errors'])
        self.assertTrue(self.lint(schedule='2100-01-01', cron='')['errors'])
        self.assertTrue(self.lint(schedule='event', cron='', trigger='mail')['errors'])
        self.assertFalse(self.lint(schedule='event', cron='', trigger='mail', connected=['mail'])['errors'])
        self.assertTrue(self.lint(schedule='event', trigger='mail', connected=['mail'])['errors'])

    def test_silence_and_calendar(self):
        self.assertTrue(self.lint(notify='only on change')['warnings'])
        self.assertFalse(self.lint(notify='on-change', liveness='daily ping')['warnings'])
        self.assertTrue(self.lint(cron='0 0 31 2 *')['errors'])
        self.assertFalse(self.lint(cron='0 0 31 2 1')['errors'])  # DOM/DOW OR
        self.assertFalse(self.lint(cron='0,30 1,2 * * *')['errors'])

    def test_dst(self):
        zone = r.ZoneInfo('America/Los_Angeles')
        self.assertEqual(r.local_instants(datetime(2027, 3, 14, 2, 30), zone), [])
        self.assertEqual(len(r.local_instants(datetime(2026, 11, 1, 1, 30), zone)), 2)
        with self.assertRaises(ValueError):
            r.timestamp('2026-11-01T01:30:00', zone)
        out = self.lint(timezone='America/Los_Angeles', cron='30 2 * * *',
                        now=datetime(2027, 3, 14, 9, tzinfo=timezone.utc))
        self.assertEqual(out['local'], '2027-03-15T02:30:00-07:00')
        summer = self.lint(timezone='America/Los_Angeles',
                           now=datetime(2027, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(summer['utc_cron'], '0 23 * * 5')

    def test_json_events(self):
        command = [sys.executable, 'routine_lint.py', 'fixtures/events.json',
                   '--now', NOW.isoformat(), '--json']
        disconnected = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(disconnected.returncode, 1)
        connected = subprocess.run(command + ['--connected-source', 'mail'],
                                   text=True, capture_output=True)
        self.assertEqual(connected.returncode, 0, connected.stderr)
        self.assertEqual(json.loads(connected.stdout)['errors'], [])

    def test_cli(self):
        for filename, status in [('good.md', 0), ('bad.md', 1), ('missing.md', 1)]:
            proc = subprocess.run([sys.executable, 'routine_lint.py', 'fixtures/' + filename,
                                   '--now', NOW.isoformat(), '--json'], text=True, capture_output=True)
            self.assertEqual(proc.returncode, status, proc.stderr)
            self.assertIn('rows', json.loads(proc.stdout))
        self.assertEqual(len(r.read_rows(Path('fixtures/good.md'))), 2)


if __name__ == '__main__':
    unittest.main()
