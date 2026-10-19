import json
import tempfile
import unittest
from pathlib import Path

from tools.check_public_repo import collect_walk_files, scan, scan_file


class PublicRepoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_clean_file_passes(self):
        self.write("README.md", "# Title\nnormal documentation\n")
        self.assertEqual(scan(self.root, ["README.md"]), [])

    def test_secret_is_flagged(self):
        fake = "ghp_" + "x" * 24
        self.write("notes.txt", f"token = \"{fake}\"\n")
        self.assertTrue(scan_file(self.root, "notes.txt"))

    def test_developer_path_is_flagged(self):
        fake = "C:" + "\\" + "Users" + "\\" + "someone" + "\\game"
        self.write("map.md", "see " + fake + "\n")
        self.assertTrue(scan_file(self.root, "map.md"))

    def test_forbidden_extension_is_flagged(self):
        (self.root / "chunk0.resources").write_bytes(b"\x00")
        self.assertTrue(scan_file(self.root, "chunk0.resources"))

    def test_translation_english_leak_is_flagged(self):
        payload = [{"id": "strings/english.lang:#a", "english": "Secret string",
                    "arabic": "نص"}]
        self.write("translation/arabic/phase_25.json", json.dumps(payload))
        self.assertTrue(scan_file(self.root, "translation/arabic/phase_25.json"))

    def test_translation_without_english_passes(self):
        payload = [{"id": "strings/english.lang:#a", "english": "", "arabic": "نص"}]
        self.write("translation/arabic/phase_25.json", json.dumps(payload))
        self.assertEqual(scan_file(self.root, "translation/arabic/phase_25.json"), [])

    def test_walk_skips_private_dirs(self):
        self.write("workspace/all_text/corpus.jsonl", "{}")
        self.write("src/main.py", "print('hi')\n")
        files = collect_walk_files(self.root)
        self.assertIn("src/main.py", files)
        self.assertNotIn("workspace/all_text/corpus.jsonl", files)


if __name__ == "__main__":
    unittest.main()
