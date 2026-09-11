# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic policy fixtures, not GUI execution or screenshots of WaveQuay."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

VERIFIER = Path(__file__).resolve().parents[1] / 'verify_gui_evidence.py'


class GuiEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(VERIFIER.is_file(), 'Staged GUI evidence verifier is not implemented')
        spec = importlib.util.spec_from_file_location('gui_evidence', VERIFIER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        # A deterministic PNG fixture; never represented as a product screenshot.
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
        pixels = b''.join(b'\0' + bytes(range(256)) * 9 + bytes(96) for _ in range(600))
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 800, 600, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
        (self.directory / 'fixture.png').write_bytes(png)
        self.screenshot = dict(path='fixture.png', sha256=hashlib.sha256(png).hexdigest(), width=800, height=600, sampledColors=256)
        self.inventory = [dict(path='bin/' + name, sha256=hashlib.sha256(name.encode()).hexdigest(), bytes=100)
                          for name in ('WaveQuay.exe', 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Qml.dll', 'Qt6Quick.dll', 'qwindows.dll')]
        self.report = dict(schemaVersion=1, sourceCommit='a' * 40, stageRoot=r'D:\a\stage', systemRoot=r'C:\Windows',
                           executable=r'D:\a\stage\bin\WaveQuay.exe', executableSha256=self.inventory[0]['sha256'],
                           processId=123, arguments=[], survivedUntilCleanup=True, errors=[],
                           cleanup=dict(ownedJobClosed=True, processExited=True),
                           userStateBefore=[dict(path=r'C:\Users\runner\AppData\Local\Trieflow LLC\WaveQuay', exists=False)],
                           environment={'PATH': r'D:\a\stage\bin;C:\Windows\System32;C:\Windows', 'SystemRoot': r'C:\Windows'},
                           modules=[dict(path='D:\\a\\stage\\' + entry['path'].replace('/', '\\'), sha256=entry['sha256']) for entry in self.inventory],
                           events=[])
        for index, (page, button) in enumerate((('Select a theme', 'Next'), ('Clip visualization', 'Next'), ('What UI layout (workspace) do you want?', 'Accept & continue'))):
            self.report['events'].append(dict(kind='onboarding', title='Getting started', page=page, button=button,
                processId=123, elapsedMs=1000 + index * 1500, interaction='uia-invoke',
                tree=[self.node(page, 'Pane'), self.node(button, 'Button', invoke=True)], screenshot=copy.deepcopy(self.screenshot)))
        for when in (6000, 9500):
            self.report['events'].append(dict(kind='main-window', title='WaveQuay 4', processId=123, elapsedMs=when,
                tree=[self.node('Playback toolbar', 'ToolBar'), self.node('Add track', 'Button', invoke=True)],
                screenshot=copy.deepcopy(self.screenshot)))

    @staticmethod
    def node(name, role, invoke=False):
        return dict(name=name, controlType=role, enabled=True, offscreen=False, invoke=invoke, processId=123)

    def verify(self):
        return self.module.verify(self.report, self.inventory, self.directory, 'a' * 40)

    def reject(self):
        with self.assertRaises(ValueError):
            self.verify()

    def test_complete_staged_observations_pass(self):
        self.verify()

    def test_missing_main_window_rejects_splash_only(self):
        self.report['events'] = self.report['events'][:3]
        self.reject()

    def test_early_exit_rejects_even_with_previous_main_window(self):
        self.report['survivedUntilCleanup'] = False
        self.reject()

    def test_error_dialog_rejects_even_with_main_window(self):
        self.report['errors'].append('Native dialog: Missing Qt6Core.dll')
        self.reject()

    def test_wrong_title_and_missing_or_disabled_editor_controls_reject(self):
        for field, value in (('title', 'Audacity 4'), ('tree', []), ('tree', [self.node('Playback toolbar', 'ToolBar')])):
            with self.subTest(field=field, value=value):
                report = copy.deepcopy(self.report)
                self.report['events'][-1][field] = value
                self.reject()
                self.report = report
        self.report['events'][-1]['tree'][-1]['enabled'] = False
        self.reject()

    def test_hidden_or_foreign_editor_controls_do_not_count(self):
        for key, value in (('offscreen', True), ('processId', 999)):
            with self.subTest(key=key):
                self.report['events'][-1]['tree'][-1][key] = value
                self.reject()
                self.report['events'][-1]['tree'][-1][key] = False if key == 'offscreen' else 123

    def test_onboarding_must_be_three_pages_in_order(self):
        self.report['events'][0], self.report['events'][1] = self.report['events'][1], self.report['events'][0]
        self.reject()

    def test_unverified_keyboard_action_rejected(self):
        self.report['events'][0]['interaction'] = 'uia-focused-enter'
        self.reject()
        self.report['events'][0]['focusedName'] = 'Select a theme. Next'
        self.report['events'][0]['focusedProcessId'] = 123
        self.report['events'][0]['foregroundProcessId'] = 123
        self.verify()

    def test_too_short_observation_rejected(self):
        self.report['events'][-1]['elapsedMs'] = 6001
        self.reject()

    def test_runner_qt_or_path_prefix_lookalike_rejected(self):
        for foreign in (r'D:\Qt\6.11.2\bin\Qt6Core.dll', r'D:\a\stage-evil\bin\Qt6Core.dll', r'D:\a\stage\..\Qt6Core.dll'):
            with self.subTest(path=foreign):
                self.report['modules'][1]['path'] = foreign
                self.reject()

    def test_uninventoried_or_changed_staged_module_rejected(self):
        self.report['modules'][1]['sha256'] = '0' * 64
        self.reject()
        self.report['modules'][1]['sha256'] = self.inventory[1]['sha256']
        self.inventory.pop(1)
        self.reject()

    def test_missing_platform_plugin_rejected(self):
        self.report['modules'].pop()
        self.reject()

    def test_changed_executable_and_source_commit_rejected(self):
        self.report['executableSha256'] = '0' * 64
        self.reject()
        self.report['executableSha256'] = self.inventory[0]['sha256']
        self.report['sourceCommit'] = 'b' * 40
        self.reject()

    def test_system_dll_allowed_but_external_qt_not_system_dll(self):
        self.report['modules'].append(dict(path=r'C:\Windows\System32\kernel32.dll', sha256='0' * 64))
        self.verify()
        self.report['modules'].append(dict(path=r'C:\Windows\System32\Qt6Core.dll', sha256='0' * 64))
        self.reject()

    def test_inherited_qt_environment_and_contaminated_path_rejected(self):
        self.report['environment']['QT_PLUGIN_PATH'] = r'D:\Qt\plugins'
        self.reject()
        self.report['environment'].pop('QT_PLUGIN_PATH')
        self.report['environment']['PATH'] += r';D:\Qt\bin'
        self.reject()

    def test_existing_user_state_rejected_without_resetting_it(self):
        self.report['userStateBefore'][0]['exists'] = True
        self.reject()

    def test_missing_changed_or_blank_screenshot_rejected(self):
        self.report['events'][-1]['screenshot']['sampledColors'] = 1
        self.reject()
        self.report['events'][-1]['screenshot']['sampledColors'] = 256
        (self.directory / 'fixture.png').write_bytes(b'changed')
        self.reject()

    def test_cleanup_failure_rejected(self):
        self.report['cleanup']['processExited'] = False
        self.reject()


if __name__ == '__main__':
    unittest.main()
