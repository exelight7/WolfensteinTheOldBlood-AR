import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_runtime_localization as brl  # noqa: E402
import formatted_text as ft  # noqa: E402


class CorpusGateTests(unittest.TestCase):
    def test_confirmed_corpus_identity(self):
        rows = brl.load_partitions(100)
        self.assertEqual(len(rows), 3574)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        translated = [r for r in rows if r["status"] == "translated"]
        dnt = [r for r in rows if r["status"] == "do_not_translate"]
        self.assertEqual((len(translated), len(dnt)), (3376, 198))
        self.assertEqual(len(translated) + len(dnt), 3574)

    def test_two_loose_records_are_the_driver_warning(self):
        rows = brl.load_partitions(100)
        loose = [r for r in rows if r["resource"] != "strings/english.lang"]
        self.assertEqual({r["resource"] for r in loose}, {brl.LOOSE_RESOURCE})
        self.assertEqual({r["location"] for r in loose}, {"english_head", "english_body"})

    def test_do_not_translate_never_translated(self):
        rows = brl.load_partitions(100)
        for row in rows:
            if row["status"] == "do_not_translate":
                self.assertEqual(row["arabic"], "")
            else:
                self.assertTrue(row["arabic"])


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.v4 = brl.invert_pua(
            json.loads(brl.V4_INFO.read_text(encoding="utf-8"))["mapping"])

    def test_v4_mapping_preserved_as_prefix(self):
        extra = {"\u061B", "\u00AB"}  # not present in the V4 mapping
        mapping = brl.build_mapping(set(self.v4) | extra, self.v4)
        for character, code in self.v4.items():
            self.assertEqual(mapping[character], code)
        self.assertEqual(min(mapping.values()), 0xE000)
        self.assertEqual(max(self.v4.values()), 0xE061)
        for character in extra:
            self.assertGreater(mapping[character], max(self.v4.values()))

    def test_new_characters_get_contiguous_codes_in_sorted_order(self):
        v4 = {chr(0xFE80): 0xE000}
        mapping = brl.build_mapping({chr(0xFE80), chr(0xFE83), chr(0xFE81)}, v4)
        self.assertEqual(mapping[chr(0xFE81)], 0xE001)
        self.assertEqual(mapping[chr(0xFE83)], 0xE002)

    def test_mapping_is_deterministic(self):
        chars = set(self.v4) | {"\u060C", "\u00AB"}
        self.assertEqual(brl.build_mapping(chars, self.v4),
                         brl.build_mapping(set(reversed(list(chars))), self.v4))


class ShapeRecordTests(unittest.TestCase):
    def mapping(self):
        return brl.invert_pua(
            json.loads(brl.V4_INFO.read_text(encoding="utf-8"))["mapping"])

    def test_token_and_newline_parity(self):
        record = dict(id="x", arabic="\u0645\u0631\u062d\u0628\u0627 [1.0] \u0628\u0643\n\u0643\u064a\u0641 %d",
                      english="Hello [1.0] you\nHow %d")
        literal, visual = brl.shape_record(record, self.mapping())
        self.assertEqual(visual.count("\n"), 1)
        self.assertEqual(ft.decode_lang_value(literal), visual)

    def test_bracket_mismatch_is_rejected(self):
        record = dict(id="x", arabic="\u0645\u0631\u062d\u0628\u0627 [1.0]",
                      english="Hello")
        with self.assertRaises(ValueError):
            brl.shape_record(record, self.mapping())

    def test_candidate_c_is_applied_uniformly(self):
        # "واحد" ends on a non-joining letter, so the timed spans are safe to reorder
        arabic = "\u0648\u0627\u062d\u062f [2] \u0627\u062b\u0646\u0627\u0646"
        self.assertNotEqual(ft.shape_formatted_ordered(arabic, None),
                            ft.shape_formatted(arabic, None))


class LangRewriteTests(unittest.TestCase):
    SOURCE = (b'\xef\xbb\xbf// hdr\r\n{\r\n'
              b'\t"#str_a"\t"A [1]"\r\n'
              b'\t"#str_b"\t"Keep me"\r\n'
              b'}\r\n')

    def test_only_intended_key_is_replaced(self):
        out = brl.rewrite_lang(self.SOURCE, {"#str_a": "\u0645\u0631\u062d\u0628\u0627 [1]"})
        self.assertTrue(out.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(out.endswith(b"}\r\n"))
        from local_reference import parse_lang
        rows = {r["source_key"]: r["english"] for r in parse_lang(out)}
        self.assertEqual(rows["#str_a"], "\u0645\u0631\u062d\u0628\u0627 [1]")
        self.assertEqual(rows["#str_b"], "Keep me")

    def test_missing_key_is_an_error(self):
        with self.assertRaises(ValueError):
            brl.rewrite_lang(self.SOURCE, {"#str_missing": "x"})


class LooseRewriteTests(unittest.TestCase):
    SOURCE = (b'\xef\xbb\xbf{\r\n'
              b'\t"english_body" : "Old %s",\r\n'
              b'\t"german_body" : "Deutsch %s"\r\n'
              b'}\r\n')

    def test_only_english_values_are_replaced(self):
        value = "\u062c\u062f\u064a\u062f %s"
        out = brl.rewrite_loose(self.SOURCE, {"english_body": value})
        obj = json.loads(out.decode("utf-8-sig"))
        self.assertEqual(obj["english_body"], value)
        self.assertEqual(obj["german_body"], "Deutsch %s")
        self.assertEqual(out.count(b"\r\n"), self.SOURCE.count(b"\r\n"))

    def test_missing_key_is_an_error(self):
        with self.assertRaises(ValueError):
            brl.rewrite_loose(self.SOURCE, {"english_head": "x"})


if __name__ == "__main__":
    unittest.main()
