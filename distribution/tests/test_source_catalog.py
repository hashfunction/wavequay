# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'distribution/msix'))
from files import file_record, inventory_tree
from source_archives import digest


class SourceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('source_catalog'), 'Source catalog verifier absent')
        import source_catalog
        self.m = source_catalog
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.base = self.root / 'distribution/corresponding-source'
        (self.base / 'notices').mkdir(parents=True)
        recipe = self.root / 'muse_deps/recipes/ogg'; recipe.mkdir(parents=True)
        (recipe / 'spec.cmake').write_text('original exact recipe\n')
        (self.root / 'LICENSE.txt').write_bytes(b'original application license\n')
        self.archives = {}; rows = []
        for name in ['ogg'] + list(self.m.EXTRA_SOURCE_OWNERS):
            data = (name + ' complete original license\n').encode()
            path = self.root / (name + '.tar.gz')
            with tarfile.open(path, 'w:gz') as archive:
                member = tarfile.TarInfo(name + '/LICENSE'); member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            self.archives[name + '/' + name] = path
            notice = dict(path='notices/' + name + '.txt', member=name + '/LICENSE', sourceMember=digest(data),
                          offset=0, length=len(data), notice=digest(data))
            (self.base / notice['path']).write_bytes(data)
            row = dict(component=name, subdir=name, filename=path.name, origin='https://example.org/' + path.name,
                       url='https://example.org/' + path.name, notices=[notice], **file_record(path))
            if name == 'ogg': row.update(recipe='muse_deps/recipes/ogg', recipeFiles=inventory_tree(recipe))
            rows.append(row)
        data = (self.root / 'LICENSE.txt').read_bytes()
        vendored = dict(path='notices/application.txt', member='LICENSE.txt', sourceMember=digest(data), offset=0,
                        length=len(data), notice=digest(data))
        (self.base / vendored['path']).write_bytes(data)
        self.catalog = dict(schemaVersion=1, archives=rows, repositoryNotices=[vendored])
        self.native = dict(components=[dict(name='ogg', recipe='muse_deps/recipes/ogg', recipeFiles=inventory_tree(recipe),
                           sources=[dict(subdir='ogg', url=rows[0]['origin'], sha256=rows[0]['sha256'])])])

    def save(self):
        (self.base / 'source-inputs.json').write_text(json.dumps(self.catalog))

    def test_exact_catalog_notices_current_recipes_and_actual_archives(self):
        self.save()
        result = self.m.verify_catalog(self.root, self.native)
        self.assertEqual(result['archiveCount'], 8)
        self.assertEqual(result['noticeCount'], 9)
        proof = self.m.verify_archives(self.root, self.archives, self.native)
        self.assertEqual(set(proof['archives']), set(self.archives))
        self.assertIs(proof['sourceLicenseClosure'], False)

    def test_missing_extra_changed_notice_and_repository_source_refused(self):
        self.save(); path = self.base / 'notices/ogg.txt'; original = path.read_bytes()
        for value in (None, b'altered terms'):
            if value is None: path.unlink()
            else: path.write_bytes(value)
            with self.subTest(value=value), self.assertRaises((ValueError, OSError)): self.m.verify_catalog(self.root, self.native)
            path.write_bytes(original)
        extra = self.base / 'notices/extra.txt'; extra.write_text('unindexed terms')
        with self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)
        extra.unlink(); (self.root / 'LICENSE.txt').write_bytes(b'changed application terms')
        with self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)

    def test_exact_consumed_owner_recipe_and_source_set_not_a_subset(self):
        original = copy.deepcopy(self.catalog)
        mutations = [lambda c: c['archives'].pop(0), lambda c: c['archives'].pop(),
                     lambda c: c['archives'][0].update(origin='https://example.org/foreign.tar.gz'),
                     lambda c: c['archives'][0].update(sha256='b'*64),
                     lambda c: c['archives'][0]['recipeFiles'].clear(),
                     lambda c: c['archives'].append(copy.deepcopy(c['archives'][0]))]
        for change in mutations:
            self.catalog = copy.deepcopy(original); change(self.catalog); self.save()
            with self.subTest(change=change), self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)
        self.catalog = original; self.save()
        (self.root / 'muse_deps/recipes/ogg/spec.cmake').write_text('modified current recipe')
        with self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)

    def test_bool_bounds_credentials_alias_and_missing_original_archive_refused(self):
        original = copy.deepcopy(self.catalog)
        mutations = [lambda c: c['archives'][0].update(bytes=True),
                     lambda c: c['archives'][0].update(url='https://user:secret@example.org/a'),
                     lambda c: c['archives'][0]['notices'][0].update(offset=True),
                     lambda c: c['archives'][1]['notices'][0].update(path='notices/OGG.txt'),
                     lambda c: c['repositoryNotices'][0].update(member='../LICENSE.txt')]
        for change in mutations:
            self.catalog = copy.deepcopy(original); change(self.catalog); self.save()
            with self.subTest(change=change), self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)
        self.catalog = original; self.save()
        missing = dict(self.archives); missing.pop('ogg/ogg')
        with self.assertRaises(ValueError): self.m.verify_archives(self.root, missing, self.native)
        self.archives['ogg/ogg'].write_bytes(b'foreign source archive')
        with self.assertRaises(ValueError): self.m.verify_archives(self.root, self.archives, self.native)

    def test_explicit_lossless_windows_checkout_comparison_preserves_original_notice_bytes(self):
        row = self.catalog['repositoryNotices'][0]
        row['allowWindowsCheckoutCRLF'] = True
        original = (self.root / row['member']).read_bytes()
        self.save(); (self.root / row['member']).write_bytes(original.replace(b'\n', b'\r\n'))
        observed = self.m.verify_catalog(self.root, self.native)
        self.assertEqual(observed['repositoryComparisons'][row['member']], 'LF-to-CRLF checkout')
        self.assertEqual((self.base / row['path']).read_bytes(), original)
        for change in (original.replace(b'\n', b'\r'), original.replace(b'license', b'license '),
                       original.replace(b'original', b'changed')):
            (self.root / row['member']).write_bytes(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)
        row['allowWindowsCheckoutCRLF'] = False; self.save()
        (self.root / row['member']).write_bytes(original.replace(b'\n', b'\r\n'))
        with self.assertRaises(ValueError): self.m.verify_catalog(self.root, self.native)


