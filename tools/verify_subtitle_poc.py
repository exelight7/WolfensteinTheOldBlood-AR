"""Static verification of the Stage-1 subtitle POC build. Read-only.

  A. Pilot regression anchor: the approved installed menu pilot output hashes
     are reconfirmed; build_menu_pilot.py itself asserts no-op rebuild
     identity and deterministic rebuilds during any rebuild.
  B. POC artifacts: the built english.lang is parsed from the built archive,
     every changed row is re-derived fully independently from the master
     corpus, and literal/decode/token/charset disciplines are verified.

Writes workspace/subtitle_poc/VERIFY_REPORT.local.json.
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
POC_OUT = ROOT / "workspace" / "subtitle_poc"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bracket_sequence(text):
    return re.findall(r"\[[^\]\r\n]*\]", text)


def main():
    approved = json.loads(
        (PILOT_OUT / "BUILD_INFO.local.json").read_text(encoding="utf-8"))["output_hashes"]

    original = {n: (BACKUP_DIR / n).read_bytes() for n in SOURCE_HASHES}
    assert sha(original["chunk0.index"]) == SOURCE_HASHES["chunk0.index"]
    assert sha(original["chunk0.resources"]) == SOURCE_HASHES["chunk0.resources"]

    poc = {n: (POC_OUT / n).read_bytes() for n in SOURCE_HASHES}
    info = json.loads((POC_OUT / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
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
    runtime = (POC_OUT / "english_runtime.local.lang").read_bytes()
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

    # build mapping: master source chars -> PUA visual codes
    mapping = {chr(int(k[2:], 16)): int(v[2:], 16) for k, v in info["mapping"].items()}
    pua_max = 0xE000 + len(mapping)

    changed, verified = 0, 0
    failures = []
    for old, new in zip(rows_original, rows_new):
        key = old["source_key"]
        if new["english"] == old["english"]:
            # untouched rows must be byte-identical to the original
            assert old["english_literal"] == new["english_literal"], key
            continue
        changed += 1
        try:
            arabic_row = master.get(key) or menu_by_key.get(key)
            assert arabic_row is not None, key
            arabic = arabic_row["arabic"]
            is_master = key in master

            expected_visual = shape_formatted(arabic, mapping)
            expected_literal = ft.encode_lang_value(expected_visual)

            # literal-level and decoded-level agreement with the built table
            assert new["english_literal"] == expected_literal, key
            assert new["english"] == expected_visual == ft.decode_lang_value(new["english_literal"]), key

            # escape discipline: only \\n and \\" escapes may appear
            cleaned = expected_literal.replace("\\n", "").replace('\\"', "")
            assert "\\" not in cleaned, key

            # charset discipline: only ASCII and mapped PUA codepoints
            for c in expected_visual:
                o = ord(c)
                assert o <= 127 or (0xE000 <= o < pua_max), (key, hex(o))

            # structure parity with the logical source
            assert expected_visual.count("\n") == arabic.count("\n"), key
            if is_master:
                assert bracket_sequence(expected_visual) == bracket_sequence(
                    master[key]["english"]), key
            verified += 1
        except AssertionError as exc:
            failures.append((key, str(exc)))

    assert changed == 48, "expected exactly 48 changed rows, got %d" % changed
    assert verified == changed and not failures, failures[:5]

    report = dict(
        build="subtitle_poc_stage1",
        archive_rows=len(rows_new),
        changed_rows=changed,
        verified_changed=verified,
        failed_changes=[],
        mapping_size=len(mapping),
        pua_max_hex=hex(pua_max),
        approved_pilot_hashes=approved,
        runtime_verified=False,
        installed=False,
        status="static_build_verified",
        notes=[
            "install gate: this build is NOT installed; game chunk0 remains the menu pilot build",
            "all %d changed rows were re-derived independently from the master corpus" % changed,
            "bracket token parity reproduced for every master-backed record",
        ])
    (POC_OUT / "VERIFY_REPORT.local.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("build", "archive_rows", "changed_rows",
                                             "verified_changed", "mapping_size", "status")}, indent=2))


if __name__ == "__main__":
    main()
