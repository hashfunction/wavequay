# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Independent final gate for exactly one untouched unsigned assigned MSIX.

Both original installed lifecycles, current payload/source/run/attempt, complete
native/source/notice comparison and anonymously public exact application source
are mandatory. Staged or diagnostic observations cannot replace either install.
Original binary oracles are bound to retained snapshots, not rerun after cleanup.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from files import file_record,inventory_tree,_regular_stream,_reject_link,_write_new
from source_archives import digest
from source_catalog import read_owned,require
from run_context import current,validate as validate_run
from package import identity_for_mode,package_name
from build_package import verify_record,assert_current_checkout,source_inputs
from source_closure import collect as collect_closure
from application_source import collect as collect_public_source
from consumer_records import validate as validate_consumer
from verify_gui_evidence import verify as verify_gui
from consumer_audio import validate_flow
from oracle_records import hashed,integer,path

INSTALL_FILES=('installation-start.json','gui/gui-observations.json','gui/consumer-workflow.json',
    'gui/consumer-validation.json','gui/consumer-fixture-claim.json','gui/installed-profile-claim.json',
    'gui/display-preparation.json','gui/watchdog.json')
STAGE_FILES=('gui/gui-observations.json','gui/consumer-workflow.json','gui/consumer-validation.json',
             'gui/consumer-fixture-claim.json','gui/display-preparation.json','gui/watchdog.json')


def validate_stage(record,run):
    require(record.get('source_commit')==run['sourceCommit'],'Staged consumer belongs to another source')
    validate_run(record.get('runContext'),run)
    for key in ('built','native_recipe_tests','staged','windows_main_window_verified','windows_local_file_workflow_verified'):
        require(record.get(key) is True,'Required current staged qualification is incomplete: '+key)
    for key in ('diagnosticAccessibilityGraph','audio_device_tests','native_export_tests','source_license_closure','submitted'):
        require(record.get(key) is False,'Premature/diagnostic staged claim: '+key)
    require(record.get('diagnosticProvenanceErrors')==[],'Diagnostic provenance failures cannot qualify')


