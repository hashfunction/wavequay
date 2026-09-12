# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'distribution/msix'))
from files import file_record


class PlatformNativeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('platform_native_proof'), 'Original Mesa archive collector absent')
        import platform_native_proof
        self.m = platform_native_proof
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.cache = self.root / '.qt-archives'; self.cache.mkdir()
        self.leaf = self.root / 'opengl32sw.dll'; self.leaf.write_bytes(b'MZ original Mesa fixture')
        self.payload = {'bin/opengl32sw.dll': file_record(self.leaf), 'bin/foreign.dll': file_record(self.leaf)}
        self.archive = self.cache / self.m.FILENAME
        with zipfile.ZipFile(self.archive, 'w') as archive: archive.write(self.leaf, 'opengl32sw.dll')
        self.inputs = dict(schemaVersion=1, owner='Mesa', version='11.2.2', compilerSource='LLVM/LLVM',
                           binaryArchive=dict(filename=self.m.FILENAME, url=self.m.URL, **file_record(self.archive)),
                           nativeFile=dict(path='bin/opengl32sw.dll', member='opengl32sw.dll', **file_record(self.leaf)))
        self.cmake = Path(shutil.which('cmake')).resolve()

    def verify(self): return self.m.verify(self.inputs, self.cache, self.payload, self.cmake)

    def test_original_native_archive_member_is_the_only_adopted_owner(self):
        record = self.verify()
        self.assertEqual(set(record['nativeFiles']), {'bin/opengl32sw.dll'})
        self.assertEqual(record['nativeFiles']['bin/opengl32sw.dll']['owner'], 'Mesa')
        self.assertEqual(record['archiveMembership']['members']['opengl32sw.dll'], file_record(self.leaf))
        self.assertIs(record['sourceLicenseClosure'], False)

    def test_changed_missing_payload_original_archive_or_owner_fail(self):
        original = copy.deepcopy(self.inputs)
        for mutate in (lambda x: x.update(owner='foreign'), lambda x: x.update(version='current'),
                       lambda x: x.update(compilerSource='LLVM/new'),
                       lambda x: x['binaryArchive'].update(url='https://example.org/foreign.7z'),
                       lambda x: x['binaryArchive'].update(filename='../foreign.7z'),
                       lambda x: x['nativeFile'].update(path='bin/foreign.dll'),
                       lambda x: x['nativeFile'].update(member='foreign.dll'),
                       lambda x: x['nativeFile'].update(sha256='b'*64)):
            self.inputs = copy.deepcopy(original); mutate(self.inputs)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.verify()
        self.inputs = original
        self.payload.pop('bin/opengl32sw.dll')
        with self.assertRaises(ValueError): self.verify()
        self.payload['bin/opengl32sw.dll'] = file_record(self.leaf)
        self.archive.write_bytes(self.archive.read_bytes() + b'changed')
        with self.assertRaises(ValueError): self.verify()

    def test_production_collector_binds_exact_current_fixed_input(self):
        path = self.root / self.m.INPUTS; path.parent.mkdir(parents=True); path.write_text(json.dumps(self.inputs))
        record = self.m.collect(self.root, self.payload, self.cmake)
        self.assertEqual(record['fixedInputs'], file_record(path))


if __name__ == '__main__': unittest.main()
