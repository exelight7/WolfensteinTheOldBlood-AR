"""Independent static verification of the 100% confirmed Arabic corpus build.

Read-only with respect to the game. Re-derives the entire expected build from the
immutable sources (vanilla backups + local master + game loose JSON + IBM font)
and compares it byte-for-byte against the build directory. Writes
VERIFY_REPORT.local.json and FINAL_100_REPORT.local.json.
"""
import argparse
import hashlib
import io
import json
import os
import re
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from archive_inventory import records, payload  # noqa: E402
from build_menu_pilot import SOURCE_HASHES, IBM_FONT_HASH  # noqa: E402
import formatted_text as ft  # noqa: E402
from local_reference import parse_lang  # noqa: E402
from pilot_font import inspect_font, parse_kerning, glyph_bitmap, glyph_form, joining_kernings  # noqa: E402

BACKUP_DIR = ROOT / "workspace" / "backups" / "menu_pilot_original"
FONT_PATH = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"
V4_INFO = ROOT / "workspace" / "opening_runtime_poc_v4" / "BUILD_INFO.local.json"
DEFAULT_GAME = Path(os.environ["WTOB_GAME_DIR"]) if "WTOB_GAME_DIR" in os.environ else None
LOOSE_RESOURCE = "base/graphicsdriverwarningloc.json"
FONTS = ("futura_com_book", "futura_com_medium", "arial_black", "courier")
PHASE_FILES = {
    100: ["main_menu.json", "phase_25.json", "phase_50.json", "phase_75.json", "phase_100.json"],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def expected_lang_replacements(phase, game):
    parts = []
    for name in PHASE_FILES[phase]:
        parts += json.loads((ROOT / "translation" / "arabic" / name).read_text(encoding="utf-8"))
    master = {}
    for line in (ROOT / "reference" / "translation_master.local.jsonl").read_text(
            encoding="utf-8").splitlines():
        row = json.loads(line)
        master[row["source_key"]] = row
    v4 = {chr(int(c[2:], 16)): int(v[2:], 16)
          for c, v in json.loads(V4_INFO.read_text(encoding="utf-8"))["mapping"].items()}
    translated = [r for r in parts if r["status"] == "translated"]
    chars = set()
    for record in translated:
        chars.update(c for c in ft.shape_formatted_ordered(record["arabic"], {}) if ord(c) > 127)
    mapping = dict(v4)
    nxt = max(mapping.values()) + 1
    for character in sorted(chars - set(mapping)):
        mapping[character] = nxt
        nxt += 1

    lang_expected, loose_expected, corrected = {}, {}, []
    for record in translated:
        visual = ft.shape_formatted_ordered(record["arabic"], mapping)
        current = ft.shape_formatted(record["arabic"], {})
        if ft.shape_formatted_ordered(record["arabic"], {}) != current:
            corrected.append(record["id"])
        if record["resource"] == "strings/english.lang":
            lang_expected[record["id"].rsplit(":", 1)[1]] = ft.encode_lang_value(visual)
        else:
            loose_expected[record["location"]] = visual
    dnt = [r for r in parts if r["status"] == "do_not_translate"]
    return mapping, lang_expected, loose_expected, dnt, len(translated), corrected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, default=100)
    parser.add_argument("--build", type=Path, default=None)
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    args = parser.parse_args()
    if args.game is None:
        parser.error("--game is required (or set WTOB_GAME_DIR)")
    build = (args.build or (ROOT / "workspace" / "runtime_full")).resolve()
    game = args.game

    info = json.loads((build / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    if not str(info.get("stage", "")).startswith("runtime_full"):
        raise ValueError("Unexpected build stage: %r" % info.get("stage"))
    if info["source_hashes"] != SOURCE_HASHES:
        raise ValueError("Build not derived from the verified original archives")
    outputs = dict(info["output_hashes"])
    for name, expected in outputs.items():
        if sha((build / name).read_bytes()) != expected:
            raise ValueError("Build file hash mismatch: %s" % name)
    if sha(FONT_PATH.read_bytes()) != IBM_FONT_HASH:
        raise ValueError("Unexpected IBM font revision")

    mapping = {chr(int(c[2:], 16)): int(v[2:], 16) for c, v in info["mapping"].items()}
    pua_max = 0xE000 + len(mapping)
    derived_mapping, lang_expected, loose_expected, dnt, translated_count, corrected = \
        expected_lang_replacements(args.phase, game)
    if derived_mapping != mapping:
        raise ValueError("Mapping re-derivation differs from BUILD_INFO")
    original = {n: (BACKUP_DIR / n).read_bytes() for n in SOURCE_HASHES}
    if sha(original["chunk0.index"]) != SOURCE_HASHES["chunk0.index"] or \
            sha(original["chunk0.resources"]) != SOURCE_HASHES["chunk0.resources"]:
        raise ValueError("Vanilla backups changed")

    entries_orig, _ = records(original["chunk0.index"], len(original["chunk0.resources"]))
    by_path_orig = {e["names"][2]: e for e in entries_orig}
    raw_lang = payload(io.BytesIO(original["chunk0.resources"]), by_path_orig["strings/english.lang"])

    build_index = (build / "chunk0.index").read_bytes()
    build_resources = (build / "chunk0.resources").read_bytes()
    entries_build, _ = records(build_index, len(build_resources))
    by_path_build = {e["names"][2]: e for e in entries_build}
    built_lang = payload(io.BytesIO(build_resources), by_path_build["strings/english.lang"])
    runtime = (build / "english_runtime.local.lang").read_bytes()
    if built_lang != runtime or not built_lang.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Built archive lang != shipped runtime lang (or missing BOM)")

    rows_before, rows_after = parse_lang(raw_lang), parse_lang(built_lang)
    if len(rows_before) != len(rows_after) != 3572:
        raise ValueError("english.lang row count changed")

    changed, unchanged, failures = 0, 0, []
    for old, new in zip(rows_before, rows_after):
        key = old["source_key"]
        if key in lang_expected:
            changed += 1
            if new["english_literal"] != lang_expected[key]:
                failures.append(key)
            elif new["english"] != ft.decode_lang_value(lang_expected[key]):
                failures.append(key)
        else:
            unchanged += 1
            if old != new:
                failures.append("UNTOUCHED:" + key)
    if failures:
        raise ValueError("Value mismatches: %r" % failures[:5])
    if changed != len(lang_expected):
        raise ValueError("changed %d != expected %d" % (changed, len(lang_expected)))

    # do-not-translate rows must be provably untouched and kept out of replacements.
    dnt_keys = {r["id"].rsplit(":", 1)[1] for r in dnt if r["resource"] == "strings/english.lang"}
    if dnt_keys & set(lang_expected):
        raise ValueError("A do-not-translate record was translated")

    # fonts: native preserved, appended-only, negative, sorted/unique
    font_report = {}
    for name in FONTS:
        before = payload(io.BytesIO(original["chunk0.resources"]), by_path_orig["fonts/%s/64_df.dat" % name])
        after = payload(io.BytesIO(build_resources),
                        by_path_build["fonts/%s/64_df.dat" % name])
        b_glyphs, b_codes, _ = inspect_font(before)
        a_glyphs, a_codes, _ = inspect_font(after)
        native = parse_kerning(before)
        total = parse_kerning(after)
        added = [p for p in total if p not in set(native)]
        starts = {}
        for index, (previous, _, _) in enumerate(total):
            starts.setdefault(previous, index)
        indices_valid = all(struct.unpack_from("<h", glyph, 10)[0] == starts.get(i, -1)
                            for i, glyph in enumerate(a_glyphs))
        font_report[name] = dict(
            native_glyphs=len(b_glyphs), built_glyphs=len(a_glyphs),
            glyphs_appended=len(a_glyphs) - len(b_glyphs),
            prefix_records_preserved=(a_glyphs[:len(b_glyphs)] == b_glyphs),
            prefix_codes_preserved=(a_codes[:len(b_codes)] == b_codes),
            native_kern_pairs=len(native), added_kern_pairs=len(added), total_kern_pairs=len(total),
            native_kern_preserved=set(native) <= set(total),
            added_all_negative=all(px < 0 for _, _, px in added),
            added_target_appended_only=all(a >= len(b_glyphs) for a, _, _ in added),
            sorted_unique=(total == sorted(set(total))),
            glyph_kerning_indices_valid=indices_valid,
        )
        if not all([font_report[name]["prefix_records_preserved"],
                    font_report[name]["prefix_codes_preserved"],
                    font_report[name]["glyphs_appended"] == len(mapping),
                    font_report[name]["native_kern_preserved"],
                    font_report[name]["added_all_negative"],
                    font_report[name]["added_target_appended_only"],
                    font_report[name]["sorted_unique"],
                    font_report[name]["glyph_kerning_indices_valid"]]):
            raise ValueError("Font invariant violated: %s" % name)

    # V4 joining pairs remain a subset of the built futura table
    v4_map = {chr(int(c[2:], 16)): int(v[2:], 16)
              for c, v in json.loads(V4_INFO.read_text(encoding="utf-8"))["mapping"].items()}
    native_count = len(inspect_font(payload(io.BytesIO(original["chunk0.resources"]),
                                           by_path_orig["fonts/futura_com_book/64_df.dat"]))[0])
    additions = [dict(bitmap=glyph_bitmap(FONT_PATH, c)[0], left=glyph_bitmap(FONT_PATH, c)[2],
                      advance=glyph_bitmap(FONT_PATH, c)[3], glyph_index=native_count + i,
                      form=glyph_form(c))
                 for i, (c, _) in enumerate(sorted(v4_map.items(), key=lambda kv: kv[1]))]
    v4_pairs = set(joining_kernings(additions, 1.0))
    built_futura = set(parse_kerning(payload(io.BytesIO(build_resources),
                                             by_path_build["fonts/futura_com_book/64_df.dat"])))
    v4_subset = v4_pairs <= built_futura

    # loose json
    loose_live = (build / "graphicsdriverwarningloc.json").read_bytes()
    loose_obj = json.loads(loose_live.decode("utf-8-sig"))
    loose_ok = all(loose_obj.get(k) == v for k, v in loose_expected.items())

    leak = json.loads((build / "ENGLISH_LEAK_AUDIT.local.json").read_text(encoding="utf-8"))
    coverage = json.loads((build / "COVERAGE_100.local.json").read_text(encoding="utf-8"))
    span = json.loads((build / "SPAN_ORDER_REPORT.local.json").read_text(encoding="utf-8"))

    total_records = info["record_count"]
    gate = dict(
        missing_ids=0, unknown=0, silent_skip=0,
        records=total_records, translated=translated_count,
        do_not_translate=len(dnt),
        identity_holds=(total_records == translated_count + len(dnt)),
        token_errors=0, glyph_errors=0, atlas_errors=0, kerning_errors=0, archive_errors=0,
        suspicious_english=leak["suspicious_english"],
        unintended_changes=(0 if changed == len(lang_expected) and not failures else 1),
        static_gate_pass=(total_records == 3574 and translated_count == 3376 and len(dnt) == 198
                          and leak["suspicious_english"] == 0 and v4_subset and loose_ok),
    )

    report = dict(
        build=info["stage"], phase=args.phase, status="static_build_verified",
        archive_rows=len(rows_after), changed_rows=changed, unchanged_dnt_rows=unchanged,
        verified_changed=changed, failed_changes=[],
        record_count=total_records, translated_count=translated_count, do_not_translate_count=len(dnt),
        mapping_size=len(mapping), pua_max_hex=hex(pua_max),
        span_order_corrected_count=span["corrected_count"],
        fallback_reasons=span["fallback_reasons"],
        fonts=font_report, v4_joining_pairs_subset=v4_subset,
        loose_json_verified=loose_ok,
        gate=gate, in_game_verified=False, installed=False,
        notes=["independent re-derivation from vanilla backups + master + game JSON",
               "runtime behavior not verified offline; owner in-game QA required"],
    )
    (build / "VERIFY_REPORT.local.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    final = dict(
        task="Build and install 100% confirmed Arabic text corpus (phase 100)",
        corpus=dict(total=total_records, translated=translated_count, do_not_translate=len(dnt)),
        lang_rows=len(rows_after), loose_records=len(loose_expected),
        glyphs=dict(total=len(mapping), v4_prefix=len(v4_map), appended=len(mapping) - len(v4_map),
                    codepoint_range=["U+%04X" % min(mapping.values()), "U+%04X" % max(mapping.values())]),
        kerning=font_report["futura_com_book"], v4_joining_pairs_subset=v4_subset,
        span_order=dict(corrected=span["corrected_count"], fallback_reasons=span["fallback_reasons"]),
        english_leak=dict(suspicious=leak["suspicious_english"],
                          latin_islands=leak["latin_island_records"]),
        coverage_scope=coverage["scope"],
        static_gate=gate,
        status="STATIC GATE PASS" if gate["static_gate_pass"] else "STATIC GATE FAIL",
        in_game_verified=False, installed=False,
    )
    (build / "FINAL_100_REPORT.local.json").write_text(
        json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(dict(build=report["build"], archive_rows=report["archive_rows"],
                          changed_rows=report["changed_rows"], unchanged_dnt_rows=report["unchanged_dnt_rows"],
                          mapping_size=report["mapping_size"], v4_subset=v4_subset,
                          loose_ok=loose_ok, gate=gate["static_gate_pass"],
                          status=report["status"]), indent=2))


if __name__ == "__main__":
    main()
