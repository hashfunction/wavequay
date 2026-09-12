# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Observe current consumed native inputs without claiming license clearance.

This collector does not download or execute any dependency, adopt unrelated
archive contents, or equate a resolved prefix with original archive provenance.
The subsequent source-publication gate must close each explicitly open item.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.parse import urlsplit

from files import file_record, inventory_tree, _checked_path, _regular_stream, _reject_link


def require(value, message):
    if not value:
        raise ValueError(message)


def prebuilt_record(root, name, recipe):
    """Same recipe signature algorithm as pinned _bd_recipe_sig, engine rev 4."""
    files = inventory_tree(recipe)
    signature = '4|windows|x86_64' + ''.join('|' + v['sha256'] for k, v in sorted(files.items()) if k != 'meta.cmake')
    signature = hashlib.sha256(signature.encode()).hexdigest()[:12]
    rows = [line.split() for line in (root / 'muse_deps/prebuilt.lock').read_text().splitlines()
            if line and not line.startswith('#')]
    rows = [row for row in rows if row[0] == name and row[2:4] == ['windows', 'x86_64']]
    require(len(rows) == 1 and len(rows[0]) == 7, 'Missing/duplicate prebuilt lock: ' + name)
    _, version, _, _, archive, sha, release = rows[0]
    require(archive.endswith('-' + signature + '.7z'), 'Prebuilt recipe signature differs: ' + name)
    require(re.fullmatch('[0-9a-f]{64}', sha), 'Invalid prebuilt hash')
    return dict(filename=archive, version=version, sha256=sha,
                url=f'https://github.com/musescore/muse_deps/releases/download/{release}/{archive}')


def original_notices(root, names):
    result = {}
    for name in names:
        _checked_path(name)
        require(name not in result, 'Duplicate original notice')
        result[name] = file_record(root / name)
    return result


def match_native_payload(payload, owners):
    matches, unknown = {}, []
    for path, info in payload.items():
        if PurePosixPath(path).suffix.lower() not in ('.exe', '.dll') or path == 'bin/WaveWeft.exe':
            continue
        candidates = []
        for owner, members in owners.items():
            for member, record in members.items():
                # Exact leaf and exact bytes; equal bytes under an unrelated
                # basename are never sufficient provenance.
                if PurePosixPath(member).name.casefold() == PurePosixPath(path).name.casefold() and record == info:
                    candidates.append(dict(owner=owner, member=member))
        if candidates:
            matches[path] = candidates
        else:
            unknown.append(path)
    return matches, unknown


def sources_from_record(row):
    result = []
    for source in row['sources']:
        fields = source.split('|')
        require(len(fields) == 4, 'Malformed consumed source record')
        subdir, kind, url, sha = fields
        _checked_path(subdir)
        parsed = urlsplit(url)
        require(kind == 'tarball' and parsed.scheme == 'https' and parsed.netloc
                and not parsed.username and not parsed.password and re.fullmatch('[0-9a-f]{64}', sha),
                'Consumed source must be an exact HTTPS/hash archive: ' + row['name'])
        result.append(dict(subdir=subdir, url=url, sha256=sha))
    require(result, 'Consumed dependency has no exact source: ' + row['name'])
    return result


