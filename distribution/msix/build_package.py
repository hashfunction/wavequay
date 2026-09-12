# SPDX-License-Identifier: MIT
# Copyright 2026 Trieflow LLC. See PIPELINE-MIT.txt and RETICLEQUAY-MIT.txt.
"""SDK package construction and independent current-input verification.

Building a fixed Store identity is not installed qualification or publication.
The untouched unsigned package is the only output eligible for later export.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from package import (identity_for_mode, package_name, expected_payload, stage_payload,
                     verify_msix, verify_unpacked, verify_installed, inventory_tree, file_record)
from files import _regular_stream, _reject_link, _write_new

SDK = '10.0.26100.0'


def load(path):
    with _regular_stream(path) as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError('Oversized package input JSON')
    return json.loads(raw.decode('utf-8-sig'))


def source_inputs(root):
    names = ['CMakeLists.txt', 'version.cmake', 'buildscripts/cmake/SetupDependencies.cmake',
             'SetupConfigure.cmake', 'buildscripts/ci/windows/wavequay-release.cmake',
             'muse_deps/prebuilt.lock', 'distribution/consumer_audio.py', 'distribution/verify_gui_evidence.py',
             'distribution/invoke-windows-gui.ps1', 'distribution/qualify-windows.ps1',
             'distribution/RecordConsumedDependencies.cmake', 'distribution/branding/waveweft.png']
    for base in ('distribution/msix', 'distribution/windows-gui', 'distribution/recipes/portaudio'):
        for path in sorted((root / base).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py', '.ps1', '.cs', '.txt', '.cmake', '.patch'):
                names.append(path.relative_to(root).as_posix())
    return {name: file_record(root / name) for name in sorted(set(names))}


def context(release, root, native, source_commit, mode):
    if not re.fullmatch('[0-9a-f]{40}', source_commit or ''):
        raise ValueError('Exact source revision required')
    measured = inventory_tree(release)
    inputs = load(native)
    if inputs.get('schemaVersion') != 1 or inputs.get('sourceCommit') != source_commit or inputs.get('payload') != measured:
        raise ValueError('Current stage differs from same-source native input inventory')
    return dict(schemaVersion=1, sourceCommit=source_commit, identityMode=mode, identity=identity_for_mode(mode),
                qualificationIdentityOnly=mode == 'qualification', storeIdentityUsed=mode == 'store',
                signed=False, publicRelease=False, licenseClearanceClaimed=False, installationQualificationPassed=False,
                sourceInputs=source_inputs(root), nativeInput=file_record(native), release=measured,
                artwork=file_record(root / 'distribution/branding/waveweft.png'), payload=expected_payload(release, mode))


def tool_record(path):
    path = Path(path)
    if not path.is_absolute() or [p.casefold() for p in path.parts[-6:]] != ['windows kits', '10', 'bin', SDK, 'x64', 'makeappx.exe']:
        raise ValueError('Absolute Windows SDK 10.0.26100.0 x64 MakeAppx required')
    return dict(path=str(path), sdkVersion=SDK, **file_record(path))


def execute(command):
    subprocess.run(command, check=True, shell=False, timeout=900)


def build_package(release, root, native, source_commit, makeappx, output, mode='qualification', runner=execute):
    record = context(release, root, native, source_commit, mode)
    tool = tool_record(makeappx)
    output = Path(output)
    if os.path.lexists(output):
        raise ValueError('Package output already exists')
    for parent in output.absolute().parents:
        _reject_link(parent)
    temporary = Path(tempfile.mkdtemp(prefix='.waveweft-msix-', dir=output.parent))
    stage, package, unpacked = temporary / 'stage', temporary / package_name(mode), temporary / 'unpacked'
    try:
        if stage_payload(release, stage, mode) != record['payload']:
            raise ValueError('Source package inputs changed before build')
        commands = [[str(makeappx), 'pack', '/d', str(stage), '/p', str(package), '/v', '/h', 'SHA256'],
                    [str(makeappx), 'unpack', '/p', str(package), '/d', str(unpacked), '/v']]
        for command in commands:
            if tool_record(makeappx) != tool:
                raise ValueError('MakeAppx changed before SDK execution')
            runner(command)
            if inventory_tree(stage) != record['payload']:
                raise ValueError('Payload changed during SDK execution')
        if tool_record(makeappx) != tool:
            raise ValueError('MakeAppx changed during SDK execution')
        record.update(makeAppx=tool, containerVerification=verify_msix(package, record['payload'], mode),
                      unpackedVerification=verify_unpacked(unpacked, record['payload'], mode))
        if any(record[k] != v for k, v in context(release, root, native, source_commit, mode).items()):
            raise ValueError('Current source/native inputs changed during build')
        output.mkdir()
        with _regular_stream(package) as source, (output / package.name).open('xb') as destination:
            shutil.copyfileobj(source, destination, 1024 * 1024)
        _write_new(output / 'package-record.json', (json.dumps(record, indent=2) + '\n').encode())
        shutil.rmtree(temporary)
        return output
    except Exception as error:
        raise ValueError(f'Package construction failed; owned temporary evidence retained at {temporary}: {error}') from error


def verify_record(package, record_path, release, root, native, source_commit, mode='qualification'):
    record = load(record_path)
    expected = context(release, root, native, source_commit, mode)
    if any(record.get(k) != v for k, v in expected.items()):
        raise ValueError('Package record differs from independently regenerated current inputs')
    for name in ('qualificationIdentityOnly', 'storeIdentityUsed'):
        if type(record.get(name)) is not bool or record[name] != expected[name]:
            raise ValueError('Package identity flags must be exact selected-mode booleans')
    for name in ('signed', 'publicRelease', 'licenseClearanceClaimed', 'installationQualificationPassed'):
        if record.get(name) is not False:
            raise ValueError('Package record has a premature signed/release/qualification claim')
    if record.get('containerVerification') != verify_msix(package, expected['payload'], mode):
        raise ValueError('Package record container hash differs')
    if record.get('unpackedVerification') != dict(verifiedPayloadFiles=len(expected['payload'])):
        raise ValueError('SDK unpack evidence differs')
    if record.get('makeAppx') != tool_record(record['makeAppx']['path']):
        raise ValueError('Recorded SDK tool differs')
    return record


def assert_current_checkout(root, commit):
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != commit:
        raise ValueError('Current Git source differs from requested revision')
    subprocess.run(['git', '-C', str(root), 'diff', '--exit-code', '--quiet', 'HEAD', '--ignore-submodules=none'], check=True)
    for name, pin in {'muse': '3c5512eb8ee1a863a6123e62bd75a6ab55045752', 'muse_deps': 'b915e6703a2a9839b2a98d4ca2468a88e361929f'}.items():
        if subprocess.check_output(['git', '-C', str(root / name), 'rev-parse', 'HEAD'], text=True).strip() != pin:
            raise ValueError('Pinned native source differs: ' + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['build', 'verify', 'installed'])
    for name in ('root', 'release', 'native-input', 'output', 'makeappx', 'package', 'record', 'installed-root'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--identity-mode', choices=['qualification', 'store'], default='qualification')
    args = parser.parse_args()
    root = args.root or Path(__file__).resolve().parents[2]
    assert_current_checkout(root, args.source_commit)
    if args.command == 'build':
        build_package(args.release, root, args.native_input, args.source_commit, args.makeappx, args.output, args.identity_mode)
    else:
        record = verify_record(args.package, args.record, args.release, root, args.native_input, args.source_commit, args.identity_mode)
        if args.command == 'installed':
            verify_installed(args.installed_root, record['payload'], args.identity_mode)
    print('PASS: exact unsigned package/current inputs verified; installed consumer and source-publication gates are separate.')


if __name__ == '__main__': main()
