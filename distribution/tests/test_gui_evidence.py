# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic policy fixtures, not GUI execution or screenshots of WaveWeft."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib

VERIFIER = Path(__file__).resolve().parents[1] / 'verify_gui_evidence.py'


class GuiEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Evaluate the real complete release SetupConfigure, including version.cmake
        # and its final add_compile_definitions. No duplicate title formula or stubs.
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 3.24)\nproject(TitleContract LANGUAGES C CXX)\n'
                f'set(MUSE_FRAMEWORK_SRC_PATH "{(root / "muse/framework").as_posix()}")\n'
                f'list(APPEND CMAKE_MODULE_PATH "{root.as_posix()}" '
                f'"{(root / "muse/buildscripts/cmake").as_posix()}" '
                f'"{(root / "muse/framework/cmake").as_posix()}")\n'
                'include(SetupConfigure)\n'
                'get_directory_property(definitions COMPILE_DEFINITIONS)\n'
                'file(WRITE "${CMAKE_BINARY_DIR}/definitions.txt" "${definitions}")\n'
                'file(WRITE "${CMAKE_BINARY_DIR}/brand.txt" "${MUSE_APP_NAME}\\n${MUSE_APP_VERSION}\\n${MUSE_APP_GUI_IDENTIFIER}")\n', encoding='utf-8')
            configured = subprocess.run(['cmake', '-S', str(source), '-B', str(source / 'build'), '-G', 'Ninja',
                '-C', str(root / 'buildscripts/ci/windows/wavequay-release.cmake')], capture_output=True, text=True)
            if configured.returncode:
                raise AssertionError(configured.stdout + configured.stderr)
            cls.production_brand = (source / 'build/brand.txt').read_text(encoding='utf-8').splitlines()
            definitions = (source / 'build/definitions.txt').read_text(encoding='utf-8').split(';')
            title_definitions = [d for d in definitions if d.startswith('AU4_APP_TITLE_VERSION=')]
            if len(title_definitions) != 1:
                raise AssertionError(f'Expected exactly one actual compiler title definition: {definitions}')
            quoted_title = title_definitions[0].removeprefix('AU4_APP_TITLE_VERSION=')
            if not (quoted_title.startswith('"') and quoted_title.endswith('"')):
                raise AssertionError(f'Expected a quoted compiler title: {quoted_title!r}')
            cls.production_title = quoted_title[1:-1]

    def setUp(self):
        self.assertTrue(VERIFIER.is_file(), 'Staged GUI evidence verifier is not implemented')
        spec = importlib.util.spec_from_file_location('gui_evidence', VERIFIER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        mode = dict(width=1920, height=1080, bits=32, frequency=60, orientation=0, flags=0)
        self.display = dict(schema_version=1, source_commit='a' * 40, restore_error=None,
            display=dict(device='fixture-primary', before=mode, after=mode, restored=mode, restore_verified=True,
                selected=None, supported_modes=[mode], test_result=None, apply_result=None, restore_result=None,
                registry_updated=False, unsafe_modes_enabled=False, dpi_changed=False, renderer_emulation_used=False))
        self.write_display()
        # A deterministic PNG fixture; never represented as a product screenshot.
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
        pixels = b''.join(b'\0' + bytes(range(256)) * 9 + bytes(96) for _ in range(600))
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 800, 600, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
        (self.directory / 'fixture.png').write_bytes(png)
        self.screenshot = dict(path='fixture.png', sha256=hashlib.sha256(png).hexdigest(), width=800, height=600, sampledColors=256)
        self.inventory = [dict(path='bin/' + name, sha256=hashlib.sha256(name.encode()).hexdigest(), bytes=100)
                          for name in ('WaveWeft.exe', 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Qml.dll', 'Qt6Quick.dll', 'qwindows.dll')]
        self.report = dict(schemaVersion=1, sourceCommit='a' * 40, stageRoot=r'D:\a\stage', systemRoot=r'C:\Windows',
                           executable=r'D:\a\stage\bin\WaveWeft.exe', executableSha256=self.inventory[0]['sha256'],
                           processId=123, arguments=[], expectedMainWindowTitle=self.production_title, survivedUntilCleanup=True, errors=[],
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
            self.report['events'].append(dict(kind='main-window', title=self.production_title, processId=123, elapsedMs=when,
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
        try:
            self.verify()
        except ValueError as error:
            self.fail(f'Rejected actual configured title {self.production_title!r}: {error}')

    def test_exact_contextual_add_track_button_passes_with_plain_text_panel(self):
        for event in self.report['events'][3:]:
            event['tree'] = [self.node('Playback toolbar', 'Text'), self.node('Add track', 'Text'),
                             self.node('Add track panel, Add track', 'Button')]
        self.verify()

    def test_contextual_button_does_not_relax_role_ownership_visibility_or_exact_name(self):
        original = copy.deepcopy(self.report)
        for key, value in (('controlType', 'Text'), ('controlType', 'Pane'), ('enabled', False),
                           ('offscreen', True), ('processId', 999), ('name', 'Other panel, Add track'),
                           ('name', 'Add track panel, Add track extra'), ('name', 'Add track panel, Add track '),
                           ('name', 'prefix Add track'), ('name', 'Add track panel')):
            with self.subTest(key=key, value=value):
                self.report = copy.deepcopy(original)
                event = self.report['events'][-1]
                button = self.node('Add track panel, Add track', 'Button')
                button[key] = value
                event['tree'] = [self.node('Playback toolbar', 'Text'), self.node('Add track', 'Text'), button]
                self.reject()

    def install_captured_onboarding(self):
        path = Path(__file__).parent / 'fixtures/onboarding-34685414179.json'
        captured = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(captured['run_id'], 34685414179)
        self.assertEqual(captured['source_report_sha256'], '50e8a29f025aafe2a6c8b118c0d123e76e56cebbbac792058844f1097c2d7d4d')
        pid = captured['events'][0]['processId']
        self.report['processId'] = pid
        self.report['events'][:3] = copy.deepcopy(captured['events'])
        # Actual tree/input metadata in the synthetic policy harness; these
        # fixture pixels are never evidence of a real Windows capture.
        for event in self.report['events'][:3]:
            event['screenshot'] = copy.deepcopy(self.screenshot)
        for event, elapsed in zip(self.report['events'][3:], captured['main_elapsed_ms']):
            event['processId'] = pid
            event['elapsedMs'] = elapsed
            for node in event['tree']:
                node['processId'] = pid

    def test_actual_contextual_onboarding_page_and_native_input_replay(self):
        self.install_captured_onboarding()
        self.verify()

    def test_contextual_onboarding_keeps_exact_page_role_owner_and_visibility(self):
        self.install_captured_onboarding()
        original = copy.deepcopy(self.report)
        for index in (1, 2):
            event = original['events'][index]
            label = next(n['name'] for n in event['tree'] if ' panel, ' in n['name'])
            wrong_page = original['events'][3-index]['page']
            for key, value in (('controlType', 'Text'), ('controlType', 'Pane'), ('processId', 999),
                               ('enabled', False), ('offscreen', True), ('name', label + ' '),
                               ('name', 'Other panel, ' + event['page'] + '. ' + event['button']),
                               ('name', label.replace(event['page'] + '. ', wrong_page + '. ')),
                               ('name', label.replace('. ' + event['button'], '. Cancel')),
                               ('name', 'prefix ' + label)):
                with self.subTest(page=index, key=key, value=value):
                    self.report = copy.deepcopy(original)
                    node = next(n for n in self.report['events'][index]['tree'] if n['name'] == label)
                    node[key] = value
                    self.reject()

    def test_contextual_page_reading_node_does_not_replace_native_action_button(self):
        self.install_captured_onboarding()
        original = copy.deepcopy(self.report)
        for index in (1, 2):
            self.report = copy.deepcopy(original)
            event = self.report['events'][index]
            label = next(n['name'] for n in event['tree'] if ' panel, ' in n['name'])
            event['inputBefore']['name'] = label
            event['inputFinal']['name'] = label
            self.reject()

    def test_captured_contextual_pages_keep_the_other_report_gates(self):
        self.install_captured_onboarding()
        self.verify()
        original = copy.deepcopy(self.report)
        mutations = (
            (('sourceCommit',), 'b' * 40),
            (('executableSha256',), '0' * 64),
            (('modules', 1, 'sha256'), '0' * 64),
            (('events',), original['events'][:4]),
            (('events', 2, 'elapsedMs'), original['events'][1]['elapsedMs']),
            (('events', 4, 'elapsedMs'), original['events'][3]['elapsedMs'] + 2999),
            (('events', 2, 'screenshot', 'sha256'), '0' * 64),
            (('events', 2, 'sentInputs'), 1),
            (('events', 2, 'inputFinal', 'hitProcessId'), 999),
            (('cleanup', 'ownedJobClosed'), False),
            (('survivedUntilCleanup',), False),
            (('errors',), ['Observed startup error']),
        )
        for path, value in mutations:
            with self.subTest(path=path):
                self.report = copy.deepcopy(original)
                target = self.report
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.reject()

    def test_distribution_brand_and_version_come_from_actual_configuration(self):
        self.assertEqual(self.production_brand, ['WaveWeft', '1.0.1', 'com.trieflow.WaveQuay'])
        self.assertEqual(self.production_title, 'WaveWeft 1.0.1')

    def test_old_brand_title_and_executable_are_rejected(self):
        original = copy.deepcopy(self.report)
        self.report['events'][-1]['title'] = 'WaveQuay 4.0'
        self.reject()
        self.report = original
        self.report['executable'] = r'D:\a\stage\bin\WaveQuay.exe'
        self.reject()

    def test_shared_title_matches_actual_release_compile_definition(self):
        self.assertEqual(self.module.load_expected_title(), self.production_title)

    def test_main_window_title_matching_remains_exact(self):
        for title in (self.production_title.rsplit('.', 1)[0], self.production_title + ' extra',
                      self.production_title + ' ', 'prefix ' + self.production_title):
            with self.subTest(title=title):
                self.report['events'][-1]['title'] = title
                self.reject()

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

    def write_display(self):
        (self.directory / 'display-preparation.json').write_text(json.dumps(self.display))

    def test_native_click_requires_real_observed_button_and_stable_ownership(self):
        event = self.report['events'][1]
        event['interaction'] = 'owned-native-button-click'
        event['sentInputs'] = 2
        event['cursorPosition'] = [714,561]
        event['tree'].append(dict(self.node('Getting started', 'Window'), nativeWindowHandle=262498, bounds=[232,143,560,442]))
        event['tree'][1]['bounds'] = [648,547,132,28]
        snapshot = dict(name='Next', controlType='Button', windowTitle='Getting started', enabled=True, offscreen=False,
            matchingButtons=1, processId=123, nativeWindowProcessId=123, foregroundProcessId=123, hitProcessId=123,
            windowHandle=262498, foregroundHandle=262498, hitRootHandle=262498,
            buttonBounds=[648,547,132,28], windowBounds=[232,143,560,442], desktopBounds=[0,0,1920,1080], point=[714,561])
        event['inputBefore'] = copy.deepcopy(snapshot); event['inputFinal'] = copy.deepcopy(snapshot)
        self.verify()
        for field, value in [('processId',999),('nativeWindowProcessId',999),('foregroundProcessId',999),('hitProcessId',999),
                ('foregroundHandle',262616),('hitRootHandle',262616),('matchingButtons',2),('name','Clip visualization. Next'),
                ('enabled',False),('offscreen',True),('point',[0,0]),('buttonBounds',[0,0,132,28]),('desktopBounds',[0,0,700,500])]:
            with self.subTest(field=field):
                # Coherently mutate both snapshots: independent policy must reject.
                event['inputBefore'] = dict(snapshot, **{field: value}); event['inputFinal'] = dict(snapshot, **{field: value})
                self.reject()
        event['inputBefore'] = copy.deepcopy(snapshot); event['inputFinal'] = copy.deepcopy(snapshot)
        event['inputFinal']['desktopBounds'] = [0,0,2560,1440]; self.reject()
        event['inputFinal'] = copy.deepcopy(snapshot); event['sentInputs'] = 1; self.reject()
        event['sentInputs'] = 2; event['cursorPosition'] = [715,561]; self.reject()
        event['cursorPosition'] = [714,561]; event['tree'][1]['bounds'] = [647,547,132,28]; self.reject()

    def test_display_mutations_and_failed_restore_rejected(self):
        original = copy.deepcopy(self.display)
        for field, value in [('restore_verified',False),('restored',{}),('renderer_emulation_used',True),('registry_updated',True),
                              ('unsafe_modes_enabled',True),('dpi_changed',True),('after',dict(width=1024,height=768,bits=32))]:
            with self.subTest(field=field):
                self.display = copy.deepcopy(original); self.display['display'][field] = value; self.write_display(); self.reject()
        self.display = copy.deepcopy(original); self.display['source_commit'] = 'b' * 40; self.write_display(); self.reject()
        self.display = copy.deepcopy(original); d = self.display['display']; selected = copy.deepcopy(d['before'])
        d.update(before=dict(width=1024,height=768,bits=32,frequency=60,orientation=0,flags=0),selected=selected,
                 test_result=0,apply_result=0,restore_result=0)
        d['restored'] = copy.deepcopy(d['before']); self.write_display(); self.verify()
        for field, value in [('supported_modes',[]),('test_result',-1),('apply_result',-1),('restore_result',-1)]:
            with self.subTest(field=field):
                saved = d[field]; d[field] = value; self.write_display(); self.reject(); d[field] = saved

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

    def test_diagnostic_environment_requires_explicit_disposable_opt_in(self):
        self.report['environment'].update(CI='true', WAVEQUAY_STARTUP_DIAGNOSTICS='1')
        self.verify()
        for value in ('false', 'TRUE', ''):
            self.report['environment']['CI'] = value
            self.reject()
        self.report['environment']['CI'] = 'true'
        self.report['environment']['WAVEQUAY_STARTUP_DIAGNOSTICS'] = 'true'
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
