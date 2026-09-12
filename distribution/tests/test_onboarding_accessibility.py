"""Exercise the real onboarding model/QML and Muse accessibility/navigation providers."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class OnboardingAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="wavequay-onboarding-")
        cls.addClassCleanup(cls.directory.cleanup)
        build = Path(cls.directory.name)
        for command in (
            ["cmake", "-S", str(ROOT / "distribution/onboarding-accessibility-tests"),
             "-B", str(build), "-DCMAKE_BUILD_TYPE=Release"],
            ["cmake", "--build", str(build), "--config", "Release", "--parallel", "2"],
        ):
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
        cls.executable = next(path for path in (
            build / "onboarding_accessibility_probe",
            build / "Release/onboarding_accessibility_probe.exe",
            build / "onboarding_accessibility_probe.exe",
        ) if path.is_file())

    def run_probe(self, *arguments):
        try:
            result = subprocess.run([str(self.executable), *arguments],
                                    capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as error:
            def output_text(value):
                return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
            self.fail('Onboarding runtime exceeded 30 seconds. Captured diagnostics:\n'
                      + output_text(error.stdout) + output_text(error.stderr))
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Onboarding accessibility runtime passed", output)
        self.assertNotIn("TypeError", output)
        self.assertNotIn("ReferenceError", output)

    def test_dialog_provider_and_actions_when_qt_factory_is_last(self):
        self.run_probe()

    def test_dialog_provider_and_actions_when_muse_factory_is_last(self):
        self.run_probe("--muse-factory-last")


if __name__ == "__main__":
    unittest.main()
