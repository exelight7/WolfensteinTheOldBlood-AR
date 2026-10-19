"""Inspect id Tech 5 / Scaleform SWF resources for player-visible text.

Two families are found in WTOB:
  * swf/*.swf            standard Adobe SWF (FWS = raw, CWS = zlib)
  * generated/swf/*.bswf id "BSW" wrapper (BSW<version> + header + payload)

This tool locates the embedded SWF, decompresses it, and dumps:
  * readable strings (UTF-8 and UTF-16LE), classified
  * references to english.lang (#str_ ids) and other localization ids
  * embedded images / shape glyph data (evidence that text is baked vs. string-ref)

Read-only: extracts into workspace/coverage_hunt/bswf/.
"""
import argparse
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import records, payload  # noqa: E402

if "WTOB_GAME_DIR" not in os.environ:
    raise SystemExit("Set WTOB_GAME_DIR to the Wolfenstein: The Old Blood directory")
GAME = Path(os.environ["WTOB_GAME_DIR"]) / "base"
OUT = ROOT / "workspace" / "coverage_hunt" / "bswf"

STR8 = re.compile(rb"[\x20-\x7e]{4,}")
STR16 = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")
STRID = re.compile(rb"#str_[A-Za-z0-9_]+")


def find_swf(data):
    """Return (signature, offset, decompressed_swf_bytes) for a BSW/SWF payload."""
    for sig in (b"FWS", b"CWS", b"ZWS"):
        pos = data.find(sig)
        if pos >= 0:
            return sig.decode(), pos, decompress_swf(data[pos:])
    return None, None, None


def decompress_swf(blob):
    if blob[:3] == b"FWS":
        return blob
    if blob[:3] == b"CWS":
        return b"FWS" + blob[3:8] + zlib.decompress(blob[8:])
    return blob


def strings_of(blob):
    out8 = []
    for m in STR8.finditer(blob):
        out8.append(m.group().decode("latin-1"))
    out16 = []
    for m in STR16.finditer(blob):
        out16.append(m.group().decode("utf-16-le", "replace"))
    return out8, out16


def classify_visible(s):
    """Rough player-visible filter: has a word of >=3 latin letters, not a path/asset."""
    if re.match(r"^(?:[a-z0-9_]+/)+", s):
        return False
    if re.search(r"\.(swf|bswf|decl|tga|dds|bimage|png|lang|txt|cfg|dat|bin)$", s, re.I):
        return False
    if re.search(r"[A-Za-z]{3,}", s) and " " not in s and "_" in s and s.islower():
        return False
    return bool(re.search(r"[A-Za-z]{3,}", s))


def inspect(name, data):
    sig, off, swf = find_swf(data)
    str8, str16 = strings_of(swf if swf else data)
    ids = sorted(set(m.group().decode("latin-1") for m in STRID.finditer(swf if swf else data)))
    visible = sorted({s for s in str8 + str16 if classify_visible(s)})
    return dict(
        name=name, size=len(data), swf_signature=sig, swf_offset=off,
        swf_size=(len(swf) if swf else None),
        string_count_utf8=len(str8), string_count_utf16=len(str16),
        localization_ids=ids,
        visible_candidate_strings=visible[:400],
        visible_candidate_count=len(visible),
        has_shapes=b"\x0b\x00" in (swf or b""),  # SWF DefineShape tag id (11) LE16
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=GAME)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    (args.out).mkdir(parents=True, exist_ok=True)
    report = []
    for index in sorted(args.game.glob("chunk*.index")):
        entries, _ = records(index.read_bytes(), index.with_suffix(".resources").stat().st_size)
        with index.with_suffix(".resources").open("rb") as stream:
            for entry in entries:
                name = entry["names"][2]
                if not name.lower().endswith((".bswf", ".swf")):
                    continue
                try:
                    data = payload(stream, entry)
                except Exception as exc:  # noqa: BLE001
                    report.append(dict(name=name, chunk=index.stem, error=str(exc)))
                    continue
                (args.out / f"{index.stem}_{entry['ordinal']:06d}_{Path(name).name}").write_bytes(data)
                report.append(dict(chunk=index.stem, ordinal=entry["ordinal"], **inspect(name, data)))
    (args.out / "BSWF_REPORT.local.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("files:", len(report))
    for item in report:
        print("%-46s sig=%s ids=%d visible=%d" % (
            item.get("name"), item.get("swf_signature"),
            len(item.get("localization_ids", [])), item.get("visible_candidate_count", 0)))


if __name__ == "__main__":
    main()
