import io
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bimage_codec as bc  # noqa: E402
from archive_inventory import records, payload  # noqa: E402

BASE = ROOT / "workspace" / "runtime_full"
BUILD = ROOT / "workspace" / "runtime_complete"
IMG = ROOT / "workspace" / "coverage_hunt" / "images" / "wtob_photosensitivity_row.bimage"
ENIGMA = ["#str_menu_enigma_crack_it", "#str_menu_enigma_tab0", "#str_menu_enigma_tab1",
          "#str_menu_enigma_tab2", "#str_menu_enigma_tab3", "#str_menu_enigma_you_cracked_it"]


class BimageCodecTest(unittest.TestCase):
    def test_noop_rebuild_is_byte_identical(self):
        self.assertTrue(IMG.exists(), "run tools/build_photosensitivity.py first")
        blob = IMG.read_bytes()
        hdr = bc.read_header(blob)
        rgba = bc.decode(blob[0x48:], hdr["width"], hdr["height"], hdr["fmt"])
        mask = np.zeros((hdr["height"], hdr["width"]), bool)
        self.assertEqual(bc.rebuild(blob, rgba, mask), blob)

    def test_rebuild_preserves_header_and_size(self):
        blob = IMG.read_bytes()
        hdr = bc.read_header(blob)
        rgba = bc.decode(blob[0x48:], hdr["width"], hdr["height"], hdr["fmt"])
        mask = np.zeros((hdr["height"], hdr["width"]), bool)
        mask[960:, :] = True
        out = bc.rebuild(blob, rgba, mask)
        self.assertEqual(len(out), len(blob))
        self.assertEqual(out[:0x48], blob[:0x48])


class RuntimeCompleteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (BUILD / "chunk0.index").exists():
            raise unittest.SkipTest("runtime_complete not built")
        cls.base = ((BASE / "chunk0.index").read_bytes(),
                    (BASE / "chunk0.resources").read_bytes())
        cls.build = ((BUILD / "chunk0.index").read_bytes(),
                     (BUILD / "chunk0.resources").read_bytes())
        cls.ebase, _ = records(cls.base[0], len(cls.base[1]))
        cls.ebuild, _ = records(cls.build[0], len(cls.build[1]))

    def test_only_two_resources_changed(self):
        lang, img = 22456, 19434
        changed = []
        with io.BytesIO(self.base[1]) as s0, io.BytesIO(self.build[1]) as s1:
            for eb, en in zip(self.ebase, self.ebuild):
                if eb["ordinal"] in (lang, img):
                    continue
                if payload(s0, eb) != payload(s1, en):
                    changed.append(en["ordinal"])
        self.assertEqual(changed, [])

    def test_enigma_keys_and_row_count(self):
        lang = payload(io.BytesIO(self.build[1]), self.ebuild[22456]).decode("utf-8-sig")
        rows = [l for l in lang.splitlines() if l.lstrip().startswith('"#str_')]
        self.assertEqual(len(rows), 3578)
        import re
        keys = set(re.findall(r'"(#str_[A-Za-z0-9_]+)"', lang))
        for k in ENIGMA:
            self.assertIn(k, keys)

    def test_image_changed_only_in_bottom_region(self):
        b = payload(io.BytesIO(self.base[1]), self.ebase[19434])
        n = payload(io.BytesIO(self.build[1]), self.ebuild[19434])
        hdr = bc.read_header(b)
        ra = bc.decode(b[0x48:], hdr["width"], hdr["height"], hdr["fmt"])
        rb = bc.decode(n[0x48:], hdr["width"], hdr["height"], hdr["fmt"])
        diff = np.abs(ra.astype(int) - rb.astype(int)).sum(axis=2) > 0
        rows = np.where(diff.any(axis=1))[0]
        self.assertGreater(len(rows), 0)
        self.assertGreaterEqual(int(rows.min()), 940)


if __name__ == "__main__":
    unittest.main()
