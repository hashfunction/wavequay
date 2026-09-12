# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Trieflow LLC
"""Original demo fixture, independent audio checks, and stopped-owner cleanup.

This module never drives the product or writes its preferences/project/recipe.
The original six-second stereo composition is dedicated to CC0 by Trieflow LLC.
Output receipts are metadata; fixture WAV/project/profile payloads are not uploaded.
"""
import argparse
from contextlib import closing
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import struct
import uuid
import wave

RATE, FRAMES = 44100, 264600
RECIPE = 'Dawn thread stereo'
FIXTURE_FILES = {'.owner.json', 'Dawn-thread.wav', 'protected.txt', 'Dawn-thread.aup4',
                 'Dawn-thread.aup4-wal', 'Dawn-thread.aup4-shm', 'reversed.wav', 'reopened.wav'}


def require(value, message):
    if not value:
        raise ValueError(message)


def no_redirect(path):
    for item in (path, *path.parents):
        if not item.exists() and not item.is_symlink():
            continue
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                f'Redirected path: {item}')


def digest(path):
    no_redirect(path)
    require(path.is_file() and path.stat().st_size <= 128 * 1024 * 1024, f'Not a bounded regular file: {path}')
    before = path.stat()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'File replaced before reading')
        value = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()
        after = os.fstat(stream.fileno())
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'File changed while reading')
    return dict(bytes=before.st_size, sha256=value)


@lru_cache(maxsize=1)
def demo_frames():
    # A changing three-note motif with independent stereo parts; reversing this
    # audio is distinguishable from copying, silence, channel swaps or a trim.
    frames = []
    for n in range(FRAMES):
        t = n / RATE
        note = (220., 329.6275569, 293.6647679)[min(2, int(t / 2))]
        envelope = min(1., t / .06, (6. - t) / .14) * (.65 + .3 * math.sin(2 * math.pi * .37 * t))
        left = envelope * (.23 * math.sin(2 * math.pi * note * t) + .07 * math.sin(2 * math.pi * 2 * note * t))
        right = envelope * (.19 * math.sin(2 * math.pi * 1.5 * note * t + .3) + .06 * math.sin(2 * math.pi * 3 * note * t))
        frames.append(struct.pack('<hh', round(left * 32767), round(right * 32767)))
    return tuple(frames)


def prepare(root, source_commit):
    require(re.fullmatch('[0-9a-f]{40}', source_commit), 'Exact source commit required')
    no_redirect(root.parent)
    root.mkdir()  # exclusive: never adopt a pre-existing fixture
    claim = dict(schemaVersion=1, sourceCommit=source_commit, token=str(uuid.uuid4()), protected={})
    with wave.open(str(root / 'Dawn-thread.wav'), 'wb') as output:
        output.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        output.writeframes(b''.join(demo_frames()))
    (root / 'protected.txt').write_bytes(b'WaveWeft consumer fixture: preserve these original bytes.\n')
    claim['protected'] = {name: digest(root / name) for name in ('Dawn-thread.wav', 'protected.txt')}
    with (root / '.owner.json').open('x', encoding='utf-8') as output:
        json.dump(claim, output, indent=2)
    return claim


def verify_claim(root, claim):
    no_redirect(root)
    require(json.loads((root / '.owner.json').read_text()) == claim, 'Fixture owner marker changed')
    require(set(claim['protected']) == {'Dawn-thread.wav', 'protected.txt'}, 'Invalid protected file claim')
    for name, expected in claim['protected'].items():
        require(digest(root / name) == expected, f'Changed protected input: {name}')


def snapshot(root):
    no_redirect(root)
    result = {}
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(folder) / name
            no_redirect(path)
            relative = path.relative_to(root).as_posix()
            result[relative] = {'directory': True} if path.is_dir() else digest(path)
            require(len(result) <= 1000, 'Owned cleanup inventory exceeded 1000 entries')
    require(sum(item.get('bytes', 0) for item in result.values()) <= 256 * 1024 * 1024, 'Owned cleanup inventory exceeded 256MiB')
    return result


def fixture_snapshot(root, claim):
    verify_claim(root, claim)
    observed = snapshot(root)
    require(set(observed) <= FIXTURE_FILES, 'Unexpected fixture file; preserve the entire fixture')
    require(not any('directory' in item for item in observed.values()), 'Unexpected fixture directory')
    return observed


