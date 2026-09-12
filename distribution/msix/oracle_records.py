# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Validate original stopped-owner file oracle and cleanup snapshot metadata.

consumer_audio.finalize independently inspected the actual WAV/SQLite/recipe
files before exact owned cleanup. This module binds those original records;
it does not claim to reparse media or projects that have already been deleted.
"""
import io
import json
import math
from pathlib import PureWindowsPath
import re
import sys
import uuid
import wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import consumer_audio as audio
from source_archives import digest
from source_catalog import require
from files import _checked_path


def integer(value,minimum=0,maximum=2**63-1):
    require(type(value) is int and minimum<=value<=maximum,'Missing or invalid typed integer evidence')
    return value


def hashed(value,allow_empty=False):
    require(isinstance(value,dict) and set(value)=={'bytes','sha256'},'Incomplete or extra file hash record')
    integer(value['bytes'],0 if allow_empty else 1,256*1024**2)
    require(isinstance(value['sha256'],str) and re.fullmatch('[0-9a-f]{64}',value['sha256']),'Invalid original SHA-256')
    return value


def inventory(value):
    require(isinstance(value,dict) and len(value)<=1000,'Incomplete or excessive cleanup snapshot')
    for name,row in value.items():
        _checked_path(name)
        if row=={'directory':True}:
            require(row['directory'] is True,'Untyped directory snapshot')
        else:hashed(row,True)
    require(sum(row.get('bytes',0) for row in value.values())<=256*1024**2,'Excessive cleanup snapshot bytes')


def path(value):
    require(isinstance(value,str),'Missing original Windows path')
    p=PureWindowsPath(value)
    require(p.is_absolute() and '..' not in p.parts,'Noncanonical original Windows path')
    return p


def validate_oracle(value,claim,claim_raw,gui,package_claim,evidence_root):
    commit=gui['sourceCommit']
    require(gui.get('diagnosticAccessibilityGraph') is False and gui.get('ownedJobEmptyBeforeClose') is True,
            'Diagnostic or unproved stopped-owner oracle cannot qualify')
    require(type(value.get('schemaVersion')) is int and value['schemaVersion']==1 and value.get('sourceCommit')==commit
            and value.get('verified') is True and value.get('cleanup') is True and value.get('errors')==[],
            'Missing/stale/incomplete original consumer file oracle')
    require(set(claim)=={'schemaVersion','sourceCommit','token','protected'} and type(claim['schemaVersion']) is int
            and claim['schemaVersion']==1 and claim['sourceCommit']==commit and str(uuid.UUID(claim['token']))==claim['token']
            and json.loads(claim_raw.decode('utf-8'))==claim,'Original exclusive fixture claim differs')
    wav=io.BytesIO()
    with wave.open(wav,'wb') as output:
        output.setparams((2,2,audio.RATE,0,'NONE','not compressed'));output.writeframes(b''.join(audio.demo_frames()))
    protected={'Dawn-thread.wav':digest(wav.getvalue()),'protected.txt':digest(b'WaveWeft consumer fixture: preserve these original bytes.\n')}
    require(claim['protected']==protected,'Original fixture is not the exact original six-second stereo composition')
    files=value['files'];inventory(files)
    required={'.owner.json','Dawn-thread.wav','protected.txt','Dawn-thread.aup4','reversed.wav','reopened.wav'}
    require(required<=set(files)<=audio.FIXTURE_FILES and all('directory' not in row for row in files.values()),
            'Original fixture snapshot is missing/partial or contains foreign files')
    require(files['.owner.json']==digest(claim_raw) and all(files[name]==row for name,row in protected.items()),
            'Original fixture snapshot differs from retained owner/input claim')
    project=value['project']
    require(set(project)=={'bytes','sha256','applicationId','documentBytes','blocks','sampleBytes','integrity'}
            and project['applicationId']=='AUDY' and project['integrity']=='ok','Incomplete original SQLite project oracle')
    hashed({key:project[key] for key in ('bytes','sha256')});integer(project['bytes'],4097)
    integer(project['documentBytes'],1);integer(project['blocks'],1);integer(project['sampleBytes'],audio.FRAMES*4)
    require(files['Dawn-thread.aup4']=={key:project[key] for key in ('bytes','sha256')},'Project oracle does not bind the original cleanup snapshot')
    require(set(value['exports'])=={'reversed.wav','reopened.wav'},'Both actual UI export oracles are required')
    for name,record in value['exports'].items():
        require(set(record)=={'bytes','sha256','frames','sampleRate','channels','bits','seconds','rms','maximumErrorLsb','meanErrorLsb','pcmSha256'},
                'Incomplete original exported PCM oracle')
        hashed({key:record[key] for key in ('bytes','sha256')});integer(record['bytes'],audio.FRAMES*4+44)
        require(files[name]=={key:record[key] for key in ('bytes','sha256')},'Export oracle differs from original cleanup snapshot')
        for key,expected in dict(frames=audio.FRAMES,sampleRate=audio.RATE,channels=2,bits=16,seconds=6).items():
            require(type(record[key]) is int and record[key]==expected,'Original export encoding/duration differs')
        integer(record['maximumErrorLsb'],0,4)
        for key,low,high in [('rms',.01,.5),('meanErrorLsb',0,1.5)]:
            number=record[key];require(type(number) in (int,float) and math.isfinite(number)
                and (low<number<high if key=='rms' else low<=number<=high),'Original reversed PCM oracle bounds differ')
        require(record['meanErrorLsb']<=record['maximumErrorLsb'] and isinstance(record['pcmSha256'],str)
                and re.fullmatch('[0-9a-f]{64}',record['pcmSha256']),'Original PCM hash/error evidence differs')
    profiles=value['profileFiles'];host=gui['consumerProfileClaim']
    require(str(uuid.UUID(host['token']))==host['token'] and host['marker']=='.waveweft-consumer-owner'
            and isinstance(profiles,list) and len(profiles)==len(host['paths'])==7,'Incomplete owned host profile snapshot')
    require(len({path(p['path']) for p in profiles})==len(profiles)
            and {path(p['path']) for p in profiles}=={path(p) for p in host['paths']},'Host profile snapshot differs from exact claimed paths')
    for profile in profiles:
        inventory(profile['entries'])
        require(profile['entries'].get(host['marker'])==digest(host['token'].encode()),'Host profile owner snapshot differs')
        require(path(profile['path'])==path(str(evidence_root))/'private-environment' or
                (path(profile['path']).name in ('Audacity4','Audacity4Development') and
                 any(path(before['path'])==path(profile['path']) and before['exists'] is False for before in gui['userStateBefore'])),
                'Host profile snapshot was not absent before normal installed UI')
    registry=value['profileRegistry']
    require(isinstance(registry,dict) and set(registry)==set(host['registry'])
            and set(registry)=={r'Software\Trieflow\Audacity4',r'Software\Trieflow\Audacity4Development'},'Owned registry snapshot differs')
    for entries in registry.values():
        require(isinstance(entries,dict) and '' in entries and 0<len(entries)<=1000
                and all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) for h in entries.values()),'Incomplete registry snapshot hashes')
    package=value['packageProfileFiles']
    require(value.get('packageProfileCleanupDelegatedToUninstall') is True and isinstance(package,list) and len(package)==1
            and path(package[0]['path'])==path(package_claim['dataRoot']) and package_claim['preinstallDataRootAbsent'] is True
            and type(package_claim.get('schemaVersion')) is int and package_claim['schemaVersion']==1
            and package_claim['sourceCommit']==commit and str(uuid.UUID(package_claim['token']))==package_claim['token'],
            'Missing/stale exact package profile snapshot and uninstall delegation')
    inventory(package[0]['entries'])
    require(package[0]['entries'].get('.waveweft-msix-owner')==digest(package_claim['token'].encode()),'Package owner marker snapshot differs')
    recipes=[]
    for profile in profiles+package:
        for relative,record in profile['entries'].items():
            if PureWindowsPath(relative).name=='export-recipes-v1.json':recipes.append((path(profile['path'])/relative,hashed(record)))
    recipe=value['recipe'];require(set(recipe)=={'path','bytes','sha256','settings'} and len(recipes)==1
            and recipes[0]==(path(recipe['path']),{key:recipe[key] for key in ('bytes','sha256')}),'Recipe oracle does not bind the unique original profile snapshot')
    settings=recipe['settings'];audio.validate_recipe(dict(schemaVersion=1,recipes=[settings]))
    for key in ('schemaVersion','process','channelType','channels','sampleRate'):integer(settings[key])
    for parameter in settings['parameters']:
        for key in ('id','type','value'):integer(parameter[key])
    return dict(project=project,exports=value['exports'],recipe=recipe,originalFileOracleVerified=True,
                originalSnapshotHashesBound=True,deletedFilesReparsed=False)
