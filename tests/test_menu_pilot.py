import io
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from archive_inventory import records, payload
from build_menu_pilot import rebuild, translate_table
from local_reference import parse_lang
from pilot_font import inspect_font, inspect_image


class PilotTests(unittest.TestCase):
    def pair(self):
        names = b"".join(struct.pack("<I", len(n)) + n for n in (b"file", b"test", b"test"))
        index = bytes(0x24) + struct.pack(">II", 1, 0) + names + struct.pack(">IIII", 0, 3, 3, 0) + bytes(5)
        return index, b"abc"

    def test_rebuild_preserves_original_and_is_idempotent(self):
        index, archive = self.pair()
        self.assertEqual(rebuild(index, archive, {}), (index, archive))
        self.assertEqual(rebuild(index, archive, {0: b"abc"}), (index, archive))
        new_index, new_archive = rebuild(index, archive, {0: b"replacement"})
        entries, _ = records(new_index, len(new_archive))
        self.assertEqual(payload(io.BytesIO(new_archive), entries[0]), b"replacement")
        self.assertEqual(rebuild(new_index, new_archive, {0: b"replacement"}), (new_index, new_archive))
        with self.assertRaises(ValueError):
            rebuild(index, archive, {999: b"bad"})

    def test_middle_replacement_preserves_streaming_order(self):
        header = bytes(0x24) + struct.pack(">II", 3, 0)
        records_data = []
        for i, offset in enumerate((16, 32, 48)):
            names = b"".join(struct.pack("<I", len(n)) + n for n in (b"file", b"item", str(i).encode()))
            records_data.append(names + struct.pack(">IIII", offset, 3, 3, 0) + bytes(5))
        index = header + bytes(4).join(records_data)
        archive = bytes(16) + b"one" + bytes(13) + b"two" + bytes(13) + b"end"
        replacement = b"middle resource grew substantially"
        new_index, new_archive = rebuild(index, archive, {1: replacement})
        entries, _ = records(new_index, len(new_archive))
        self.assertEqual([e["offset"] for e in entries], sorted(e["offset"] for e in entries))
        self.assertEqual(payload(io.BytesIO(new_archive), entries[0]), b"one")
        self.assertEqual(payload(io.BytesIO(new_archive), entries[1]), replacement)
        self.assertEqual(payload(io.BytesIO(new_archive), entries[2]), b"end")
        self.assertEqual(rebuild(index, archive, {}), (index, archive))
        self.assertEqual(rebuild(new_index, new_archive, {1: replacement}), (new_index, new_archive))

    def test_table_replacement_and_source_hash_gate(self):
        source = b'\xef\xbb\xbf{\r\n "#str_a" "Synthetic menu"\r\n "#str_b" "Keep me"\r\n}\r\n'
        row = parse_lang(source)[0]
        translation = dict(id=row["id"], english_sha256=row["english_sha256"], arabic="لعبة جديدة")
        output = translate_table(source, [translation], {})
        self.assertEqual(parse_lang(output)[1], parse_lang(source)[1])
        self.assertTrue(output.endswith(b"}\r\n"))
        with self.assertRaises(ValueError):
            translate_table(source, [dict(translation, english_sha256="bad")], {})

    def test_font_and_atlas_reject_corruption(self):
        metrics = b"idf+" + struct.pack(">hhhH", 64, 60, -15, 1) + bytes(12) + struct.pack("<I", 65) + bytes(2)
        self.assertEqual(inspect_font(metrics)[1], [65])
        with self.assertRaises(ValueError):
            inspect_font(metrics[:-1])
        header = [0] * 18
        header[1], header[3], header[4], header[6], header[8] = 0x094D4942, 2, 2, 1, 5
        header[15:18] = [2, 2, 4]
        data = struct.pack(">18I", *header) + bytes(4)
        self.assertEqual(inspect_image(data)[1].size, (2, 2))
        with self.assertRaises(ValueError):
            inspect_image(data[:-1])


if __name__ == "__main__":
    unittest.main()