def remove_snapshot(root, observed):
    require(snapshot(root) == observed, 'Owned tree changed after observation; cleanup refused')
    # Validate the entire tree before the first deletion, and each file again
    # immediately before unlink. Never recursively delete a discovered target.
    for name in sorted(observed, key=lambda x: (-len(Path(x).parts), x)):
        path = root / name
        no_redirect(path)
        if observed[name] == {'directory': True}:
            path.rmdir()
        else:
            require(digest(path) == observed[name], 'Owned file changed before cleanup')
            path.unlink()
    root.rmdir()


def validate_audio(path):
    file_info = digest(path)
    try:
        with wave.open(str(path), 'rb') as audio:
            require((audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes(), audio.getcomptype())
                    == (2, 2, RATE, FRAMES, 'NONE'), 'Export rate/channels/encoding/duration differs')
            pcm = audio.readframes(FRAMES + 1)
    except (EOFError, wave.Error) as error:
        raise ValueError(f'Invalid WAV: {error}') from error
    require(len(pcm) == FRAMES * 4, 'Truncated audio data')
    expected = b''.join(reversed(demo_frames()))
    actual_samples = struct.unpack('<' + 'h' * (FRAMES * 2), pcm)
    expected_samples = struct.unpack('<' + 'h' * (FRAMES * 2), expected)
    # Float pipeline -> PCM16 may dither by a few LSB. Permit that bounded
    # quantization, never a shifted, attenuated, unedited or partly reversed file.
    errors = [abs(a - b) for a, b in zip(actual_samples, expected_samples)]
    require(max(errors) <= 4 and sum(errors) / len(errors) <= 1.5, 'Export does not contain the complete reversed original stereo audio')
    rms = math.sqrt(sum((v / 32768.) ** 2 for v in actual_samples) / len(actual_samples))
    require(.01 < rms < .5 and max(abs(v) for v in actual_samples) < 32760, 'Silent or clipped export')
    return dict(**file_info, frames=FRAMES, sampleRate=RATE, channels=2, bits=16, seconds=6,
                rms=rms, maximumErrorLsb=max(errors), meanErrorLsb=sum(errors) / len(errors), pcmSha256=hashlib.sha256(pcm).hexdigest())


def validate_project(path):
    info = digest(path)
    require(info['bytes'] > 4096, 'Saved project absent/empty')
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as database:
            require(database.execute('PRAGMA integrity_check').fetchone() == ('ok',), 'Saved project integrity failed')
            require(database.execute('PRAGMA application_id').fetchone() == (0x41554459,), 'Saved file is not an Audacity project')
            project = database.execute('SELECT id,length(dict),length(doc) FROM project').fetchall()
            require(len(project) == 1 and project[0][0] == 1 and project[0][1] > 0 and project[0][2] > 0, 'Saved project document missing')
            blocks, samples = database.execute('SELECT count(*),sum(length(samples)) FROM sampleblocks').fetchone()
            require(blocks > 0 and samples >= FRAMES * 4, 'Saved project audio blocks missing')
    except sqlite3.Error as error:
        raise ValueError(f'Invalid saved project: {error}') from error
    require(digest(path) == info, 'Project changed during independent inspection')
    return dict(**info, applicationId='AUDY', documentBytes=project[0][2], blocks=blocks, sampleBytes=samples, integrity='ok')


