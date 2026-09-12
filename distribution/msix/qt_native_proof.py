# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Bind shipped Qt files and current SDK metadata to original native archives."""
import json
from pathlib import Path, PurePosixPath

from archive_members import verify_members
from files import file_record, _checked_path, _register_path, _reject_link, _write_new
from source_archives import digest
from source_catalog import read_owned, require

MODULES = ('qtbase', 'qtdeclarative', 'qt5compat', 'qtshadertools', 'qtsvg')
INPUTS = 'distribution/corresponding-source/qt-source-proof-inputs.json'


def staged_path(member):
    _checked_path(member)
    # Qt's deployment layout puts native plugins under bin, while preserving
    # the QML import tree beside bin. This is the actual current stage layout.
    return 'bin/' + member[len('plugins/'):] if member.startswith('plugins/') else member


def native_members(document):
    require(document.get('spdxVersion') == 'SPDX-2.3' and isinstance(document.get('files'), list)
            and 0 < len(document['files']) <= 50000, 'Missing bounded original Qt binary SPDX inventory')
    result, seen = {}, {}
    for row in document['files']:
        name = row['fileName']
        require(isinstance(name, str) and name.startswith('./'), 'Original Qt member must be relative')
        name = name[2:]
        _register_path(name, seen)
        if PurePosixPath(name).suffix.lower() in ('.dll', '.exe'):
            deployed = staged_path(name)
            require(deployed not in result, 'Ambiguous deployed Qt native member')
            result[deployed] = name
    require(result, 'Original Qt inventory contains no native members')
    return result


def verify_modules(inputs, cache, qt, payload, cmake):
    cache, qt = Path(cache), Path(qt)
    require(type(inputs.get('schemaVersion')) is int and inputs['schemaVersion'] == 1
            and isinstance(inputs.get('modules'), list), 'Invalid fixed Qt inputs')
    names = [row['name'] for row in inputs['modules']]
    require(len(names) == len(MODULES) and set(names) == set(MODULES), 'Exact original Qt module set required')
    modules, owned = {}, {}
    for row in inputs['modules']:
        name = row['name']; archive = row['binaryArchive']; filename = archive['filename']
        _checked_path(filename)
        require('/' not in filename and filename.endswith('.7z') and row['version'] == '6.11.2',
                'Unexpected original Qt archive/version')
        binary_metadata = 'sbom/' + name + '-6.11.2.spdx.json'
        source_metadata = 'sbom/' + name + '-6.11.2.source.spdx'
        metadata = row['originalMetadata']
        require(set(metadata) == {binary_metadata, source_metadata}, 'Exact original Qt metadata pair required')
        data = {}
        for path, expected in metadata.items():
            data[path] = read_owned(qt, path, 32 * 1024**2)
            require(digest(data[path]) == expected, 'Current Qt metadata differs from original archive input: ' + path)
        mapping = {path: member for path, member in native_members(json.loads(data[binary_metadata])).items() if path in payload}
        require(mapping, 'Original Qt module has no shipped native member: ' + name)
        members = dict(metadata)
        for path, member in mapping.items():
            require(path not in owned, 'Shipped Qt native file has duplicate original owners: ' + path)
            members[member] = payload[path]
            owned[path] = dict(owner=name, member=member, **payload[path])
        proof = verify_members(cache / filename, dict(bytes=archive['bytes'], sha256=archive['sha256']), members, cmake)
        for path, expected in metadata.items():
            require(file_record(qt / path) == expected, 'Current Qt metadata changed during archive comparison')
        modules[name] = dict(mapping=mapping, originalMetadata=metadata, archiveMembership=proof)
    return dict(schemaVersion=1, modules=modules, nativeFiles=owned, sourceLicenseClosure=False)


def collect(root, qt, payload, cmake):
    root = Path(root)
    raw = read_owned(root, INPUTS, 8 * 1024**2)
    record = verify_modules(json.loads(raw), root / '.qt-archives', qt, payload, cmake)
    require(file_record(root / INPUTS) == digest(raw), 'Fixed Qt inputs changed during native comparison')
    return dict(record, fixedInputs=digest(raw))


def collect_and_retain(root, qt, payload, cmake, output):
    record = collect(root, qt, payload, cmake)
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Original Qt metadata output must be absent')
    for parent in output.absolute().parents:
        if parent.exists():
            _reject_link(parent)
    output.mkdir(parents=True)
    for module in record['modules'].values():
        for name, expected in module['originalMetadata'].items():
            data = read_owned(Path(qt), name, 32 * 1024**2)
            require(digest(data) == expected, 'Original Qt metadata changed before retention')
            _write_new(output / name, data)
            require(file_record(output / name) == expected, 'Retained original Qt metadata differs')
    return record
