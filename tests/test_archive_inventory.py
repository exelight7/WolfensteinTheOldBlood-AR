import io
import struct
import unittest
import zlib
from tools.archive_inventory import records, payload


class ArchiveTests(unittest.TestCase):
    def fixture(self, offset=0, stored=3):
        names = b"".join(struct.pack("<I", len(n)) + n for n in (b"type", b"path", b"name"))
        return bytes(0x24) + struct.pack(">II", 1, 0) + names + struct.pack(">IIII", offset, 3, stored, 0) + bytes(5)

    def test_index_and_bounds(self):
        entries, info = records(self.fixture(), 3)
        self.assertEqual(info["trailing_bytes"], 0)
        self.assertEqual(payload(io.BytesIO(b"abc"), entries[0]), b"abc")
        with self.assertRaises(ValueError):
            records(self.fixture(offset=1), 3)
        with self.assertRaises(ValueError):
            records(self.fixture()[:-1], 3)

    def test_sync_flush_boundary(self):
        source = b"synthetic font " * 30
        compressor = zlib.compressobj(wbits=-15)
        encoded = compressor.compress(source) + compressor.flush(zlib.Z_SYNC_FLUSH)
        record = dict(offset=0, size=len(source), stored=len(encoded))
        self.assertEqual(payload(io.BytesIO(encoded), record), source)
        with self.assertRaises(ValueError):
            payload(io.BytesIO(encoded[:-1]), dict(record, stored=len(encoded) - 1))

    def test_strict_deflate(self):
        source = b"synthetic resource " * 30
        compressor = zlib.compressobj(wbits=-15)
        encoded = compressor.compress(source) + compressor.flush()
        record = dict(offset=0, size=len(source), stored=len(encoded))
        self.assertEqual(payload(io.BytesIO(encoded), record), source)
        for broken in (encoded[:-1], encoded + b"trailer"):
            with self.assertRaises(ValueError):
                payload(io.BytesIO(broken), dict(record, stored=len(broken)))


if __name__ == "__main__":
    unittest.main()
