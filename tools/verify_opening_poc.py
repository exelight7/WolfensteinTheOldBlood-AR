"""Static verification of the opening-runtime POC build. Read-only.

Adds the dedicated screenshot assertion: the exact owner-reported English
line must be mapped to the exact runtime record, the exact Arabic value,
and the exact rebuilt resource. The check fails loudly if the English
value remains unchanged in the rebuilt english.lang.
"""
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import payload, records  # noqa: E402
from build_menu_pilot import SOURCE_HASHES  # noqa: E402
import formatted_text as ft  # noqa: E402
from formatted_text import shape_formatted  # noqa: E402
from local_reference import parse_lang  # noqa: E402

BACKUP_DIR = ROOT / "workspace" / "backups" / "menu_pilot_original"
PILOT_OUT = ROOT / "workspace" / "menu_pilot_ordered"
POC_OUT = ROOT / "workspace" / "opening_runtime_poc"

SCREENSHOT_RECORD = "#str_vo_agentone_dlc1_c01_123"
SCREENSHOT_SENTENCE = (
    "is keeping the folder mentioned in your mission briefing "
    "at her base of operations --")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bracket_sequence(text):
    return re.findall(r"\[[^\]\r\n]*\]", text)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=None,
                        help="POC build directory (default workspace/opening_runtime_poc)")
    args = parser.parse_args()
    poc_dir = args.build or POC_OUT
    approved = json.loads(
        (PILOT_OUT / "BUILD_INFO.local.json").read_text(encoding="utf-8"))["output_hashes"]

    original = {n: (BACKUP_DIR / n).read_bytes() for n in SOURCE_HASHES}
    assert sha(original["chunk0.index"]) == SOURCE_HASHES["chunk0.index"]
    assert sha(original["chunk0.resources"]) == SOURCE_HASHES["chunk0.resources"]

    poc = {n: (poc_dir / n).read_bytes() for n in SOURCE_HASHES}
    info = json.loads((poc_dir / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    assert info["stage"] in ("opening_runtime_poc", "opening_runtime_poc_v2",
                             "opening_runtime_poc_v3", "opening_runtime_poc_v4")
    for n in SOURCE_HASHES:
        assert sha(poc[n]) == info["output_hashes"][n]

    entries_original, _ = records(original["chunk0.index"], len(original["chunk0.resources"]))
    by_path = {e["names"][2]: e for e in entries_original}
    raw_original = payload(io.BytesIO(original["chunk0.resources"]),
                           by_path["strings/english.lang"])

    entries_poc, _ = records(poc["chunk0.index"], len(poc["chunk0.resources"]))
    by_path_poc = {e["names"][2]: e for e in entries_poc}
    built_lang = payload(io.BytesIO(poc["chunk0.resources"]),
                         by_path_poc["strings/english.lang"])
    runtime = (poc_dir / "english_runtime.local.lang").read_bytes()
    assert built_lang == runtime, "built archive lang != shipped runtime lang"
    assert built_lang.startswith(b"\xef\xbb\xbf"), "built lang must carry a BOM"

    rows_original = parse_lang(raw_original)
    rows_new = parse_lang(built_lang)
    assert len(rows_original) == len(rows_new) == 3572

    master = {}
    for line in (ROOT / "reference" / "translation_master.local.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["status"] == "translated" and row.get("arabic"):
            master[row["source_key"]] = row
    menu = json.loads((ROOT / "translation" / "arabic" / "main_menu.json").read_text(encoding="utf-8"))
    menu_by_key = {row["id"].rsplit(":", 1)[1]: row for row in menu}

    mapping = {chr(int(k[2:], 16)): int(v[2:], 16) for k, v in info["mapping"].items()}
    pua_max = 0xE000 + len(mapping)
    expected_changed = set(info["opening_ids"]) | {r["id"].rsplit(":", 1)[1] for r in menu}
    span_corrected = set(info.get("span_order_corrected_ids", []))

    changed, verified = 0, 0
    failures = []
    rows = dict(parsed_new={}, parsed_old={})
    for old, new in zip(rows_original, rows_new):
        key = old["source_key"]
        if new["english"] == old["english"]:
            assert old["english_literal"] == new["english_literal"], key
            assert key not in expected_changed, "intended record was NOT transformed: %s" % key
            continue
        assert key in expected_changed, "unexpected changed record: %s" % key
        changed += 1
        rows["parsed_old"][key] = old
        rows["parsed_new"][key] = new
        try:
            arabic = (master.get(key) or menu_by_key.get(key))["arabic"]
            is_master = key in master
            if key in span_corrected:
                expected_visual = ft.shape_formatted_ordered(arabic, mapping)
            else:
                expected_visual = shape_formatted(arabic, mapping)
            expected_literal = ft.encode_lang_value(expected_visual)

            # dedicated screenshot assertion: exact runtime record, exact
            # Arabic value, exact rebuilt resource
            if key == SCREENSHOT_RECORD:
                target = master[SCREENSHOT_RECORD]
                # 1. the record's english source contains the owner's sentence
                assert SCREENSHOT_SENTENCE in old["english_literal"], key
                assert SCREENSHOT_SENTENCE in old["english"], key
                # 2. the rebuilt resource no longer contains the English sentence
                assert SCREENSHOT_SENTENCE not in new["english"], (
                    "SCREENSHOT STRING STILL PRESENT in rebuilt runtime value")
                assert SCREENSHOT_SENTENCE not in new["english_literal"], (
                    "SCREENSHOT STRING STILL PRESENT in rebuilt literal")
                # 3. the rebuilt value is exactly the transformed Arabic
                assert new["english"] == expected_visual, key
                assert new["english_literal"] == expected_literal, key
                # 4. timing-tag parity is preserved
                assert bracket_sequence(new["english"]) == bracket_sequence(
                    target["english"]), key

            cleaned = expected_literal.replace("\\n", "").replace('\\"', "")
            assert "\\" not in cleaned, key
            for c in expected_visual:
                o = ord(c)
                assert o <= 127 or (0xE000 <= o < pua_max), (key, hex(o))
            assert new["english_literal"] == expected_literal, key
            assert new["english"] == expected_visual == ft.decode_lang_value(
                new["english_literal"]), key
            assert expected_visual.count("\n") == arabic.count("\n"), key
            if is_master:
                assert bracket_sequence(expected_visual) == bracket_sequence(
                    master[key]["english"]), key
            verified += 1
        except AssertionError as exc:
            failures.append((key, str(exc)))

    assert changed == len(expected_changed), "changed %d != expected %d" % (changed, len(expected_changed))
    assert verified == changed and not failures, failures[:5]

    report = dict(
        build=info["stage"],
        archive_rows=len(rows_new),
        changed_rows=changed,
        verified_changed=verified,
        failed_changes=[],
        screenshot_record=SCREENSHOT_RECORD,
        screenshot_check="PASS" if verified else "FAIL",
        mapping_size=len(mapping),
        pua_max_hex=hex(pua_max),
        approved_pilot_hashes=approved,
        runtime_verified=False,
        installed=False,
        status="static_build_verified",
        notes=[
            "install gate: this build is NOT installed; live game keeps the subtitle POC",
            "screenshot sentence is provably transformed in the rebuilt english.lang",
            "str_video_dlc1_c01_intro_location_* family deliberately excluded (experiment)",
        ])
    (poc_dir / "VERIFY_REPORT.local.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("build", "archive_rows", "changed_rows",
                                             "verified_changed", "screenshot_check",
                                             "mapping_size", "status")}, indent=2))


if __name__ == "__main__":
    main()
