from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from extract_dialogue import category, export, referenced_ids


class DialogueTests(unittest.TestCase):
    def row(self, key, text="Synthetic dialogue"):
        return dict(id="strings/english.lang:" + key, source_key=key, index=0,
                    english=text, english_literal=text, arabic="", status="untranslated")

    def test_dialogue_excludes_ui_and_cutscene_titlecards(self):
        self.assertEqual(category(self.row("#str_vo_bj_dlc1_c01_001"), []), "story_dialogue")
        self.assertEqual(category(self.row("#str_officerhans_ai_idle_01"), []), "combat_chatter")
        self.assertEqual(category(self.row("#str_video_dlc1_c01_intro"), []), "cutscene_dialogue")
        self.assertIsNone(category(self.row("#str_video_dlc1_c01_intro_location1_title"), []))
        self.assertIsNone(category(self.row("#str_menu_main_new"), []))
        self.assertIsNone(category(self.row("#str_dlg_confirm"), []))

    def test_binary_length_prevents_false_key_suffixes(self):
        key = b"#str_vo_demo_c01_001"
        data = b"#VTR" + len(key).to_bytes(4, "little") + key + b"7"
        self.assertEqual(referenced_ids(data), {key.decode()})
        self.assertIsNone(category(self.row("#str_npcname_agentone"), [{"resource": "test"}]))

    def test_preserves_tags_duplicates_and_empty_source(self):
        rows = [self.row("#str_vo_bj_dlc1_c01_001", "[eng][1.5]Synthetic line.[3]"),
                self.row("#str_vo_bj_dlc1_c01_002", "[eng][1.5]Synthetic line.[3]"),
                self.row("#str_video_dlc1_c07_enterpl", "")]
        with tempfile.TemporaryDirectory() as temp:
            summary = export(rows, {}, Path(temp), {})
            self.assertEqual(summary["dialogue_entries"], 3)
            self.assertEqual(summary["entries_with_text"], 2)
            text = (Path(temp) / "ALL_DIALOGUE.local.md").read_text(encoding="utf-8")
            self.assertEqual(text.count("[eng][1.5]Synthetic line.[3]"), 2)
            self.assertLess(text.index("AR:"), text.index("EN:"))


if __name__ == "__main__":
    unittest.main()
