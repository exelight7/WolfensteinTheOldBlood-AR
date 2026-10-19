"""Build the Stage-1 subtitle POC patch locally. Never writes installed files.

Extends the validated 33-record menu pilot into token-aware subtitles:
15 POC records drawn from the translated master corpus, on top of the
33 menu records, all shaped through tools/formatted_text.py and rendered
with the same font/atlas pipeline as build_menu_pilot.py (which stays
untouched as the regression anchor).

Output: workspace/subtitle_poc/ only. Installation is not part of this build.
"""
import hashlib
import io
import json
import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import records, payload  # noqa: E402
from build_menu_pilot import SOURCE_HASHES, IBM_FONT_HASH, rebuild  # noqa: E402
import formatted_text as ft  # noqa: E402
from formatted_text import shape_formatted  # noqa: E402
from local_reference import parse_lang  # noqa: E402
from pilot_font import extend_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "workspace" / "backups" / "menu_pilot_original"
OUT_DIR = ROOT / "workspace" / "subtitle_poc"
FONT_PATH = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"

POC_IDS = [
    "#str_dlg_ps4_autosave_data_not_available",
    "#str_dlg_xbone_autosave_data_not_available",
    "#str_menu_gamemodemenu_2_description",
    "#str_video_dlc1_c05_boatride",
    "#str_video_dlc1_c05_escape",
    "#str_ev_c03_helpagentone_agentone",
    "#str_ev_c04_findnails_kessler",
    "#str_ev_c02_dinner_rudijager",
    "#str_newsarticle_c03p1_2_desc",
    "#str_vo_helga_tape01_markus",
    "#str_ev_c04_drnk_look_villagerjosef",
    "#str_achievement_29_desc",
    "#str_ev_c05_barinslt_officerrolf",
    "#str_menu_videoadv_vt_cuda_transcode_help",
    "#str_achievement_07_desc",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bracket_sequence(text):
    return re.findall(r"\[[^\]\r\n]*\]", text)


def main():
    master = {}
    for line in (ROOT / "reference" / "translation_master.local.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        master[row["source_key"]] = row
    menu = json.loads((ROOT / "translation" / "arabic" / "main_menu.json").read_text(encoding="utf-8"))

    selected = [master[i] for i in POC_IDS]
    for row in selected:
        assert row["status"] == "translated" and row["arabic"], row["id"]
    menu_ids = {r["id"] for r in menu}
    assert not menu_ids & set(POC_IDS), "menu and POC record sets must not overlap"

    originals = {name: (BACKUP_DIR / name).read_bytes() for name in SOURCE_HASHES}
    assert sha(originals["chunk0.index"]) == SOURCE_HASHES["chunk0.index"]
    assert sha(originals["chunk0.resources"]) == SOURCE_HASHES["chunk0.resources"]
    assert sha(FONT_PATH.read_bytes()) == IBM_FONT_HASH

    # Mapping pass 1: collect every non-ASCII visual character across all 48
    # records, then assign deterministic ascending PUA codes.
    all_records = [(row["arabic"], row) for row in menu] + [(row["arabic"], row) for row in selected]
    char_set = set()
    for arabic, _ in all_records:
        blind = shape_formatted(arabic, {})
        char_set.update(c for c in blind if ord(c) > 127)
    characters = sorted(char_set)
    font = TTFont(FONT_PATH)
    cmap = font.getBestCmap()
    missing = [c for c in characters if ord(c) not in cmap]
    assert not missing, "IBM font is missing required glyphs: %r" % "".join(missing)
    mapping = {c: 0xE000 + i for i, c in enumerate(characters)}

    # Mapping pass 2: encode every record deterministically through the PUA map.
    shapes = {}
    pua_max = 0xE000 + len(mapping)
    for arabic, row in all_records:
        visual = shape_formatted(arabic, mapping)
        assert not any(ord(c) > 127 and c not in mapping and not (
            0xE000 <= ord(c) < pua_max) for c in visual), row["id"]
        assert visual.count("\n") == arabic.count("\n"), row["id"]
        if "english" in row:
            assert bracket_sequence(visual) == bracket_sequence(row["english"]), row["id"]
        literal = ft.encode_lang_value(visual)
        assert ft.decode_lang_value(literal) == visual
        assert '"' not in literal.replace('\\"', ""), row["id"]
        shapes[row["id"]] = literal

    replacements = {r["source_key"]: shapes[r["id"]] for r in selected}
    for r in menu:
        # menu rows mirror master keying: bare "#str_key" = path suffix of id
        replacements[r["id"].rsplit(":", 1)[1]] = shapes[r["id"]]
    assert len(replacements) == len(menu) + len(POC_IDS) == 48

    entries, _ = records(originals["chunk0.index"], len(originals["chunk0.resources"]))
    by_path = {e["names"][2]: e for e in entries}
    lang_entry = by_path["strings/english.lang"]
    raw_lang = payload(io.BytesIO(originals["chunk0.resources"]), lang_entry)

    text = raw_lang.decode("utf-8-sig")
    pattern = re.compile(r'("(#str_[^"\\]+)"\s*")((?:[^"\\]|\\["n])*)(")')
    changed = set()

    def replace(match):
        key = match[2]
        if key not in replacements:
            return match[0]
        changed.add(key)
        return match[1] + replacements[key] + match[4]

    output = pattern.sub(replace, text)
    assert changed == set(replacements), "not all translations were serialized"

    encoded = b"\xef\xbb\xbf" + output.encode("utf-8")
    rows = parse_lang(raw_lang)
    new_rows = parse_lang(encoded)
    assert len(rows) == len(new_rows)
    for old, new in zip(rows, new_rows):
        if old["source_key"] in replacements:
            assert new["english"] == ft.decode_lang_value(replacements[old["source_key"]])
        else:
            assert old == new, old["id"]

    source = io.BytesIO(originals["chunk0.resources"])
    changes = {lang_entry["ordinal"]: encoded}
    fonts_changed = []
    for name in ("futura_com_book", "futura_com_medium", "arial_black", "courier"):
        metrics = by_path["fonts/%s/64_df.dat" % name]
        image_name = "generated/textures/borderclamp_alpha_fonts/%s/64_df.bimage" % name
        image = by_path[image_name]
        new_metrics, new_image = extend_font(
            payload(source, metrics), payload(source, image), FONT_PATH, mapping)
        changes[metrics["ordinal"]] = new_metrics
        changes[image["ordinal"]] = new_image
        fonts_changed.append(name)

    assert rebuild(originals["chunk0.index"], originals["chunk0.resources"], {}) == (
        originals["chunk0.index"], originals["chunk0.resources"])
    built_index, built_archive = rebuild(originals["chunk0.index"], originals["chunk0.resources"], changes)
    assert rebuild(originals["chunk0.index"], originals["chunk0.resources"], changes) == (
        built_index, built_archive)
    assert rebuild(built_index, built_archive, changes) == (built_index, built_archive)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {"chunk0.index": built_index, "chunk0.resources": built_archive}
    for name, data in outputs.items():
        (OUT_DIR / name).write_bytes(data)
    (OUT_DIR / "english_runtime.local.lang").write_bytes(encoded)
    manifest = dict(
        stage="subtitle_poc_stage1", in_game_verified=False, installed=False,
        archive_layout="ordered_v1", record_count=len(replacements),
        menu_records=len(translations := menu), poc_records=len(POC_IDS),
        new_glyph_count=len(mapping), fonts=fonts_changed,
        source_hashes=SOURCE_HASHES, font_sha256=IBM_FONT_HASH,
        output_hashes={n: sha(b) for n, b in outputs.items()},
        mapping={("U+%04X" % ord(c)): ("U+%04X" % v) for c, v in mapping.items()},
        flattened_features={
            row["id"]: dict(
                timing_tokens=len(bracket_sequence(row["english"])),
                newlines=row["arabic"].count("\n") + row["arabic"].count("\\n"),
                digits=bool(re.search(r"[0-9]", row["arabic"])),
                latin=bool(re.search(r"[A-Za-z]", row["arabic"])),
                length=len(row["arabic"]))
            for row in selected},
        changed_resources=[e["names"][2] for e in entries if e["ordinal"] in changes],
        strategy=("token-aware formatted stimuli: tokens kept at logical byte "
                  "positions, Arabic segments shaped per token-free segment with "
                  "run composition; static build verified, runtime unverified"))
    (OUT_DIR / "BUILD_INFO.local.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "POC_MANIFEST.local.json").write_text(
        json.dumps({"poc_ids": POC_IDS, "lang_sha256": sha(encoded),
                    "menu_ids": sorted(menu_ids), "translations": shapes},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("record_count", "new_glyph_count", "fonts",
                                               "output_hashes", "changed_resources")}, indent=2))


if __name__ == "__main__":
    main()
