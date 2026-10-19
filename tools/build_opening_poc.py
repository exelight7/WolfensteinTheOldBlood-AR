"""Build the opening-runtime POC: true first-10-minutes content. Not installed.

Selection is driven by the runtime trace of the owner's screenshot line
("#str_vo_agentone_dlc1_c01_123") and the opening sequence:
  - pre-rendered intro cutscene subtitle track (#str_video_dlc1_c01_intro)
  - the four overlay cards (str_introcard family; the duplicate
    str_video_dlc1_c01_intro_location_* family is deliberately excluded —
    if English location cards still appear at runtime, that reveals which
    family the engine actually reads)
  - the cell briefing (screenshot line and its two neighbours + opener)
  - the first in-engine car-ride dialogue lines

Reuses the proven pipeline: formatted_text shaping, pilot_font glyph
extension, ordered archive rebuild from the verified original backups.
Output: workspace/opening_runtime_poc/ only.
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
OUT_DIR = ROOT / "workspace" / "opening_runtime_poc"
FONT_PATH = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"

SCREENSHOT_RECORD = "#str_vo_agentone_dlc1_c01_123"
SCREENSHOT_SENTENCE = (
    "is keeping the folder mentioned in your mission briefing "
    "at her base of operations --")

# Candidate C diagnostic set (stage *_v3): multi-span RTL records whose
# visible text is emitted in span-order-corrected visual order. #124 (single
# span) and carride012 (single span) stay on the current algorithm as
# controls. Only #123 and #123_1 are corrected so the owner can compare a
# corrected line (#123) directly against an uncorrected one (#123_1 / #124).
SPAN_ORDER_CORRECTED_IDS = [
    "#str_vo_agentone_dlc1_c01_123",
    "#str_vo_agentone_dlc1_c01_123_1",
]

OPENING_IDS = [
    "#str_video_dlc1_c01_intro",
    "#str_introcard_top",
    "#str_introcard_center",
    "#str_introcard2_top",
    "#str_introcard2_center",
    "#str_introcard3_top",
    "#str_introcard3_center",
    "#str_introcard4_top",
    "#str_introcard4_center",
    SCREENSHOT_RECORD,
    "#str_vo_agentone_dlc1_c01_123_1",
    "#str_vo_agentone_dlc1_c01_124",
    "#str_vo_agentone_dlc1_c01_001",
    "#str_ev_c01_carride012_agentone",
    "#str_ev_c01_carride013_agentone",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bracket_sequence(text):
    return re.findall(r"\[[^\]\r\n]*\]", text)


def token_debug_for(record_key, arabic, english, mapping):
    """Diagnostics for the transparency pipeline on one record."""
    diagnostics = []
    import arabic_reshaper
    from bidi.algorithm import get_display
    # A: all invisible tokens removed
    stripped = ft.TOKEN_RE.sub("", arabic)
    shaped_a = shape_formatted(stripped, {})
    # B: token-aware pipeline
    shaped_b = shape_formatted(arabic, {})
    b_stripped = ft.TOKEN_RE.sub("", shaped_b)
    spans = []
    cursor = 0
    for m in ft.TOKEN_RE.finditer(arabic):
        TokClass = ("TRANSPARENT_JOIN"
                    if ft._transparent_gap([m.group(0)])
                    else "LINE_BOUNDARY" if m.group(0) == "\n" else "VISIBLE_LTR")
        spans.append(dict(token=m.group(0), byte_offset=m.start(), classification=TokClass,
                          left_text=arabic[cursor:m.start()]))
        cursor = m.end()
    spans.append(dict(token=None, byte_offset=len(arabic), left_text=arabic[cursor:]))
    return dict(
        record=record_key,
        logical_arabic_chars=len(arabic),
        tokens=spans,
        token_classes={
            "TRANSPARENT_JOIN": "[timing]/[lang]/^colour (engine-scanned bytes, never drawn)",
            "VISIBLE_LTR": "%spec, <JOYn>, {n}, _id, $var (visible Latin islands)",
            "HARD_BOUNDARY": "\\n newline",
        },
        shape_with_all_tokens_removed=shaped_a,
        shape_token_aware=shaped_b,
        token_aware_with_tokens_stripped=b_stripped,
        glyph_multiset_matches_form_only_equivalence=(
            sorted(ord(c) for c in b_stripped if ord(c) > 127) ==
            sorted(ord(c) for c in shaped_a if ord(c) > 127)),
        zwj_leak=ft.ZWJ in shaped_b,
        pua_mapping_size=len(mapping),
        reshaper=arabic_reshaper.__version__ if hasattr(arabic_reshaper, "__version__") else "default",
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None,
                        help="output directory (default workspace/opening_runtime_poc)")
    parser.add_argument("--stage", default=None,
                        help="manifest stage name (default opening_runtime_poc; "
                             "opening_runtime_poc_v2 for the transparency build)")
    args = parser.parse_args()
    out_dir = args.out or OUT_DIR
    stage = args.stage or "opening_runtime_poc"
    write_token_debug = stage.endswith("_v2")
    use_span_order = stage.endswith("_v3") or stage.endswith("_v4")
    use_join_fix = stage.endswith("_v4")
    master = {}
    for line in (ROOT / "reference" / "translation_master.local.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        master[row["source_key"]] = row
    menu = json.loads((ROOT / "translation" / "arabic" / "main_menu.json").read_text(encoding="utf-8"))

    selected = []
    for key in OPENING_IDS:
        row = master[key]
        if row["status"] != "translated" or not row["arabic"]:
            raise SystemExit("Record lacks a completed Arabic translation: %s" % key)
        selected.append(row)
    assert SCREENSHOT_RECORD in OPENING_IDS
    target = master[SCREENSHOT_RECORD]
    assert SCREENSHOT_SENTENCE in target["english"], "screenshot sentence vanished from master"

    menu_ids = {r["id"] for r in menu}
    assert not menu_ids & set(OPENING_IDS), "menu and opening record sets must not overlap"

    originals = {name: (BACKUP_DIR / name).read_bytes() for name in SOURCE_HASHES}
    assert sha(originals["chunk0.index"]) == SOURCE_HASHES["chunk0.index"]
    assert sha(originals["chunk0.resources"]) == SOURCE_HASHES["chunk0.resources"]
    assert sha(FONT_PATH.read_bytes()) == IBM_FONT_HASH

    all_records = [(r["arabic"], r) for r in menu] + [(r["arabic"], r) for r in selected]
    char_set = set()
    for arabic, _ in all_records:
        blind = shape_formatted(arabic, {})
        char_set.update(c for c in blind if ord(c) > 127)
    characters = sorted(char_set)
    cmap = TTFont(FONT_PATH).getBestCmap()
    missing = [c for c in characters if ord(c) not in cmap]
    assert not missing, "IBM font is missing required glyphs: %r" % "".join(missing)
    mapping = {c: 0xE000 + i for i, c in enumerate(characters)}

    shapes = {}
    pua_max = 0xE000 + len(mapping)
    span_corrected_applied = []
    for arabic, row in all_records:
        key = row.get("source_key", "")
        if use_span_order and key in SPAN_ORDER_CORRECTED_IDS:
            visual = ft.shape_formatted_ordered(arabic, mapping)
            span_corrected_applied.append(key)
        else:
            visual = shape_formatted(arabic, mapping)
        assert not any(ord(c) > 127 and c not in mapping and not (
            0xE000 <= ord(c) < pua_max) for c in visual), row["id"]
        assert visual.count("\n") == arabic.count("\n"), row["id"]
        if "english" in row:
            assert bracket_sequence(visual) == bracket_sequence(row["english"]), row["id"]
        literal = ft.encode_lang_value(visual)
        assert ft.decode_lang_value(literal) == visual
        shapes[row["id"]] = literal

    replacements = {r["source_key"]: shapes[r["id"]] for r in selected}
    for r in menu:
        replacements[r["id"].rsplit(":", 1)[1]] = shapes[r["id"]]
    assert len(replacements) == len(menu) + len(OPENING_IDS) == 48

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
    assert len(rows) == len(new_rows) == 3572
    for old, new in zip(rows, new_rows):
        if old["source_key"] in replacements:
            assert new["english"] == ft.decode_lang_value(replacements[old["source_key"]])
        else:
            assert old == new, old["id"]

    source = io.BytesIO(originals["chunk0.resources"])
    changes = {lang_entry["ordinal"]: encoded}
    fonts_changed = []
    join_fix_pairs = 0
    for name in ("futura_com_book", "futura_com_medium", "arial_black", "courier"):
        metrics = by_path["fonts/%s/64_df.dat" % name]
        image_name = "generated/textures/borderclamp_alpha_fonts/%s/64_df.bimage" % name
        image = by_path[image_name]
        raw_metrics = payload(source, metrics)
        new_metrics, new_image = extend_font(
            raw_metrics, payload(source, image), FONT_PATH, mapping,
            joining_kern=use_join_fix)
        if use_join_fix:
            from pilot_font import parse_kerning
            join_fix_pairs = len(parse_kerning(new_metrics)) - len(parse_kerning(raw_metrics))
        changes[metrics["ordinal"]] = new_metrics
        changes[image["ordinal"]] = new_image
        fonts_changed.append(name)

    assert rebuild(originals["chunk0.index"], originals["chunk0.resources"], {}) == (
        originals["chunk0.index"], originals["chunk0.resources"])
    built_index, built_archive = rebuild(originals["chunk0.index"], originals["chunk0.resources"], changes)
    assert rebuild(originals["chunk0.index"], originals["chunk0.resources"], changes) == (
        built_index, built_archive)
    assert rebuild(built_index, built_archive, changes) == (built_index, built_archive)

    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {"chunk0.index": built_index, "chunk0.resources": built_archive}
    for name, data in outputs.items():
        (out_dir / name).write_bytes(data)
    (out_dir / "english_runtime.local.lang").write_bytes(encoded)
    debug = {}
    if write_token_debug:
        debug[SCREENSHOT_RECORD] = token_debug_for(SCREENSHOT_RECORD, target["arabic"], target["english"], mapping)
        v1_values = {r["source_key"]: r["english"] for r in parse_lang(
            (ROOT / "workspace" / "opening_runtime_poc" / "english_runtime.local.lang").read_bytes())
            if r["source_key"].startswith("#str_")}
        v2_values = {r["source_key"]: r["english"] for r in parse_lang(encoded)}
        all_ids = ([row["source_key"] for row in selected] +
                   [r["id"].rsplit(":", 1)[1] for r in menu])
        rows_equal = {key: v1_values.get(key) == v2_values[key]
                      for key in v2_values if key in v1_values and key in all_ids}
        debug["v1_vs_v2_rows_identical"] = rows_equal
        debug["v1_vs_v2_summary"] = {
            "rows": len(rows_equal), "identical": sum(rows_equal.values()),
            "different": [key for key, ok in rows_equal.items() if not ok]}
        (out_dir / "TOKEN_DEBUG.local.json").write_text(
            json.dumps(debug, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if use_span_order:
        span_debug = {}
        for key in SPAN_ORDER_CORRECTED_IDS:
            arabic = master[key]["arabic"]
            span_debug[key] = dict(
                logical_arabic=arabic,
                tokens=ft.tokens_in(arabic),
                spans=[p for k, p in ft._shape_line_spans(arabic) if k == "text"],
                model_A_current_visual=shape_formatted(arabic, {}),
                model_C_span_ordered_visual=ft.shape_formatted_ordered(arabic, {}),
                span_order_corrected=True,
            )
        (out_dir / "SPAN_ORDER_DEBUG.local.json").write_text(
            json.dumps(span_debug, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = dict(
        stage=stage, in_game_verified=False, installed=False,
        archive_layout="ordered_v1", record_count=len(replacements),
        menu_records=len(menu), opening_records=len(OPENING_IDS),
        screenshot_record=SCREENSHOT_RECORD,
        new_glyph_count=len(mapping), fonts=fonts_changed,
        source_hashes=SOURCE_HASHES, font_sha256=IBM_FONT_HASH,
        output_hashes={n: sha(b) for n, b in outputs.items()},
        mapping={("U+%04X" % ord(c)): ("U+%04X" % v) for c, v in mapping.items()},
        excluded_duplicate_family=[
            "strings/english.lang:%s" % k for k in master
            if k.startswith("#str_video_dlc1_c01_intro_location") and k != "#str_video_dlc1_c01_intro_location_info"],
        excluded_records_note=(
            "str_video_dlc1_c01_intro_location_* is a textual duplicate of the "
            "str_introcard_* family; excluded to keep coverage within budget. If "
            "the cutscene still shows English cards, the engine reads the "
            "location_* family and that family must be added next build."),
        opening_ids=OPENING_IDS,
        span_order_corrected_ids=(SPAN_ORDER_CORRECTED_IDS if use_span_order else []),
        span_order_corrected_applied=span_corrected_applied,
        joining_kern_pairs=(join_fix_pairs if use_join_fix else 0),
        changed_resources=[e["names"][2] for e in entries if e["ordinal"] in changes],
        strategy=("true first-10-minutes reachability POC: intro cutscene track, "
                  "overlay cards, cell briefing (screenshot line), first car-ride "
                  "dialogue; tokens kept in logical byte order; static build "
                  "verified, runtime unverified"))
    (out_dir / "BUILD_INFO.local.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "OPENING_MANIFEST.local.json").write_text(
        json.dumps({"opening_ids": OPENING_IDS, "lang_sha256": sha(encoded),
                    "menu_ids": sorted(menu_ids), "translations": shapes,
                    "screenshot_sentence": SCREENSHOT_SENTENCE},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("record_count", "new_glyph_count", "fonts",
                                               "output_hashes", "changed_resources")}, indent=2))


if __name__ == "__main__":
    main()
