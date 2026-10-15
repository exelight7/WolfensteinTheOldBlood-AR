from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_text_sources import analyze
from collect_text_corpus import binary_strings, record, native_candidates


class TextAuditTests(unittest.TestCase):
    def test_binary_string_bounds_and_utf8(self):
        text = b"Synthetic menu label"
        data = len(text).to_bytes(4, "little") + text + bytes(8)
        self.assertIn((4, text.decode()), binary_strings(data))
        self.assertEqual(binary_strings(data[:10]), [])

    def test_text_and_binary_are_distinguished(self):
        ids, text = analyze(b'{ label = "#str_demo"; }')
        self.assertEqual(ids, {"#str_demo"})
        self.assertIsNotNone(text)
        self.assertIsNone(analyze(b"\xff\x00\x01")[1])

    def test_native_text_candidates_preserve_both_encodings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.exe"
            path.write_bytes(b"\x00Synthetic warning\x00\x00\x00" + "Another warning".encode("utf-16le"))
            rows = native_candidates(Path(temp))
            self.assertTrue(any(r["english"] == "Synthetic warning" for r in rows))
            self.assertTrue(any(r["english"] == "Another warning" for r in rows))
            self.assertTrue(all(r["status"] == "needs_classification" for r in rows))

    def test_external_record_has_stable_key_and_hash(self):
        a = record("warning.json", "english_body", "Synthetic %s", "confirmed")
        b = record("warning.json", "english_body", "Synthetic %s", "confirmed")
        self.assertEqual(a, b)
        self.assertEqual(a["arabic"], "")
        self.assertEqual(len(a["english_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
