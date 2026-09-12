# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'distribution/msix'))
from source_archives import digest


class SourceMaterialTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('source_material'),'Exact generated package notices absent')
        import source_material
        self.m=source_material

    def test_real_original_notice_bytes_and_current_source_locations_are_generated(self):
        files=self.m.generate(ROOT,'a'*40)
        document=json.loads(files['SOURCE-INFO.json'])
        self.assertEqual(document['application']['commit'],'a'*40)
        self.assertEqual(document['application']['archiveUrl'],'https://github.com/hashfunction/wavequay/archive/'+'a'*40+'.tar.gz')
        self.assertEqual(len(document['preferredSources']),40)
        self.assertEqual(len(document['notices']),532)
        self.assertEqual(len(document['microsoftDocuments']),5)
        self.assertEqual(len(files),539)
        for name,expected in document['notices'].items():self.assertEqual(digest(files['Notices/'+name]),expected)
        self.assertTrue(all(row['url'].startswith('https://github.com/hashfunction/wavequay/releases/download/') for row in document['preferredSources']))
        changed=self.m.generate(ROOT,'b'*40)
        self.assertNotEqual(changed['SOURCE-INFO.json'],files['SOURCE-INFO.json'])
        self.assertEqual(changed['Notices/Repository/application/0001-LICENSE.txt'],files['Notices/Repository/application/0001-LICENSE.txt'])

    def test_missing_mutated_or_untracked_notice_bytes_refuse_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();base=root/'distribution/corresponding-source'
            shutil.copytree(ROOT/'distribution/corresponding-source',base)
            notice=next((base/'notices').rglob('*.txt'));data=notice.read_bytes();notice.write_bytes(data+b'changed')
            with self.assertRaises(ValueError):self.m.generate(root,'a'*40)
            notice.write_bytes(data);(base/'notices/foreign.txt').write_text('untracked')
            with self.assertRaises(ValueError):self.m.generate(root,'a'*40)

    def test_invalid_source_reference_is_not_rendered_as_a_source_offer(self):
        for commit in ('','main','a'*39,'A'*40):
            with self.subTest(commit=commit),self.assertRaises(ValueError):self.m.generate(ROOT,commit)


if __name__=='__main__':unittest.main()
