"""Instantiate real appshell-selected QML offscreen, without the audio engine."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class QmlModuleTests(unittest.TestCase):
    def checked(self, command):
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def probe(self, directory, *definitions):
        build = Path(directory)
        self.checked(['cmake', '-S', str(ROOT / 'distribution/qml-module-tests'),
                      '-B', str(build), *definitions])
        self.checked(['cmake', '--build', str(build), '--config', 'Release', '--parallel', '2'])
        candidates = [build / 'qml_module_probe', build / 'Release/qml_module_probe.exe',
                      build / 'qml_module_probe.exe']
        executable = next(path for path in candidates if path.is_file())
        selected = Path((build / 'selected-view.txt').read_text().strip())
        return executable, hashlib.sha256(selected.read_bytes()).hexdigest()

    def test_offline_view_loads_without_unavailable_extension_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            executable, selected_hash = self.probe(directory, '-DAU_TRIEFLOW_DISTRIBUTION=ON')
            result = self.checked([str(executable)])
            self.assertIn(f'Selected QML SHA256 {selected_hash}', result.stderr)
            self.assertIn('Production ExtensionsListView QML instantiated', result.stderr)
            self.assertNotIn('ReferenceError', result.stderr)

    def test_upstream_view_retains_its_extension_model_requirement(self):
        with tempfile.TemporaryDirectory() as directory:
            executable, selected_hash = self.probe(directory, '-DAU_TRIEFLOW_DISTRIBUTION=OFF',
                                                   '-DMUSE_MODULE_EXTENSIONS=ON')
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn(f'Selected QML SHA256 {selected_hash}', result.stderr)
            self.assertIn('DevExtensionsListModel is not a type', result.stderr)
            enabled = self.checked([str(executable), '--enabled-model'])
            self.assertIn(f'Selected QML SHA256 {selected_hash}', enabled.stderr)
            self.assertIn('Production ExtensionsListView QML instantiated', enabled.stderr)
            self.assertNotIn('ReferenceError', enabled.stderr)


if __name__ == '__main__':
    unittest.main()
