# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'distribution/msix'))
from source_archives import digest


class WindowsRuntimeProofTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('windows_runtime_proof'), 'Independent Windows origin verifier absent')
        import windows_runtime_proof
        self.m = windows_runtime_proof; self.commit = 'a'*40
        vc = 'C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC'
        crt = vc + '/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT'
        self.config = dict(schemaVersion=1, vcInstallDir=vc, msvcRedistDir=vc+'/Redist/MSVC/14.44.35112',
                           msvcCrtDir=crt, windowsSdkDir='C:/Program Files (x86)/Windows Kits/10',
                           windowsSdkVersion='10.0.26100.0\\', debugRuntimes=False,
                           libraries=[crt+'/'+name for name in self.m.CRT])
        self.payload = {}; files = {}
        for name in self.m.CRT + ('d3dcompiler_47.dll',):
            path = 'bin/'+name; self.payload[path] = digest(('MZ fixture '+name).encode())
            origin = crt+'/'+name if name in self.m.CRT else self.config['windowsSdkDir']+'/Redist/D3D/x64/'+name
            files[path] = dict(owner='Microsoft.VC143.CRT' if name in self.m.CRT else 'Microsoft.WindowsSDK.D3D',
                              origin=origin, file=self.payload[path], signature=dict(status='Valid',
                              signerSubject='CN=Microsoft Windows, O=Microsoft Corporation, C=US',
                              signerIssuer='CN=fixture', signerThumbprint='1'*40, signerCertificateSha256='2'*64,
                              companyName='Microsoft Corporation', fileVersion='fixture', productVersion='fixture', originalFilename=name))
        self.raw = json.dumps(self.config).encode()
        self.record = dict(schemaVersion=1, sourceCommit=self.commit, configuredRuntimes=digest(self.raw),
                           files=files, nativeFileCount=9, sourceLicenseClosure=False)

    def verify(self): return self.m.verify(self.record, self.raw, self.payload, self.commit)

    def test_exact_current_configuration_origin_signatures_and_all_nine_files_bound(self):
        result = self.verify()
        self.assertEqual(set(result['nativeFiles']), set(self.payload))
        self.assertEqual(result['configuredRuntimes'], digest(self.raw))
        self.assertIs(result['sourceLicenseClosure'], False)

    def test_partial_stale_untyped_foreign_signature_or_payload_evidence_fails(self):
        original = copy.deepcopy(self.record)
        name='bin/msvcp140.dll'
        mutations = [lambda r: r.update(sourceCommit='b'*40), lambda r: r.update(schemaVersion=True),
                     lambda r: r.update(nativeFileCount='9'), lambda r: r.update(sourceLicenseClosure=True),
                     lambda r: r['configuredRuntimes'].update(sha256='b'*64),
                     lambda r: r['files'].pop(name), lambda r: r['files'].update({'bin/foreign.dll':r['files'][name]}),
                     lambda r: r['files'][name].update(origin='C:/foreign/msvcp140.dll'),
                     lambda r: r['files'][name].update(owner='Microsoft.WindowsSDK.D3D'),
                     lambda r: r['files'][name]['file'].update(sha256='b'*64),
                     lambda r: r['files'][name]['signature'].update(status='NotSigned'),
                     lambda r: r['files'][name]['signature'].update(signerSubject='CN=Microsoft imposter'),
                     lambda r: r['files'][name]['signature'].update(companyName='foreign'),
                     lambda r: r['files'][name]['signature'].update(originalFilename=None),
                     lambda r: r['files'][name]['signature'].update(signerCertificateSha256='bad')]
        for mutation in mutations:
            self.record=copy.deepcopy(original); mutation(self.record)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify()

    def test_coherent_foreign_debug_sdk_or_duplicate_configuration_does_not_gain_ownership(self):
        original=copy.deepcopy(self.config)
        for mutation in (lambda c: c.update(debugRuntimes='false'), lambda c: c.update(debugRuntimes=True),
                         lambda c: c.update(windowsSdkVersion='10.0.19041.0'),
                         lambda c: c.update(vcInstallDir='C:/foreign/VC'),
                         lambda c: c.update(msvcCrtDir=c['msvcCrtDir'].replace('/x64/','/x86/')),
                         lambda c: c['libraries'].__setitem__(1,c['libraries'][0]),
                         lambda c: c['libraries'].__setitem__(0,c['libraries'][0]+':stream'),
                         lambda c: c.update(msvcRedistDir=c['msvcRedistDir']+'/../14.44.35112')):
            self.config=copy.deepcopy(original); mutation(self.config); self.raw=json.dumps(self.config).encode()
            self.record['configuredRuntimes']=digest(self.raw)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify()

    def test_production_reader_binds_both_original_files_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); config=root/'configuration.json'; receipt=root/'receipt.json'
            config.write_bytes(self.raw); data=json.dumps(self.record).encode(); receipt.write_bytes(data)
            result=self.m.collect(config, receipt, self.payload, self.commit)
            self.assertEqual(result['originalReceipt'], digest(data))
            run=dict(repository='hashfunction/wavequay',sourceCommit=self.commit,runId='34700392536',runAttempt=2)
            with self.assertRaises(ValueError):self.m.collect(config,receipt,self.payload,self.commit,run)
            self.record['runContext']=run;receipt.write_text(json.dumps(self.record))
            self.assertEqual(self.m.collect(config,receipt,self.payload,self.commit,run)['runContext'],run)
            stale=dict(run,runAttempt=1)
            with self.assertRaises(ValueError):self.m.collect(config,receipt,self.payload,self.commit,stale)
            config.write_bytes(self.raw+b' ')
            with self.assertRaisesRegex(ValueError, 'configuration bytes'):
                self.m.collect(config, receipt, self.payload, self.commit)


if __name__ == '__main__': unittest.main()
