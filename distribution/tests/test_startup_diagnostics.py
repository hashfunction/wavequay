"""Compile and run the real native logger/diagnostic sink, with Qt Core and without GUI."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class StartupDiagnosticTests(unittest.TestCase):
    def checked(self, command):
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_actual_logger_opt_in_and_redirected_native_stderr(self):
        with tempfile.TemporaryDirectory() as temporary:
            build = Path(temporary)
            self.checked(['cmake', '-S', str(ROOT / 'distribution/startup-diagnostics-tests'),
                            '-B', str(build)])
            self.checked(['cmake', '--build', str(build), '--config', 'Release', '--parallel', '2'])
            paths = [build / 'startup_diagnostics_tests', build / 'Release/startup_diagnostics_tests.exe',
                     build / 'startup_diagnostics_tests.exe']
            executable = next(path for path in paths if path.is_file())
            result = subprocess.run([str(executable), str(build / 'original-application.log')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable), '--real-pipe'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertIn('configured/native/logs', result.stderr)
            self.assertIn('Actual logger QML failure fixture', result.stderr)


if __name__ == '__main__': unittest.main()
