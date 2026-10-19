"""Regression + synthetic tests for token-transparent Arabic joining.

Anchor record: #str_vo_agentone_dlc1_c01_123 (real token structure).
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from formatted_text import (  # noqa: E402
    TOKEN_RE,
    ZWJ,
    _first_arabic_letter,
    _is_arabic_letter,
    _joins_forward,
    _last_arabic_letter,
    _shape_text_segment,
    _span_is_pure_rtl,
    _transparent_gap,
    shape_formatted,
    shape_formatted_ordered,
    shape_line,
    shape_line_spans_ordered,
    tokens_in,
)

# Real logical Arabic of #str_vo_agentone_dlc1_c01_123 (translated, master):
RECORD_123_ARABIC = (
    "[eng]ويسلي: يحيط المقر الأمر بسرية تامة.[2.4] يصنع الجنرال ديثسهيد آلات "
    "قتل لا تقهر في مجمع سري. [7.6] إحدى مساعداته، هيلغا فون شابس، [10] "
    "تحتفظ بالملف المذكور في موجز مهمتك في مقر عملياتها، [13.2] قلعة "
    "ولفنشتاين. "
)
RECORD_123_TAGS = ["[eng]", "[2.4]", "[7.6]", "[10]", "[13.2]"]


def pua_encode(text, mapping):
    # BUILD_INFO mapping is stored as "U+XXXX" strings for source->PUA
    decoded = {chr(int(k[2:], 16)): chr(int(v[2:], 16)) for k, v in mapping.items()}
    return "".join(decoded.get(c, c) for c in text)


def strip_tokens(visual):
    return TOKEN_RE.sub("", visual)


class _123FixtureTests(unittest.TestCase):
    def test_tokens_unchanged_and_in_order(self):
        out = shape_line(RECORD_123_ARABIC, None)
        self.assertEqual(tokens_in(RECORD_123_ARABIC), RECORD_123_TAGS)
        positions = [out.find(tok) for tok in RECORD_123_TAGS]
        self.assertTrue(all(p >= 0 for p in positions))
        self.assertEqual(positions, sorted(positions))

    def test_no_joiner_leak(self):
        out = shape_line(RECORD_123_ARABIC, None)
        self.assertNotIn(ZWJ, out)

    def test_deterministic_repeat(self):
        self.assertEqual(shape_line(RECORD_123_ARABIC, None), shape_line(RECORD_123_ARABIC, None))

    def test_no_isolated_forms_of_span_internal_arabic(self):
        spans = TOKEN_RE.split(RECORD_123_ARABIC)
        concat = "".join(shape_line(s, None) for s in spans)
        out = shape_line(RECORD_123_ARABIC, None)
        self.assertEqual(strip_tokens(out), concat)

    def test_reproduces_installed_poc_value(self):
        info = json.loads((ROOT / "workspace" / "opening_runtime_poc" / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
        expected_pua = pua_encode(shape_line(RECORD_123_ARABIC, None), info["mapping"])
        runtime = (ROOT / "workspace" / "opening_runtime_poc" / "english_runtime.local.lang").read_text(encoding="utf-8")
        self.assertTrue(expected_pua in runtime,
                        "expected %r head=%r tail=%r" % (
                            expected_pua[:40], runtime[:80], expected_pua[len(expected_pua)//2:len(expected_pua)//2+40]))


class SyntheticEdgeTests(unittest.TestCase):
    def test_letter_tag_letter_joins(self):
        out = shape_line("س[2.4]ر", None)
        self.assertIn("ﺳ", out)      # U+FEB3 initial: joins forward across tag
        self.assertIn("ﺮ", out)      # U+FEAE final: receives the connection

    def test_letter_tag_chain_letter_joins(self):
        out = shape_line("س[eng][10]ر", None)
        self.assertIn("ﺳ", out)
        self.assertIn("ﺮ", out)

    def test_space_breaks_joining(self):
        out = shape_line("س [2.4] ر", None)
        self.assertIn("ﺱ", out)      # U+FEB1 isolated
        self.assertIn("ﺭ", out)      # U+FEAD isolated
        self.assertNotIn("ﺳ", out)   # no initial form
        self.assertNotIn("ﺮ", out)   # no final form

    def test_right_joining_letter_does_not_forward_join(self):
        out = shape_line("ر[2.4]س", None)
        self.assertIn("ﺭ", out)      # ر cannot emit a join
        self.assertIn("ﺱ", out)      # س must stay isolated
        self.assertNotIn("ﺳ", out)

    def test_visible_ltr_token_hard_boundary(self):
        out = shape_line("س%dر", None)
        self.assertIn("ﺱ", out)
        self.assertIn("ﺭ", out)
        self.assertNotIn("ﺳ", out)
        self.assertNotIn("ﺮ", out)
        self.assertIn("%d", out)

    def test_colour_code_transparent(self):
        out = shape_line("س^1ر", None)
        self.assertIn("ﺳ", out)
        self.assertIn("ﺮ", out)
        self.assertIn("^1", out)

    def test_newline_hard_boundary(self):
        out = shape_formatted("س\nر[2.4]ح", None)
        lines = out.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "\ufeB1")  # U+FEB1 Arabic SEEN isolated form
        self.assertEqual(strip_tokens(lines[1]), "\ufeAD\ufea1")  # ر iso, ح iso
        self.assertIn("[2.4]", lines[1])
        self.assertNotIn(ZWJ, out)  # newline = hard boundary for joining
        self.assertEqual(out.count("\n"), 1)

    def test_arabic_number_island(self):
        out = shape_line("س 1234 ر", None)
        self.assertEqual(out.count("1234"), 1)

    def test_latin_island_between_arabic_words(self):
        out = shape_line("ABC س ر", None)
        self.assertIn("ABC", out)

    def test_deterministic(self):
        self.assertEqual(shape_line("س[2.4]ر [7]ق", None), shape_line("س[2.4]ر [7]ق", None))

    def test_no_tag_loss_round_trip(self):
        logical = "س[2.4]ر [7]ق <JOY1> {0} _id $v"
        out = shape_line(logical, None)
        for tok in tokens_in(logical):
            self.assertIn(tok, out)


class WholeStrippedEquivalenceTests(unittest.TestCase):
    """Phase 9 key assertion: stripping transparent tokens from the TOKEN-AWARE
    output B yields the same Arabic glyph FORMS as shaping the token-stripped
    logical string A."""

    BATTERY = [
        "س[2.4]ر",
        "س[eng][10]ر",
        "س^3ق[2.4]ح",
        "توبة.[2.4] يصنع الجنرال.",
        "شابس، [10] تحتفظ بالملف.",
        "[eng]ويسلي: يحيط.[2.4] يصنع. [7.6] قلعة.",
    ]

    def _glyph_forms(self, text):
        shaped = shape_line(text, None)
        return sorted(ud_codepoint(c) for c in strip_tokens(shaped) if not c.isascii())

    def test_forms_equal_to_token_free_shaping(self):
        for text in self.BATTERY:
            stripped = strip_tokens(text)
            self.assertTrue(any(_is_arabic_letter(c) for c in stripped), text)
            self.assertEqual(self._glyph_forms(text), self._glyph_forms(stripped), text)

    def test_letter_tag_letter_forms_match_no_token_case(self):
        # the classic supervisor example: س[2.4]ر must shape like سر
        self.assertEqual(self._glyph_forms("س[2.4]ر"), self._glyph_forms("سر"))


def ud_codepoint(ch):
    return ord(ch)


RECORD_123_1_ARABIC = (
    "[eng] يحوي هذا الملف موقع مجمع ديثسهيد. [4] قد تكون هذه فرصتنا الأخيرة. "
    "[6] قبل أن يمحو النازيون كل ما هو طيب في هذا العالم."
)


class SpanOrderCorrectionTests(unittest.TestCase):
    """Candidate C: whole visible line must read coherently RTL across timed
    spans, i.e. the concatenation of the visible text must equal the visual
    order of the token-free line."""

    def _full_line_visual(self, logical):
        return _shape_text_segment(TOKEN_RE.sub("", logical))

    def _visible(self, visual):
        return strip_tokens(visual)

    def test_123_visible_equals_full_line_visual(self):
        out = shape_line_spans_ordered(RECORD_123_ARABIC, None)
        self.assertEqual(self._visible(out), self._full_line_visual(RECORD_123_ARABIC))

    def test_123_1_visible_equals_full_line_visual(self):
        out = shape_line_spans_ordered(RECORD_123_1_ARABIC, None)
        self.assertEqual(self._visible(out), self._full_line_visual(RECORD_123_1_ARABIC))

    def test_current_algorithm_is_not_full_line_visual(self):
        # documents WHY the correction exists: the plain pipeline emits spans
        # in logical order, which is the wrong visual order for an RTL line.
        out = shape_line(RECORD_123_ARABIC, None)
        self.assertNotEqual(self._visible(out), self._full_line_visual(RECORD_123_ARABIC))

    def test_span_order_is_pure_permutation_same_length(self):
        a = shape_line(RECORD_123_ARABIC, None)
        c = shape_line_spans_ordered(RECORD_123_ARABIC, None)
        self.assertEqual(len(a), len(c))
        self.assertEqual(sorted(self._visible(a)), sorted(self._visible(c)))

    def test_tokens_preserved_in_order(self):
        for logical in (RECORD_123_ARABIC, RECORD_123_1_ARABIC):
            out = shape_line_spans_ordered(logical, None)
            positions = [out.find(tok) for tok in tokens_in(logical)]
            self.assertTrue(all(p >= 0 for p in positions))
            self.assertEqual(positions, sorted(positions))

    def test_single_span_equals_current(self):
        single = "[eng][2]ويسلي: أنا وأنت يا بلازكوفيتش. نحن فريق جيد."
        self.assertEqual(shape_line_spans_ordered(single, None), shape_line(single, None))

    def test_latin_island_falls_back_to_current(self):
        mixed = "ABC س [2.4] ر"
        self.assertEqual(shape_line_spans_ordered(mixed, None), shape_line(mixed, None))

    def test_pure_rtl_detector(self):
        self.assertTrue(_span_is_pure_rtl("س ر ق"))
        self.assertFalse(_span_is_pure_rtl("س ABC ر"))

    def test_no_joiner_leak(self):
        self.assertNotIn(ZWJ, shape_line_spans_ordered(RECORD_123_ARABIC, None))

    def test_deterministic(self):
        self.assertEqual(shape_line_spans_ordered(RECORD_123_ARABIC, None),
                         shape_line_spans_ordered(RECORD_123_ARABIC, None))

    def test_consecutive_tags(self):
        logical = "واحد [eng][10] اثنان [7] ثلاثة"
        out = shape_line_spans_ordered(logical, None)
        self.assertEqual(self._visible(out), self._full_line_visual(logical))
        self.assertEqual([out.find(t) for t in tokens_in(logical)],
                         sorted(out.find(t) for t in tokens_in(logical)))

    def test_letter_adjacent_consecutive_tags_falls_back(self):
        # س joins forward across the gap, so reordering is unsafe -> current pipeline
        logical = "س[eng][10]ر"
        self.assertTrue(_joins_forward("س"))
        self.assertEqual(shape_line_spans_ordered(logical, None), shape_line(logical, None))

    def test_non_joining_boundary_still_equals_full_line(self):
        # د does not join forward, so no joining crosses the gap and the
        # correction is safe: visible text equals the whole-line visual order
        logical = "واحد[eng][10]اثنان"
        self.assertFalse(_joins_forward("د"))
        self.assertEqual(self._visible(shape_line_spans_ordered(logical, None)),
                         self._full_line_visual(logical))

    def test_arabic_digits_punctuation(self):
        logical = "التقرير رقم 1234، جاهز.[2.4] تم."
        out = shape_line_spans_ordered(logical, None)
        self.assertIn("1234", out)
        self.assertEqual(self._visible(out), self._full_line_visual(logical))

    def test_multiline_per_line(self):
        logical = "أول سطر.[2] ثاني جزء.\nسطر آخر.[3] نهاية."
        out = shape_formatted_ordered(logical, None)
        self.assertEqual(out.count("\n"), 1)
        first, second = out.split("\n")
        self.assertEqual(self._visible(first), self._full_line_visual("أول سطر.[2] ثاني جزء."))
        self.assertEqual(self._visible(second), self._full_line_visual("سطر آخر.[3] نهاية."))

    def test_pua_mapping_preserves_order(self):
        base = shape_line_spans_ordered(RECORD_123_ARABIC, None)
        chars = sorted({c for c in base if ord(c) > 127})
        mapping = {c: 0xE000 + i for i, c in enumerate(chars)}
        out = shape_line_spans_ordered(RECORD_123_ARABIC, mapping)
        self.assertEqual(out.count("[eng]"), 1)
        self.assertTrue(all(ord(c) <= 127 or 0xE000 <= ord(c) < 0xE000 + len(mapping)
                            for c in out))
        positions = [out.find(t) for t in RECORD_123_TAGS]
        self.assertTrue(all(p >= 0 for p in positions))
        self.assertEqual(positions, sorted(positions))


class TransparencyCensusRulesTests(unittest.TestCase):
    def test_gap_transparency_classification(self):
        self.assertTrue(_transparent_gap(["[eng]"]))
        self.assertTrue(_transparent_gap(["[2.4]", "[eng]", "[400]"]))
        self.assertTrue(_transparent_gap(["^1"]))
        self.assertFalse(_transparent_gap(["%d"]))
        self.assertFalse(_transparent_gap(["<JOY1>"]))
        self.assertFalse(_transparent_gap(["{0}"]))
        self.assertFalse(_transparent_gap(["_id"]))
        self.assertFalse(_transparent_gap(["$var"]))

    def test_joins_forward_table(self):
        self.assertTrue(_joins_forward("س"))
        self.assertFalse(_joins_forward("ر"))
        self.assertFalse(_joins_forward("؟"))
        self.assertFalse(_joins_forward(" "))
        self.assertTrue(_joins_forward("\u0640"))

    def test_letter_skippers(self):
        self.assertEqual(_last_arabic_letter("س\u064e"), "س")
        self.assertEqual(_first_arabic_letter("\u064eس"), "س")
        self.assertIsNone(_last_arabic_letter("س\u064e "))  # space terminates adjacency
        self.assertIsNone(_last_arabic_letter("abc"))
        self.assertIsNone(_last_arabic_letter(""))


if __name__ == "__main__":
    unittest.main()
