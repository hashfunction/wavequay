# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'distribution/msix'))

class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('source_archives'),'Preferred-source archive reader absent')
        import source_archives
        self.m=source_archives
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()

    def make_archive(self,form):
        path=self.root/('source.'+form)
        values={'src/LICENSE':b'original complete terms\n', 'src/sqlite.c':b'/* Public domain blessing. */\nint original_source;'}
        if form=='zip':
            with zipfile.ZipFile(path,'w') as archive:
                for name,data in values.items():archive.writestr(name,data)
        else:
            with tarfile.open(path,'w:gz') as archive:
                for name,data in values.items():
                    member=tarfile.TarInfo(name);member.size=len(data);archive.addfile(member,io.BytesIO(data))
        return path,values

    def test_complete_notice_and_explicit_original_header_from_tar_and_zip(self):
        for form in ('tar.gz','zip'):
            with self.subTest(form=form):
                path,values=self.make_archive(form)
                result=self.m.read_members(path,self.m.file_record(path),list(values))
                self.assertEqual(result,values)
                record=dict(member='src/sqlite.c',sourceMember=self.m.digest(values['src/sqlite.c']),offset=0,length=29,
                            notice=self.m.digest(values['src/sqlite.c'][:29]))
                self.assertEqual(self.m.notice_bytes(result,record),values['src/sqlite.c'][:29])

    def test_changed_archive_member_notice_and_truncated_bounds_refused(self):
        path,values=self.make_archive('zip');fixed=self.m.file_record(path)
        record=dict(member='src/LICENSE',sourceMember=self.m.digest(values['src/LICENSE']),offset=0,length=len(values['src/LICENSE']),notice=self.m.digest(values['src/LICENSE']))
        for change in ('archive','sourceMember','notice','length'):
            altered=dict(record)
            if change=='archive':
                with self.assertRaises(ValueError):self.m.read_members(path,dict(fixed,sha256='a'*64),list(values))
            else:
                altered[change]=len(values['src/LICENSE'])+1 if change=='length' else dict(bytes=1,sha256='a'*64)
                with self.subTest(change=change),self.assertRaises(ValueError):self.m.notice_bytes(values,altered)

    def test_missing_duplicate_and_symlink_selected_members_refused_without_extraction(self):
        path,values=self.make_archive('zip')
        with self.assertRaisesRegex(ValueError,'member'):self.m.read_members(path,self.m.file_record(path),['src/missing'])
        with zipfile.ZipFile(path,'a') as archive:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning);archive.writestr('src/LICENSE',b'other')
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.m.read_members(path,self.m.file_record(path),['src/LICENSE'])
        path=self.root/'link.tar.gz'
        with tarfile.open(path,'w:gz') as archive:
            entry=tarfile.TarInfo('src/LICENSE');entry.type=tarfile.SYMTYPE;entry.linkname='/etc/passwd';archive.addfile(entry)
        with self.assertRaisesRegex(ValueError,'regular'):self.m.read_members(path,self.m.file_record(path),['src/LICENSE'])
        self.assertFalse((self.root/'src').exists())

if __name__=='__main__':unittest.main()
