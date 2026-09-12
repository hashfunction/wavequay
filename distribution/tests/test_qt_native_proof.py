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
from files import file_record, inventory_tree


class QtNativeProofTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('qt_native_proof'), 'Original Qt native proof collector absent')
        import qt_native_proof
        self.m = qt_native_proof
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.qt = self.root / 'qt'; self.cache = self.root / '.qt-archives'
        (self.qt / 'sbom').mkdir(parents=True); self.cache.mkdir()
        self.payload = {}; self.inputs = dict(schemaVersion=1, modules=[])
        for index, name in enumerate(self.m.MODULES):
            member = ('plugins/platforms/' if index == 0 else 'qml/Module/' if index == 1 else 'bin/') + name + '.dll'
            staged = self.m.staged_path(member)
            content = b'MZ original ' + name.encode()
            binary = self.root / (name + '.dll'); binary.write_bytes(content); self.payload[staged] = file_record(binary)
            metadata = 'sbom/' + name + '-6.11.2.spdx.json'
            document = dict(spdxVersion='SPDX-2.3', files=[dict(fileName='./' + member)])
            (self.qt / metadata).write_text(json.dumps(document))
            source_metadata = 'sbom/' + name + '-6.11.2.source.spdx'
            (self.qt / source_metadata).write_text('SPDXVersion: SPDX-2.1\noriginal source inventory\n')
            original = {path: file_record(self.qt / path) for path in (metadata, source_metadata)}
            archive = self.cache / (name + '.7z')
            # Real CMake LibArchive reads this ZIP fixture by signature.
            with zipfile.ZipFile(archive, 'w') as target:
                target.writestr(member, content)
                for path in original: target.write(self.qt / path, path)
            self.inputs['modules'].append(dict(name=name, version='6.11.2',
                binaryArchive=dict(filename=archive.name, **file_record(archive)), originalMetadata=original))
        self.cmake = Path(shutil.which('cmake')).resolve()

    def prove(self):
        return self.m.verify_modules(self.inputs, self.cache, self.qt, self.payload, self.cmake)

    def test_actual_archive_proof_preserves_exact_plugin_qml_and_dll_owners(self):
        result = self.prove()
        self.assertEqual(set(result['nativeFiles']), set(self.payload))
        self.assertEqual(len(result['modules']), 5)
        self.assertEqual(result['nativeFiles']['bin/platforms/qtbase.dll']['member'], 'plugins/platforms/qtbase.dll')
        self.assertIs(result['sourceLicenseClosure'], False)

    def test_current_sdk_metadata_original_archive_and_payload_substitution_refused(self):
        first = self.inputs['modules'][0]; path = self.qt / next(iter(first['originalMetadata']))
        data = path.read_bytes(); path.write_bytes(data + b' ')
        with self.assertRaises(ValueError): self.prove()
        path.write_bytes(data)
        archive = self.cache / first['binaryArchive']['filename']; data = archive.read_bytes(); archive.write_bytes(data + b'changed')
        with self.assertRaises(ValueError): self.prove()
        archive.write_bytes(data)
        self.payload['bin/platforms/qtbase.dll']['sha256'] = 'b' * 64
        with self.assertRaises(ValueError): self.prove()

    def test_exact_module_set_duplicate_native_ownership_and_unsafe_spdx_paths_refused(self):
        original = copy.deepcopy(self.inputs)
        self.inputs['modules'].pop()
        with self.assertRaises(ValueError): self.prove()
        self.inputs = copy.deepcopy(original); self.inputs['modules'].append(copy.deepcopy(self.inputs['modules'][0]))
        with self.assertRaises(ValueError): self.prove()
        for names in (['./bin/a.dll', './bin/a.dll'], ['./bin/A.dll', './bin/a.dll'], ['../foreign.dll'], ['C:/foreign.dll']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                self.m.native_members(dict(spdxVersion='SPDX-2.3', files=[dict(fileName=n) for n in names]))
        self.inputs = original
        # A coherent altered metadata/archive still cannot assign one shipped
        # native path to two module owners.
        first, second = self.inputs['modules'][:2]
        metadata = 'sbom/' + second['name'] + '-6.11.2.spdx.json'
        (self.qt / metadata).write_text(json.dumps(dict(spdxVersion='SPDX-2.3', files=[dict(fileName='./plugins/platforms/qtbase.dll')])))
        second['originalMetadata'][metadata] = file_record(self.qt / metadata)
        with self.assertRaisesRegex(ValueError, 'owner'): self.prove()

    def test_unshipped_spdx_members_are_not_adopted_and_empty_module_fails(self):
        self.payload['bin/foreign.dll'] = dict(bytes=12, sha256='a'*64)
        self.assertNotIn('bin/foreign.dll', self.prove()['nativeFiles'])
        self.payload.pop('bin/platforms/qtbase.dll')
        with self.assertRaisesRegex(ValueError, 'shipped'): self.prove()

    def test_production_collector_retains_only_exact_original_metadata_once(self):
        path = self.root / self.m.INPUTS; path.parent.mkdir(parents=True); path.write_text(json.dumps(self.inputs))
        output = self.root / 'evidence/native-source/qt'
        result = self.m.collect_and_retain(self.root, self.qt, self.payload, self.cmake, output)
        expected = {name: info for row in self.inputs['modules'] for name, info in row['originalMetadata'].items()}
        self.assertEqual(inventory_tree(output), expected)
        self.assertEqual(result['fixedInputs'], file_record(path))
        with self.assertRaisesRegex(ValueError, 'absent'):
            self.m.collect_and_retain(self.root, self.qt, self.payload, self.cmake, output)
        self.assertTrue(all(not name.endswith(('.dll', '.exe')) for name in inventory_tree(output)))


if __name__ == '__main__': unittest.main()
