"""Build the 100% confirmed Arabic text corpus runtime patch (phase 100).

Scope: the *fixed confirmed electronic-text corpus* only:
  * strings/english.lang          (3572 records: 3374 translated + 198 do-not-translate)
  * base/graphicsdriverwarningloc.json (2 loose records, both translated)
  => 3574 records total = 3376 translated + 198 do-not-translate.

This is NOT "100% of every player-visible asset": BSWF/menu textures, image
textures, Bink video and native engine messages are explicitly out of scope and
stay UNCERTIFIED.

Pipeline (frozen, no redesign):
  * formatted_text.shape_formatted_ordered  (Candidate C, applied uniformly; it
    falls back to shape_line when a span carries a Latin island or an unsafe
    joining gap crosses a transparent token)
  * pilot_font.extend_font(..., joining_kern=True)  (append-only SDF glyphs +
    generated Arabic joining kerning)
  * build_menu_pilot.rebuild  (ordered, streaming-safe archive rewrite from the
    untouched vanilla backups)

Regression invariants vs the installed Opening Runtime POC V4:
  * the V4 PUA mapping (U+E000..U+E061) is preserved exactly as a prefix; new
    visual characters are appended after it, so V4 glyph records, atlas region
    and the 1428 V4 joining pairs remain a byte-identical subset.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from archive_inventory import records, payload  # noqa: E402
from build_menu_pilot import SOURCE_HASHES, IBM_FONT_HASH, rebuild  # noqa: E402
import formatted_text as ft  # noqa: E402
from local_reference import parse_lang  # noqa: E402
from pilot_font import (extend_font, parse_kerning, inspect_font,  # noqa: E402
                        glyph_bitmap, glyph_form, joining_kernings)

BACKUP_DIR = ROOT / "workspace" / "backups" / "menu_pilot_original"
FONT_PATH = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"
V4_INFO = ROOT / "workspace" / "opening_runtime_poc_v4" / "BUILD_INFO.local.json"
DEFAULT_GAME = Path(os.environ["WTOB_GAME_DIR"]) if "WTOB_GAME_DIR" in os.environ else None
LOOSE_RESOURCE = "base/graphicsdriverwarningloc.json"
FONTS = ("futura_com_book", "futura_com_medium", "arial_black", "courier")

PHASE_FILES = {
    25: ["main_menu.json", "phase_25.json"],
    50: ["main_menu.json", "phase_25.json", "phase_50.json"],
    75: ["main_menu.json", "phase_25.json", "phase_50.json", "phase_75.json"],
    100: ["main_menu.json", "phase_25.json", "phase_50.json", "phase_75.json", "phase_100.json"],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_key(record):
    return record["id"].rsplit(":", 1)[1]


def load_master():
    master = {}
    for line in (ROOT / "reference" / "translation_master.local.jsonl").read_text(
            encoding="utf-8").splitlines():
        row = json.loads(line)
        master[row["source_key"]] = row
    return master


def load_partitions(phase):
    rows = []
    for name in PHASE_FILES[phase]:
        rows += json.loads((ROOT / "translation" / "arabic" / name).read_text(encoding="utf-8"))
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate translation IDs across selected partitions")
    return rows


def load_loose(game):
    return json.loads((game / "base" / "graphicsdriverwarningloc.json").read_bytes().decode("utf-8-sig"))


def invert_pua(mapping):
    return {chr(int(char[2:], 16)): int(code[2:], 16) for char, code in mapping.items()}


def build_mapping(visual_chars, v4_mapping):
    """Seed with the V4 mapping so its glyph indices/atlas stay a byte-exact prefix."""
    mapping = dict(v4_mapping)
    next_code = max(mapping.values()) + 1
    for character in sorted(visual_chars - set(mapping)):
        mapping[character] = next_code
        next_code += 1
    return mapping


def shape_record(record, mapping):
    """Uniform Candidate C (shape_formatted_ordered) with all build assertions."""
    arabic = record["arabic"]
    visual = ft.shape_formatted_ordered(arabic, mapping)
    pua_max = 0xE000 + len(mapping)
    if any(ord(c) > 127 and c not in mapping and not (0xE000 <= ord(c) < pua_max) for c in visual):
        raise ValueError("Unmapped non-ASCII visual character in %s" % record["id"])
    if visual.count("\n") != arabic.count("\n"):
        raise ValueError("Newline parity broken for %s" % record["id"])
    literal = ft.encode_lang_value(visual)
    if ft.decode_lang_value(literal) != visual:
        raise ValueError("Round-trip failed for %s" % record["id"])
    if "english" in record:
        if re.findall(r"\[[^\]\r\n]*\]", visual) != re.findall(r"\[[^\]\r\n]*\]", record["english"]):
            raise ValueError("Bracket-tag parity broken for %s" % record["id"])
    return literal, visual


def rewrite_lang(raw, replacements):
    """Replace the value of every #str_ key present in replacements."""
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
        raise ValueError("Not all translations were serialized (missing %r)"
                         % sorted(set(replacements) - changed)[:5])
    return b"\xef\xbb\xbf" + output.encode("utf-8")


