# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Join actual native provenance, complete preferred sources and original notices.

The original native observer is rerun read-only, rather than accepting its
summary booleans. Installed acceptance and current public application-source
availability remain independent final-export requirements.
"""
import argparse
import json
from pathlib import Path, PurePosixPath

from files import file_record, inventory_tree, _write_new
from source_archives import digest
from source_catalog import checked_hash, read_owned, require
from run_context import current, validate
from native_sources import observe
from source_delivery import collect as collect_sources
from microsoft_notices import verify as verify_microsoft


def resolve_native_owners(native):
    payload=native['payload']
    expected={name:info for name,info in payload.items() if PurePosixPath(name).suffix.lower() in ('.exe','.dll')}
    require('bin/WaveWeft.exe' in expected and native['builtApplication']==dict(path='bin/WaveWeft.exe',**expected['bin/WaveWeft.exe']),
            'Current source-built application byte identity differs')
    result={'bin/WaveWeft.exe':dict(owner='application',**expected['bin/WaveWeft.exe'])}
    for field in ('qtOriginalArchives','mesaOriginalArchive','windowsRuntimeOrigins'):
        for name,original in native[field]['nativeFiles'].items():
            data=dict(bytes=original['bytes'],sha256=original['sha256']);checked_hash(data)
            require(name in expected and name not in result and data==expected[name],
                    'Original native archive/origin ownership is missing, overlapping or changed: '+name)
            result[name]=dict(original)
    unresolved=native['unresolvedNative'];windows=native['windowsRuntimeOrigins']['nativeFiles']
    require(isinstance(unresolved,list) and len(unresolved)==len(set(unresolved)) and set(unresolved)==set(windows),
            'Unresolved prefix owners are not exactly covered by observed Microsoft originals')
    components={}
    for row in native['components']:
        require(row['name'] not in components,'Duplicate consumed native source owner')
        components[row['name']]=row
    for name,info in expected.items():
        if name in result:continue
        candidates=native['nativeMatches'].get(name)
        require(isinstance(candidates,list) and len(candidates)==1,'Shipped native member has missing/ambiguous source ownership: '+name)
        candidate=candidates[0];owner,member=candidate['owner'],candidate['member']
        require(owner in components and components[owner]['resolvedNativeFiles'].get(member)==info,
                'Shipped native member differs from observed consumed prefix: '+name)
        component=components[owner]
        if 'binaryArchive' in component:
            require(component['archiveMembership']['members'].get(member)==info,
                    'Shipped consumed member is absent from its original native archive: '+name)
            origin='original-prebuilt-archive'
        else:
            require(component.get('builtFromSource') is True,'Native source-built origin is unobserved: '+name)
            origin='current-consumed-source-build'
        result[name]=dict(owner=owner,member=member,origin=origin,**info)
    require(set(result)==set(expected),'Incomplete actual native owner closure')
    return result


def collect(root, native_path, run):
    root,native_path=Path(root).absolute(),Path(native_path).absolute()
    from build_package import assert_current_checkout, source_inputs
    assert_current_checkout(root,run['sourceCommit']);validate(run,run)
    data=read_owned(native_path.parent,native_path.name,16*1024**2);native=json.loads(data)
    validate(native.get('runContext'),run)
    require(native.get('sourceCommit')==run['sourceCommit'] and native.get('sourceLicenseClosure') is False,
            'Current native original/source flags differ')
    qt=Path(native['qtPrefix']);require(qt.is_absolute(),'Actual original Qt installation prefix must be absolute')
    repeated=observe(root,root/'build',root/'stage',qt,run['sourceCommit'],run,native_path.parent)
    require(repeated==native,'Original native evidence differs from independent current source/archive observation')
    owners=resolve_native_owners(repeated)
    sources=collect_sources(root,repeated,native_path.parent/'native-source/qt')
    microsoft=verify_microsoft(root)
    require(microsoft['nativeFiles']=={name:row['owner'] for name,row in repeated['windowsRuntimeOrigins']['nativeFiles'].items()},
            'Original Microsoft terms do not cover the exact shipped Microsoft components')
    require(file_record(native_path)==digest(data) and inventory_tree(root/'stage')==native['payload'],
            'Original native evidence or current stage changed during source comparison')
    assert_current_checkout(root,run['sourceCommit'])
    return dict(schemaVersion=1,sourceCommit=run['sourceCommit'],runContext=run,nativeInput=digest(data),
                sourceInputs=source_inputs(root),nativeOriginalOwners=owners,nativeFileCount=len(owners),
                sources=sources,microsoftTerms=microsoft,nativeOwnershipComplete=True,
                preferredSourceComparisonComplete=True,noticeCoverageComplete=True,sourceLicenseClosure=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['collect','verify'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-commit',required=True);args=parser.parse_args()
    record=collect(args.root,args.native,current(args.source_commit))
    if args.command=='collect':_write_new(args.output,(json.dumps(record,indent=2)+'\n').encode())
    else:
        before=read_owned(args.output.absolute().parent,args.output.name,16*1024**2)
        require(json.loads(before)==record,'Original complete source evidence differs from current independent comparison')
    print('PASS: exact current native/source/notice inputs; installed and public application-source gates remain separate.')