def validate_effect_pointer_inputs(flow):
    """Independently verify the two exact non-activating menu pointer actions."""
    events = [e for e in flow['inputs'] if e['action'] == 'reverse-selected-audio']
    require([e['kind'] for e in events] == ['keys', 'click', 'menu-hover', 'menu-click'],
            'Effect pointer route is partial, repeated or reordered')
    require(events[0]['keys'] == [17, 65] and events[1]['before']['name'] == 'Effect'
            and events[1]['before']['role'] == 'Button', 'Effect pointer route did not select audio and open Effect')
    require(events[2].get('positioned') is True and type(events[3].get('sent')) is int and events[3]['sent'] == 2,
            'Effect pointer positioning/click incomplete')
    pid, main = flow['processId'], flow['mainWindowHandle']
    def rect(r):
        return isinstance(r, list) and len(r) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in r) and min(r[2:]) >= 2
    def contains(a, b):
        return b[0] >= a[0] and b[1] >= a[1] and b[0]+b[2] <= a[0]+a[2] and b[1]+b[3] <= a[1]+a[3]
    for event, name in zip(events[2:], ('Special Menu', 'Reverse')):
        for snap in (event['before'], event['final']):
            target = snap['target']; window = target['window']
            require(type(window) is int and window > 0 and window != main and target['main'] == main
                    and type(target['matches']) is int and target['matches'] == 1 and target['name'] == name
                    and target['role'] == 'MenuItem' and target['title'] == 'Audacity4' and target['identity']
                    and all(target[k] is True for k in ('owned', 'enabled')) and target['offscreen'] is False
                    and snap['targetInPopup'] is True, 'Effect menu target identity/role/visibility differs')
            require(all(target[k] == pid for k in ('pid', 'nativePid', 'foregroundPid', 'hitPid')) and snap['mainPid'] == pid
                    and target['foreground'] == main and target['hitRoot'] == window, 'Effect menu native ownership differs')
            require(snap['mainTitle'] == 'Dawn-thread * - WaveWeft 1.0.1' and snap['popupRole'] == 'Window'
                    and snap['popupClass'] == 'QQuickView' and snap['popupIdentity']
                    and snap['popupAutomationId'] == 'muse::accessibility::AccessibleAppRootObject.MenuView_WindowView_QQuickView'
                    and snap['popupEnabled'] is True and snap['popupVisible'] is True, 'Effect menu popup identity differs')
            owners = snap['owners']
            require(isinstance(owners, list) and 2 <= len(owners) <= 12
                    and owners[0]['window'] == window and owners[-1]['window'] == main
                    and all(o['pid'] == pid and type(o['window']) is int and o['window'] > 0 for o in owners)
                    and len({o['window'] for o in owners}) == len(owners)
                    and all(o['owner'] == nxt['window'] and o['window'] != main for o, nxt in zip(owners, owners[1:])),
                    'Effect menu owner chain differs')
            require(all(rect(r) for r in (target['targetBounds'], target['windowBounds'], target['desktopBounds'], snap['mainBounds']))
                    and contains(target['windowBounds'], target['targetBounds']) and contains(target['desktopBounds'], target['windowBounds'])
                    and contains(target['desktopBounds'], snap['mainBounds']), 'Effect menu geometry is invalid/clipped')
            b = target['targetBounds']
            require(target['point'] == [math.floor(b[0]+b[2]/2), math.floor(b[1]+b[3]/2)], 'Effect menu pointer is not observed center')
        before, final = event['before'], event['final']
        require(all(before[k] == final[k] for k in ('popupIdentity', 'mainBounds', 'owners'))
                and all(before['target'][k] == final['target'][k] for k in ('identity', 'window', 'targetBounds', 'windowBounds', 'desktopBounds')),
                'Effect menu changed between pointer checks')
    require([e for e in flow['inputs'] if e['kind'] in ('menu-hover', 'menu-click')] == events[2:],
            'Unexpected additional effect menu action')


