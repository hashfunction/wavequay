# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'distribution/msix'))


class ArchiveMemberTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('archive_members'), 'Original archive member verifier absent')
        import archive_members
        self.m=archive_members
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.cmake=Path(shutil.which('cmake')).resolve()

    def archive(self, form='7zip'):
        source=self.root/'source';(source/'bin').mkdir(parents=True)
        (source/'bin/FLAC.dll').write_bytes(b'MZ original native library')
        (source/'COPYING.Xiph').write_bytes(b'original source notice')
        archive=self.root/'native.archive'
        subprocess.run([str(self.cmake),'-E','tar','cf',str(archive),'--format='+form,'bin','COPYING.Xiph'],cwd=source,check=True)
        expected={n:self.m.file_record(source/n) for n in ('bin/FLAC.dll','COPYING.Xiph')}
        return archive,expected

    def test_real_cmake_original_7zip_and_zip_member_bytes(self):
        for form in ('7zip','zip'):
            with self.subTest(form=form):
                if (self.root/'source').exists():shutil.rmtree(self.root/'source')
                archive,expected=self.archive(form)
                result=self.m.verify_members(archive,self.m.file_record(archive),expected,self.cmake)
                self.assertEqual(result['members'],expected)
                self.assertEqual(result['archive'],self.m.file_record(archive))
                self.assertEqual(result['tool']['path'],str(self.cmake))

    def test_current_prefix_native_or_notice_substitution_rejected(self):
        archive,expected=self.archive()
        for member in expected:
            altered=dict(expected);altered[member]=dict(expected[member],sha256='0'*64)
            with self.subTest(member=member), self.assertRaisesRegex(ValueError,'member'):
                self.m.verify_members(archive,self.m.file_record(archive),altered,self.cmake)

    def test_unbound_archive_and_missing_exact_member_rejected(self):
        archive,expected=self.archive()
        with self.assertRaisesRegex(ValueError,'archive'):
            self.m.verify_members(archive,dict(bytes=1,sha256='a'*64),expected,self.cmake)
        expected['foreign/FLAC.dll']=expected['bin/FLAC.dll']
        with self.assertRaisesRegex(ValueError,'member'):
            self.m.verify_members(archive,self.m.file_record(archive),expected,self.cmake)

    def test_link_traversal_and_windows_alias_headers_refused(self):
        for names in (['bin/A.dll','bin/a.dll'],['../escape.dll'],['bin/link.dll']):
            archive=self.root/'hostile.tar'
            with tarfile.open(archive,'w') as out:
                for name in names:
                    item=tarfile.TarInfo(name);item.size=3
                    if name.endswith('link.dll'):item.type=tarfile.SYMTYPE;item.linkname='../foreign';item.size=0
                    out.addfile(item,io.BytesIO(b'bad') if item.isfile() else None)
            with self.subTest(names=names),self.assertRaises(ValueError):
                self.m.verify_members(archive,self.m.file_record(archive),{'bin/A.dll':dict(bytes=3,sha256='a'*64)},self.cmake)
        self.assertFalse((self.root.parent/'escape.dll').exists())

    def test_archive_replacement_during_real_tool_invocation_is_rejected(self):
        archive,expected=self.archive()
        original_run=subprocess.run
        def replace_after_observation(*args,**kwargs):
            result=original_run(*args,**kwargs)
            archive.write_bytes(b'replaced original')
            return result
        with patch.object(self.m.subprocess,'run',side_effect=replace_after_observation):
            with self.assertRaisesRegex(ValueError,'changed during observation'):
                self.m.verify_members(archive,self.m.file_record(archive),expected,self.cmake)


if __name__=='__main__':unittest.main()
