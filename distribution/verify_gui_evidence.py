# SPDX-License-Identifier: GPL-3.0-only
"""Fail-closed policy for observations captured by the native Windows UIA probe.

Synthetic unit fixtures exercise this policy only. Only a fresh Windows probe of
an inventoried stage can supply product qualification evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import struct

PAGES = (('Select a theme', 'Next'), ('Clip visualization', 'Next'),
         ('What UI layout (workspace) do you want?', 'Accept & continue'))
QT_MODULES = {'qt6core.dll', 'qt6gui.dll', 'qt6qml.dll', 'qt6quick.dll', 'qwindows.dll'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_expected_title():
    # Shared with the native launcher. A source-backed configure test compares
    # this exact value with SetupConfigure.cmake's AU4_APP_TITLE_VERSION.
    title = (Path(__file__).parent / 'windows-gui/expected-main-window-title.txt').read_text(encoding='utf-8').rstrip('\r\n')
    require(bool(title.strip()) and '\r' not in title and '\n' not in title, 'Invalid expected main-window title')
    return title


def windows_path(value):
    path = PureWindowsPath(value)
    require(path.is_absolute() and '..' not in path.parts, 'Noncanonical absolute Windows path: ' + value)
    return path


def visible_node(event, name, pid, button=False):
    return any(n.get('name') == name and n.get('processId') == pid and n.get('offscreen') is False
               and n.get('enabled') is True and (not button or n.get('controlType') == 'Button')
               for n in event['tree'])


def verify_native_click(event, button, pid):
    snapshots = (event.get('inputBefore'), event.get('inputFinal'))
    require(all(isinstance(v, dict) for v in snapshots) and event.get('sentInputs') == 2,
            'Native click lacks complete before/final/input observations')
    before, final = snapshots
    require(before == final, 'Onboarding input ownership or geometry changed')
    require(before.get('name') == button and before.get('controlType') == 'Button'
            and before.get('enabled') is True and before.get('offscreen') is False
            and before.get('windowTitle') == 'Getting started' and before.get('matchingButtons') == 1,
            'Native input target is not the unique visible onboarding button')
    for field in ('processId', 'nativeWindowProcessId', 'foregroundProcessId', 'hitProcessId'):
        require(type(before.get(field)) is int and before[field] == pid, 'Native input process ownership differs')
    handle = before.get('windowHandle')
    require(type(handle) is int and handle != 0 and before.get('foregroundHandle') == handle
            and before.get('hitRootHandle') == handle, 'Native click targeted another window')
    bounds = [before.get(field) for field in ('buttonBounds', 'windowBounds', 'desktopBounds')]
    require(all(isinstance(b, list) and len(b) == 4 and all(type(n) in (int, float) and math.isfinite(n) for n in b)
                and b[2] > 0 and b[3] > 0 for b in bounds), 'Invalid native input geometry')
    target, window, desktop = bounds
    require(event.get('cursorPosition') == before.get('point'), 'Cursor was not at the observed button before input')
    def contains(outer, inner):
        return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[0] + inner[2] <= outer[0] + outer[2] and inner[1] + inner[3] <= outer[1] + outer[3]
    require(target[2] >= 4 and target[3] >= 4 and contains(window, target) and contains(desktop, window)
            and before.get('point') == [math.floor(target[0] + target[2] / 2), math.floor(target[1] + target[3] / 2)],
            'Native click was outside the observed fully visible button/window')
    buttons = [n for n in event['tree'] if n.get('name') == button and n.get('controlType') == 'Button'
               and n.get('processId') == pid and n.get('enabled') is True and n.get('offscreen') is False]
    windows = [n for n in event['tree'] if n.get('name') == 'Getting started' and n.get('controlType') == 'Window'
               and n.get('processId') == pid and n.get('nativeWindowHandle') == handle]
    require(len(buttons) == 1 and buttons[0].get('bounds') == target and len(windows) == 1
            and windows[0].get('bounds') == window, 'Native click differs from the captured UIA button/window')


def verify_display(evidence_dir, expected_commit):
    path = Path(evidence_dir) / 'display-preparation.json'
    require(path.is_file() and not path.is_symlink(), 'Missing native display preparation/restore evidence')
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    require(record.get('schema_version') == 1 and record.get('source_commit') == expected_commit
            and record.get('restore_error') is None, 'Display evidence source/restoration differs')
    d = record['display']
    require(d['restore_verified'] is True and d['restored'] == d['before'] and bool(d['device']),
            'Original native display mode was not restored')
    require(all(d[k] is False for k in ('registry_updated', 'unsafe_modes_enabled', 'dpi_changed', 'renderer_emulation_used')),
            'Unapproved display preparation')
    require(d['after']['width'] >= 1472 and d['after']['height'] >= 1080 and d['after']['bits'] == 32,
            'Native display is inadequate for full-window evidence')
    if d['selected'] is not None:
        require(d['selected'] in d['supported_modes'] and d['after'] == d['selected']
                and d['test_result'] == 0 and d['apply_result'] == 0 and d['restore_result'] == 0,
                'Native display mode was not enumerated, tested, applied and restored')
    else:
        require(d['before'] == d['after'] and all(d[k] is None for k in ('test_result', 'apply_result', 'restore_result')),
                'Unchanged native display evidence differs')


def verify(report, inventory, evidence_dir, expected_commit):
    expected_title = load_expected_title()
    verify_display(evidence_dir, expected_commit)
    require(report.get('expectedMainWindowTitle') == expected_title, 'Observer used a different expected title')
    require(report['schemaVersion'] == 1 and report['sourceCommit'] == expected_commit, 'Wrong evidence/source revision')
    require(len(expected_commit) == 40, 'Expected an exact source commit')
    require(report['errors'] == [] and report['survivedUntilCleanup'] is True, 'Startup error or early exit')
    require(report['cleanup'] == {'ownedJobClosed': True, 'processExited': True}, 'Owned process cleanup failed')
    pid = report['processId']
    require(isinstance(pid, int) and pid > 0 and report['arguments'] == [], 'Unexpected launch identity/arguments')
    stage, system = windows_path(report['stageRoot']), windows_path(report['systemRoot'])
    executable = windows_path(report['executable'])
    require(executable == stage / 'bin' / 'WaveQuay.exe', 'Wrong staged executable')
    env = {k.upper(): v for k, v in report['environment'].items()}
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'USERPROFILE', 'APPDATA',
               'LOCALAPPDATA', 'TEMP', 'TMP', 'LANG', 'CI', 'WAVEQUAY_STARTUP_DIAGNOSTICS', 'QT_FORCE_STDERR_LOGGING', 'QT_DEBUG_PLUGINS'}
    require(set(env) <= allowed, 'Unexpected inherited environment')
    if 'WAVEQUAY_STARTUP_DIAGNOSTICS' in env:
        require(env['WAVEQUAY_STARTUP_DIAGNOSTICS'] == '1' and env.get('CI') == 'true',
                'Startup diagnostics require exact disposable-CI opt-in')
    require([windows_path(p) for p in env['PATH'].split(';')] ==
            [stage / 'bin', system / 'System32', system], 'PATH contains runner/build dependencies')
    require(windows_path(env['SYSTEMROOT']) == system, 'Wrong system root')
    require(report['userStateBefore'] and all(s['exists'] is False for s in report['userStateBefore']),
            'Existing profile state would bypass genuine onboarding')
    locked = {}
    for entry in inventory:
        path = PureWindowsPath(entry['path'])
        require(not path.is_absolute() and not path.drive and '..' not in path.parts and path not in locked,
                'Invalid or duplicate inventory entry')
        locked[path] = entry['sha256'].lower()
    require(locked[PureWindowsPath('bin/WaveQuay.exe')] == report['executableSha256'].lower(), 'Executable hash changed')
    loaded = set()
    for module in report['modules']:
        path = windows_path(module['path'])
        name = path.name.lower()
        if path.is_relative_to(stage):
            relative = path.relative_to(stage)
            require(relative in locked and module['sha256'].lower() == locked[relative], 'Changed/uninventoried staged module: ' + str(path))
            loaded.add(name)
        else:
            require(path.is_relative_to(system) and not name.startswith('qt') and name != 'qwindows.dll',
                    'Module resolved outside stage/Windows: ' + str(path))
    require(QT_MODULES | {'wavequay.exe'} <= loaded, 'Missing staged executable/Qt/platform module evidence')
    events = report['events']
    require(len(events) == 5, 'Require three onboarding pages and two stable main-window observations')
    previous_ms = -1
    for event in events:
        require(event['processId'] == pid and event['elapsedMs'] > previous_ms, 'Wrong process or observation order')
        previous_ms = event['elapsedMs']
        shot = event['screenshot']
        relative = Path(shot['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Screenshot escaped evidence directory')
        path = Path(evidence_dir) / relative
        require(path.is_file() and not path.is_symlink(), 'Missing screenshot')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == shot['sha256'].lower(), 'Screenshot hash changed')
        require(len(data) > 24 and data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR', 'Not a PNG screenshot')
        width, height = struct.unpack('!II', data[16:24])
        require((width, height) == (shot['width'], shot['height']) and width >= 400 and height >= 300
                and shot['sampledColors'] >= 16, 'Blank or implausible screenshot')
    for event, (page, button) in zip(events[:3], PAGES):
        require(event['kind'] == 'onboarding' and event['title'] == 'Getting started'
                and event['page'] == page and event['button'] == button, 'Unexpected onboarding page/order')
        require(visible_node(event, page, pid) or visible_node(event, page + '. ' + button, pid, button=True),
                'Missing real accessible onboarding page')
        if event['interaction'] == 'uia-invoke':
            require(any(n.get('invoke') and n.get('name') == button and n.get('enabled') is True
                        and n.get('offscreen') is False and n.get('processId') == pid and n.get('controlType') == 'Button'
                        for n in event['tree']), 'No accessible button was invoked')
        elif event['interaction'] == 'owned-native-button-click':
            verify_native_click(event, button, pid)
        else:
            require(event['interaction'] == 'uia-focused-enter' and event.get('focusedName') == page + '. ' + button
                    and event.get('focusedProcessId') == pid and event.get('foregroundProcessId') == pid,
                    'Keyboard input without verified accessible/foreground focus')
    for event in events[3:]:
        require(event['kind'] == 'main-window' and event['title'] == expected_title, 'Wrong main window')
        require(visible_node(event, 'Playback toolbar', pid) and visible_node(event, 'Add track', pid, button=True),
                'Missing meaningful editing controls')
        require(not any(n.get('name') == 'Getting started' for n in event['tree']), 'Onboarding still covers editor')
    require(events[4]['elapsedMs'] - events[3]['elapsedMs'] >= 3000, 'Main window did not remain available')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    verify(json.loads(args.report.read_text(encoding='utf-8-sig')),
           json.loads(args.inventory.read_text(encoding='utf-8-sig')), args.report.parent, args.source_commit)
    print('PASS: staged WaveQuay onboarding and main-window observations verified; audio/export/license gates remain open.')


if __name__ == '__main__':
    main()
