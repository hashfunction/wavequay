"""Run the distribution guard before any Qt/native dependency acquisition."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class DistributionConfigurationTests(unittest.TestCase):
    def configure(self, *definitions):
        with tempfile.TemporaryDirectory() as directory:
            script = pathlib.Path(directory) / "configure.cmake"
            script.write_text(
                f'include("{(ROOT / "distribution/ConfigureWaveQuay.cmake").as_posix()}")\n'
                'if(AU_BUILD_CLOUD_AUDIOCOM OR AU_BUILD_USAGEINFO_MODULE OR MUSE_MODULE_NETWORK)\n'
                ' message(FATAL_ERROR "Remote modules remain enabled")\nendif()\n'
            )
            return subprocess.run(
                ["cmake", "-DAU_TRIEFLOW_DISTRIBUTION=ON", *definitions, "-P", str(script)],
                capture_output=True, text=True,
            )

    def test_default_offline_configuration(self):
        result = self.configure()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_remote_conflicts_are_rejected(self):
        for option in ("AU_BUILD_CLOUD_AUDIOCOM", "AU_BUILD_USAGEINFO_MODULE",
                       "MUSE_MODULE_NETWORK", "MUSE_MODULE_UPDATE",
                       "MUSE_MODULE_DIAGNOSTICS_CRASHPAD_CLIENT"):
            with self.subTest(option=option):
                result = self.configure(f"-D{option}=ON")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"WaveQuay forbids {option}", result.stderr)

    def test_portaudio_owned_recipe_explicitly_disables_asio(self):
        with tempfile.TemporaryDirectory() as directory:
            script = pathlib.Path(directory) / "portaudio.cmake"
            script.write_text(
                'cmake_minimum_required(VERSION 3.24)\nset(BD_OS windows)\n'
                'set_property(GLOBAL PROPERTY asiosdk_SOURCE_DIR "unwanted-sdk")\n'
                'function(_bd_cmake_build src)\n'
                ' if(NOT "-DPA_USE_ASIO=OFF" IN_LIST DEP_CMAKE_ARGS)\n'
                '  message(FATAL_ERROR "ASIO was not disabled")\n endif()\n'
                ' if("-DPA_USE_ASIO=ON" IN_LIST DEP_CMAKE_ARGS)\n'
                '  message(FATAL_ERROR "ASIO was enabled")\n endif()\n'
                'endfunction()\n'
                f'include("{(ROOT / "distribution/recipes/portaudio/spec.cmake").as_posix()}")\n'
                f'include("{(ROOT / "distribution/recipes/portaudio/build.cmake").as_posix()}")\n'
            )
            result = subprocess.run(["cmake", "-DCMAKE_POLICY_DEFAULT_CMP0057=NEW", "-P", str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
