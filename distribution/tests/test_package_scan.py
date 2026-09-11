import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

class PackageScanTests(unittest.TestCase):
    def scan(self, content):
        with tempfile.TemporaryDirectory() as directory:
            pathlib.Path(directory,"sample.dll").write_bytes(content)
            return subprocess.run(["python3",str(ROOT/"distribution/scan-package.py"),directory],capture_output=True,text=True)
    def test_rejects_service_endpoints_in_both_binary_string_encodings(self):
        for encoding in ("utf-8","utf-16-le"):
            result=self.scan("https://api.audio.com/v1/analytics".encode(encoding))
            self.assertNotEqual(result.returncode,0)
            self.assertIn("api.audio.com",result.stdout)
    def test_allows_source_attribution_and_gpl_license_urls(self):
        result=self.scan(b"https://www.gnu.org/licenses/ https://github.com/audacity/audacity")
        self.assertEqual(result.returncode,0,result.stderr)
