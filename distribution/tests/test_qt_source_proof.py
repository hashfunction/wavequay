# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'distribution/msix'))

class QtSourceProofTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('qt_source_proof'),'Qt original source comparison absent')
        import qt_source_proof
        self.m=qt_source_proof
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.data={'src/paint.cpp':b'int original;\n','CMakeLists.txt':b'original_build()\n','.tag':b'archive revision\n'}
        self.expected={'src/paint.cpp':hashlib.sha1(b'int original;\r\n').hexdigest(),'CMakeLists.txt':hashlib.sha1(self.data['CMakeLists.txt']).hexdigest(),'.tag':hashlib.sha1(b'original git tag').hexdigest(),'.gitignore':hashlib.sha1(b'original git ignore').hexdigest()}
        self.exceptions={'.tag':'release-generated-tag','.gitignore':'omitted-vcs-control'}
    def archive(self):
        p=self.root/'qt.tar.gz'
        with tarfile.open(p,'w:gz') as archive:
            for n,b in self.data.items():
                e=tarfile.TarInfo('qt-src/'+n);e.size=len(b);archive.addfile(e,io.BytesIO(b))
        return p
    def spdx(self):
        return ('SPDXVersion: SPDX-2.1\nDocumentName: qtfixture\n'+''.join('FileName: ./'+n.replace('/','\\')+'\nFileChecksum: SHA1: '+h+'\n' for n,h in self.expected.items())).encode()
    def test_original_inventory_exact_and_explicit_windows_line_endings(self):
        p=self.archive();proof=self.m.compare(p,self.m.file_record(p),'qt-src',self.spdx(),self.exceptions)
        self.assertEqual(proof['exactFiles'],1);self.assertEqual(proof['lfToCrlfFiles'],1)
        self.assertEqual(proof['exceptions'],self.exceptions);self.assertEqual(proof['comparedFiles'],2)
    def test_changed_or_missing_implementation_and_build_files_fail(self):
        for n in ('src/paint.cpp','CMakeLists.txt'):
            original=self.data[n]
            for kind in ('change','missing'):
                if kind=='change':self.data[n]=original+b' '
                else:self.data.pop(n)
                p=self.archive()
                with self.subTest(name=n,kind=kind),self.assertRaisesRegex(ValueError,'source'):
                    self.m.compare(p,self.m.file_record(p),'qt-src',self.spdx(),self.exceptions)
                self.data[n]=original
    def test_omissions_cannot_be_generalized_or_hide_source(self):
        for exceptions in ({},dict(self.exceptions,**{'src/paint.cpp':'omitted-vcs-control'}),dict(self.exceptions,**{'.gitattributes':'omitted-vcs-control'})):
            p=self.archive()
            with self.subTest(exceptions=exceptions),self.assertRaises(ValueError):self.m.compare(p,self.m.file_record(p),'qt-src',self.spdx(),exceptions)
    def test_duplicate_inventory_hashes_paths_and_source_members_rejected(self):
        p=self.archive()
        for bad in (self.spdx()+b'FileChecksum: SHA1: '+b'a'*40+b'\n',self.spdx()+b'FileName: ./src\\paint.cpp\nFileChecksum: SHA1: '+b'a'*40+b'\n',self.spdx().replace(b'./src\\paint.cpp',b'../escape')):
            with self.assertRaises(ValueError):self.m.compare(p,self.m.file_record(p),'qt-src',bad,self.exceptions)
        with tarfile.open(p,'w:gz') as archive:
            for _ in range(2):
                e=tarfile.TarInfo('qt-src/src/paint.cpp');e.size=2;archive.addfile(e,io.BytesIO(b'xx'))
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.m.compare(p,self.m.file_record(p),'qt-src',self.spdx(),self.exceptions)

if __name__=='__main__':unittest.main()
