"""Compile and replay the actual C# discovery method; not Windows GUI evidence."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WindowDiscoveryTests(unittest.TestCase):
    def test_owned_popup_under_uia_main_root_is_discovered_without_weakening_identity(self):
        dotnet = os.environ.get('WAVEQUAY_TEST_DOTNET') or shutil.which('dotnet')
        self.assertTrue(dotnet, 'A .NET SDK is required for the actual C# discovery replay')
        version = subprocess.check_output([dotnet, '--version'], text=True).strip()
        major = int(version.split('.')[0])
        self.assertGreaterEqual(major, 8)
        code = (ROOT / 'distribution/windows-gui/GuiProbe.cs').read_text(encoding='utf-8')
        start = code.index('private static List<AutomationElement> Windows(')
        brace = code.index('{', start)
        depth, end = 1, brace + 1
        while depth:
            depth += (code[end] == '{') - (code[end] == '}')
            end += 1
        method = code[start:end]
        replay = (ROOT / 'distribution/windows-gui/WindowDiscoveryReplay.cs').read_text(encoding='utf-8')
        self.assertEqual(replay.count('// ACTUAL_WINDOWS_METHOD'), 1)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'Replay.cs').write_text(replay.replace('// ACTUAL_WINDOWS_METHOD', method), encoding='utf-8')
            (project / 'Replay.csproj').write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
                f'<TargetFramework>net{major}.0</TargetFramework><Nullable>disable</Nullable>'
                '<LangVersion>5</LangVersion></PropertyGroup></Project>', encoding='utf-8')
            result = subprocess.run([dotnet, 'run', '--project', str(project / 'Replay.csproj'),
                                     '--verbosity', 'quiet'], capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS: actual discovery method', result.stdout)


if __name__ == '__main__': unittest.main()
