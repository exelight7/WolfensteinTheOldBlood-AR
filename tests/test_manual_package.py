import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manual_package", ROOT / "tools/build_manual_package.py")
manual = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manual)


class ManualPackageTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/supported_versions.json").read_text(encoding="utf-8"))

    def test_supported_config_and_unknown_target_refusal(self):
        manual.validate_config(self.config)
        bad = copy.deepcopy(self.config)
        bad["supported_versions"][0]["vanilla"]["../danger"] = "a" * 64
        with self.assertRaises(ValueError):
            manual.validate_config(bad)

    def test_prior_state_requires_complete_archive_pair(self):
        bad = copy.deepcopy(self.config)
        bad["supported_versions"][0]["also_accepted_states"] = [{"base/chunk0.index": "a" * 64}]
        with self.assertRaises(ValueError):
            manual.validate_config(bad)

    def test_archive_allowlist_and_windows_arabic_encoding(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            sidecar = path / "wtob-build.exe"
            sidecar.write_bytes(b"MZtest-fixture")
            out = path / "manual.zip"
            result = manual.build_package(sidecar, ROOT / "config/supported_versions.json", out)
            self.assertEqual(result["size"], out.stat().st_size)
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(set(archive.namelist()), {"wtob-build.exe", "supported_versions.json", "Install.cmd", "Restore.cmd", "Manual.ps1", "README.md", "licenses/IBM_Plex_OFL.txt", "licenses/LICENSE", "licenses/THIRD_PARTY_NOTICES.md", "licenses/PYTHON_DEPENDENCIES.txt"})
                self.assertTrue(archive.read("Manual.ps1").startswith(b"\xef\xbb\xbf"))
                self.assertFalse(any("chunk0" in name or "english" in name for name in archive.namelist()))

    def test_non_windows_builder_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            fake = path / "builder"
            fake.write_bytes(b"not an exe")
            with self.assertRaises(ValueError):
                manual.build_package(fake, ROOT / "config/supported_versions.json", path / "manual.zip")


if __name__ == "__main__":
    unittest.main()