def validate_flow(output, flow, gui):
    require(flow['sourceCommit'] == gui['sourceCommit'] and flow['processId'] == gui['processId'], 'Consumer differs from retained startup source/process')
    require(flow['completed'] is True and flow['errors'] == [] and type(flow['normalCloseExitCode']) is int
            and flow['normalCloseExitCode'] == 0 and gui.get('consumerClosedNormally') is True, 'Consumer normal workflow/close not proved')
    stages = ['imported', 'reversed', 'project-saved', 'recipe-saved', 'recipe-applied', 'exported',
              'project-closed', 'project-reopened', 'reopened-exported']
    require([event['stage'] for event in flow['observations']] == stages, 'Required consumer UI stages missing')
    require(flow.get('recipeMonoBeforeApply') is True and flow.get('recipeStereoAfterApply') is True, 'Recipe change/application UI state missing')
    previous = -1
    for event in flow['observations']:
        require(event['elapsedMs'] > previous, 'Consumer UI observations out of order')
        previous = event['elapsedMs']
        root = event['tree'][0]
        require(root['processId'] == flow['processId'] and root['nativeWindowHandle'] == event['window']
                and root['name'] == event['title'] and root['offscreen'] is False, 'Consumer screenshot/UI root identity differs')
        if event['stage'] in ('recipe-saved', 'recipe-applied'):
            require(event['title'] == 'Export audio', 'Recipe dialog differs')
        else:
            require(event['window'] == flow['mainWindowHandle'], 'Consumer changed the retained editor window')
        if event['stage'] == 'project-closed':
            require(event['title'] == gui['expectedMainWindowTitle'], 'Project did not close before reopening')
        screen = event['screenshot']
        require(screen['path'] == 'consumer-' + event['stage'] + '.png', 'Consumer screenshot escaped its exact stage path')
        path = output / screen['path']
        require(digest(path)['sha256'] == screen['sha256'], 'Consumer screenshot differs')
        data = path.read_bytes()
        require(data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR' and len(data) > 24, 'Invalid consumer screenshot PNG')
        width, height = struct.unpack('!II', data[16:24])
        require((width, height) == (screen['width'], screen['height']) and width >= 400 and height >= 300 and screen['sampledColors'] >= 16,
                'Blank or clipped consumer screenshot')
    require(flow['inputs'] and flow['hardwareRecordingOrPlaybackTested'] is False, 'Consumer input evidence absent or hardware claim differs')
    validate_effect_pointer_inputs(flow)
    for event in flow['inputs']:
        if event['kind'] in ('menu-hover', 'menu-click'):
            continue  # complete independent pointer checks above, not keyboard focus
        require(event['kind'] in ('click', 'keys', 'unicode'), 'Unknown consumer input kind')
        if event['kind'] == 'click':
            require(event['sent'] == 2, 'Partial native click')
        elif event['kind'] == 'keys':
            require(event['sent'] == event['expected'] == 2 * len(event['keys']), 'Partial native key sequence')
        else:
            require(0 < event['characters'] == event['guardedCharacters'] <= 4096, 'Unguarded Unicode input')
        for snapshot_name in (('before', 'final') if event['kind'] != 'unicode' else ('final',)):
            snap = event[snapshot_name]
            require(snap['pid'] == flow['processId'] and snap['main'] == flow['mainWindowHandle'] and snap['owned'] is True
                    and snap['foreground'] == snap['window'], 'Consumer input ownership receipt differs')
            if event['kind'] == 'click':
                require(snap['hitRoot'] == snap['window'] and snap['hitPid'] == flow['processId'] and snap['matches'] == 1,
                        'Consumer click hit/uniqueness differs')
            else:
                require(snap['nativeFocusRoot'] == snap['window'] and snap['expectedTargetContainsFocus'] is True
                        and snap['nativeFocusPid'] == flow['processId'] and snap['uiaFocusPid'] == flow['processId'], 'Consumer input focus differs')


def validate_recipe(store):
    require(set(store) == {'schemaVersion', 'recipes'} and store['schemaVersion'] == 1 and len(store['recipes']) == 1,
            'Unexpected recipe store/schema/count')
    recipe = store['recipes'][0]
    expected_keys = {'schemaVersion', 'id', 'name', 'format', 'process', 'channelType', 'channels', 'sampleRate',
                     'trimBlankSpace', 'mapping', 'parameters'}
    require(set(recipe) == expected_keys, 'Recipe contains unexpected fields or file/media paths')
    require(recipe['schemaVersion'] == 1 and recipe['name'] == RECIPE and str(uuid.UUID(recipe['id'])) == recipe['id'], 'Recipe identity differs')
    require((recipe['format'], recipe['process'], recipe['channelType'], recipe['channels'], recipe['sampleRate'])
            == ('WAV', 0, 2, 2, RATE), 'Saved recipe settings differ')
    require(type(recipe['trimBlankSpace']) is bool and recipe['mapping'] == [], 'Unexpected recipe mapping/trim type')
    require(recipe['parameters'] == [dict(id=65536, type=1, value=2)], 'Recipe is not WAV signed PCM16')
    return recipe


def host_profile_roots():
    import ctypes
    roots = []
    for identifier in (28, 26, 5):  # LocalApplicationData, ApplicationData, MyDocuments
        value = ctypes.create_unicode_buffer(32768)
        require(ctypes.windll.shell32.SHGetFolderPathW(None, identifier, None, 0, value) == 0, 'Cannot resolve actual Windows profile roots')
        base = Path(value.value)
        require(base.is_absolute(), 'Native profile root is not absolute')
        for app in ('Audacity4', 'Audacity4Development'):
            roots.append(base / 'Trieflow' / app if identifier != 5 else base / app)
    return set(roots)


def profile_inventory(output, gui):
    """Authorize only exact leaves created by ConsumerProfile after fresh checks."""
    claim = gui['consumerProfileClaim']
    token = claim['token']
    require(str(uuid.UUID(token)) == token and claim['marker'] == '.waveweft-consumer-owner', 'Invalid profile claim')
    before = {Path(item['path']): item['exists'] for item in gui['userStateBefore']}
    private = output / 'private-environment'
    allowed = host_profile_roots() | {private}
    result = []
    require(len(claim['paths']) == len(set(claim['paths'])) <= 7, 'Duplicate/excessive profile claims')
    for text in claim['paths']:
        root = Path(text)
        require(root in allowed and root.is_absolute() and '..' not in root.parts and
                (root == private or (before.get(root) is False and root.name in {'Audacity4', 'Audacity4Development'})),
                'Profile cleanup target was not exclusively claimed before launch')
        no_redirect(root)
        require((root / claim['marker']).read_text(encoding='utf-8') == token, 'Profile owner marker changed')
        result.append((root, snapshot(root)))
    return result


def package_data_root(family):
    import ctypes
    value = ctypes.create_unicode_buffer(32768)
    require(ctypes.windll.shell32.SHGetFolderPathW(None, 28, None, 0, value) == 0,
            'Cannot resolve actual LocalAppData package root')
    return Path(value.value) / 'Packages' / family


def package_profile_inventory(output, gui):
    """Read exact newly installed package data; only package uninstall removes it."""
    launch = gui.get('installedLaunch')
    if launch is None:
        require(not (output / 'installed-profile-claim.json').exists(), 'Staged workflow has an installed profile claim')
        return []
    path = output / 'installed-profile-claim.json'
    no_redirect(path)
    claim = json.loads(path.read_text(encoding='utf-8-sig'))
    require(claim['schemaVersion'] == 1 and claim['sourceCommit'] == gui['sourceCommit']
            and claim['preinstallDataRootAbsent'] is True, 'Package data was not absent before this installation')
    mode, family = claim['identityMode'], claim['packageFamilyName']
    name = {'store': '1659hashfunction.WaveQuay', 'qualification': 'Trieflow.WaveQuay.Qualification'}.get(mode)
    require(name and re.fullmatch(re.escape(name) + '_[0-9a-hjkmnp-tv-z]{13}', family), 'Foreign package profile identity')
    if mode == 'store':
        require(family == '1659hashfunction.WaveQuay_r3hxytd7jt6c4', 'Assigned package profile family differs')
    full = name + '_1.0.1.0_x64__' + family.rsplit('_', 1)[1]
    require(claim['packageFullName'] == full and launch['packageFullName'] == full
            and launch['identityMode'] == mode and launch['packageFamilyName'] == family,
            'Package profile differs from retained activated identity')
    root = package_data_root(family)
    require(root.is_absolute() and Path(claim['dataRoot']) == root and Path(launch['packageDataRoot']) == root,
            'Package profile escaped exact native LocalAppData/PFN root')
    no_redirect(root)
    token = claim['token']
    require(str(uuid.UUID(token)) == token and (root / '.waveweft-msix-owner').read_text(encoding='utf-8') == token,
            'Package profile ownership marker changed')
    return [(root, snapshot(root))]


def registry_inventory(gui):
    import winreg
    claim = gui['consumerProfileClaim']
    keys = claim['registry']
    require(len(keys) == len(set(keys)) and set(keys) <= {r'Software\Trieflow\Audacity4', r'Software\Trieflow\Audacity4Development'},
            'Foreign registry cleanup target')
    def visit(key, relative, values):
        require(len(values) < 1000, 'Registry inventory exceeded bound')
        children, count, _ = winreg.QueryInfoKey(key)
        current = []
        for i in range(count):
            name, data, kind = winreg.EnumValue(key, i)
            if isinstance(data, bytes):
                data = data.hex()
            current.append((name, kind, data))
        values[relative] = hashlib.sha256(json.dumps(sorted(current), ensure_ascii=True).encode()).hexdigest()
        for i in range(children):
            name = winreg.EnumKey(key, i)
            with winreg.OpenKey(key, name) as child:
                visit(child, relative + '\\' + name, values)
    result = {}
    for name in keys:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, name) as key:
            require(winreg.QueryValueEx(key, '__WaveWeftConsumerOwner') == (claim['token'], winreg.REG_SZ), 'Registry owner marker changed')
            result[name] = {}
            visit(key, '', result[name])
    return result


