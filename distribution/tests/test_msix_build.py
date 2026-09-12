# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'distribution/msix'))


class MsixBuildTests(unittest.TestCase):
    def setUp(self):
        env=patch.dict('os.environ',dict(CI='true',GITHUB_SHA='a'*40,GITHUB_REPOSITORY='hashfunction/wavequay',
            GITHUB_RUN_ID='34700392536',GITHUB_RUN_ATTEMPT='2'))
        env.start();self.addCleanup(env.stop)

    def test_actual_build_boundary_records_both_modes_and_rejects_tool_mutation(self):
        self.assertIsNotNone(importlib.util.find_spec('build_package'), 'MSIX SDK orchestration is absent')
        import build_package as b
        for mode, mutate in [('qualification', False), ('store', False), ('store', True)]:
            with self.subTest(mode=mode, mutate=mutate), tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve(); release = root / 'release'; (release / 'bin').mkdir(parents=True)
                (release / 'bin/WaveWeft.exe').write_bytes(b'MZ fixture app')
                native = root / 'native.json'
                native.write_text(json.dumps(dict(schemaVersion=1, sourceCommit='a' * 40, runContext=b.current_run('a'*40), payload=b.inventory_tree(release),
                                                  sourceLicenseClosure=False, openItems=['fixture not native source proof'])))
                tool = root / 'Windows Kits/10/bin/10.0.26100.0/x64/makeappx.exe'
                tool.parent.mkdir(parents=True); tool.write_bytes(b'MZ SDK fixture')
                calls = []
                def sdk(command):
                    calls.append(command)
                    if command[1] == 'pack':
                        stage = Path(command[command.index('/d') + 1]); package = Path(command[command.index('/p') + 1])
                        with zipfile.ZipFile(package, 'w') as archive:
                            for file in stage.rglob('*'):
                                if file.is_file(): archive.write(file, file.relative_to(stage).as_posix())
                            archive.writestr('[Content_Types].xml', '<Types/>')
                            archive.writestr('AppxBlockMap.xml', '<BlockMap/>')
                        if mutate: tool.write_bytes(b'changed SDK')
                    else:
                        package = Path(command[command.index('/p') + 1]); target = Path(command[command.index('/d') + 1])
                        with zipfile.ZipFile(package) as archive: archive.extractall(target)
                if mutate:
                    with self.assertRaisesRegex(ValueError, 'MakeAppx changed'):
                        b.build_package(release, ROOT, native, 'a' * 40, tool, root / 'output', mode, runner=sdk)
                    self.assertEqual(len(calls), 1)
                    self.assertFalse((root / 'output').exists())
                else:
                    out = b.build_package(release, ROOT, native, 'a' * 40, tool, root / 'output', mode, runner=sdk)
                    record = json.loads((out / 'package-record.json').read_text())
                    self.assertEqual(record['identityMode'], mode)
                    for flag in ('signed', 'publicRelease', 'licenseClearanceClaimed', 'installationQualificationPassed'):
                        self.assertIs(record[flag], False)
                    self.assertEqual(len(calls), 2)
                    b.verify_record(out / b.package_name(mode), out / 'package-record.json', release, ROOT, native, 'a' * 40, mode)
                    changed=json.loads(json.dumps(record));changed['runContext']['runAttempt']=1
                    (out/'package-record.json').write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError,'source/run/attempt'):
                        b.verify_record(out/b.package_name(mode),out/'package-record.json',release,ROOT,native,'a'*40,mode)
                    for flag in ('storeIdentityUsed', 'qualificationIdentityOnly'):
                        changed = dict(record); changed[flag] = int(record[flag])
                        (out / 'package-record.json').write_text(json.dumps(changed))
                        with self.subTest(flag=flag), self.assertRaises(ValueError):
                            b.verify_record(out / b.package_name(mode), out / 'package-record.json', release, ROOT, native, 'a' * 40, mode)
                    (out / 'package-record.json').write_text(json.dumps(record))
                    (release / 'bin/WaveWeft.exe').write_bytes(b'changed current release')
                    with self.assertRaises(ValueError):
                        b.verify_record(out / b.package_name(mode), out / 'package-record.json', release, ROOT, native, 'a' * 40, mode)


if __name__ == '__main__': unittest.main()
