# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

HELPERS = Path(__file__).resolve().parents[1] / 'msix'
sys.path.insert(0, str(HELPERS))


class PackageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.find_spec('package')
        if spec is None:
            raise AssertionError('WaveWeft MSIX packaging contract is not implemented')
        import package
        cls.p = package

    def test_exact_fixed_store_identity_and_disposable_default(self):
        store = self.p.identity_for_mode('store')
        self.assertEqual(store['packageName'], '1659hashfunction.WaveQuay')
        self.assertEqual(store['publisher'], 'CN=B6A2631A-FD32-45CC-AE12-82466975F528')
        self.assertEqual(store['familyName'], '1659hashfunction.WaveQuay_r3hxytd7jt6c4')
        self.assertEqual(store['applicationId'], 'WaveQuay')
        self.assertEqual(store['executable'], 'bin/WaveWeft.exe')
        self.assertEqual(store['version'], '1.0.1.0')
        self.assertNotEqual(self.p.identity_for_mode()['packageName'], store['packageName'])
        for bad in ('', 'STORE', '1659hashfunction.WaveQuay', None):
            with self.subTest(mode=bad), self.assertRaises(ValueError):
                self.p.identity_for_mode(bad)

    def test_manifest_exact_modes_and_mutations(self):
        for mode in ('qualification', 'store'):
            raw = self.p.create_manifest(mode)
            self.assertEqual(self.p.validate_manifest(raw, mode), self.p.identity_for_mode(mode))
            with self.assertRaises(ValueError):
                self.p.validate_manifest(raw, 'store' if mode == 'qualification' else 'qualification')
            for old, new in ((b'1.0.1.0', b'1.0.2.0'), (b'WaveWeft.exe', b'WaveQuay.exe'),
                             (b'Id="WaveQuay"', b'Id="WaveWeft"'), (b'runFullTrust', b'broadFileSystemAccess'),
                             (b'Windows.Desktop', b'Windows.Universal')):
                self.assertIn(old, raw)
                with self.subTest(mode=mode, mutation=old), self.assertRaises(ValueError):
                    self.p.validate_manifest(raw.replace(old, new), mode)
            tree = ET.fromstring(raw)
            tree.append(copy.deepcopy(tree[0]))
            with self.assertRaises(ValueError):
                self.p.validate_manifest(ET.tostring(tree), mode)

    def inputs(self, root):
        release = root / 'release'
        (release / 'bin').mkdir(parents=True)
        (release / 'bin/WaveWeft.exe').write_bytes(b'MZ fixture application')
        (release / 'bin/Qt6Core.dll').write_bytes(b'MZ fixture Qt')
        (release / 'licenses').mkdir()
        (release / 'licenses/COPYING.txt').write_bytes(b'fixture original license')
        return release

    def test_regenerated_payload_rejects_coherent_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); release = self.inputs(root)
            expected = self.p.expected_payload(release, 'store')
            self.assertEqual(expected['bin/WaveWeft.exe'], self.p.file_record(release / 'bin/WaveWeft.exe'))
            staged = root / 'package'
            self.p.stage_payload(release, staged, 'store')
            self.assertEqual(self.p.inventory_tree(staged), expected)
            self.p.verify_unpacked(staged, expected, 'store')
            (staged / 'bin/WaveWeft.exe').write_bytes(b'MZ coherent replacement')
            with self.assertRaises(ValueError):
                self.p.verify_unpacked(staged, self.p.expected_payload(release, 'store'), 'store')

    def test_signed_inputs_aliases_and_links_rejected(self):
        for filename in ('secret.pfx', 'secret.PEM', 'AppxSignature.p7x', 'private.key', 'code.cer'):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve(); release = self.inputs(root)
                (release / filename).write_bytes(b'signing material')
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    self.p.expected_payload(release)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); release = self.inputs(root)
            (release / 'bin/foreign.dll').symlink_to(release / 'bin/Qt6Core.dll')
            with self.assertRaises(ValueError):
                self.p.expected_payload(release)

    def test_container_missing_extra_signature_and_case_alias_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); release = self.inputs(root); stage = root / 'package'
            self.p.stage_payload(release, stage, 'store')
            expected = self.p.expected_payload(release, 'store')
            names = list(expected)
            for extra in ('foreign.dll', 'AppxSignature.p7x', 'BIN/WaveWeft.exe', '../escape'):
                msix = root / 'fixture.msix'
                with zipfile.ZipFile(msix, 'w') as archive:
                    for name in names: archive.write(stage / name, name)
                    archive.writestr('[Content_Types].xml', '<Types/>')
                    archive.writestr('AppxBlockMap.xml', '<BlockMap/>')
                    archive.writestr(extra, b'extra')
                with self.subTest(extra=extra), self.assertRaises(ValueError):
                    self.p.verify_msix(msix, expected, 'store')

    def test_destination_redirect_refused_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); release = self.inputs(root)
            (root / 'outside').mkdir(); (root / 'redirect').symlink_to(root / 'outside', target_is_directory=True)
            with self.assertRaises(ValueError):
                self.p.stage_payload(release, root / 'redirect/package')
            self.assertEqual(list((root / 'outside').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
