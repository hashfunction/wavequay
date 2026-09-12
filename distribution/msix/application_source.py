# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Anonymous, bounded public Git object-tree comparison for current sources.

GitHub's commit and complete recursive tree must match every local object/mode,
including both pinned submodule links. Original dependency archives are checked
separately by source_delivery. No token, private API, or mutable branch is used.
"""
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from source_catalog import require
from source_archives import digest
from source_material import SUBMODULES
from run_context import validate

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Public source API redirect refused')


def request(url):
    require(url.startswith('https://api.github.com/repos/'),'Unexpected public source API origin')
    start=time.monotonic()
    req=urllib.request.Request(url,headers={'User-Agent':'WaveWeft-public-source-verifier','Accept':'application/vnd.github+json'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response:
        require(response.status==200 and response.url==url,'Public source API response differs')
        chunks=[];size=0
        while block:=response.read(1024*1024):
            size+=len(block);require(size<=16*1024**2 and time.monotonic()-start<=120,'Public source API bound exceeded')
            chunks.append(block)
    raw=b''.join(chunks)
    return json.loads(raw),dict(url=url,**digest(raw),anonymous=True,httpsVerified=True)


def local_tree(root,commit):
    tree=subprocess.check_output(['git','-C',str(root),'rev-parse',commit+'^{tree}'],text=True).strip()
    raw=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','-t','-z',commit])
    entries={}
    for record in raw.split(b'\0'):
        if not record:continue
        header,path=record.split(b'\t',1);mode,kind,sha=header.decode().split(' ')
        entries[path.decode('utf-8')]=dict(mode=mode,type=kind,sha=sha)
    return dict(tree=tree,entries=entries)


def verify_responses(repository,commit,local,repo,revision,tree):
    require(repo.get('full_name')==repository and repo.get('private') is False and repo.get('visibility')=='public',
            'Current corresponding-source repository is not the exact public repository')
    require(revision.get('sha')==commit and revision.get('tree',{}).get('sha')==local['tree']
            and tree.get('sha')==local['tree'] and tree.get('truncated') is False,'Public current source commit/tree is missing or incomplete')
    rows=tree.get('tree');require(isinstance(rows,list) and 0<len(rows)<=100000,'Missing/bounded public source tree')
    observed={}
    for row in rows:
        path=row['path'];require(isinstance(path,str) and path not in observed,'Duplicate public source member')
        observed[path]={key:row[key] for key in ('mode','type','sha')}
    require(observed==local['entries'],'Public source is not the complete exact current local Git tree')
    return dict(repository='https://github.com/'+repository,commit=commit,tree=local['tree'],entryCount=len(observed),
                completeTreeMatched=True,publicRepository=True)


def collect(root,run,fetch=request):
    validate(run,run);root=Path(root)
    definitions={'application':dict(repository='https://github.com/hashfunction/wavequay',commit=run['sourceCommit']),**SUBMODULES}
    result={}
    for name,row in definitions.items():
        repository=row['repository'].removeprefix('https://github.com/');commit=row['commit']
        local=local_tree(root if name=='application' else root/name,commit)
        base='https://api.github.com/repos/'+repository
        urls=[base,base+'/git/commits/'+commit,base+'/git/trees/'+local['tree']+'?recursive=1']
        responses=[fetch(url) for url in urls]
        proof=verify_responses(repository,commit,local,*(item[0] for item in responses))
        proof['responses']=[item[1] for item in responses];result[name]=proof
    links={name:row for name,row in local_tree(root,run['sourceCommit'])['entries'].items() if row['type']=='commit'}
    require(links=={name:dict(mode='160000',type='commit',sha=row['commit']) for name,row in SUBMODULES.items()},
            'Current application submodules differ from complete public source closure')
    for name,row in SUBMODULES.items():
        require(not any(item['type']=='commit' for item in local_tree(root/name,row['commit'])['entries'].values()),
                'Unaccounted recursive submodule source')
    return dict(schemaVersion=1,sourceCommit=run['sourceCommit'],runContext=run,repositories=result,
                anonymousPublicTreesMatched=True)
