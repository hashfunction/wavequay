# SPDX-License-Identifier: GPL-3.0-only
"""Independent file-policy fixtures; these are never product UI evidence."""
import importlib.util
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import wave

SOURCE = Path(__file__).resolve().parents[1] / 'consumer_audio.py'


class ConsumerAudioTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('consumer_audio', SOURCE)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'fixture'
        self.claim = self.m.prepare(self.root, 'a' * 40)

    def exported(self, name='reversed.wav', reverse=True, channels=2, rate=44100):
        frames = self.m.demo_frames()
        if reverse:
            frames = frames[::-1]
        with wave.open(str(self.root / name), 'wb') as out:
            out.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
            out.writeframes(b''.join(frame[:channels * 2] for frame in frames))
        return self.root / name

    def test_generated_original_and_reversed_export(self):
        self.assertEqual(self.m.validate_audio(self.exported())['frames'], 264600)
        self.assertGreater(self.m.validate_audio(self.exported())['rms'], .01)

    def test_unedited_export_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'reversed'):
            self.m.validate_audio(self.exported(reverse=False))

    def test_wrong_rate_and_channels_rejected(self):
        for channels, rate in [(1, 44100), (2, 48000)]:
            with self.subTest(channels=channels, rate=rate), self.assertRaises(ValueError):
                self.m.validate_audio(self.exported(channels=channels, rate=rate))

    def test_truncated_audio_rejected(self):
        path = self.exported()
        path.write_bytes(path.read_bytes()[:-200])
        with self.assertRaises(ValueError):
            self.m.validate_audio(path)

    def test_original_is_protected(self):
        (self.root / 'Dawn-thread.wav').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'protected'):
            self.m.verify_claim(self.root, self.claim)

    def test_existing_fixture_not_adopted(self):
        with self.assertRaises(FileExistsError):
            self.m.prepare(self.root, 'a' * 40)

    def test_unexpected_file_blocks_cleanup_without_deleting_anything(self):
        (self.root / 'foreign.txt').write_text('untouched')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.m.fixture_snapshot(self.root, self.claim)
        self.assertTrue((self.root / 'Dawn-thread.wav').exists())

    def test_changed_snapshot_blocks_cleanup(self):
        snapshot = self.m.fixture_snapshot(self.root, self.claim)
        (self.root / 'protected.txt').write_text('changed')
        with self.assertRaises(ValueError):
            self.m.remove_snapshot(self.root, snapshot)
        self.assertTrue((self.root / 'Dawn-thread.wav').exists())

    def test_exact_cleanup_preserves_foreign_sibling(self):
        sibling = self.root.parent / 'foreign.txt'
        sibling.write_bytes(b'keep this original')
        observed = self.m.fixture_snapshot(self.root, self.claim)
        self.m.remove_snapshot(self.root, observed)
        self.assertFalse(self.root.exists())
        self.assertEqual(sibling.read_bytes(), b'keep this original')

    def test_unproved_process_or_child_stop_refuses_output_reads_and_cleanup(self):
        output = self.root.parent
        renamed = output / 'consumer-fixture'
        self.root.rename(renamed)
        self.root = renamed
        (output / 'consumer-fixture-claim.json').write_text(json.dumps(self.claim))
        for cleanup, empty in [(dict(ownedJobClosed=False, processExited=False), False),
                               (dict(ownedJobClosed=True, processExited=True), False)]:
            (output / 'gui-observations.json').write_text(json.dumps(dict(sourceCommit='a' * 40,
                cleanup=cleanup, ownedJobEmptyBeforeClose=empty)))
            result = self.m.finalize(output, 'a' * 40)
            self.assertFalse(result['verified'])
            self.assertFalse(result['cleanup'])
            self.assertTrue((renamed / 'Dawn-thread.wav').exists())
            self.assertNotIn('files', result)
            (output / 'consumer-validation.json').unlink()

    def test_symlink_refused(self):
        (self.root / 'reversed.wav').symlink_to(self.root / 'Dawn-thread.wav')
        with self.assertRaises(ValueError):
            self.m.fixture_snapshot(self.root, self.claim)

    def test_recipe_requires_exact_settings_and_no_media_paths(self):
        recipe = dict(schemaVersion=1, id='11111111-1111-4111-8111-111111111111', name='Dawn thread stereo',
                      format='WAV', process=0, channelType=2, channels=2, sampleRate=44100,
                      trimBlankSpace=True, mapping=[], parameters=[dict(id=65536, type=1, value=2)])
        store = dict(schemaVersion=1, recipes=[recipe])
        self.m.validate_recipe(store)
        for key, value in [('channels', 1), ('format', 'MP3'), ('filename', 'private.wav')]:
            altered = json.loads(json.dumps(store))
            altered['recipes'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.m.validate_recipe(altered)

    def test_read_only_saved_project_checks_real_sqlite_structure(self):
        path = self.root / 'Dawn-thread.aup4'
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript('PRAGMA application_id=1096107097; CREATE TABLE project(id INTEGER,dict BLOB,doc BLOB);'
                             'CREATE TABLE sampleblocks(samples BLOB);')
            db.execute('INSERT INTO project VALUES(1,?,?)', (b'fixture dictionary', b'fixture document'))
            db.execute('INSERT INTO sampleblocks VALUES(?)', (bytes(self.m.FRAMES * 4),))
        before = path.read_bytes()
        self.assertEqual(self.m.validate_project(path)['applicationId'], 'AUDY')
        self.assertEqual(path.read_bytes(), before)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('DELETE FROM sampleblocks')
        with self.assertRaisesRegex(ValueError, 'audio blocks'):
            self.m.validate_project(path)

    def test_audio_renamed_as_project_rejected(self):
        path = self.exported(name='Dawn-thread.aup4')
        with self.assertRaisesRegex(ValueError, 'Invalid saved project'):
            self.m.validate_project(path)

    def test_project_inspection_closes_connection_on_success_and_both_failures(self):
        path = self.root / 'Dawn-thread.aup4'
        connect = sqlite3.connect
        for case in ('valid', 'wrong-application', 'invalid-database'):
            with self.subTest(case=case):
                if path.exists():
                    path.unlink()
                if case == 'invalid-database':
                    path.write_bytes(b'not a database' * 1024)
                else:
                    with closing(connect(path)) as db, db:
                        db.executescript('PRAGMA application_id=1096107097; CREATE TABLE project(id INTEGER,dict BLOB,doc BLOB);'
                                         'CREATE TABLE sampleblocks(samples BLOB);')
                        db.execute('INSERT INTO project VALUES(1,?,?)', (b'dictionary', b'document'))
                        db.execute('INSERT INTO sampleblocks VALUES(?)', (bytes(self.m.FRAMES * 4),))
                        if case == 'wrong-application':
                            db.execute('PRAGMA application_id=7')
                connections = []
                def retain_connection(*args, **kwargs):
                    connection = connect(*args, **kwargs)
                    connections.append(connection)
                    return connection
                try:
                    with patch.object(self.m.sqlite3, 'connect', side_effect=retain_connection):
                        if case == 'valid':
                            self.assertEqual(self.m.validate_project(path)['applicationId'], 'AUDY')
                        else:
                            with self.assertRaises(ValueError):
                                self.m.validate_project(path)
                    self.assertEqual(len(connections), 1)
                    # Keep a strong reference: garbage collection must not own cleanup.
                    with self.assertRaisesRegex(sqlite3.ProgrammingError, 'closed'):
                        connections[0].execute('SELECT 1')
                finally:
                    for connection in connections:
                        connection.close()

    def test_profile_marker_and_native_root_mapping_required(self):
        profile = self.root.parent / 'Audacity4'
        profile.mkdir()
        marker = '.waveweft-consumer-owner'
        token = self.claim['token']
        (profile / marker).write_text(token)
        gui = dict(consumerProfileClaim=dict(token=token, marker=marker, paths=[str(profile)], registry=[]),
                   userStateBefore=[dict(path=str(profile), exists=False)])
        with patch.object(self.m, 'host_profile_roots', return_value={profile}):
            self.assertEqual(len(self.m.profile_inventory(self.root.parent, gui)), 1)
            (profile / marker).write_text('foreign owner')
            with self.assertRaisesRegex(ValueError, 'marker changed'):
                self.m.profile_inventory(self.root.parent, gui)
        (profile / marker).write_text(token)
        with patch.object(self.m, 'host_profile_roots', return_value=set()):
            with self.assertRaisesRegex(ValueError, 'not exclusively claimed'):
                self.m.profile_inventory(self.root.parent, gui)

    def test_unproved_normal_close_and_foreign_process_are_rejected_before_outputs(self):
        gui = dict(sourceCommit='a' * 40, processId=12, consumerClosedNormally=True)
        base = dict(sourceCommit='a' * 40, processId=12, completed=True, errors=[], normalCloseExitCode=0, observations=[])
        for field, value in [('processId', 13), ('sourceCommit', 'b' * 40), ('completed', False), ('normalCloseExitCode', 9), ('normalCloseExitCode', False)]:
            flow = dict(base, **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.m.validate_flow(self.root.parent, flow, gui)


if __name__ == '__main__':
    unittest.main()
