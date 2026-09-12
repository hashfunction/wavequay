# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Prove the exact historical Qt-distributed Mesa software-renderer member.

This observes original archive bytes, not a reproducible-build claim. Mesa and
LLVM preferred sources/notices are independently covered by the source catalog.
"""
import json
from pathlib import Path

from archive_members import verify_members
from files import file_record
from source_archives import digest
from source_catalog import checked_hash, read_owned, require

INPUTS = 'distribution/corresponding-source/mesa-native-inputs.json'
FILENAME = 'opengl32sw-64-mesa_11_2_2-signed_sha256.7z'
URL = ('https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_6112/'
       'qt6_6112_msvc2022_64/qt.qt6.6112.win64_msvc2022_64/6.11.2-0-202608131017' + FILENAME)


def verify(inputs, cache, payload, cmake):
    require(type(inputs.get('schemaVersion')) is int and inputs['schemaVersion'] == 1
            and inputs.get('owner') == 'Mesa' and inputs.get('version') == '11.2.2'
            and inputs.get('compilerSource') == 'LLVM/LLVM', 'Unexpected original software renderer owner')
    archive, native = inputs['binaryArchive'], inputs['nativeFile']
    require(archive.get('filename') == FILENAME and archive.get('url') == URL
            and native.get('path') == 'bin/opengl32sw.dll' and native.get('member') == 'opengl32sw.dll',
            'Unexpected exact original software renderer archive/member/path')
    original = dict(bytes=archive['bytes'], sha256=archive['sha256'])
    expected = dict(bytes=native['bytes'], sha256=native['sha256'])
    checked_hash(original); checked_hash(expected)
    require(payload.get(native['path']) == expected, 'Current software renderer differs from original native input')
    proof = verify_members(Path(cache) / FILENAME, original, {native['member']: expected}, cmake)
    return dict(schemaVersion=1, archiveMembership=proof, binaryArchive=archive,
                nativeFiles={native['path']: dict(owner='Mesa', member=native['member'], **expected)},
                preferredSourceOwners=['Mesa/Mesa', 'LLVM/LLVM'], sourceLicenseClosure=False)


def collect(root, payload, cmake):
    root = Path(root); data = read_owned(root, INPUTS, 65536)
    record = verify(json.loads(data), root / '.qt-archives', payload, cmake)
    require(file_record(root / INPUTS) == digest(data), 'Fixed software renderer input changed during archive comparison')
    return dict(record, fixedInputs=digest(data))
