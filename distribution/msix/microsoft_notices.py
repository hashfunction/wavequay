# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Verify the separate original Microsoft runtime terms and exact component scope.

These documents establish the retained applicable terms and distributable lists.
They are not a substitute for actual signed/original runtime provenance, do not
relicense WaveWeft source, and do not claim installed or Store acceptance.
"""
import json
from pathlib import Path

from files import file_record, inventory_tree
from source_archives import digest
from source_catalog import read_owned, require
from source_publication import timestamp
from windows_runtime_proof import CRT

INPUTS = 'distribution/corresponding-source/microsoft-notice-inputs.json'
BASE = 'distribution/corresponding-source/microsoft-notices'
DOCUMENTS = {
    'Visual-Studio-2022-Enterprise-Professional-License-EN.docx': dict(bytes=63513,
        sha256='9c0cd52b20db9d081854c75bd1b50c75514b8f8cb09c8cad15e89d90b97b5bf3',
        url='https://visualstudio.microsoft.com/wp-content/uploads/2021/11/Visual-Studio-2022-Enterprise-Professional-License-EN.docx'),
    'Visual-C-Runtime-2015-2022-License-1.docx': dict(bytes=39644,
        sha256='f1e3d56ceb2ad68aae0711b910375009e651ac5530fa0760f0dea6e81e54fae1',
        url='https://visualstudio.microsoft.com/wp-content/uploads/2021/09/Visual-C-Runtime-2015-2022-License-1.docx'),
    'Visual-Studio-2022-redist.md': dict(bytes=24763,
        sha256='0240b9a75f8fd997d998af27ea84b901f576782177f8ff535b7b07924c9570f7',
        url='https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution?accept=text/markdown'),
    'Windows-SDK-license.md': dict(bytes=29470,
        sha256='0b0f3f06e59fbf03e9b18e9688a90366ea26d9f95c3d82b302f97b1680b1199b',
        url='https://learn.microsoft.com/en-us/legal/windows-sdk/license?accept=text/markdown'),
    'Windows-SDK-redist.md': dict(bytes=19214,
        sha256='ff4dc82936ef9e8449927a3d06ee1fca801933c1464ceee60fa14003eb656dd0',
        url='https://learn.microsoft.com/en-us/legal/windows-sdk/redist?accept=text/markdown'),
}
OWNERS = {
    'Microsoft.VC143.CRT': dict(files=['bin/'+name for name in CRT], documents=[
        'Visual-C-Runtime-2015-2022-License-1.docx', 'Visual-Studio-2022-Enterprise-Professional-License-EN.docx',
        'Visual-Studio-2022-redist.md']),
    'Microsoft.WindowsSDK.D3D': dict(files=['bin/d3dcompiler_47.dll'], documents=['Windows-SDK-license.md', 'Windows-SDK-redist.md']),
}


def verify(root):
    root=Path(root); data=read_owned(root, INPUTS, 65536); document=json.loads(data)
    require(type(document.get('schemaVersion')) is int and document['schemaVersion']==1
            and document.get('product')=='WaveWeft'
            and document.get('scope')=='Microsoft runtime components only; does not relicense application or open-source components',
            'Microsoft notice supplement must retain exact separate component scope')
    timestamp(document['retrievedAtUtc'])
    require(document.get('owners')==OWNERS and isinstance(document.get('documents'), dict)
            and set(document['documents'])==set(DOCUMENTS), 'Microsoft terms must cover only the exact nine runtime files')
    records={}
    for name, fixed in DOCUMENTS.items():
        require(all(document['documents'][name].get(field)==value for field,value in fixed.items()),
                'Original Microsoft terms/list delivery or hash changed: '+name)
        expected=dict(bytes=fixed['bytes'], sha256=fixed['sha256'])
        require(digest(read_owned(root, BASE+'/'+name, 1024**2))==expected,
                'Original Microsoft terms/list bytes changed: '+name)
        records[name]=expected
    require(inventory_tree(root/BASE)==records and file_record(root/INPUTS)==digest(data),
            'Microsoft terms/list inventory is untracked or changed')
    return dict(schemaVersion=1, fixedInputs=digest(data), documents=records, owners=OWNERS,
                nativeFiles={name:owner for owner,row in OWNERS.items() for name in row['files']},
                sourceLicenseClosure=False)
