"""Exercise the real onboarding model/QML and Muse accessibility/navigation providers."""
from pathlib import Path
import os
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
        cls.font = build / "fonts/FreeSerif.ttf"

    def run_probe(self, *arguments):
        environment = os.environ.copy()
        # Windows Qt otherwise chooses OutputDebugString when CI has no console.
        environment["QT_FORCE_STDERR_LOGGING"] = "1"
        try:
            result = subprocess.run([str(self.executable), *arguments],
                                    capture_output=True, text=True, timeout=30,
                                    env=environment)
        except subprocess.TimeoutExpired as error:
            def output_text(value):
                return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
            self.fail('Onboarding runtime exceeded 30 seconds. Captured diagnostics:\n'
                      + output_text(error.stdout) + output_text(error.stderr))
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Onboarding accessibility runtime passed", output)
        # Exercise redirected output before and after Muse takes over Qt logging.
        # These checkpoints must survive the same pipes used on timeout in CI.
        for checkpoint in (
            "Onboarding probe: constructing QGuiApplication",
            "Onboarding probe: application constructed",
            "Onboarding probe: fixture font registered FreeSerif",
            "Onboarding probe: QML engine constructed",
            "Onboarding probe: navigation initialized",
            "Onboarding probe: dialog component created",
            "Onboarding probe: offscreen views shown",
            "Onboarding probe: popup interface queried",
            "Onboarding probe: dialog destroyed",
            "Onboarding accessibility runtime passed",
        ):
            self.assertIn(checkpoint, result.stderr, output)
        self.assertNotIn("TypeError", output)
        self.assertNotIn("ReferenceError", output)
        self.assertNotIn("Cannot find font directory", output)

    def test_missing_or_invalid_fixture_font_fails_before_qml(self):
        original = self.font.read_bytes()
        try:
            for contents in (None, b"invalid font fixture"):
                with self.subTest(missing=contents is None):
                    if contents is None:
                        self.font.unlink()
                    else:
                        self.font.write_bytes(contents)
                    with self.assertRaisesRegex(AssertionError, "fixture font must register") as error:
                        self.run_probe()
                    self.assertNotIn("QML engine constructed", str(error.exception))
                    self.assertNotIn("exceeded 30 seconds", str(error.exception))
        finally:
            self.font.write_bytes(original)

    def test_dialog_provider_and_actions_when_qt_factory_is_last(self):
        self.run_probe()

    def test_dialog_provider_and_actions_when_muse_factory_is_last(self):
        self.run_probe("--muse-factory-last")


if __name__ == "__main__":
    unittest.main()
