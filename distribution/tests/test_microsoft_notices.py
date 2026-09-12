# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'distribution/msix'))


class MicrosoftNoticeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('microsoft_notices'), 'Original Microsoft terms verifier absent')
        import microsoft_notices
        self.m=microsoft_notices
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.base=self.root/'distribution/corresponding-source';self.base.mkdir(parents=True)
        shutil.copytree(ROOT/'distribution/corresponding-source/microsoft-notices', self.base/'microsoft-notices')
        shutil.copyfile(ROOT/self.m.INPUTS,self.root/self.m.INPUTS)

    def test_original_terms_exact_five_files_cover_only_nine_microsoft_components(self):
        record=self.m.verify(ROOT)
        self.assertEqual(len(record['documents']),5)
        self.assertEqual(sum(x['bytes'] for x in record['documents'].values()),176604)
        self.assertEqual(len(record['nativeFiles']),9)
        self.assertIs(record['sourceLicenseClosure'],False)

    def test_modified_missing_extra_or_renamed_terms_fail_closed(self):
        name=next(iter(self.m.DOCUMENTS)); path=self.base/'microsoft-notices'/name; data=path.read_bytes()
        for mutation in ('changed','missing','foreign'):
            if mutation=='changed': path.write_bytes(data+b'changed')
            elif mutation=='missing': path.unlink()
            else: path.write_bytes(data); (path.parent/'foreign.txt').write_text('untracked')
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,FileNotFoundError)):
                self.m.verify(self.root)
            if not path.exists(): path.write_bytes(data)

    def test_coherent_file_hash_owner_or_delivery_substitution_cannot_relicense_payload(self):
        original=(self.root/self.m.INPUTS).read_text()
        for mutation in (lambda x:x['owners']['Microsoft.WindowsSDK.D3D']['files'].append('bin/WaveWeft.exe'),
                         lambda x:x['owners']['Microsoft.VC143.CRT']['documents'].pop(),
                         lambda x:x['documents'][next(iter(x['documents']))].update(sha256='a'*64),
                         lambda x:x['documents'][next(iter(x['documents']))].update(url='https://example.org/foreign'),
                         lambda x:x.update(schemaVersion=True)):
            document=json.loads(original);mutation(document);(self.root/self.m.INPUTS).write_text(json.dumps(document))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.m.verify(self.root)

    def test_hashed_originals_explicitly_disable_git_checkout_text_conversion(self):
        paths=['distribution/corresponding-source/source-inputs.json',
               'distribution/corresponding-source/publication/public-readback.json',
               'distribution/corresponding-source/microsoft-notices/Windows-SDK-license.md']
        output=subprocess.check_output(['git','-C',str(ROOT),'check-attr','text','--',*paths],text=True)
        self.assertEqual(output.splitlines(),[path+': text: unset' for path in paths])


if __name__=='__main__':unittest.main()
