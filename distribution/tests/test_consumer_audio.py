# SPDX-License-Identifier: GPL-3.0-only
"""Independent file-policy fixtures; these are never product UI evidence."""
import importlib.util
import copy
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

    def test_installed_profile_read_requires_fixed_family_absent_before_and_owner(self):
        self.assertTrue(hasattr(self.m, 'package_profile_inventory'), 'Installed package profile observation is absent')
        output = self.root.parent
        profile = output / 'package-data'; profile.mkdir()
        token = '11111111-1111-4111-8111-111111111111'
        marker = profile / '.waveweft-msix-owner'; marker.write_text(token)
        (profile / 'LocalCache').mkdir(); (profile / 'LocalCache/actual.txt').write_text('actual app data')
        family = '1659hashfunction.WaveQuay_r3hxytd7jt6c4'
        full = '1659hashfunction.WaveQuay_1.0.1.0_x64__r3hxytd7jt6c4'
        claim = dict(schemaVersion=1, sourceCommit='a' * 40, identityMode='store', packageFamilyName=family,
                     packageFullName=full, dataRoot=str(profile), preinstallDataRootAbsent=True, token=token)
        path = output / 'installed-profile-claim.json'; path.write_text(json.dumps(claim))
        gui = dict(sourceCommit='a' * 40, installedLaunch=dict(identityMode='store', packageFamilyName=family,
                   packageFullName=full, packageDataRoot=str(profile)))
        with patch.object(self.m, 'package_data_root', return_value=profile):
            observed = self.m.package_profile_inventory(output, gui)
            self.assertEqual(observed[0][0], profile)
            self.assertEqual(observed[0][1]['LocalCache/actual.txt'], self.m.digest(profile / 'LocalCache/actual.txt'))
            claim['preinstallDataRootAbsent'] = False; path.write_text(json.dumps(claim))
            with self.assertRaises(ValueError): self.m.package_profile_inventory(output, gui)
            claim['preinstallDataRootAbsent'] = True; path.write_text(json.dumps(claim)); marker.write_text('foreign')
            with self.assertRaises(ValueError): self.m.package_profile_inventory(output, gui)
        self.assertEqual((profile / 'LocalCache/actual.txt').read_text(), 'actual app data')

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

    def test_private_desktop_uses_existing_complete_inventory_and_owned_cleanup(self):
        private = self.root.parent / 'private-environment'
        desktop = private / 'Desktop'
        desktop.mkdir(parents=True)
        token = self.claim['token']
        marker = '.waveweft-consumer-owner'
        (private / marker).write_text(token)
        foreign = self.root.parent / 'Desktop'
        foreign.mkdir()
        sentinel = foreign / 'original.txt'
        sentinel.write_text('retain outside the claimed private environment')
        gui = dict(consumerProfileClaim=dict(token=token, marker=marker, paths=[str(private)], registry=[]),
                   userStateBefore=[])
        with patch.object(self.m, 'host_profile_roots', return_value=set()):
            inventory = self.m.profile_inventory(self.root.parent, gui)
        self.assertEqual(inventory[0][0], private)
        self.assertEqual(inventory[0][1]['Desktop'], {'directory': True})
        # A change after the complete stopped-process snapshot still blocks all deletion.
        added = desktop / 'changed.txt'
        added.write_text('new bytes after snapshot')
        with self.assertRaisesRegex(ValueError, 'changed after observation'):
            self.m.remove_snapshot(private, inventory[0][1])
        self.assertTrue((private / marker).exists())
        self.assertEqual(added.read_text(), 'new bytes after snapshot')
        with patch.object(self.m, 'host_profile_roots', return_value=set()):
            fresh = self.m.profile_inventory(self.root.parent, gui)
        self.m.remove_snapshot(private, fresh[0][1])
        self.assertFalse(private.exists())
        self.assertEqual(sentinel.read_text(), 'retain outside the claimed private environment')

    def test_unproved_normal_close_and_foreign_process_are_rejected_before_outputs(self):
        gui = dict(sourceCommit='a' * 40, processId=12, consumerClosedNormally=True)
        base = dict(sourceCommit='a' * 40, processId=12, completed=True, errors=[], normalCloseExitCode=0, observations=[])
        for field, value in [('processId', 13), ('sourceCommit', 'b' * 40), ('completed', False), ('normalCloseExitCode', 9), ('normalCloseExitCode', False)]:
            flow = dict(base, **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.m.validate_flow(self.root.parent, flow, gui)

    def menu_flow(self):
        # Actual Special UIA label/role/geometry from run 34694396308. Owner,
        # foreground and unseen Reverse geometry are policy fixture inputs.
        target = dict(name='Special Menu', role='MenuItem', title='Audacity4', identity='fixture-item',
                      pid=6484, nativePid=6484, foregroundPid=6484, hitPid=6484, matches=1,
                      window=393616, foreground=262212, hitRoot=393616, main=262212, owned=True, enabled=True, offscreen=False,
                      targetBounds=[699,445,209,32], windowBounds=[691,119,225,442], desktopBounds=[0,0,1920,1080], point=[803,461])
        snap = dict(target=target, mainPid=6484, mainTitle='Dawn-thread * - WaveWeft 1.0.1', mainBounds=[377,89,1166,839],
                    popupIdentity='fixture-root', popupRole='Window', popupClass='QQuickView',
                    popupAutomationId='muse::accessibility::AccessibleAppRootObject.MenuView_WindowView_QQuickView',
                    popupEnabled=True, popupVisible=True, targetInPopup=True,
                    owners=[dict(window=393616, owner=262212, pid=6484), dict(window=262212, owner=0, pid=6484)])
        action='reverse-selected-audio'
        click=copy.deepcopy(snap);click['target']['name']='Reverse'
        return dict(processId=6484, mainWindowHandle=262212, inputs=[
            dict(action=action, kind='keys', keys=[17,65]),
            dict(action=action, kind='click', before=dict(name='Effect',role='Button')),
            dict(action=action, kind='menu-hover', before=snap, final=copy.deepcopy(snap), positioned=True),
            dict(action=action, kind='menu-click', before=click, final=copy.deepcopy(click), sent=2)])

    def test_exact_effect_pointer_sequence_and_mutations(self):
        self.assertTrue(hasattr(self.m, 'validate_effect_pointer_inputs'), 'Independent pointer receipt gate absent')
        base=self.menu_flow(); self.m.validate_effect_pointer_inputs(base)
        for field,value in [('pid',99),('nativePid',99),('foregroundPid',99),('hitPid',99),('main',1),('window',1),
                            ('foreground',393616),('hitRoot',262212),('matches',2),('name','Special'),('role','Text'),
                            ('owned',False),('enabled',False),('offscreen',True),('identity','changed'),
                            ('targetBounds',[699,445,209,999]),('point',[803,460]),('desktopBounds',[0,0,1024,768])]:
            flow=copy.deepcopy(base);flow['inputs'][2]['final']['target'][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):self.m.validate_effect_pointer_inputs(flow)
        for field,value in [('mainPid',1),('mainTitle','foreign'),('popupClass','foreign'),('popupRole','Pane'),
                            ('popupAutomationId','foreign'),('popupIdentity','changed'),('popupEnabled',False),('popupVisible',False),
                            ('targetInPopup',False),('owners',[]),('mainBounds',[377,89,99999,839])]:
            flow=copy.deepcopy(base);flow['inputs'][3]['final'][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):self.m.validate_effect_pointer_inputs(flow)
        for change in ('missing-hover','double-click','wrong-action','partial-click','position-not-proved','swapped', 'foreign-owner'):
            flow=copy.deepcopy(base)
            if change=='missing-hover':flow['inputs'].pop(2)
            elif change=='double-click':flow['inputs'].append(copy.deepcopy(flow['inputs'][-1]))
            elif change=='wrong-action':flow['inputs'][3]['action']='export'
            elif change=='partial-click':flow['inputs'][3]['sent']=1
            elif change=='position-not-proved':flow['inputs'][2]['positioned']=1
            elif change=='swapped':flow['inputs'][2:]=reversed(flow['inputs'][2:])
            else:flow['inputs'][2]['final']['owners'][0]['owner']=99
            with self.subTest(change=change), self.assertRaises(ValueError):self.m.validate_effect_pointer_inputs(flow)


if __name__ == '__main__':
    unittest.main()
