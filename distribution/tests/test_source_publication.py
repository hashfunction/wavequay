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
from files import file_record


class SourcePublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('source_publication'), 'Source publication verifier absent')
        import source_publication
        self.m = source_publication
        base = ROOT / 'distribution/corresponding-source'
        self.catalog = json.loads((base / 'source-inputs.json').read_text())
        self.manifest = json.loads((base / 'publication/source-release-manifest.json').read_text())
        self.readback = json.loads((base / 'publication/public-readback.json').read_text())
        self.assets = {'source-inputs.json': file_record(base / 'source-inputs.json')}
        for name in ['source-release-manifest.json', 'SOURCE-README.md']:
            self.assets[name] = file_record(base / 'publication' / name)

    def verify(self):
        return self.m.validate_documents(self.catalog, self.manifest, self.readback, self.assets)

    def test_original_publication_binds_every_archive_and_all_anonymous_readbacks(self):
        record = self.m.verify_publication(ROOT)
        self.assertEqual(record['archiveCount'], 40)
        self.assertEqual(record['archiveBytes'], 254427730)
        self.assertEqual(len(record['publicAssets']), 43)
        self.assertTrue(all(r['url'].startswith(self.m.ASSET_BASE) for r in record['archives']))
        self.assertIs(record['sourceLicenseClosure'], False)

    def test_partial_coherently_changed_archive_owner_url_or_hash_cannot_replace_current_catalog(self):
        original = copy.deepcopy(self.manifest)
        mutations = [lambda m: m['archives'].pop(), lambda m: m['archives'].append(copy.deepcopy(m['archives'][0])),
                     lambda m: m['archives'][0].update(component='foreign'),
                     lambda m: m['archives'][0].update(sha256='b'*64),
                     lambda m: m['archives'][0].update(origin='https://example.org/foreign'),
                     lambda m: m['archives'][0].update(previous_public_url='https://example.org/foreign'),
                     lambda m: m['archives'][0].update(url='https://github.com/foreign/source.tar.gz')]
        for change in mutations:
            self.manifest = copy.deepcopy(original); change(self.manifest)
            with self.subTest(change=change), self.assertRaises(ValueError): self.verify()

    def test_missing_duplicate_false_typed_or_credentialed_public_observations_fail_closed(self):
        original = copy.deepcopy(self.readback)
        mutations = [lambda r: r['verified_assets'].pop(),
                     lambda r: r['verified_assets'].append(copy.deepcopy(r['verified_assets'][0])),
                     lambda r: r.update(anonymous='true'), lambda r: r.update(credentials_sent=True),
                     lambda r: r.update(tls_certificate_verification=False), lambda r: r.update(all_public_assets_verified=False),
                     lambda r: r.update(archive_count=True), lambda r: r.update(public_assets_count=42),
                     lambda r: r.update(source_license_closure=True), lambda r: r.update(windows_qualification_claimed=True),
                     lambda r: r.update(tag_commit='b'*40),
                     lambda r: r['verified_assets'][0].update(sha256='b'*64),
                     lambda r: r['verified_assets'][0].update(url='https://example.org/foreign'),
                     lambda r: r['verified_assets'][0].update(redirect_host='example.org'),
                     lambda r: r['verified_assets'][0].update(verified_at_utc='not a timestamp')]
        for change in mutations:
            self.readback = copy.deepcopy(original); change(self.readback)
            with self.subTest(change=change), self.assertRaises(ValueError): self.verify()

    def test_current_original_records_are_pinned_before_document_interpretation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for changed in self.m.ORIGINALS:
                for name in self.m.ORIGINALS:
                    path = root / self.m.BASE / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((ROOT / self.m.BASE / name).read_bytes() + (b'\n' if name == changed else b''))
                with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'Original source publication record changed'):
                    self.m.verify_publication(root)


if __name__ == '__main__': unittest.main()