def rewrite_loose(raw, replacements):
    """Replace english_* values in the loose graphics-driver-warning JSON in place."""
    text = raw.decode("utf-8-sig")
    pattern = re.compile(r'("(english_[a-z]+)"\s*:\s*")((?:[^"\\]|\\.)*)(")')
    changed = set()

    def replace(match):
        key = match[2]
        if key not in replacements:
            return match[0]
        changed.add(key)
        return match[1] + json.dumps(replacements[key], ensure_ascii=False)[1:-1] + match[4]

    output = pattern.sub(replace, text)
    if changed != set(replacements):
        raise ValueError("Not all loose values were serialized")
    bom = b"\xef\xbb\xbf" if raw[:3] == b"\xef\xbb\xbf" else b""
    return bom + output.encode("utf-8")


_REASON_PRIORITY = ("latin_island_fallback", "unsafe_joining_gap_fallback",
                    "single_span", "no_reordering_needed")


def _line_span_reason(line):
    items = ft._shape_line_spans(line)
    spans = [p for k, p in items if k == "text"]
    if len(spans) <= 1:
        return "single_span"
    if not all(ft._span_is_pure_rtl(s) for s in spans):
        return "latin_island_fallback"
    for index, (kind, pl) in enumerate(items):
        if kind != "tokens" or not ft._transparent_gap(pl):
            continue
        nxt = items[index + 1] if index + 1 < len(items) else None
        prv = items[index - 1] if index > 0 else None
        if nxt and prv and nxt[0] == "text" and prv[0] == "text":
            left = ft._last_arabic_letter(prv[1])
            right = ft._first_arabic_letter(nxt[1])
            if left is not None and right is not None and ft._joins_forward(left):
                return "unsafe_joining_gap_fallback"
    return "no_reordering_needed"