def clean_profiles(output, gui, files, registry):
    import winreg
    require(profile_inventory(output, gui) == files and registry_inventory(gui) == registry,
            'Profile/registry changed after stopped-owner snapshot; all profile cleanup refused')
    for root, entries in files:
        remove_snapshot(root, entries)
    require(registry_inventory(gui) == registry, 'Registry changed before cleanup')
    for root, keys in registry.items():
        for relative in sorted(keys, key=lambda p: -len(p.split('\\'))):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, root + relative)


def finalize(output, source_commit):
    result = dict(schemaVersion=1, sourceCommit=source_commit, verified=False, errors=[], cleanup=False)
    root = output / 'consumer-fixture'
    try:
        claim = json.loads((output / 'consumer-fixture-claim.json').read_text())
        require(claim['sourceCommit'] == source_commit, 'Fixture source mismatch')
        gui = json.loads((output / 'gui-observations.json').read_text(encoding='utf-8-sig'))
        require(gui['sourceCommit'] == source_commit, 'Consumer source mismatch')
        require(gui['cleanup'] == dict(ownedJobClosed=True, processExited=True), 'Owned process/job stop not proved; no file reads/cleanup')
        require(gui.get('ownedJobEmptyBeforeClose') is True, 'Owned child processes not proven stopped; no profile reads/cleanup')
        files = fixture_snapshot(root, claim)
        result['files'] = files
        profiles = profile_inventory(output, gui)
        package_profiles = package_profile_inventory(output, gui)
        registry = registry_inventory(gui)
        result['profileFiles'] = [dict(path=str(path), entries=entries) for path, entries in profiles]
        result['profileRegistry'] = registry
        if package_profiles:
            result['packageProfileFiles'] = [dict(path=str(path), entries=entries) for path, entries in package_profiles]
            result['packageProfileCleanupDelegatedToUninstall'] = True
        try:
            flow = json.loads((output / 'consumer-workflow.json').read_text(encoding='utf-8-sig'))
            validate_flow(output, flow, gui)
            result['project'] = validate_project(root / 'Dawn-thread.aup4')
            result['exports'] = {name: validate_audio(root / name) for name in ('reversed.wav', 'reopened.wav')}
            # Read recipe metadata only after the original process's normal exit.
            recipes = []
            for profile, entries in profiles + package_profiles:
                for relative in entries:
                    if Path(relative).name != 'export-recipes-v1.json':
                        continue
                    candidate = profile / relative
                    no_redirect(candidate)
                    recipes.append((candidate, validate_recipe(json.loads(candidate.read_text(encoding='utf-8')))))
            require(len(recipes) == 1, 'Expected one recipe in a profile proved absent before launch')
            result['recipe'] = dict(path=str(recipes[0][0]), **digest(recipes[0][0]), settings=recipes[0][1])
            require(gui.get('diagnosticAccessibilityGraph') is not True, 'Graph diagnostic cannot confer consumer qualification')
            result['verified'] = True
        except (OSError, ValueError, KeyError, TypeError) as error:
            result['errors'].append(str(error))
        # The fixture claim is exclusive and original hashes were checked above.
        remove_snapshot(root, files)
        clean_profiles(output, gui, profiles, registry)
        result['cleanup'] = True
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['errors'].append(str(error))
    result['verified'] = result['verified'] and result['cleanup'] and not result['errors']
    with (output / 'consumer-validation.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'finalize'])
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        claim = prepare(args.evidence / 'consumer-fixture', args.source_commit)
        with (args.evidence / 'consumer-fixture-claim.json').open('x', encoding='utf-8') as stream:
            json.dump(claim, stream, indent=2)
    else:
        receipt = finalize(args.evidence, args.source_commit)
        print(json.dumps(dict(verified=receipt['verified'], cleanup=receipt['cleanup'], errors=receipt['errors'])))
        raise SystemExit(0 if receipt['verified'] else 1)
