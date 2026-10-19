import struct
import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pilot_font import (glyph_form, joining_kernings, pack_kerning, parse_kerning)


def ink_bitmap(columns, width=24, height=4):
    """SDF bitmap with >=128 ink in the given column range [lo, hi]."""
    lo, hi = columns
    bitmap = Image.new("L", (width, height), 0)
    for x in range(lo, hi + 1):
        for y in range(height):
            bitmap.putpixel((x, y), 200)
    return bitmap


def glyph(index, form, left, advance, columns, width=24):
    return dict(glyph_index=index, form=form, left=left, advance=advance,
                bitmap=ink_bitmap(columns, width=width))


class JoiningKerningTests(unittest.TestCase):
    def test_round_trip_and_sorted(self):
        pairs = [(7, 3, -1.5), (0, 1, -2.0), (0, 0, 0.5)]
        blob = pack_kerning(pairs)
        header = b"idf+" + struct.pack(">hhhH", 64, 60, -15, 1) + bytes(12) + struct.pack("<I", 65)
        self.assertEqual(parse_kerning(header + blob), sorted(pairs))

    def test_duplicate_pair_rejected(self):
        with self.assertRaises(ValueError):
            pack_kerning([(1, 2, -1.0), (1, 2, -2.0)])

    def test_glyph_form_classes(self):
        self.assertEqual(glyph_form("\uFEE3"), "INITIAL")
        self.assertEqual(glyph_form("\uFEDC"), "MEDIAL")
        self.assertEqual(glyph_form("\uFE98"), "MEDIAL")
        self.assertEqual(glyph_form("\uFE90"), "FINAL")
        self.assertEqual(glyph_form("\uFE8E"), "FINAL")
        self.assertIsNone(glyph_form("\u0645"))

    def test_closes_zero_gap_join_with_margin(self):
        # render order: previous=FINAL, next=INITIAL. gap = adv_F + x_left - f_right.
        following = glyph(10, "INITIAL", left=-2, advance=20, columns=(0, 5))   # x_left = -2
        previous = glyph(3, "FINAL", left=-1, advance=18, columns=(0, 17))      # f_right = 16
        pairs = joining_kernings([previous, following], overlap=1.0)
        # gap = 18 + (-2) - 16 = 0  ->  adjustment = -(0 + 1) = -1, keyed (prev, next)
        self.assertEqual(pairs, [(3, 10, -1.0)])

    def test_only_valid_adjacent_forms(self):
        # X must be INITIAL/MEDIAL (the joining glyph) and F must be MEDIAL/FINAL.
        both = [glyph(0, "ISOLATED", 0, 18, (0, 4)), glyph(1, "FINAL", 0, 18, (0, 4)),
                glyph(2, "INITIAL", 0, 20, (0, 5)), glyph(3, "FINAL", 0, 20, (0, 5))]
        keys = {(p, n) for p, n, _ in joining_kernings(both, overlap=1.0)}
        self.assertIn((1, 2), keys)          # FINAL -> INITIAL: a join
        self.assertNotIn((0, 2), keys)       # ISOLATED cannot precede a join
        self.assertNotIn((1, 3), keys)       # FINAL cannot follow a join as the joining glyph

    def test_already_overlapping_pair_untouched(self):
        following = glyph(1, "INITIAL", left=0, advance=10, columns=(0, 3))   # x_left = 0
        previous = glyph(0, "MEDIAL", left=0, advance=10, columns=(0, 12))    # f_right = 12
        # gap = 10 + 0 - 12 = -2, already overlapping by 2px > target -> no pair emitted
        self.assertEqual(joining_kernings([previous, following], overlap=1.0), [])


if __name__ == "__main__":
    unittest.main()
