"""Validate and merge logical Arabic batches, preserving English and source IDs."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from local_reference import generate


BRACKETS = re.compile(r"\[[^\]\r\n]*\]")
TOKENS = re.compile(r"\[[^\]\r\n]*\]|<[^>\r\n]+>|%[-+#0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLzjt]*[diuoxXfFeEgGaAcspn]|%\d+|\{[^}\r\n]+\}|(?<!\w)_[A-Za-z][A-Za-z0-9_]*|\$[A-Za-z][A-Za-z0-9_]*|\^[0-9]")
PUBLIC_FIELDS = ("id", "resource", "index", "location", "english_sha256", "arabic", "status", "notes", "context")


def validate(source, translation):
    errors = []
    for field in ("id", "english", "english_literal", "english_sha256", "source_key", "resource", "index", "location"):
        if source.get(field) != translation.get(field):
            errors.append("source_field_changed:" + field)
    english = source["english"]
    if hashlib.sha256(english.encode("utf-8")).hexdigest() != source["english_sha256"]:
        errors.append("source_hash_mismatch")
    arabic = translation.get("arabic", "")
    status = translation.get("status")
    if status == "do_not_translate":
        if arabic or not translation.get("notes"):
            errors.append("excluded_entry_requires_empty_arabic_and_reason")
        return errors
    if status != "translated" or not arabic.strip():
        errors.append("missing_translation_or_invalid_status")
    if not re.search(r"[\u0621-\u064a\u066e-\u06d3]", arabic):
        errors.append("no_arabic_letters")
    if Counter(TOKENS.findall(english)) != Counter(TOKENS.findall(arabic)):
        errors.append("placeholder_or_tag_mismatch")
    if BRACKETS.findall(english) != BRACKETS.findall(arabic):
        errors.append("timing_or_language_tag_order_changed")
    if english.count("\n") != arabic.count("\n"):
        errors.append("newline_count_changed")
    if any(english.count(c) != arabic.count(c) for c in ("\r", "\t")):
        errors.append("control_character_count_changed")
    if english.count("%") != arabic.count("%"):
        errors.append("percent_escape_count_changed")
    if any(0xE000 <= ord(c) <= 0xF8FF or 0xFB50 <= ord(c) <= 0xFDFF
           or 0xFE70 <= ord(c) <= 0xFEFF or 0x202A <= ord(c) <= 0x202E
           or 0x2066 <= ord(c) <= 0x2069 for c in arabic):
        errors.append("runtime_encoding_or_bidi_controls_in_master")
    return errors


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def save_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", nargs="+", type=Path)
    parser.add_argument("--phase", type=int, choices=(25, 50, 75, 100), required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    corpus_path = Path("workspace/all_text/ALL_CONFIRMED_TEXT.local.jsonl")
    corpus = read_rows(corpus_path)
    by_id = {row["id"]: row for row in corpus}
    batch = [row for path in args.batches for row in read_rows(path)]
    if len(by_id) != len(corpus) or len({row["id"] for row in batch}) != len(batch):
        parser.error("Duplicate corpus or batch IDs")
    errors = {}
    for row in batch:
        if row["id"] not in by_id:
            errors[row["id"]] = ["unknown_source_id"]
            continue
        failures = validate(by_id[row["id"]], row)
        previous = by_id[row["id"]]
        if previous["status"] != "untranslated" and previous.get("arabic") != row.get("arabic"):
            failures.append("conflicting_existing_translation")
        if failures:
            errors[row["id"]] = failures
    report_path = Path(f"workspace/translation_batches/phase{args.phase}/validation.local.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(dict(entries=len(batch), errors=errors), ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        print(json.dumps(errors, ensure_ascii=False, indent=2))
        raise SystemExit("Batch rejected; no translation data was changed")
    updates = {row["id"]: row for row in batch}
    merged = [dict(row, **{k: v for k, v in updates[row["id"]].items() if k in ("arabic", "status", "notes", "context")})
              if row["id"] in updates else row for row in corpus]
    counts = Counter(row["status"] for row in merged)
    processed = sum(counts[s] for s in ("translated", "reviewed", "in_game_verified", "do_not_translate"))
    report = dict(phase=args.phase, corpus_entries=len(corpus), batch_entries=len(batch), statuses=dict(counts),
                  processed_entries=processed, completion_percent=round(processed / len(corpus) * 100, 2),
                  translated_percent=round(sum(counts[s] for s in ("translated", "reviewed", "in_game_verified")) / len(corpus) * 100, 2),
                  source_preserved=True, placeholder_validation_passed=True, installed=False, reviewed=False)
    print(json.dumps(report, indent=2))
    if not args.apply:
        return
    primary = Path("reference/translation_master.local.jsonl")
    backup = report_path.parent / "pre_apply_backup"
    backup.mkdir(exist_ok=True)
    for path in (primary, corpus_path):
        dest = backup / path.name
        if not dest.exists():
            shutil.copy2(path, dest)
    public = [{key: row[key] for key in PUBLIC_FIELDS if key in row} for row in batch]
    public_path = Path(f"translation/arabic/phase_{args.phase}.json")
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save_rows(corpus_path, merged)
    merged_by_id = {row["id"]: row for row in merged}
    old_primary = read_rows(primary)
    new_primary = [dict(row, **{k: v for k, v in merged_by_id[row["id"]].items() if k in ("arabic", "status", "notes", "context")}) for row in old_primary]
    save_rows(primary, new_primary)
    generate(Path("reference/english_source.local.lang").read_bytes(), Path("reference"))
    lines = ["# All confirmed text — local bilingual reference", ""]
    for row in merged:
        lines += ["## " + row["id"], "", "STATUS: " + row["status"], "", "AR:", row["arabic"], "", "EN:", row["english"], ""]
    Path("workspace/all_text/ALL_CONFIRMED_TEXT.local.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    Path(f"reports/translation_phase_{args.phase}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