def collect(root, build, stage, qt, source_commit):
    require(re.fullmatch('[0-9a-f]{40}', source_commit or ''), 'Exact source revision required')
    with _regular_stream(build / 'waveweft-consumed-dependencies.json') as stream:
        configuration = json.load(stream)
    require(configuration.get('schemaVersion') == 1 and configuration.get('dependencies'), 'Missing consumed dependency record')
    payload = inventory_tree(stage)
    components, owners, issues = [], {}, []
    for row in configuration['dependencies']:
        name = row['name']
        require(re.fullmatch('[a-z0-9_-]+', name or '') and name not in owners, 'Invalid/duplicate consumed owner')
        expected_recipe = 'distribution/recipes/portaudio' if name == 'portaudio' else 'muse_deps/recipes/' + name
        require(row['recipe'] == expected_recipe, 'Unexpected recipe override')
        prefix = Path(row['prefix'])
        require(prefix == build / '_deps' / name, 'Consumed prefix escapes exact build dependency root')
        _reject_link(prefix)
        members = {}
        for text in row['runtime']:
            runtime = Path(text)
            require(runtime.is_relative_to(prefix), 'Resolved runtime escapes owned prefix')
            relative = runtime.relative_to(prefix).as_posix()
            _checked_path(relative)
            require(relative not in members, 'Duplicate resolved runtime')
            for parent in runtime.parents:
                _reject_link(parent)
            members[relative] = file_record(runtime)
        if (prefix / 'licenses').is_dir():
            members.update({'licenses/' + p: v for p, v in inventory_tree(prefix / 'licenses').items()})
        owners[name] = members
        record = dict(name=name, version=row['version'], recipe=row['recipe'],
                      recipeFiles=inventory_tree(root / row['recipe']), sources=sources_from_record(row),
                      resolvedNativeFiles={p: v for p, v in members.items() if PurePosixPath(p).suffix.lower() in ('.dll', '.exe')},
                      installedNotices={p: v for p, v in members.items() if p.startswith('licenses/')})
        stamp = prefix / '.prebuilt'
        if stamp.exists():
            locked = prebuilt_record(root, name, root / row['recipe'])
            require(stamp.read_text() == locked['filename'], 'Resolved prebuilt stamp differs from lock')
            archive = root / '.ci-dependency-cache/prebuilt' / locked['filename']
            actual = file_record(archive)
            require(actual['sha256'] == locked['sha256'], 'Current prebuilt archive hash differs: ' + name)
            record['binaryArchive'] = dict(locked, bytes=actual['bytes'])
            from archive_members import verify_members
            tool = shutil.which('cmake')
            require(tool, 'Original native archive comparison requires the configured CMake tool')
            record['archiveMembership'] = verify_members(archive, actual,
                dict(record['resolvedNativeFiles'], **record['installedNotices']), Path(tool).resolve())
            issues.append(name + ': original members verified; source/notice delivery pending')
        else:
            record['builtFromSource'] = True
            issues.append(name + ': current downloaded source/member and notice review pending')
        components.append(record)
    # Hash only native inputs and original SBOM records, not unrelated Qt
    # documentation, headers or examples. Source archives are separate inputs.
    qt_members = {}
    for directory in ('bin', 'plugins', 'qml', 'sbom'):
        base = qt / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if not path.is_file() or (directory != 'sbom' and path.suffix.lower() not in ('.exe', '.dll')):
                continue
            for parent in path.parents:
                _reject_link(parent)
            qt_members[path.relative_to(qt).as_posix()] = file_record(path)
    owners['qt-online'] = {p: v for p, v in qt_members.items() if PurePosixPath(p).suffix.lower() in ('.exe', '.dll')}
    matches, unknown = match_native_payload(payload, owners)
    # The app is source-built; MSVC files may be installed by windeployqt from
    # the toolchain, so they must remain unknown until their origin is captured.
    issues.extend('Unmatched native payload: ' + path for path in unknown)
    issues.append('Qt original archive/member/SBOM/source/notices and Microsoft redistribution records pending')
    return dict(schemaVersion=1, sourceCommit=source_commit, payload=payload,
                consumedConfiguration=file_record(build / 'waveweft-consumed-dependencies.json'),
                builtApplication=dict(path='bin/WaveWeft.exe', **payload['bin/WaveWeft.exe']),
                components=components, nativeMatches=matches, unresolvedNative=unknown,
                qtOriginalMetadata={p: v for p, v in qt_members.items() if p.startswith('sbom/')},
                sourceLicenseClosure=False, openItems=issues)


def main():
    parser = argparse.ArgumentParser()
    for name in ('root', 'build', 'stage', 'qt', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    from run_context import current
    run = current(args.source_commit)
    record = collect(*(getattr(args, field).absolute() for field in ('root', 'build', 'stage', 'qt')), args.source_commit)
    record['runContext'] = run
    # The command-line release collector always observes the original Qt
    # archives. The lower-level consumed-prefix collector remains useful for
    # separately testing unresolved ownership without inventing Qt metadata.
    from qt_native_proof import collect_and_retain as collect_qt
    tool = shutil.which('cmake')
    require(tool, 'Original Qt archive comparison requires the configured CMake tool')
    retained = args.output.absolute().parent / 'native-source' / 'qt'
    record['qtOriginalArchives'] = collect_qt(args.root.absolute(), args.qt.absolute(), record['payload'], Path(tool).resolve(), retained)
    from platform_native_proof import collect as collect_mesa
    record['mesaOriginalArchive'] = collect_mesa(args.root.absolute(), record['payload'], Path(tool).resolve())
    from windows_runtime_proof import collect as collect_windows
    record['windowsRuntimeOrigins'] = collect_windows(args.build.absolute() / 'waveweft-windows-runtimes.json',
        args.output.absolute().parent / 'windows-runtime-origins.json', record['payload'], args.source_commit, run)
    record['openItems'] = [item for item in record['openItems']
                           if item != 'Qt original archive/member/SBOM/source/notices and Microsoft redistribution records pending']
    record['openItems'].append('Qt/Mesa original native archives and Microsoft origin observations verified; complete preferred-source/notice delivery and Microsoft terms gate pending')
    require(inventory_tree(args.stage.absolute()) == record['payload'], 'Current stage changed during original native observations')
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(record, output, indent=2); output.write('\n')


if __name__ == '__main__':
    main()
