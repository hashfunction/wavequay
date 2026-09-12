# SPDX-License-Identifier: GPL-3.0-only
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WindowsRuntimeRecordTests(unittest.TestCase):
    def test_observe_actual_cmake_runtime_selection_without_changing_it(self):
        helper = ROOT / 'distribution/RecordWindowsRuntimes.cmake'
        self.assertTrue(helper.is_file(), 'Configured Windows runtime recorder absent')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); script = root / 'record.cmake'
            libraries = ['C:/Program Files/VC/Redist/x64/msvcp140.dll', 'C:/Program Files/VC/Redist/x64/concrt140.dll']
            script.write_text('set(PROJECT_SOURCE_DIR "' + ROOT.as_posix() + '")\n'
                              'set(PROJECT_BINARY_DIR "' + root.as_posix() + '")\n'
                              'set(MSVC_REDIST_DIR "C:/Program Files/VC/Redist")\n'
                              'set(MSVC_CRT_DIR "C:/Program Files/VC/Redist/x64")\n'
                              'set(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS "' + ';'.join(libraries) + '")\n'
                              'set(CMAKE_INSTALL_DEBUG_LIBRARIES OFF)\n'
                              'include("' + helper.as_posix() + '")\n'
                              'waveweft_record_windows_runtimes()\n'
                              'if(NOT CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS STREQUAL "' + ';'.join(libraries) + '")\n'
                              'message(FATAL_ERROR "Runtime selection changed")\nendif()\n')
            env = dict(os.environ, WindowsSdkDir='C:\\Program Files (x86)\\Windows Kits\\10\\', WindowsSDKVersion='10.0.26100.0\\')
            process = subprocess.run(['cmake', '-P', str(script)], capture_output=True, text=True, env=env)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            record = json.loads((root / 'waveweft-windows-runtimes.json').read_text())
            self.assertEqual(record['libraries'], libraries)
            self.assertEqual(record['windowsSdkDir'], env['WindowsSdkDir'])
            self.assertEqual(record['msvcCrtDir'], 'C:/Program Files/VC/Redist/x64')
            self.assertIs(record['debugRuntimes'], False)
            script.write_text(script.read_text().replace('CMAKE_INSTALL_DEBUG_LIBRARIES OFF', 'CMAKE_INSTALL_DEBUG_LIBRARIES ON'))
            process = subprocess.run(['cmake', '-P', str(script)], capture_output=True, text=True, env=env)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertIs(json.loads((root / 'waveweft-windows-runtimes.json').read_text())['debugRuntimes'], True)


if __name__ == '__main__': unittest.main()
