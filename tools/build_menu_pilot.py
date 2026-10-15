"""Build an experimental main-menu patch locally. Never writes installed files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

import arabic_reshaper
from bidi.algorithm import get_display
from fontTools.ttLib import TTFont

from archive_inventory import records, payload
from local_reference import parse_lang
from pilot_font import extend_font


SOURCE_HASHES = {
    "chunk0.resources": "7a76fa93c0f122c556dcf8eeac94630a1d4a657db94c57cc15e41c506735e5b4",
    "chunk0.index": "3aa93b17e2d2167e686758428bdcc84c1895b61f1512a01814f0e62314cba750",
}
IBM_FONT_HASH = "8e0f1046c736bf939d4939ee3ae0116acf61cbcd6592deae7656761627080981"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rebuild(index, archive, changes):
    entries, info = records(index, len(archive))
    if info["trailing_bytes"] or not set(changes) <= {r["ordinal"] for r in entries}:
        raise ValueError("Unexpected index or unknown replacement")
    result_index, result_archive = bytearray(index), bytearray(archive)
    changed_fields = set()
    for entry in entries:
        replacement = changes.get(entry["ordinal"])
        if replacement is None:
            continue
        # No-op replacements preserve the complete original pair byte-for-byte.
        import io
        if payload(io.BytesIO(archive), entry) == replacement:
            continue
        result_archive += bytes((-len(result_archive)) % 16)
        offset = len(result_archive)
        result_archive += replacement
        pos = entry["metadata_offset"]
        struct.pack_into(">III", result_index, pos, offset, len(replacement), len(replacement))
        changed_fields.update(range(pos, pos + 12))
    assert result_archive[:len(archive)] == archive
    assert all(a == b or i in changed_fields for i, (a, b) in enumerate(zip(index, result_index)))
    updated, _ = records(result_index, len(result_archive))
    import io
    for old, new in zip(entries, updated):
        if old["ordinal"] in changes:
            assert payload(io.BytesIO(result_archive), new) == changes[old["ordinal"]]
        else:
            assert old == new
    return bytes(result_index), bytes(result_archive)


def translate_table(raw, translations, mapping):
    rows = parse_lang(raw)
    by_id = {row["id"]: row for row in rows}
    replacements = {}
    for record in translations:
        source = by_id[record["id"]]
        if source["english_sha256"] != record["english_sha256"]:
            raise ValueError("English source hash mismatch")
        # shortcut: this pilot accepts only plain strings; add measured token grammar before expanding.
        if any(c in source["english"] for c in ('%', '{', '}', '<', '>', '\n', '\\')) or "_menu" in source["english"]:
            raise ValueError("Formatted source outside plain-menu pilot scope")
        visual = get_display(arabic_reshaper.reshape(record["arabic"]))
        encoded = "".join(chr(mapping[c]) if c in mapping else c for c in visual)
        replacements[source["source_key"]] = encoded
    text = raw.decode("utf-8-sig")
    pattern = re.compile(r'("(#str_[^"\\]+)"\s*")((?:[^"\\]|\\["n])*)(")')
    changed = set()
    def replace(match):
        key = match[2]
        if key not in replacements:
            return match[0]
        changed.add(key)
        return match[1] + replacements[key] + match[4]
    output = pattern.sub(replace, text)
    if changed != set(replacements):
        raise ValueError("Not all translations were serialized")
    encoded = b"\xef\xbb\xbf" + output.encode("utf-8")
    result = parse_lang(encoded)
    for old, new in zip(rows, result):
        if old["source_key"] not in replacements:
            assert old == new
        else:
            assert new["english"] == replacements[old["source_key"]]
    return encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("workspace/menu_pilot"))
    args = parser.parse_args()
    game = args.game.resolve(strict=True)
    out = args.output.resolve()
    if out == game or game in out.parents:
        parser.error("Build output must be outside the game")
    originals = {name: (game / "base" / name).read_bytes() for name in SOURCE_HASHES}
    if any(sha(raw) != SOURCE_HASHES[name] for name, raw in originals.items()):
        parser.error("Unsupported or already modified source archives")
    if sha(args.font.read_bytes()) != IBM_FONT_HASH:
        parser.error("Unexpected IBM font revision")
    translations = json.loads(Path("translation/arabic/main_menu.json").read_text(encoding="utf-8"))
    if len({row["id"] for row in translations}) != len(translations):
        parser.error("Duplicate translation IDs")
    visual = "".join(get_display(arabic_reshaper.reshape(r["arabic"])) for r in translations)
    characters = sorted(set(c for c in visual if ord(c) > 127))
    font = TTFont(args.font)
    if any(ord(c) not in font.getBestCmap() for c in characters):
        parser.error("IBM font is missing a required glyph")
    mapping = {c: 0xE000 + i for i, c in enumerate(characters)}
    index, archive = originals["chunk0.index"], originals["chunk0.resources"]
    entries, _ = records(index, len(archive))
    by_path = {e["names"][2]: e for e in entries}
    import io
    source = io.BytesIO(archive)
    lang_entry = by_path["strings/english.lang"]
    changes = {lang_entry["ordinal"]: translate_table(payload(source, lang_entry), translations, mapping)}
    fonts_changed = []
    for name in ("futura_com_book", "futura_com_medium", "arial_black", "courier"):
        metrics = by_path[f"fonts/{name}/64_df.dat"]
        image_name = f"generated/textures/borderclamp_alpha_fonts/{name}/64_df.bimage"
        image = by_path[image_name]
        new_metrics, new_image = extend_font(payload(source, metrics), payload(source, image), args.font, mapping)
        changes[metrics["ordinal"]] = new_metrics
        changes[image["ordinal"]] = new_image
        fonts_changed.append(name)
    # Prove both byte-identical no-op and deterministic changed builds before installation.
    assert rebuild(index, archive, {}) == (index, archive)
    built_index, built_archive = rebuild(index, archive, changes)
    assert rebuild(index, archive, changes) == (built_index, built_archive)
    assert rebuild(built_index, built_archive, changes) == (built_index, built_archive)
    out.mkdir(parents=True, exist_ok=True)
    outputs = {"chunk0.index": built_index, "chunk0.resources": built_archive}
    for name, data in outputs.items():
        (out / name).write_bytes(data)
    (out / "english_runtime.local.lang").write_bytes(changes[lang_entry["ordinal"]])
    manifest = dict(experimental=True, in_game_verified=False, translation_count=len(translations),
                    new_glyph_count=len(mapping), fonts=fonts_changed, source_hashes=SOURCE_HASHES,
                    output_hashes={n: sha(b) for n, b in outputs.items()},
                    font_sha256=IBM_FONT_HASH, mapping={f"U+{ord(c):04X}": f"U+{v:04X}" for c, v in mapping.items()},
                    changed_resources=[e["names"][2] for e in entries if e["ordinal"] in changes],
                    strategy="pre-shaped visual Arabic mapped to appended PUA glyphs; runtime behavior unverified")
    (out / "BUILD_INFO.local.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("translation_count", "new_glyph_count", "output_hashes", "changed_resources")}, indent=2))


if __name__ == "__main__":
    main()
