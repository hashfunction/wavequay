# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Check curated original notices against current consumed source inputs.

This is source and notice observation, not installed qualification, anonymous
publication verification or a blanket license approval. Archive readers never
extract or execute a preferred-source tree.
"""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from files import file_record, inventory_tree, _checked_path, _register_path, _regular_stream, _reject_link
from source_archives import digest, read_members, notice_bytes

EXTRA_SOURCE_OWNERS = ('qtbase', 'qtdeclarative', 'qt5compat', 'qtshadertools', 'qtsvg', 'Mesa', 'LLVM')
CATALOG = 'distribution/corresponding-source/source-inputs.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def read_owned(root, name, bound):
    _checked_path(name)
    path = root / name
    for parent in path.absolute().parents:
        _reject_link(parent)
    before = file_record(path)
    require(before['bytes'] <= bound, 'Oversized source/notice input: ' + name)
    with _regular_stream(path) as stream:
        data = stream.read(bound + 1)
    require(digest(data) == before == file_record(path), 'Source/notice input changed: ' + name)
    return data


def checked_hash(value):
    require(isinstance(value, dict) and set(value) == {'bytes', 'sha256'}
            and type(value['bytes']) is int and 0 < value['bytes'] <= 1024**3
            and isinstance(value['sha256'], str) and re.fullmatch('[0-9a-f]{64}', value['sha256']),
            'Invalid exact source/notice size and hash')


def checked_url(value):
    require(isinstance(value, str), 'Missing source URL')
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
            and not parsed.fragment and not parsed.query and not any(c.isspace() for c in value),
            'Source URL must be an uncredentialed exact HTTPS resource')


def _read_catalog(root):
    data = read_owned(root, CATALOG, 8 * 1024**2)
    catalog = json.loads(data)
    require(type(catalog.get('schemaVersion')) is int and catalog['schemaVersion'] == 1,
            'Unsupported source catalog')
    require(isinstance(catalog.get('archives'), list) and 0 < len(catalog['archives']) <= 100,
            'Missing bounded preferred-source catalog')
    require(isinstance(catalog.get('repositoryNotices'), list) and 0 < len(catalog['repositoryNotices']) <= 1024,
            'Missing bounded application/vendored notices')
    return catalog, digest(data)


def verify_catalog(root, native):
    root = Path(root)
    catalog, fixed = _read_catalog(root)
    base = root / 'distribution/corresponding-source'
    notices, seen, sources, extra = {}, {}, {}, set()

    def check_notice(row):
        _register_path(row['path'], seen)
        require(row['path'].startswith('notices/'), 'Notice escapes packaged notice tree')
        _checked_path(row['member'])
        checked_hash(row['sourceMember']); checked_hash(row['notice'])
        require(type(row['offset']) is int and type(row['length']) is int and row['offset'] >= 0
                and row['length'] > 0 and row['offset'] + row['length'] <= row['sourceMember']['bytes']
                and row['length'] == row['notice']['bytes'], 'Invalid original notice byte range')
        data = read_owned(base, row['path'], 16 * 1024**2)
        require(digest(data) == row['notice'], 'Packaged original notice differs: ' + row['path'])
        notices[row['path'].removeprefix('notices/')] = row['notice']

    for row in catalog['archives']:
        owner, part = row['component'], row['subdir']
        require(isinstance(owner, str) and re.fullmatch('[A-Za-z0-9_-]+', owner), 'Invalid source owner')
        _checked_path(part); _checked_path(row['filename'])
        require('/' not in row['filename'], 'Source filename must be a leaf')
        checked_hash(dict(bytes=row['bytes'], sha256=row['sha256']))
        checked_url(row['origin']); checked_url(row['url'])
        key = owner + '/' + part
        require(key not in sources, 'Duplicate preferred-source owner/part')
        sources[key] = row
        require(isinstance(row['notices'], list) and 0 < len(row['notices']) <= 1024,
                'Missing bounded component notices: ' + owner)
        for notice in row['notices']:
            check_notice(notice)
        if owner in EXTRA_SOURCE_OWNERS:
            require(owner not in extra and part == owner and 'recipe' not in row and 'recipeFiles' not in row,
                    'Duplicate/misclassified extra source owner')
            extra.add(owner)
        else:
            expected_recipe = 'distribution/recipes/portaudio' if owner == 'portaudio' else 'muse_deps/recipes/' + owner
            require(row.get('recipe') == expected_recipe and row.get('recipeFiles') == inventory_tree(root / expected_recipe),
                    'Current preferred-source recipe differs: ' + owner)
    require(extra == set(EXTRA_SOURCE_OWNERS), 'Exact Qt/Mesa/LLVM source catalog is incomplete')

    comparisons = {}
    for row in catalog['repositoryNotices']:
        check_notice(row)
        data = read_owned(root, row['member'], 16 * 1024**2)
        allow_crlf = row.get('allowWindowsCheckoutCRLF', False)
        require(type(allow_crlf) is bool, 'Invalid repository checkout comparison flag')
        comparison = 'exact bytes'
        if digest(data) != row['sourceMember'] and allow_crlf:
            # An explicit reversible checkout transform only. The original
            # member hash must match, and original mixed/lone CR is forbidden.
            original = data.replace(b'\r\n', b'\n')
            require(b'\r' not in original and original.replace(b'\n', b'\r\n') == data,
                    'Repository source is not a lossless LF-to-CRLF checkout')
            data = original
            comparison = 'LF-to-CRLF checkout'
        expected = notice_bytes({row['member']: data}, row)
        require(digest(expected) == row['notice'], 'Current application/vendored notice differs')
        require(row['member'] not in comparisons, 'Duplicate repository notice source member')
        comparisons[row['member']] = comparison
    require(inventory_tree(base / 'notices') == notices, 'Packaged notices have missing/unindexed/changed files')

    require(isinstance(native.get('components'), list) and native['components'], 'Current consumed components absent')
    consumed, owners = set(), set()
    for component in native['components']:
        owner = component['name']
        require(owner not in owners and owner not in EXTRA_SOURCE_OWNERS, 'Duplicate/confused consumed source owner')
        owners.add(owner)
        require(isinstance(component['sources'], list) and component['sources'], 'Consumed preferred sources absent')
        for source in component['sources']:
            key = owner + '/' + source['subdir']
            require(key not in consumed and key in sources, 'Missing/duplicate exact consumed source')
            row = sources[key]; consumed.add(key)
            require(row['origin'] == source['url'] and row['sha256'] == source['sha256']
                    and row.get('recipe') == component['recipe'] and row.get('recipeFiles') == component['recipeFiles'],
                    'Current consumed source/recipe differs: ' + key)
    require(consumed == {key for key, row in sources.items() if row['component'] not in EXTRA_SOURCE_OWNERS},
            'Catalog does not match the exact consumed source set')
    require(fixed == file_record(root / CATALOG), 'Source catalog changed during verification')
    return dict(schemaVersion=1, catalog=fixed, archiveCount=len(sources), noticeCount=len(notices),
                notices=notices, repositoryComparisons=comparisons,
                consumedSources=sorted(consumed), sourceLicenseClosure=False)


def verify_archives(root, archives, native):
    root = Path(root)
    record = verify_catalog(root, native)
    catalog, fixed = _read_catalog(root)
    require(fixed == record['catalog'], 'Source catalog changed before archive verification')
    require(set(archives) == {row['component'] + '/' + row['subdir'] for row in catalog['archives']},
            'Missing/untracked exact preferred-source archive')
    proofs = {}
    for row in catalog['archives']:
        key = row['component'] + '/' + row['subdir']
        expected = dict(bytes=row['bytes'], sha256=row['sha256'])
        members = read_members(Path(archives[key]), expected, sorted({notice['member'] for notice in row['notices']}))
        for notice in row['notices']:
            data = notice_bytes(members, notice)
            require(data == read_owned(root / 'distribution/corresponding-source', notice['path'], 16 * 1024**2),
                    'Packaged notice differs from actual preferred source')
        proofs[key] = dict(archive=expected, members={name: digest(data) for name, data in sorted(members.items())})
    require(record == verify_catalog(root, native), 'Source catalog/notice inputs changed during archive verification')
    return dict(record, archives=proofs)
