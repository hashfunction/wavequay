# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'distribution/msix'))


class NativeSourceTests(unittest.TestCase):
    def load(self):
        self.assertIsNotNone(importlib.util.find_spec('native_sources'), 'Native source collector is not implemented')
        import native_sources
        return native_sources

    def test_record_actual_consumed_recipe_and_owned_portaudio_override(self):
        helper = ROOT / 'distribution/RecordConsumedDependencies.cmake'
        self.assertTrue(helper.is_file(), 'Configure-time consumed recipe record is absent')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td).resolve()
            script = path / 'record.cmake'
            script.write_text(f'''set(PROJECT_SOURCE_DIR "{ROOT.as_posix()}")
set(PROJECT_BINARY_DIR "{path.as_posix()}")
set_property(GLOBAL PROPERTY EXTDEPS_CONSUMED flac rapidjson portaudio flac)
foreach(dep flac rapidjson portaudio)
  set_property(GLOBAL PROPERTY ${{dep}}_PREFIX "{path.as_posix()}/_deps/${{dep}}")
endforeach()
include("{helper.as_posix()}")
waveweft_record_consumed_dependencies()
''')
            run = subprocess.run(['cmake', '-P', str(script)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            record = json.loads((path / 'waveweft-consumed-dependencies.json').read_text())
            self.assertEqual([r['name'] for r in record['dependencies']], ['flac', 'portaudio', 'rapidjson'])
            port = record['dependencies'][1]
            self.assertEqual(port['recipe'], 'distribution/recipes/portaudio')
            self.assertEqual(port['version'], '19.7.0')
            self.assertIn('5af29ba58bbdbb7bbcefaaecc77ec8fc413f0db6f4c4e286c40c3e1b83174fa0', str(port))
            self.assertIn('2d2601a82d2d3b7e143a3c8d43ef616671391034bc46891a9816b79cf2d3e7a8', str(record))
            self.assertNotIn('asiosdk', str(record))

    def test_actual_archive_lock_requires_current_recipe_signature(self):
        n = self.load()
        row = n.prebuilt_record(ROOT, 'flac', ROOT / 'muse_deps/recipes/flac')
        self.assertEqual(row['filename'], 'flac-1.4.3-windows-x86_64-0b2bfbb431a5.7z')
        self.assertEqual(row['sha256'], 'd55b6d1221f163b67cfb0ec94d80f29bc6f9124e93a4ee6c440d77a8a89d2c45')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td).resolve(); (path / 'spec.cmake').write_text('changed recipe')
            with self.assertRaisesRegex(ValueError, 'recipe'):
                n.prebuilt_record(ROOT, 'flac', path)

    def test_payload_member_ownership_hash_and_ambiguity(self):
        n = self.load()
        payload = {'bin/Qt6Core.dll': {'bytes': 4, 'sha256': 'a' * 64}}
        owners = {'qt': {'bin/Qt6Core.dll': payload['bin/Qt6Core.dll']}}
        matched, unknown = n.match_native_payload(payload, owners)
        self.assertEqual(matched['bin/Qt6Core.dll'], [{'owner': 'qt', 'member': 'bin/Qt6Core.dll'}])
        self.assertEqual(unknown, [])
        owners['qt']['bin/Qt6Core.dll'] = {'bytes': 4, 'sha256': 'b' * 64}
        self.assertEqual(n.match_native_payload(payload, owners)[1], ['bin/Qt6Core.dll'])
        owners['qt']['foreign/same.dll'] = payload['bin/Qt6Core.dll']
        self.assertEqual(n.match_native_payload(payload, owners)[1], ['bin/Qt6Core.dll'])

    def test_notice_rows_require_actual_current_source_bytes(self):
        n = self.load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); (root / 'COPYING').write_text('original license')
            record = n.original_notices(root, ['COPYING'])
            self.assertEqual(record['COPYING']['bytes'], 16)
            with self.assertRaises(ValueError):
                n.original_notices(root, ['../outside'])
            (root / 'redirect').symlink_to(root / 'COPYING')
            with self.assertRaises(ValueError):
                n.original_notices(root, ['redirect'])

    def test_collector_preserves_unresolved_source_state_and_exact_payload(self):
        n = self.load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); build = root / 'build'; stage = root / 'stage'; qt = root / 'qt'
            prefix = build / '_deps/flac'
            for folder in (prefix / 'bin', prefix / 'licenses', stage / 'bin', qt / 'bin', qt / 'sbom'):
                folder.mkdir(parents=True)
            shutil.copytree(ROOT / 'muse_deps/recipes/flac', root / 'muse_deps/recipes/flac')
            (prefix / 'bin/FLAC.dll').write_bytes(b'MZ flac')
            (prefix / 'licenses/COPYING.Xiph').write_bytes(b'original')
            (qt / 'bin/Qt6Core.dll').write_bytes(b'MZ qt')
            (qt / 'sbom/qtbase.spdx').write_bytes(b'original Qt metadata')
            for name, source in [('FLAC.dll', prefix / 'bin/FLAC.dll'), ('Qt6Core.dll', qt / 'bin/Qt6Core.dll')]:
                shutil.copyfile(source, stage / 'bin' / name)
            (stage / 'bin/WaveWeft.exe').write_bytes(b'MZ app')
            (stage / 'bin/foreign.dll').write_bytes(b'MZ foreign')
            row = dict(name='flac', version='1.4.3', recipe='muse_deps/recipes/flac', prefix=str(prefix),
                       source_root='', runtime=[str(prefix / 'bin/FLAC.dll')],
                       sources=['flac|tarball|https://github.com/xiph/flac/releases/download/1.4.3/flac-1.4.3.tar.xz|6c58e69cd22348f441b861092b825e591d0b822e106de6eb0ee4d05d27205b70'])
            config = build / 'waveweft-consumed-dependencies.json'
            config.write_text(json.dumps(dict(schemaVersion=1, dependencies=[row])))
            report = n.collect(root, build, stage, qt, 'a' * 40)
            self.assertFalse(report['sourceLicenseClosure'])
            self.assertEqual(report['unresolvedNative'], ['bin/foreign.dll'])
            self.assertEqual(report['nativeMatches']['bin/FLAC.dll'], [{'owner': 'flac', 'member': 'bin/FLAC.dll'}])
            self.assertEqual(report['payload']['bin/FLAC.dll'], n.file_record(prefix / 'bin/FLAC.dll'))
            self.assertEqual(report['qtOriginalMetadata'], {'sbom/qtbase.spdx': n.file_record(qt / 'sbom/qtbase.spdx')})
            row['prefix'] = str(root / 'foreign')
            config.write_text(json.dumps(dict(schemaVersion=1, dependencies=[row])))
            with self.assertRaisesRegex(ValueError, 'prefix'):
                n.collect(root, build, stage, qt, 'a' * 40)


if __name__ == '__main__':
    unittest.main()
