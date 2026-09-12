# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'distribution/msix'))
from source_archives import digest
from windows_runtime_proof import CRT


class SourceClosureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('source_closure'),'Complete original native/source ownership gate absent')
        import source_closure
        self.m=source_closure
        paths=['bin/WaveWeft.exe','bin/Qt6Core.dll','bin/opengl32sw.dll','bin/libexpat.dll']+['bin/'+name for name in CRT+('d3dcompiler_47.dll',)]
        self.payload={path:digest(('MZ fixture '+path).encode()) for path in paths}
        def original(path,owner):return dict(owner=owner,member=Path(path).name,**self.payload[path])
        windows={path:original(path,'Microsoft.VC143.CRT' if Path(path).name in CRT else 'Microsoft.WindowsSDK.D3D') for path in paths[4:]}
        self.native=dict(payload=self.payload,builtApplication=dict(path=paths[0],**self.payload[paths[0]]),
            qtOriginalArchives=dict(nativeFiles={paths[1]:original(paths[1],'qtbase')}),
            mesaOriginalArchive=dict(nativeFiles={paths[2]:original(paths[2],'Mesa')}),
            windowsRuntimeOrigins=dict(nativeFiles=windows),unresolvedNative=list(windows),
            components=[dict(name='expat',binaryArchive={},archiveMembership=dict(members={'bin/libexpat.dll':self.payload[paths[3]]}),
                             resolvedNativeFiles={'bin/libexpat.dll':self.payload[paths[3]]})],
            nativeMatches={paths[3]:[dict(owner='expat',member='bin/libexpat.dll')]})

    def test_complete_distinct_original_owners_cover_every_current_native_member(self):
        owners=self.m.resolve_native_owners(self.native)
        self.assertEqual(set(owners),set(self.payload))
        self.assertEqual(owners['bin/libexpat.dll']['owner'],'expat')
        self.assertEqual(owners['bin/WaveWeft.exe']['owner'],'application')

    def test_unknown_partial_duplicate_or_coherently_reassigned_payload_cannot_close_sources(self):
        original=copy.deepcopy(self.native)
        mutations=[lambda n:n['payload'].update({'bin/foreign.dll':digest(b'MZ foreign')}),
                   lambda n:n['qtOriginalArchives']['nativeFiles']['bin/Qt6Core.dll'].update(sha256='a'*64),
                   lambda n:n['mesaOriginalArchive']['nativeFiles'].update({'bin/Qt6Core.dll':n['qtOriginalArchives']['nativeFiles']['bin/Qt6Core.dll']}),
                   lambda n:n['unresolvedNative'].append('bin/foreign.dll'),
                   lambda n:n['windowsRuntimeOrigins']['nativeFiles'].pop('bin/msvcp140.dll'),
                   lambda n:n['components'].append(copy.deepcopy(n['components'][0])),
                   lambda n:n['nativeMatches']['bin/libexpat.dll'].append(copy.deepcopy(n['nativeMatches']['bin/libexpat.dll'][0])),
                   lambda n:n['nativeMatches']['bin/libexpat.dll'][0].update(owner='foreign'),
                   lambda n:n['components'][0]['archiveMembership']['members'].clear(),
                   lambda n:n['builtApplication'].update(sha256='a'*64)]
        for mutate in mutations:
            self.native=copy.deepcopy(original);mutate(self.native)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):self.m.resolve_native_owners(self.native)


if __name__=='__main__':unittest.main()
