# SPDX-License-Identifier: GPL-3.0-only
"""Real-file diagnostic capture fixtures, never application GUI evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

COLLECTOR = Path(__file__).resolve().parents[1] / 'collect_application_logs.py'


class ApplicationLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'Local' / 'Trieflow' / 'Audacity4'
        self.logs = self.root / 'logs'
        self.logs.mkdir(parents=True)
        self.output = self.base / 'evidence'
        self.output.mkdir()
        self.report = self.output / 'gui-observations.json'
        self.observation = dict(userStateBefore=[dict(path=str(self.root), exists=False)])
        self.log = self.logs / 'WaveQuay_260911_123500.log'

    def collect(self):
        self.assertTrue(COLLECTOR.is_file(), 'Application log collector is missing')
        self.report.write_text(json.dumps(self.observation), encoding='utf-8')
        result = subprocess.run([sys.executable, str(COLLECTOR), '--report', str(self.report)],
                                capture_output=True, text=True)
        metadata = json.loads((self.output / 'application-logs.json').read_text(encoding='utf-8'))
        return result, metadata

    def test_preserves_real_application_error_when_stdout_and_stderr_are_empty(self):
        for name in ('stdout.log', 'stderr.log'):
            (self.output / name).write_bytes(b'')
        data = b'12:35:01 | ERROR | Failed to load main qml file, err: Type WindowContent unavailable\n'
        self.log.write_bytes(data)
        (self.root / 'preferences.ini').write_text('private preference fixture')
        (self.logs / 'unrelated.txt').write_text('not a diagnostic log')
        result, metadata = self.collect()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(metadata['files']), 1)
        entry = metadata['files'][0]
        self.assertEqual((self.output / entry['path']).read_bytes(), data)
        self.assertEqual(entry['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(entry['sourcePath'], str(self.log))
        self.assertEqual(entry['sourceBytes'], len(data))
        self.assertEqual(entry['offset'], 0)
        self.assertEqual(entry['truncated'], False)
        self.assertEqual(self.log.read_bytes(), data)
        self.assertEqual(metadata['errors'], [])

    def test_existing_profile_refuses_all_collection(self):
        self.log.write_text('must not capture an existing profile')
        self.observation['userStateBefore'][0]['exists'] = True
        result, metadata = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(metadata['files'], [])
        self.assertTrue(metadata['errors'])

    def test_arbitrary_report_path_is_not_a_log_collection_root(self):
        self.log.write_text('private file')
        self.observation['userStateBefore'][0]['path'] = str(self.base)
        result, metadata = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(metadata['files'], [])

    def test_large_log_retains_bounded_tail_and_reports_truncation(self):
        data = b'A' * (3 * 1024 * 1024) + b'FINAL QML ERROR\n'
        self.log.write_bytes(data)
        result, metadata = self.collect()
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = metadata['files'][0]
        captured = (self.output / entry['path']).read_bytes()
        self.assertEqual(captured, data[-2 * 1024 * 1024:])
        self.assertEqual(entry['sourceBytes'], len(data))
        self.assertEqual(entry['offset'], len(data) - len(captured))
        self.assertTrue(entry['truncated'])
        self.assertEqual(entry['sha256'], hashlib.sha256(captured).hexdigest())

    def test_redirected_log_directory_is_not_followed(self):
        self.logs.rmdir()
        target = self.base / 'private'
        target.mkdir()
        (target / self.log.name).write_text('private log')
        if sys.platform == 'win32':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.logs), str(target)], check=True,
                           capture_output=True, text=True)
        else:
            self.logs.symlink_to(target, target_is_directory=True)
        result, metadata = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(metadata['files'], [])
        self.assertTrue(metadata['errors'])

    def test_missing_new_application_directory_is_diagnostic_not_fabricated(self):
        self.logs.rmdir()
        self.root.rmdir()
        result, metadata = self.collect()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(metadata['files'], [])
        self.assertEqual(metadata['errors'], [])
        self.assertEqual(metadata['roots'][0]['exists'], False)


if __name__ == '__main__':
    unittest.main()
