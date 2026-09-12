# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Independently interpret the Windows observer's exact runtime receipt.

Authenticode observation is performed by windows-runtimes.ps1 on Windows. This
validator does not invent signatures: it binds that retained observation to the
current CMake configuration, current source and each exact staged native file.
"""
import json
import re
from pathlib import Path

from files import _checked_path, file_record
from source_archives import digest
from source_catalog import checked_hash, read_owned, require

CRT = ('msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'msvcp140_atomic_wait.dll',
       'msvcp140_codecvt_ids.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'concrt140.dll')
VC = 'C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC'
SDK = 'C:/Program Files (x86)/Windows Kits/10'


def windows_path(value):
    require(isinstance(value, str), 'Missing observed absolute Windows runtime path')
    value = value.replace('\\', '/').rstrip('/')
    require(re.fullmatch(r'[A-Za-z]:/[^/].*', value), 'Expected observed absolute Windows runtime path')
    _checked_path(value[3:])
    return value


def configured_plan(context):
    require(type(context.get('schemaVersion')) is int and context['schemaVersion'] == 1
            and context.get('debugRuntimes') is False, 'Release-only typed CMake runtime observation required')
    require(windows_path(context['vcInstallDir']).casefold() == VC.casefold(), 'Foreign configured Microsoft toolchain')
    redist = windows_path(context['msvcRedistDir'])
    require(re.fullmatch(re.escape(VC) + r'/Redist/MSVC/[0-9]+\.[0-9]+\.[0-9]+', redist, re.I),
            'Expected configured original VC release redistributable directory')
    crt = redist + '/x64/Microsoft.VC143.CRT'
    require(windows_path(context['msvcCrtDir']).casefold() == crt.casefold()
            and windows_path(context['windowsSdkDir']).casefold() == SDK.casefold()
            and context['windowsSdkVersion'].rstrip('\\/') == '10.0.26100.0',
            'Configured Microsoft CRT architecture or exact SDK differs')
    libraries = context['libraries']
    require(isinstance(libraries, list) and len(libraries) == len(CRT), 'Exact configured VC file count required')
    require({windows_path(path).casefold() for path in libraries} == {(crt+'/'+name).casefold() for name in CRT},
            'Missing/duplicate/foreign configured original VC member')
    result = {'bin/'+name: dict(owner='Microsoft.VC143.CRT', origin=crt+'/'+name) for name in CRT}
    result['bin/d3dcompiler_47.dll'] = dict(owner='Microsoft.WindowsSDK.D3D', origin=SDK+'/Redist/D3D/x64/d3dcompiler_47.dll')
    return result


def verify(record, configuration, payload, source_commit):
    require(isinstance(configuration, bytes) and len(configuration) <= 65536, 'Bounded original runtime configuration required')
    require(isinstance(source_commit, str) and re.fullmatch('[0-9a-f]{40}', source_commit)
            and type(record.get('schemaVersion')) is int and record['schemaVersion'] == 1
            and record.get('sourceCommit') == source_commit and record.get('sourceLicenseClosure') is False,
            'Current source and typed Windows origin observation required')
    require(record.get('configuredRuntimes') == digest(configuration), 'Original runtime configuration bytes differ')
    plan = configured_plan(json.loads(configuration.decode('utf-8-sig')))
    require(type(record.get('nativeFileCount')) is int and record['nativeFileCount'] == len(plan)
            and isinstance(record.get('files'), dict) and set(record['files']) == set(plan),
            'All nine exact Microsoft origins must be independently observed')
    natives = {}
    for name, expected in plan.items():
        observed = record['files'][name]; signature = observed['signature']; checked_hash(observed['file'])
        require(observed.get('owner') == expected['owner']
                and windows_path(observed['origin']).casefold() == expected['origin'].casefold()
                and payload.get(name) == observed['file'], 'Current staged file differs from exact configured Microsoft origin: ' + name)
        require(signature.get('status') == 'Valid' and signature.get('companyName') == 'Microsoft Corporation'
                and isinstance(signature.get('signerSubject'), str)
                and re.search(r'(?:^|,\s*)O=Microsoft Corporation(?:,|$)', signature['signerSubject']),
                'Original Microsoft signature observation is incomplete/foreign: ' + name)
        for field, expression in [('signerThumbprint', '[0-9a-fA-F]{40}'), ('signerCertificateSha256', '[0-9a-f]{64}')]:
            require(isinstance(signature.get(field), str) and re.fullmatch(expression, signature[field]),
                    'Original Microsoft signing certificate observation differs: ' + name)
        for field in ('signerSubject', 'signerIssuer', 'companyName', 'originalFilename', 'fileVersion', 'productVersion'):
            require(isinstance(signature.get(field), str) and 0 < len(signature[field]) <= 4096,
                    'Missing bounded original Microsoft signature/version metadata: ' + name)
        natives[name] = dict(owner=expected['owner'], origin=observed['origin'], signature=signature, **observed['file'])
    return dict(schemaVersion=1, sourceCommit=source_commit, configuredRuntimes=digest(configuration),
                nativeFiles=natives, nativeFileCount=len(natives), sourceLicenseClosure=False)


def collect(configuration_path, receipt_path, payload, source_commit, run_context=None):
    configuration_path, receipt_path = Path(configuration_path).absolute(), Path(receipt_path).absolute()
    config = read_owned(configuration_path.parent, configuration_path.name, 65536)
    receipt = read_owned(receipt_path.parent, receipt_path.name, 1024**2)
    original = json.loads(receipt.decode('utf-8-sig'))
    record = verify(original, config, payload, source_commit)
    if run_context is not None:
        from run_context import validate
        validate(original.get('runContext'), run_context)
        record['runContext'] = run_context
    require(file_record(configuration_path) == digest(config) and file_record(receipt_path) == digest(receipt),
            'Windows runtime originals changed during independent interpretation')
    return dict(record, originalReceipt=digest(receipt))
