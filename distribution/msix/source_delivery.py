# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Acquire exact published preferred sources and replay their original proofs.

Only the immutable, independently verified WaveWeft source release is used for
missing archives. Existing exact consumed download-cache entries are reused;
archives are never executed or extracted into the application source tree.
"""
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from files import _checked_path, _reject_link, file_record
from source_archives import digest
from source_catalog import checked_hash, read_owned, require, verify_archives
from source_publication import ASSET_BASE, verify_publication


def https_asset_url(url):
    parsed=urlsplit(url)
    require(parsed.scheme=='https' and parsed.hostname in ('github.com','release-assets.githubusercontent.com')
            and not parsed.username and not parsed.password and not parsed.fragment,
            'Source archive redirect must stay on the exact anonymous HTTPS asset hosts')


class SourceRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        https_asset_url(new_url)
        return super().redirect_request(request,response,code,message,headers,new_url)


def acquire_one(root, row, opener=None):
    root=Path(root); filename=row['filename']; owner=row['component']
    _checked_path(filename)
    require('/' not in filename and isinstance(owner,str) and re.fullmatch('[A-Za-z0-9_-]+',owner)
            and row['url']==ASSET_BASE+filename, 'Only a fixed owned WaveWeft preferred-source asset may be acquired')
    expected=dict(bytes=row['bytes'],sha256=row['sha256']);checked_hash(expected)
    original_leaf=Path(urlsplit(row['origin']).path).name;_checked_path(original_leaf)
    cache=root/'.ci-dependency-cache/corresponding-source'
    candidates=[cache/filename, root/'.ci-dependency-cache/downloads'/owner/original_leaf]
    for path in candidates:
        for parent in path.absolute().parents:
            if parent.exists():_reject_link(parent)
        if os.path.lexists(path):
            require(file_record(path)==expected, 'Existing exact source cache entry differs: '+owner+'/'+filename)
            return path
    cache.mkdir(parents=True,exist_ok=True);_reject_link(cache)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='wb',prefix='.source-',suffix='.partial',dir=cache,delete=False) as output:
            temporary=Path(output.name);started=time.monotonic()
            open_request=opener or build_opener(SourceRedirect()).open
            request=Request(row['url'],headers={'User-Agent':'WaveWeft-corresponding-source/1.0.1'})
            with open_request(request,timeout=60) as response:
                require(response.status==200, 'Exact source asset did not return HTTP 200')
                https_asset_url(response.geturl())
                require(urlsplit(response.geturl()).hostname=='release-assets.githubusercontent.com',
                        'Source asset did not resolve to the original GitHub asset service')
                total=0
                while True:
                    require(time.monotonic()-started<=300,'Source archive download exceeded the fixed five-minute bound')
                    chunk=response.read(min(1024**2,expected['bytes']-total+1))
                    if not chunk:break
                    total+=len(chunk);require(total<=expected['bytes'],'Source archive exceeded its exact published byte bound')
                    output.write(chunk)
        require(file_record(temporary)==expected,'Downloaded source archive differs from exact published size/hash')
        destination=cache/filename
        # Exclusive creation preserves an existing cache entry even if it
        # appears between the preflight and completed anonymous download.
        with temporary.open('rb') as source,destination.open('xb') as target:shutil.copyfileobj(source,target,1024**2)
        require(file_record(destination)==expected,'Retained exact source archive changed during copying')
        return destination
    finally:
        if temporary is not None:temporary.unlink()


def verify_preferred_sources(root, native, archives, retained_qt):
    root,retained_qt=Path(root),Path(retained_qt)
    publication=verify_publication(root)
    proof=verify_archives(root,archives,native)
    from qt_native_proof import INPUTS, MODULES
    from qt_source_proof import compare
    data=read_owned(root,INPUTS,8*1024**2);qt=json.loads(data)
    require(len(qt['modules'])==len(MODULES) and {row['name'] for row in qt['modules']}==set(MODULES),
            'Exact original Qt preferred-source module set required')
    comparisons={}
    for row in qt['modules']:
        name=row['name'];member='sbom/'+name+'-6.11.2.source.spdx'
        spdx=read_owned(retained_qt,member,32*1024**2)
        require(digest(spdx)==row['originalMetadata'][member], 'Retained original Qt source SPDX changed: '+name)
        archive=row['sourceArchive'];expected=dict(bytes=archive['bytes'],sha256=archive['sha256'])
        comparison=compare(archives[name+'/'+name],expected,row['sourcePrefix'],spdx,row['sourceComparison']['exceptions'])
        require(comparison==row['sourceComparison'],'Current preferred Qt source comparison differs from original reviewed inventory: '+name)
        comparisons[name]=comparison
    require(file_record(root/INPUTS)==digest(data),'Original Qt preferred-source inputs changed during comparison')
    return dict(schemaVersion=1,publication=publication,preferredSources=proof,qtPreferredSources=comparisons,
                qtFixedInputs=digest(data),sourceLicenseClosure=False)


def collect(root,native,retained_qt):
    root=Path(root);publication=verify_publication(root)
    archives={row['component']+'/'+row['subdir']:acquire_one(root,row) for row in publication['archives']}
    return verify_preferred_sources(root,native,archives,retained_qt)
