# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Bind unchanged preferred sources to the independently verified Wave release.

The original catalog/readback remain immutable observations. This verifies
dependency delivery only; current application source and installed acceptance
must still be independently established by the final export gate.
"""
from datetime import datetime, timedelta
import json
from pathlib import Path

from files import file_record, _checked_path
from source_archives import digest
from source_catalog import read_owned, require, checked_hash

TAG = 'native-sources-2026-09-12-waveweft'
ASSET_BASE = 'https://github.com/hashfunction/wavequay/releases/download/' + TAG + '/'
RELEASE_URL = 'https://github.com/hashfunction/wavequay/releases/tag/' + TAG
TAG_COMMIT = '753e3cf724ad05e565a6f055921083a5bd090759'
BASE = 'distribution/corresponding-source/'
ORIGINALS = {
    'source-inputs.json': dict(bytes=323064, sha256='acf71b51b4cd06ab1ee3f453fa579aa72eb7099ec8939f74744e1f74787084ef'),
    'publication/source-release-manifest.json': dict(bytes=24419, sha256='4396b5cf14f3430eb89d2b2cc9f1a0fe35722f4c27e93588c5abd38c4711bf22'),
    'publication/public-readback.json': dict(bytes=19025, sha256='29775e987a9633e0dd9027be3308d8dd0d54eb7f0178eb275748a155e233456f'),
    'publication/SOURCE-README.md': dict(bytes=1064, sha256='782a8412e53cdbc1b0ab1e45b7e5f3fd5df5124bb6b3bb475a619187601e5289'),
}


def timestamp(value):
    try:
        result = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError('Missing original publication observation timestamp') from error
    require(result.utcoffset() == timedelta(0), 'Original publication timestamp must be explicit UTC')
    return result


def validate_documents(catalog, manifest, readback, assets):
    require(type(manifest.get('schema_version')) is int and manifest['schema_version'] == 1
            and manifest.get('product') == 'WaveWeft' and manifest.get('release_tag') == TAG,
            'Unexpected preferred-source publication manifest')
    require(type(readback.get('schema_version')) is int and readback['schema_version'] == 1
            and type(readback.get('release_id')) is int and readback['release_id'] == 387612459
            and readback.get('release_tag') == TAG and readback.get('release_url') == RELEASE_URL
            and readback.get('tag_commit') == TAG_COMMIT, 'Unexpected original dependency publication identity')
    for name, expected in {'anonymous': True, 'credentials_sent': False, 'tls_certificate_verification': True,
                           'all_public_assets_verified': True, 'source_license_closure': False,
                           'windows_qualification_claimed': False}.items():
        require(readback.get(name) is expected, 'Incorrect original publication flag: ' + name)
    require(set(assets) == {'source-inputs.json', 'source-release-manifest.json', 'SOURCE-README.md'},
            'Exact original public metadata assets required')
    source_catalog = manifest['source_catalog']
    require(source_catalog == dict(filename='source-inputs.json', url=ASSET_BASE + 'source-inputs.json',
                                   **assets['source-inputs.json']), 'Published original catalog differs from current catalog')
    originals = {}
    for row in catalog['archives']:
        key = row['component'] + '/' + row['subdir']
        require(key not in originals, 'Duplicate current source owner')
        originals[key] = row
    require(len(originals) == 40 and isinstance(manifest.get('archives'), list)
            and len(manifest['archives']) == len(originals), 'Incomplete exact source publication set')
    public = dict(assets); archives = []; seen = set()
    for row in manifest['archives']:
        key = row['component'] + '/' + row['subdir']
        require(key in originals and key not in seen, 'Untracked/duplicate published source owner')
        seen.add(key); original = originals[key]; filename = row['filename']
        _checked_path(filename)
        require('/' not in filename and filename not in public, 'Published source filename is duplicate/unsafe')
        for field in ('filename', 'origin', 'bytes', 'sha256'):
            require(row[field] == original[field], 'Published preferred source differs: ' + key + '/' + field)
        require(row['previous_public_url'] == original['url'] and row['url'] == ASSET_BASE + filename,
                'Published source does not retain the original and exact own-release URLs')
        fixed = dict(bytes=row['bytes'], sha256=row['sha256']); checked_hash(fixed)
        public[filename] = fixed; archives.append(dict(row))
    require(seen == set(originals), 'A current source archive is unpublished')
    expected_counts = {'archive_count': 40, 'archive_bytes': sum(row['bytes'] for row in archives),
                       'public_assets_count': len(public)}
    for name, value in expected_counts.items():
        require(type(readback.get(name)) is int and readback[name] == value, 'Incorrect typed publication total: ' + name)
    finished = timestamp(readback['verified_at_utc'])
    verified = {}
    require(isinstance(readback.get('verified_assets'), list) and len(readback['verified_assets']) == len(public),
            'Partial public source readback')
    for row in readback['verified_assets']:
        filename = row['filename']
        require(filename in public and filename not in verified, 'Foreign/duplicate public source readback')
        fixed = dict(bytes=row['bytes'], sha256=row['sha256']); checked_hash(fixed)
        require(fixed == public[filename] and row['url'] == ASSET_BASE + filename
                and row['redirect_host'] == 'release-assets.githubusercontent.com'
                and timestamp(row['verified_at_utc']) <= finished, 'Original anonymous source bytes/URL/observation differ')
        verified[filename] = dict(url=row['url'], **fixed)
    require(set(verified) == set(public), 'An exact public source asset lacks anonymous verification')
    return dict(schemaVersion=1, releaseUrl=RELEASE_URL, publicationTagCommit=TAG_COMMIT,
                archiveCount=len(archives), archiveBytes=expected_counts['archive_bytes'], archives=archives,
                publicAssets=verified, verifiedAtUtc=readback['verified_at_utc'], sourceLicenseClosure=False)


def verify_publication(root):
    root = Path(root); data = {}
    for name, fixed in ORIGINALS.items():
        data[name] = read_owned(root, BASE + name, 8 * 1024**2)
        require(digest(data[name]) == fixed, 'Original source publication record changed: ' + name)
    assets = {Path(name).name: fixed for name, fixed in ORIGINALS.items() if not name.endswith('public-readback.json')}
    result = validate_documents(json.loads(data['source-inputs.json']), json.loads(data['publication/source-release-manifest.json']),
                                json.loads(data['publication/public-readback.json']), assets)
    require(all(file_record(root / BASE / name) == fixed for name, fixed in ORIGINALS.items()),
            'Original source publication inputs changed during verification')
    return dict(result, originalRecords=ORIGINALS)
