import json
import tempfile
from pathlib import Path
import unittest
from tools.local_reference import parse_lang, generate


class ReferenceTests(unittest.TestCase):
    def test_preserves_source_and_escapes(self):
        raw = b'\xef\xbb\xbf// synthetic\r\n{ "#str_demo" "Line\\nSay \\"hello\\" %d" }'
        row = parse_lang(raw)[0]
        self.assertEqual(row["english"], 'Line\nSay "hello" %d')
        self.assertEqual(row["english_literal"], r'Line\nSay \"hello\" %d')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            generate(raw, output)
            first = (output / "ALL_TRANSLATIONS.local.md").read_bytes()
            generate(raw, output)
            self.assertEqual(first, (output / "ALL_TRANSLATIONS.local.md").read_bytes())
            self.assertEqual(raw, (output / "english_source.local.lang").read_bytes())
            self.assertLess(first.index(b"AR:"), first.index(b"EN:"))

    def test_regeneration_keeps_translation_and_refuses_source_drift(self):
        raw = b'{ "#str_demo" "Synthetic text" }'
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            generate(raw, output)
            master = output / "translation_master.local.jsonl"
            row = json.loads(master.read_text(encoding="utf-8"))
            row.update(arabic="نص تجريبي", status="draft", notes="keep this")
            master.write_text(json.dumps(row) + "\n", encoding="utf-8")
            generate(raw, output)
            self.assertEqual(json.loads(master.read_text(encoding="utf-8"))["arabic"], "نص تجريبي")
            self.assertIn("keep this", master.read_text(encoding="utf-8"))
            before = master.read_bytes()
            with self.assertRaises(ValueError):
                generate(raw.replace(b"Synthetic", b"Changed"), output)
            self.assertEqual(before, master.read_bytes())

    def test_rejects_invalid_syntax_and_duplicate_ids(self):
        for raw in (b'{ "#str_a" "x" "#str_a" "y" }',
                    b'{ "#str_a" "bad\\q" }', b'{ "#str_a" }',
                    b'{ "#str_a" "x" } garbage'):
            with self.assertRaises(ValueError):
                parse_lang(raw)


if __name__ == "__main__":
    unittest.main()
