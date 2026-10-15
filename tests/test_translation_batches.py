import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from apply_translation_batch import validate


class BatchTests(unittest.TestCase):
    def source(self, text):
        return dict(id="synthetic", english=text, english_sha256=hashlib.sha256(text.encode()).hexdigest(), arabic="", status="untranslated")

    def test_tags_placeholders_and_timing_order(self):
        source = self.source("[eng][1.3]Press _use for %d items.[3]")
        translated = dict(source, arabic="[eng][1.3]اضغط _use للحصول على %d عناصر.[3]", status="translated")
        self.assertEqual(validate(source, translated), [])
        self.assertIn("placeholder_or_tag_mismatch", validate(source, dict(translated, arabic=translated["arabic"].replace("%d", "%s"))))
        self.assertIn("timing_or_language_tag_order_changed", validate(source, dict(translated, arabic=translated["arabic"].replace("[1.3]", "[3]").replace("عناصر.[3]", "عناصر.[1.3]"))))

    def test_percent_prose_is_not_a_variable(self):
        source = self.source("100% of all items")
        self.assertEqual(validate(source, dict(source, arabic="100% من جميع العناصر", status="translated")), [])

    def test_exclusions_and_source_immutability(self):
        source = self.source("")
        self.assertEqual(validate(source, dict(source, status="do_not_translate", notes="Empty source")), [])
        self.assertIn("source_field_changed:english", validate(source, dict(source, english="Changed", status="do_not_translate", notes="Empty source")))


if __name__ == "__main__":
    unittest.main()
