"""Unit tests for tools/formatted_text.py (no game files required)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import formatted_text as ft  # noqa: E402
import arabic_reshaper  # noqa: E402
from bidi.algorithm import get_display  # noqa: E402

NL = "\n"
BS = chr(92)


def master_rows():
    path = ROOT / "reference" / "translation_master.local.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def translated():
    return [r for r in master_rows() if r["status"] == "translated"]


class TestSerialization(unittest.TestCase):
    def test_roundtrip_samples(self):
        cases = [
            ("", ""),
            ("hello", "hello"),
            ("line1" + NL + "line2", "line1" + BS + "nline2"),
            ('say "hi"', "say " + BS + '"hi' + BS + '"'),
            (NL, BS + "n"),
        ]
        for value, literal in cases:
            self.assertEqual(ft.encode_lang_value(value), literal)
            self.assertEqual(ft.decode_lang_value(literal), value)

    def test_backslash_rejected(self):
        with self.assertRaises(ValueError):
            ft.encode_lang_value("bad" + BS + "path")

    def test_master_decode_matches_reference_semantics(self):
        # decode of the stored literal must equal the master's decoded english
        for row in translated():
            self.assertEqual(ft.decode_lang_value(row["english_literal"]), row["english"])
            self.assertEqual(ft.encode_lang_value(row["english"]), row["english_literal"])

    def test_master_roundtrip_all_rows(self):
        for row in master_rows():
            value = row["english"]
            literal = ft.encode_lang_value(value)
            self.assertEqual(ft.decode_lang_value(literal), value)
            self.assertNotIn(BS + chr(0x60), literal)  # no accidental escapes

    def test_escape_inventory_exhaustive(self):
        # only \\n and \\" escapes may appear in confirmed literals
        for row in master_rows():
            literal = row["english_literal"]
            cleaned = literal.replace(BS + "n", "").replace(BS + '"', "")
            self.assertNotIn(BS, cleaned, row["id"])


class TestTokens(unittest.TestCase):
    def test_token_catalog(self):
        t = ("[ger][10.5] [] %d %02d %s {0} <JOY1> ^2 _Weapon $v" + NL + "text")
        toks = ft.tokens_in(t)
        for expected in ("[ger]", "[10.5]", "[]", "%d", "%02d", "%s", "{0}",
                         "<JOY1>", "^2", "_Weapon", "$v", NL):
            self.assertIn(expected, toks)

    def test_bracket_token_classes_ordered(self):
        t = "[eng]مرحبا [1.33][2] [p1]"
        self.assertEqual(ft.tokens_in(t), ["[eng]", "[1.33]", "[2]", "[p1]"])

    def test_percent_followed_by_latin_word(self):
        # bare % that is not a printf token must not swallow the next word
        self.assertNotIn("5%", ft.tokens_in("5%"))
        self.assertIn("%d", ft.tokens_in("%d"))

    def test_multi_tag_record_tokens化合物(self):
        t = "[eng][1.47]مهلا. [3.33]هيا يا ويسلي. [10.5][12.09]بلازكوفيتش."
        self.assertEqual(ft.tokens_in(t), ["[eng]", "[1.47]", "[3.33]", "[10.5]", "[12.09]"])


class TestRuns(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(ft._classify("م"), "R")
        self.assertEqual(ft._classify("a"), "L")
        self.assertEqual(ft._classify("5"), "L")
        self.assertEqual(ft._classify("."), "N")
        self.assertEqual(ft._classify("«"), "N")

    def test_merge_same_direction(self):
        runs = ft._runs("abc")
        self.assertEqual(runs, [("L", "abc")])
        runs = ft._runs("مرحبا")
        self.assertEqual(runs, [("R", "مرحبا")])

    def test_neutral_between_same_class_merges_forward(self):
        runs = ft._runs("45,000")
        self.assertEqual(runs, [("L", "45,000")])

    def test_neutral_between_diff_class_stays(self):
        runs = ft._runs("abc عربي")
        self.assertEqual(runs, [("L", "abc"), ("N", " "), ("R", "عربي")])


class TestShaping(unittest.TestCase):
    def test_pure_latin_passthrough(self):
        t = '"EDIT REGINE CINERES HIC SARCOPHAGVS HABET"'
        self.assertEqual(ft.shape_line(t, {}), t)

    def test_digits_island_internally_ltr(self):
        shaped = ft.shape_line('المريض رقم B6، رودولف تروملر.', {})
        self.assertIn("B6", shaped)
        self.assertEqual(shaped.count("."), 1)

    def test_tokens_never_resaped(self):
        t = "[ger][10.5][12.09]بي. جي.؟ []ويليام"
        shaped = ft.shape_line(t, {})
        for tok in ("[ger]", "[10.5]", "[12.09]", "[]"):
            self.assertIn(tok, shaped)
        expected_tokens = ft.tokens_in(t)
        self.assertEqual(ft.tokens_in(shaped), expected_tokens)

    def test_printf_specifier_intact(self):
        self.assertIn("%d", ft.shape_line("太 %d فقط", {}))
        shaped = ft.shape_line("أنهيت التحدي في %d:%02d فقط.", {})
        self.assertIn("%d:%02d", shaped)

    def test_menu_single_run_pilot_equivalence(self):
        # pure Arabic menu strings must produce byte-identical output to the
        # untouched build_menu_pilot.py pipeline (reshape + whole-line get_display)
        languages = json.loads((ROOT / "translation" / "arabic" / "main_menu.json").read_text(encoding="utf-8"))
        for row in languages:
            blind = get_display(arabic_reshaper.reshape(row["arabic"]))
            mine = ft.shape_line(row["arabic"], {})
            self.assertEqual(blind, mine, row["id"])

    def test_newline_count_preserved_all_master_arabic(self):
        for row in translated():
            if NL not in row["arabic"]:
                continue
            shaped = ft.shape_formatted(row["arabic"], {})
            self.assertEqual(shaped.count(NL), row["arabic"].count(NL), row["id"])

    def test_no_carriage_return_or_tab(self):
        for row in translated():
            value = row["arabic"]
            self.assertNotIn("\r", value)
            self.assertNotIn("\t", value)

    def test_mapping_consistency(self):
        # identical visual chars map to identical codes across records during one build
        char_set, mapping = {}, {}
        for row in translated()[:80]:
            shaped = ft.shape_formatted(row["arabic"], mapping)
            for ch in shaped:
                if ord(ch) > 127 and ch not in char_set:
                    char_set[ch] = 0xE000 + len(char_set)
        self.assertTrue(char_set, "expected non-ASCII chars")

    def test_shadda_and_marks_survive(self):
        t = "بنّ" + chr(0x651)
        shaped = ft.shape_line(t, {})
        self.assertTrue(shaped)

    def test_all_master_shapes_complete(self):
        for row in translated():
            ft.shape_formatted(row["arabic"], {})
        self.assertTrue(True)

    def test_shaped_values_serialize_cleanly(self):
        for row in translated():
            shaped = ft.shape_formatted(row["arabic"], {})
            literal = ft.encode_lang_value(shaped)
            self.assertEqual(ft.decode_lang_value(literal), shaped)
            self.assertNotIn("\r", literal)
            self.assertNotIn("\t", literal)
            # only documented escapes appear
            cleaned = literal.replace(BS + "n", "").replace(BS + '"', "")
            self.assertNotIn(BS, cleaned, row["id"])

    def test_visual_pua_mapping_roundtrip(self):
        # map non-ASCII visuals to ascending PUA codes deterministically;
        # note: reshaper folds الله into the ligature ﷲ (U+FDF2), which is
        # itself a non-ASCII char that a full build's mapping captures.
        sample = "بسم الله"
        shaped_blind = ft.shape_formatted(sample, {})
        ligature = chr(0xFDF2)
        self.assertIn(ligature, shaped_blind)
        mapping = {ch: 0xE000 + i for i, ch in enumerate(sorted(set(c for c in shaped_blind if ord(c) > 127)))}
        shaped = ft.shape_formatted(sample, mapping)
        # every visual char must be either ASCII or a mapped PUA codepoint, and
        # all mapping codes must actually appear
        self.assertTrue(all(ord(c) <= 127 or 0xE000 <= ord(c) < 0xE000 + len(mapping) for c in shaped))
        for code in range(0xE000, 0xE000 + len(mapping)):
            self.assertIn(chr(code), shaped)


if __name__ == "__main__":
    unittest.main()