def validate_watchdog(record,gui):
    require(record.get('timed_out') is False and type(record.get('exit_code')) is int and record['exit_code']==0,
            'Original native observer exited unsuccessfully or timed out')
    integer(record.get('helper_pid'),1)
    require(record['helper_pid']!=gui['processId'] and path(record['helper_executable'])==
            path(gui['systemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe','Original native observer host identity differs')
    elapsed=record.get('elapsed_seconds')
    require(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>0,'Missing actual observer elapsed time')


def validate_install_state(start,result,run,mode,unsigned):
    for record in (start,result):
        validate_run(record.get('runContext'),run)
        require(record.get('sourceCommit')==run['sourceCommit'] and record.get('identityMode')==mode,'Installed source/identity mode differs')
    require(type(result.get('schemaVersion')) is int and result['schemaVersion']==1 and result.get('runId')==run['runId']
            and result.get('runAttempt')==str(run['runAttempt']) and result.get('identity')==identity_for_mode(mode),
            'Original installed schema/legacy run/identity differs')
    for key in ('installation_qualification_passed','add_completed','installed_by_us','preinstall_data_root_absent',
        'normal_close','uninstall_verified','package_profile_removed','certificate_trust_removed','personal_certificate_removed',
        'temporary_signing_files_removed','unsigned_package_unchanged'):
        require(result.get(key) is True,'Required actual installed lifecycle/cleanup incomplete: '+key)
    require(result.get('primary_error') is None and result.get('cleanup_errors')==[] and result.get('preflight_package_full_names')==[]
            and result.get('residual_package_full_names')==[],'Failed, adopted or residual installed lifecycle')
    require(result.get('publicRelease') is False and result.get('licenseClearanceClaimed') is False,'Premature installed release claim')
    for key in ('package_full_name','package_family_name','install_location','package_data_root','preflight_package_full_names',
                'add_completed','installed_by_us','preinstall_data_root_absent'):
        require(key in start and start[key]==result[key],'Original installed start/result identity differs: '+key)
    integer(result.get('process_id'),1)
    require(result.get('unsigned_package')==unsigned,'Installed package is not the current untouched unsigned package')
    hashed(result['unsigned_package']);hashed(result['signed_copy'])
    require(result['signed_copy']['sha256']!=unsigned['sha256'] and result['signed_copy']['bytes']>unsigned['bytes'],
            'Distinct temporary signed installation copy not recorded')


class Originals:
    def __init__(self,root):self.root=Path(root).absolute();self.records={}
    def raw(self,name):
        raw=read_owned(self.root,name,16*1024**2);self.records[name]=digest(raw);return raw
    def json(self,name):return json.loads(self.raw(name).decode('utf-8-sig'))
    def unchanged(self):
        require(all(file_record(self.root/name)==record for name,record in self.records.items()),'Original qualification evidence changed during final verification')


def validate_hash_bindings(receipt,expected_names,originals,prefix=''):
    require(isinstance(receipt,dict) and set(receipt)==set(expected_names),'Missing or extra original evidence snapshot bindings')
    for name in expected_names:
        hashed(receipt[name]);originals.raw(prefix+name)
        require(receipt[name]==originals.records[prefix+name],'Original evidence snapshot hash differs: '+name)


def collect(root,run):
    root=Path(root).absolute();commit=run['sourceCommit'];assert_current_checkout(root,commit)
    evidence=Originals(root/'build-evidence');prior=evidence.json('result.json');validate_stage(prior,run)
    validate_hash_bindings(prior.get('stageEvidence'),STAGE_FILES,evidence)
    native=evidence.json('native-inputs.json');validate_run(native.get('runContext'),run)
    require(type(native.get('schemaVersion')) is int and native['schemaVersion']==1 and native.get('sourceLicenseClosure') is False,
            'Native original schema/qualification flags differ')
    stage=inventory_tree(root/'stage');require(native['payload']==stage,'Current native stage differs')
    recorded_inventory=evidence.json('stage-inventory.json')
    require(isinstance(recorded_inventory,list) and len(recorded_inventory)==len(stage),'Current stage inventory count differs')
    normalized={}
    for row in recorded_inventory:
        name=row['path'].replace('\\','/');require(name not in normalized,'Duplicate stage inventory')
        normalized[name]=dict(bytes=row['bytes'],sha256=row['sha256'].lower())
    require(normalized==stage,'Original staged payload inventory differs from current bytes')
    staged_gui=evidence.json('gui/gui-observations.json');staged_flow=evidence.json('gui/consumer-workflow.json')
    verify_gui(staged_gui,recorded_inventory,root/'build-evidence/gui',commit)
    validate_flow(root/'build-evidence/gui',staged_flow,staged_gui)
    validate_watchdog(evidence.json('gui/watchdog.json'),staged_gui)
    staged_oracle=evidence.json('gui/consumer-validation.json')
    require(staged_oracle.get('sourceCommit')==commit and staged_oracle.get('verified') is True
            and staged_oracle.get('cleanup') is True and staged_oracle.get('errors')==[],'Original staged file oracle is incomplete')
    aggregate=evidence.json('msix/qualification-result.json');validate_run(aggregate.get('runContext'),run)
    require(type(aggregate.get('schemaVersion')) is int and aggregate['schemaVersion']==1 and aggregate.get('sourceCommit')==commit
            and aggregate.get('runId')==run['runId'] and aggregate.get('runAttempt')==str(run['runAttempt'])
            and aggregate.get('qualificationInstalled') is True and aggregate.get('storeInstalled') is True
            and aggregate.get('sourceLicenseClosure') is False and aggregate.get('publicRelease') is False
            and aggregate.get('error') is None,'Both separate installed qualifications are required')
    installed={};packages={};lifetimes=[]
    for mode in ('qualification','store'):
        prefix='msix/'+mode+'/';package=root/'build-evidence'/prefix/'package'/package_name(mode)
        record_path=package.parent/'package-record.json'
        packages[mode]=verify_record(package,record_path,root/'stage',root,root/'build-evidence/native-inputs.json',commit,mode)
        evidence.raw(prefix+'package/package-record.json')
        start=evidence.json(prefix+'install/installation-start.json');result=evidence.json(prefix+'install/installation-result.json')
        validate_install_state(start,result,run,mode,file_record(package))
        validate_hash_bindings(result.get('evidence'),INSTALL_FILES,evidence,prefix+'install/')
        folder=prefix+'install/gui/';gui=evidence.json(folder+'gui-observations.json')
        validate_watchdog(evidence.json(folder+'watchdog.json'),gui)
        require(result['process_id']==gui['processId'],'Installer process differs from original native observer')
        profile=evidence.json(folder+'installed-profile-claim.json')
        require(profile.get('identityMode')==mode and profile.get('packageFullName')==start['package_full_name']
                and profile.get('packageFamilyName')==start['package_family_name']
                and path(profile['dataRoot'])==path(start['package_data_root']),'Original package profile is foreign to owned installation')
        flow=evidence.json(folder+'consumer-workflow.json');oracle=evidence.json(folder+'consumer-validation.json')
        raw=evidence.raw(folder+'consumer-fixture-claim.json');claim=json.loads(raw)
        observed=validate_consumer(root/'build-evidence'/folder,gui,flow,oracle,claim,raw,profile,recorded_inventory,commit,start)
        installed[mode]=dict(processId=gui['processId'],startedUtc=gui['startedUtc'],
            packageFullName=start['package_full_name'],packageFamilyName=start['package_family_name'],
            originalFileOracleVerified=observed['originalFileOracleVerified'],originalSnapshotHashesBound=True,
            deletedFilesReparsed=False,normalClose=True,uninstalled=True,ownedCleanup=True)
        lifetimes.append((gui['processId'],gui['startedUtc']))
    require(len(set(lifetimes))==2,'One process observation was reused for both installed identities')
    closure=evidence.json('source-closure.json')
    require(closure==collect_closure(root,root/'build-evidence/native-inputs.json',run),
            'Original source closure differs from independent complete current source/origin comparison')
    require(type(closure.get('schemaVersion')) is int and closure['schemaVersion']==1,'Source closure schema differs')
    integer(closure['nativeFileCount'],1)
    require(closure['nativeFileCount']==len(closure['nativeOriginalOwners']),'Source closure native file count differs')
    require(type(closure['sources']['publication']['archiveCount']) is int and closure['sources']['publication']['archiveCount']==40,
            'Complete preferred-source archive count differs')
    for name in ('nativeOwnershipComplete','preferredSourceComparisonComplete','noticeCoverageComplete'):
        require(closure.get(name) is True,'Incomplete current corresponding-source proof')
    require(closure.get('sourceLicenseClosure') is False,'Premature source release approval')
    public=collect_public_source(root,run)
    evidence.unchanged();assert_current_checkout(root,commit)
    require(inventory_tree(root/'stage')==stage and source_inputs(root)==packages['store']['sourceInputs'],
            'Current source or runtime payload changed during final verification')
    return dict(schemaVersion=1,product='WaveWeft',version='1.0.1.0',sourceCommit=commit,runContext=run,
        identityMode='store',identity=identity_for_mode('store'),signed=False,diagnosticAccessibilityGraph=False,
        sourceLicenseClosure=True,installationQualificationPassed=True,unsignedStoreExportEligible=True,
        submitted=False,publicRelease=True,sourceInputs=packages['store']['sourceInputs'],
        nativeFileCount=closure['nativeFileCount'],preferredSourceArchiveCount=closure['sources']['publication']['archiveCount'],
        nativeOwnershipComplete=True,preferredSourceComparisonComplete=True,noticeCoverageComplete=True,
        publicApplicationSource=public,installed=installed,originalEvidence=evidence.records),evidence,packages


def export(root,output,run):
    root,output=Path(root).absolute(),Path(output).absolute()
    require(not os.path.lexists(output),'Store export output already exists; preserving original files')
    for parent in output.parents:_reject_link(parent)
    receipt,originals,packages=collect(root,run)
    package=root/'build-evidence/msix/store/package'/package_name('store')
    original=file_record(package)
    require(original==packages['store']['containerVerification']['package'],'Verified unsigned package changed before export')
    output.mkdir()
    with _regular_stream(package) as source,(output/package.name).open('xb') as destination:
        shutil.copyfileobj(source,destination,1024*1024)
    require(file_record(package)==file_record(output/package.name)==original,'Unsigned package changed during final export')
    originals.unchanged();assert_current_checkout(root,run['sourceCommit'])
    receipt['package']=dict(path=package.name,**original)
    _write_new(output/'store-export.json',(json.dumps(receipt,indent=2)+'\n').encode())
    require(set(inventory_tree(output))=={package.name,'store-export.json'},'Unexpected public output, signing or private file')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source-commit',required=True);args=parser.parse_args()
    export(args.root,args.output,current(args.source_commit))
    print('PASS: exact unsigned Store MSIX, both installed consumers and complete current corresponding source verified. Store submission remains separate.')
