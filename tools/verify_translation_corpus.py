"""Verify the entire staged corpus against immutable English and public Arabic data."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from apply_translation_batch import read_rows, validate
from collect_text_corpus import record
from local_reference import parse_lang


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    args = parser.parse_args()
    raw = Path("reference/english_source.local.lang").read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    if source_hash != "6eeb295fffe09106c839c05fcfda8ef97913e3b0bcdee4057314135c4a7c0d1a":
        raise ValueError("Original English table changed; explicit source migration required")
    original = parse_lang(raw)
    warnings = json.loads((args.game / "base/graphicsdriverwarningloc.json").read_text(encoding="utf-8-sig"))
    original += [record("base/graphicsdriverwarningloc.json", key, value, "confirmed")
                 for key, value in warnings.items() if key.startswith("english_")]
    corpus = read_rows(Path("workspace/all_text/ALL_CONFIRMED_TEXT.local.jsonl"))
    by_id = {row["id"]: row for row in corpus}
    if len(by_id) != len(corpus) or set(by_id) != {row["id"] for row in original}:
        raise ValueError("Corpus IDs are missing, duplicated or changed")
    for source in original:
        errors = validate(source, by_id[source["id"]])
        if errors:
            raise ValueError(f"Invalid translation {source['id']}: {errors}")
    primary = read_rows(Path("reference/translation_master.local.jsonl"))
    if len(primary) != 3572 or {row["id"] for row in primary} != {row["id"] for row in original[:3572]}:
        raise ValueError("Primary local master ID set changed")
    for row in primary:
        for key in ("english", "english_literal", "english_sha256", "arabic", "status"):
            if row.get(key) != by_id[row["id"]].get(key):
                raise ValueError(f"Local masters disagree: {row['id']} / {key}")
    public = []
    for path in sorted(Path("translation/arabic").glob("*.json")):
        public += json.loads(path.read_text(encoding="utf-8"))
    if len(public) != len(corpus) or len({row["id"] for row in public}) != len(public):
        raise ValueError("Public corpus IDs are missing or duplicated")
    for row in public:
        if "english" in row or "english_literal" in row:
            raise ValueError("Proprietary English field in public translation data")
        if row["id"] not in by_id:
            raise ValueError("Unknown public source ID")
        for key in ("english_sha256", "arabic", "status"):
            if row.get(key) != by_id[row["id"]].get(key):
                raise ValueError(f"Public/local mismatch: {row['id']} / {key}")
    counts = Counter(row["status"] for row in corpus)
    if set(counts) - {"translated", "do_not_translate"}:
        raise ValueError("Unprocessed or unexpectedly promoted translation records")
    exclusions = Counter()
    for row in corpus:
        if row["status"] != "do_not_translate":
            continue
        value, key = row["english"].strip(), row.get("source_key", "")
        kind = ("empty_source" if not value else "source_placeholder" if value == "< New String >"
                else "keyboard_labels" if key.startswith("#str_key_")
                else "internal_leaderboard_identifiers" if key.startswith("#str_leaderboard_")
                else "font_coverage_metadata" if key == "#str_aaa_needed_characters"
                else "missingtext_placeholder" if value == "missingtext"
                else "numeric_identifier" if value.isdigit() else "timing_only")
        exclusions[kind] += 1
    report = dict(scope="Fixed confirmed electronic-text corpus, not all visible game assets", total_records=len(corpus),
                  statuses=dict(counts), completion_percent=100, translated_percent=round(counts["translated"] / len(corpus) * 100, 2),
                  exclusions=dict(exclusions), source_table_sha256=source_hash,
                  source_ids_values_literals_and_hashes_preserved=True,
                  all_tokens_timing_and_controls_valid=True, public_ids_unique_and_english_free=True,
                  local_masters_agree=True, full_linguistic_review=False, new_runtime_install=False,
                  broad_in_game_qa=False, remaining_extraction_scope_unverified=True)
    Path("reports/translation_final_qa.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