def span_order_reason(arabic):
    """Why Candidate C did not change a record (diagnostic only)."""
    lines = [line for line in arabic.split("\n") if line]
    reasons = {_line_span_reason(line) for line in lines} or {"empty"}
    reason = next(r for r in _REASON_PRIORITY if r in reasons)
    return ("multiline_" + reason) if len(lines) > 1 else reason


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=sorted(PHASE_FILES), default=100)
    parser.add_argument("--out", type=Path, default=None,
                        help="output directory (default workspace/runtime_full)")
    parser.add_argument("--stage", default="runtime_full")
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    args = parser.parse_args()
    if args.game is None:
        parser.error("--game is required (or set WTOB_GAME_DIR)")
    out_dir = (args.out or (ROOT / "workspace" / "runtime_full")).resolve()
    game = args.game

    v4_info = json.loads(V4_INFO.read_text(encoding="utf-8"))
    v4_mapping = invert_pua(v4_info["mapping"])

    partitions = load_partitions(args.phase)
    master = load_master()
    loose_json = load_loose(game)

    lang_records, loose_records = [], []
    for record in partitions:
        if record["resource"] == "strings/english.lang":
            lang_records.append(record)
        else:
            loose_records.append(record)

    # Attach English and validate the immutable source hash.
    for record in lang_records:
        key = source_key(record)
        if key not in master:
            raise ValueError("Record not in local master: %s" % record["id"])
        record["english"] = master[key]["english"]
        record["english_literal"] = master[key]["english_literal"]
        if master[key]["english_sha256"] != record["english_sha256"]:
            raise ValueError("English source hash mismatch: %s" % record["id"])
        if master[key]["status"] != record["status"] or master[key]["arabic"] != record["arabic"]:
            raise ValueError("Public/local translation disagree: %s" % record["id"])
    for record in loose_records:
        if record["resource"] != LOOSE_RESOURCE:
            raise ValueError("Unexpected non-lang resource: %s" % record["resource"])
        key = record["location"]
        if key not in loose_json:
            raise ValueError("Loose key missing from game file: %s" % key)
        english = loose_json[key]
        if sha(english.encode("utf-8")) != record["english_sha256"]:
            raise ValueError("Loose English source hash mismatch: %s" % key)
        record["english"] = english

    all_records = lang_records + loose_records
    translated = [r for r in all_records if r["status"] == "translated"]
    dnt = [r for r in all_records if r["status"] == "do_not_translate"]
    unknown = [r for r in all_records if r["status"] not in ("translated", "do_not_translate")]
    if unknown:
        raise ValueError("Unexpected status: %r" % unknown[:3])
    forbidden = [r for r in translated if not r["arabic"]]
    if forbidden:
        raise ValueError("Translated record without Arabic: %s" % forbidden[0]["id"])

    # Global visual glyph inventory (order is a permutation, so it is invariant).
    char_set = set()
    for record in translated:
        char_set.update(c for c in ft.shape_formatted_ordered(record["arabic"], {}) if ord(c) > 127)
    mapping = build_mapping(char_set, v4_mapping)

    from fontTools.ttLib import TTFont
    cmap = TTFont(FONT_PATH).getBestCmap()
    missing = sorted(c for c in char_set if ord(c) not in cmap)
    if missing:
        raise ValueError("IBM font is missing required glyphs: %r" % "".join(missing))

    # Shape every translated record; keep do-not-translate rows byte-identical.
    shapes, visuals, span_corrected, fallback_reasons = {}, {}, [], Counter()
    for record in translated:
        visual_current = ft.shape_formatted(record["arabic"], {})
        visual_ordered = ft.shape_formatted_ordered(record["arabic"], {})
        if visual_ordered != visual_current:
            span_corrected.append(record["id"])
        else:
            fallback_reasons[span_order_reason(record["arabic"])] += 1
        literal, visual = shape_record(record, mapping)
        shapes[record["id"]] = literal
        visuals[record["id"]] = visual

    lang_replacements = {source_key(r): shapes[r["id"]] for r in lang_records if r["status"] == "translated"}
    loose_replacements = {r["location"]: visuals[r["id"]] for r in loose_records if r["status"] == "translated"}

    originals = {name: (BACKUP_DIR / name).read_bytes() for name in SOURCE_HASHES}
    if sha(originals["chunk0.index"]) != SOURCE_HASHES["chunk0.index"] or \
            sha(originals["chunk0.resources"]) != SOURCE_HASHES["chunk0.resources"]:
        raise ValueError("Vanilla backups do not match the known original archives")
    if sha(FONT_PATH.read_bytes()) != IBM_FONT_HASH:
        raise ValueError("Unexpected IBM font revision")

    entries, _ = records(originals["chunk0.index"], len(originals["chunk0.resources"]))
    by_path = {e["names"][2]: e for e in entries}
    source = io.BytesIO(originals["chunk0.resources"])
    lang_entry = by_path["strings/english.lang"]
    raw_lang = payload(source, lang_entry)

    encoded = rewrite_lang(raw_lang, lang_replacements)
    rows_before = parse_lang(raw_lang)
    rows_after = parse_lang(encoded)
    if len(rows_before) != len(rows_after) != 3572:
        raise ValueError("Unexpected english.lang row count")
    for old, new in zip(rows_before, rows_after):
        key = old["source_key"]
        if key in lang_replacements:
            if new["english"] != ft.decode_lang_value(lang_replacements[key]):
                raise ValueError("Lang rewrite mismatch: %s" % key)
        elif old != new:
            raise ValueError("Untouched lang row changed: %s" % key)

    original_loose = (game / "base" / "graphicsdriverwarningloc.json").read_bytes()
    loose_out = rewrite_loose(original_loose, loose_replacements)
    check_loose = json.loads(loose_out.decode("utf-8-sig"))
    for key, value in loose_replacements.items():
        if check_loose[key] != value:
            raise ValueError("Loose rewrite mismatch: %s" % key)
    for key, value in json.loads(original_loose.decode("utf-8-sig")).items():
        if key not in loose_replacements and check_loose[key] != value:
            raise ValueError("Untouched loose value changed: %s" % key)

    changes = {lang_entry["ordinal"]: encoded}
    fonts_changed, kerning_report = [], {}
    for name in FONTS:
        metrics = by_path["fonts/%s/64_df.dat" % name]
        image = by_path["generated/textures/borderclamp_alpha_fonts/%s/64_df.bimage" % name]
        raw_metrics = payload(source, metrics)
        raw_image = payload(source, image)
        new_metrics, new_image = extend_font(raw_metrics, raw_image, FONT_PATH, mapping,
                                             joining_kern=True)
        native = parse_kerning(raw_metrics)
        total = parse_kerning(new_metrics)
        added = [p for p in total if p not in set(native)]
        added_only_appended = all(a >= len(inspect_font(raw_metrics)[0]) for a, _, _ in added)
        kerning_report[name] = dict(
            native_pairs=len(native), added_pairs=len(added), total_pairs=len(total),
            native_preserved=set(native) <= set(total),
            added_all_negative=all(px < 0 for _, _, px in added),
            added_target_appended_only=added_only_appended,
            sorted_unique=(total == sorted(set(total))),
        )
        if not (kerning_report[name]["native_preserved"] and kerning_report[name]["added_all_negative"]
                and kerning_report[name]["added_target_appended_only"]
                and kerning_report[name]["sorted_unique"]):
            raise ValueError("Kerning invariants violated for %s" % name)
        changes[metrics["ordinal"]] = new_metrics
        changes[image["ordinal"]] = new_image
        fonts_changed.append(name)

    if rebuild(originals["chunk0.index"], originals["chunk0.resources"], {}) != (
            originals["chunk0.index"], originals["chunk0.resources"]):
        raise ValueError("No-op rebuild is not byte-identical")
    built_index, built_archive = rebuild(originals["chunk0.index"], originals["chunk0.resources"], changes)
    if rebuild(originals["chunk0.index"], originals["chunk0.resources"], changes) != (built_index, built_archive):
        raise ValueError("Build is not deterministic (source -> build)")
    if rebuild(built_index, built_archive, changes) != (built_index, built_archive):
        raise ValueError("Build is not idempotent")

    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "chunk0.index": built_index,
        "chunk0.resources": built_archive,
        "graphicsdriverwarningloc.json": loose_out,
    }
    for name, data in outputs.items():
        (out_dir / name).write_bytes(data)
    (out_dir / "english_runtime.local.lang").write_bytes(encoded)

    dnt_categories = Counter()
    for record in dnt:
        key = source_key(record)
        value = record["english"].strip()
        kind = ("empty_source" if not value else
                "source_placeholder" if value == "< New String >" else
                "keyboard_labels" if key.startswith("#str_key_") else
                "internal_leaderboard_identifiers" if key.startswith("#str_leaderboard_") else
                "font_coverage_metadata" if key == "#str_aaa_needed_characters" else
                "missingtext_placeholder" if value == "missingtext" else
                "numeric_identifier" if value.isdigit() else "timing_only")
        dnt_categories[kind] += 1

    mapping_json = {("U+%04X" % ord(c)): ("U+%04X" % v) for c, v in sorted(mapping.items(), key=lambda i: i[1])}
    v4_codes = set(v4_mapping.values())
    appended = sorted(c for c, v in mapping.items() if v not in v4_codes)

    # --- artifacts ---------------------------------------------------------
    (out_dir / "BUILD_INFO.local.json").write_text(json.dumps(dict(
        stage=args.stage, phase=args.phase, in_game_verified=False, installed=False,
        archive_layout="ordered_v1",
        record_count=len(all_records), translated_count=len(translated),
        do_not_translate_count=len(dnt), lang_records=len(lang_records),
        loose_records=len(loose_records), lang_rows_total=len(rows_after),
        new_glyph_count=len(mapping), mapping_seed="opening_runtime_poc_v4",
        v4_prefix_glyphs=len(v4_mapping), appended_glyphs=len(appended),
        fonts=fonts_changed, source_hashes=SOURCE_HASHES, font_sha256=IBM_FONT_HASH,
        output_hashes={n: sha(b) for n, b in outputs.items()},
        mapping=mapping_json,
        span_order="uniform shape_formatted_ordered (Candidate C) with shape_line fallback",
        joining_kern_pairs=kerning_report["futura_com_book"]["added_pairs"],
        per_font_kerning=kerning_report,
        changed_resources=[e["names"][2] for e in entries if e["ordinal"] in changes],
        loose_resources=[LOOSE_RESOURCE],
        strategy=("pre-shaped visual Arabic (uniform span-order corrected) mapped to "
                  "appended PUA glyphs; V4 mapping/atlas/kerning preserved as a prefix; "
                  "generated Arabic joining kerning; static build verified, runtime unverified"),
    ), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (out_dir / "FULL_MANIFEST.local.json").write_text(json.dumps(dict(
        total_records=len(all_records), translated=len(translated),
        do_not_translate=len(dnt), identity_holds=(len(all_records) == len(translated) + len(dnt)),
        lang_records=len(lang_records), loose_records=len(loose_records),
        by_partition={name: len(json.loads((ROOT / "translation" / "arabic" / name).read_text(encoding="utf-8")))
                      for name in PHASE_FILES[args.phase]},
        do_not_translate_categories=dict(dnt_categories),
        translated_ids=sorted(r["id"] for r in translated),
        do_not_translate_ids=sorted(r["id"] for r in dnt),
    ), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (out_dir / "GLYPH_MAP.local.json").write_text(json.dumps(dict(
        new_glyph_count=len(mapping), v4_prefix_glyphs=len(v4_mapping),
        appended_glyphs=len(appended),
        codepoint_range=["U+%04X" % min(mapping.values()), "U+%04X" % max(mapping.values())],
        appended_characters=[("U+%04X" % ord(c)) for c in appended],
        mapping=mapping_json,
    ), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    built_entries, _ = records(built_index, len(built_archive))
    built_futura = [e for e in built_entries if e["names"][2] == "fonts/futura_com_book/64_df.dat"][0]
    built_futura_kern = set(parse_kerning(payload(io.BytesIO(built_archive), built_futura)))
    native_count = len(inspect_font(payload(source, by_path["fonts/futura_com_book/64_df.dat"]))[0])
    v4_pairs = _reconstruct_v4_pairs(v4_mapping, native_count)
    (out_dir / "KERNING_REPORT.local.json").write_text(json.dumps(dict(
        per_font=kerning_report,
        v4_joining_pairs=len(v4_pairs),
        v4_joining_pairs_subset=(set(v4_pairs) <= built_futura_kern),
        target_overlap_px=1.0,
        note="each added pair is a generated Arabic joining negative adjustment",
    ), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (out_dir / "TOKEN_CENSUS.local.json").write_text(json.dumps(
        _token_census(translated), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (out_dir / "SPAN_ORDER_REPORT.local.json").write_text(json.dumps(dict(
        algorithm="shape_formatted_ordered (Candidate C) applied uniformly",
        corrected_count=len(span_corrected), corrected_ids=sorted(span_corrected),
        fallback_reasons=dict(fallback_reasons),
        note=("records are reordered only when every span is pure RTL and no unsafe "
              "joining gap crosses a transparent token; otherwise shape_line is used"),
    ), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (out_dir / "COVERAGE_100.local.json").write_text(json.dumps(dict(
        scope="100% of the confirmed electronic-text corpus",
        total_records=len(all_records), translated=len(translated),
        do_not_translate=len(dnt), completion_percent=100,
        translated_percent=round(len(translated) / len(all_records) * 100, 2),
        do_not_translate_categories=dict(dnt_categories),
        not_covered_and_uncertified=[
            "BSWF/menu textures", "image textures", "Bink video subtitles",
            "native engine messages", "audio", "any asset outside the confirmed corpus"],
        statement=("100% of the confirmed electronic-text corpus is built; this is NOT a "
                   "claim of 100% coverage of every player-visible asset"),
    ), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (out_dir / "ENGLISH_LEAK_AUDIT.local.json").write_text(json.dumps(
        _english_audit(translated), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(dict(stage=args.stage, phase=args.phase, out=str(out_dir),
                          records=len(all_records), translated=len(translated), dnt=len(dnt),
                          glyphs=len(mapping), appended_glyphs=len(appended),
                          joined_kern=kerning_report["futura_com_book"]["added_pairs"],
                          span_corrected=len(span_corrected),
                          output_hashes={n: sha(b) for n, b in outputs.items()}), indent=2))


def _reconstruct_v4_pairs(v4_mapping, native_count):
    """Rebuild the V4 joining-kerning pairs so we can prove they are a subset."""
    additions = []
    for index, (character, _code) in enumerate(sorted(v4_mapping.items(), key=lambda kv: kv[1])):
        bitmap, _top, left, advance = glyph_bitmap(FONT_PATH, character)
        additions.append(dict(bitmap=bitmap, left=left, advance=advance,
                              glyph_index=native_count + index, form=glyph_form(character)))
    return joining_kernings(additions, 1.0)


def _token_census(translated):
    census = Counter()
    records_with_tokens = 0
    for record in translated:
        found = False
        for match in ft.TOKEN_RE.finditer(record["arabic"]):
            found = True
            token = match.group(0)
            if token == "\n":
                kind = "newline"
            elif ft.TRANSPARENT_JOIN_RE.fullmatch(token):
                kind = "transparent"
            elif token.startswith("["):
                kind = "bracket"
            elif token.startswith("%"):
                kind = "printf"
            elif token.startswith("<"):
                kind = "angle"
            elif token.startswith("{"):
                kind = "brace"
            elif token.startswith("_"):
                kind = "ident"
            elif token.startswith("$"):
                kind = "var"
            elif token.startswith("^"):
                kind = "caret"
            else:
                kind = "other"
            census[kind] += 1
        records_with_tokens += found
    return dict(
        translated_records=len(translated), records_with_tokens=records_with_tokens,
        token_counts=dict(census),
        classification={
            "transparent": "invisible runtime metadata ([timing]/[lang]/^colour), never drawn",
            "bracket": "bracket control tag", "printf": "printf specifier (%d/%s/..)",
            "angle": "<JOYn>", "brace": "{n}", "ident": "_identifier",
            "var": "$variable", "caret": "^colour digit", "newline": "\\n hard line break",
        })


def _english_audit(translated):
    identical, no_arabic = [], []
    latin_island = []
    for record in translated:
        arabic = record["arabic"]
        english = record.get("english")
        if english is not None and arabic == english:
            identical.append(record["id"])
        visual = ft.shape_formatted_ordered(arabic, {})
        if not any(ord(c) > 127 for c in visual):
            no_arabic.append(record["id"])
        words = re.findall(r"[A-Za-z]{2,}", ft.TOKEN_RE.sub(" ", arabic))
        if len(words) >= 2:
            latin_island.append(dict(id=record["id"], words=words))
    suspicious = sorted(set(identical) | set(no_arabic))
    return dict(
        suspicious_english=len(suspicious), suspicious_ids=suspicious,
        identical_to_english=len(identical), no_arabic_output=len(no_arabic),
        latin_island_records=len(latin_island),
        latin_island_note=("accepted Latin islands: brand names, roman numerals and "
                           "newspaper Latin, preserved verbatim by design"),
        latin_island=latin_island,
    )


if __name__ == "__main__":
    main()