class CurrentSourceCatalogTests(unittest.TestCase):
    def test_catalog_covers_actual_windows_consumed_owners_and_current_cmake_source_pins(self):
        from source_catalog import verify_catalog
        # Actual consumed configuration from native run 34697625639. This is
        # dependency input replay, never an installed or consumer receipt.
        owners = ('expat flac freetype harfbuzz lame libpng libsndfile loop-tempo-estimator mpg123 nyquist '
                  'ogg opus opusfile pffft picojson portaudio pugixml rapidjson sbsms soundtouch soxr sqlite '
                  'tft twolame utfcpp vorbis vst3sdk wavpack wxwidgets yasm zlib').split()
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td).resolve(); script = directory / 'record.cmake'
            script.write_text('set(PROJECT_SOURCE_DIR "' + ROOT.as_posix() + '")\n'
                              'set(PROJECT_BINARY_DIR "' + directory.as_posix() + '")\n'
                              'set_property(GLOBAL PROPERTY EXTDEPS_CONSUMED ' + ' '.join(owners) + ')\n'
                              'foreach(dep ' + ' '.join(owners) + ')\n'
                              'set_property(GLOBAL PROPERTY ${dep}_PREFIX "' + directory.as_posix() + '/_deps/${dep}")\n'
                              'endforeach()\ninclude("' + (ROOT / 'distribution/RecordConsumedDependencies.cmake').as_posix() + '")\n'
                              'waveweft_record_consumed_dependencies()\n')
            process = subprocess.run(['cmake', '-P', str(script)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            from native_sources import sources_from_record
            configured = json.loads((directory / 'waveweft-consumed-dependencies.json').read_text())
            components = [dict(name=row['name'], recipe=row['recipe'], recipeFiles=inventory_tree(ROOT / row['recipe']),
                               sources=sources_from_record(row)) for row in configured['dependencies']]
            record = verify_catalog(ROOT, dict(components=components))
            self.assertEqual(record['archiveCount'], 40)
            self.assertEqual(len(record['consumedSources']), 33)
            self.assertEqual(record['noticeCount'], 532)
            self.assertIs(record['sourceLicenseClosure'], False)


if __name__ == '__main__': unittest.main()
