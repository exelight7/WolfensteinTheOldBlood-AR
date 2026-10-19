"""Tests protecting the opening-runtime trace decisions."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import formatted_text as ft  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, str(ROOT / "tools"))
import build_opening_poc as bop  # noqa: E402,F401
from build_opening_poc import SCREENSHOT_RECORD, SCREENSHOT_SENTENCE, OPENING_IDS  # noqa: E402


def master():
    return [json.loads(l) for l in
            (ROOT / "reference" / "translation_master.local.jsonl").read_text(encoding="utf-8").splitlines() if l]


class TraceTests(unittest.TestCase):
    def test_screenshot_record_translated_with_exact_sentence(self):
        rows = {r["id"]: r for r in master()}
        row = rows["strings/english.lang:" + SCREENSHOT_RECORD]
        self.assertEqual(row["status"], "translated")
        self.assertIn(SCREENSHOT_SENTENCE, row["english"])
        self.assertTrue(row["arabic"].strip())

    def test_opening_ids_all_translated(self):
        rows = {r["id"].split(":")[-1]: r for r in master()}
        for key in OPENING_IDS:
            self.assertIn(rows[key]["status"], ("translated",), key)

    def test_screenshot_shape_keeps_tags_drops_sentence(self):
        rows = {r["id"].split(":")[-1]: r for r in master()}
        row = rows[SCREENSHOT_RECORD]
        visual = ft.shape_formatted(row["arabic"], {})
        self.assertEqual(visual.count("\n"), row["arabic"].count("\n"))
        tokens = ft.tokens_in(visual)
        for tag in ("[eng]", "[2.4]", "[7.6]", "[10]", "[13.2]"):
            self.assertIn(tag, tokens)
        self.assertNotIn(SCREENSHOT_SENTENCE, visual)


if __name__ == "__main__":
    unittest.main()
