"""Export local dialogue text and trace subtitle IDs through all chunk voice resources."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from archive_inventory import records, payload


KEY = re.compile(rb"#str_[A-Za-z0-9_]+")
ACTOR = re.compile(r"^#str_(?:agenttwo|commander[12]|kessler|naziofficer\w*|officer\w*|prisoner\w*|rudijager|rudolf)_(?:ai_|dlc1_|c\d)")


def referenced_ids(data):
    if not data.startswith(b"#VTR"):
        return {match.decode("ascii") for match in KEY.findall(data)}
    # Binary VTR strings are length-prefixed, not terminated by NUL.
    result = set()
    for match in KEY.finditer(data):
        start = match.start()
        if start < 4:
            continue
        length = int.from_bytes(data[start - 4:start], "little")
        if not 5 <= length <= 512 or start + length > len(data):
            continue
        value = data[start:start + length]
        if KEY.fullmatch(value):
            result.add(value.decode("ascii"))
    return result


def category(row, references):
    key = row["source_key"]
    if key.startswith("#str_npcname_") or key in ("#str_empty", "#str_unknown"):
        return None
    if key.startswith("#str_video_"):
        if "_location" in key:
            return None
        return "cutscene_dialogue"
    if key.startswith("#str_vo_"):
        return "story_dialogue"
    if key.startswith("#str_ev_"):
        return "ambient_dialogue"
    if ACTOR.match(key):
        return "combat_chatter" if "_ai_" in key else "ambient_dialogue"
    if references and key != "#str_empty" and row["english"].strip():
        return "voice_resource_dialogue"
    return None


def export(rows, references, output, scan):
    selected = []
    for row in rows:
        refs = references.get(row["source_key"], [])
        kind = category(row, refs)
        if not kind:
            continue
        chapter = re.search(r"(?:^|_)c(\d{2})(?:_|$)", row["source_key"])
        record = dict(row, category=kind,
                      chapter_code="c" + chapter[1] if chapter else "unassigned",
                      speaker_hint=row["source_key"][8:].split("_", 1)[0] if row["source_key"].startswith("#str_vo_") else None,
                      voice_references=refs)
        record["text_state"] = "empty" if not row["english"].strip() else "placeholder" if row["english"].strip() == "< New String >" else "text"
        selected.append(record)
    if len({r["id"] for r in selected}) != len(selected):
        raise ValueError("Duplicate dialogue IDs")
    output.mkdir(parents=True, exist_ok=True)
    def write_jsonl(path, entries):
        path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in entries), encoding="utf-8", newline="\n")
    write_jsonl(output / "ALL_DIALOGUE.local.jsonl", selected)
    lines = ["# All extracted dialogue — local reference", "", "Original text/timing/language tags are preserved. AR precedes EN. Speaker and chapter hints come from source IDs; a single entry can contain multiple speakers. Resource order is not playback order.", ""]
    for row in selected:
        lines += ["## " + row["source_key"], "", f"ID: {row['id']}", f"INDEX: {row['index']}",
                  f"GROUP: {row['chapter_code']} / {row['category']}", f"TEXT STATE: {row['text_state']}",
                  "", "AR:", row["arabic"], "", "EN:", row["english"], ""]
    (output / "ALL_DIALOGUE.local.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    groups = defaultdict(list)
    for row in selected:
        groups[row["chapter_code"]].append(row)
    for name, entries in groups.items():
        write_jsonl(output / f"{name}.local.jsonl", entries)
    summary = dict(dialogue_entries=len(selected), entries_with_text=sum(r["text_state"] == "text" for r in selected),
                   text_states=dict(Counter(r["text_state"] for r in selected)),
                   categories=dict(Counter(r["category"] for r in selected)),
                   groups={k: len(v) for k, v in sorted(groups.items())},
                   entries_with_voice_references=sum(bool(r["voice_references"]) for r in selected),
                   **scan,
                   limitations=["All written dialogue candidates in the extracted English table, not a transcription of uncaptioned audio.",
                                "IDs and voice-resource references are retained; timed blocks are not split or deduplicated.",
                                "Source naming is used for grouping; playback order and speaker ownership may need review."])
    (output / "summary.local.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--original-chunk0", type=Path, default=Path("workspace/backups/menu_pilot_original"))
    parser.add_argument("--master", type=Path, default=Path("reference/translation_master.local.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("workspace/dialogue"))
    args = parser.parse_args()
    game = args.game.resolve(strict=True)
    output = args.output.resolve()
    if output == game or game in output.parents:
        parser.error("Output must be outside the installed game")
    rows = [json.loads(line) for line in args.master.read_text(encoding="utf-8").splitlines() if line]
    for row in rows:
        if hashlib.sha256(row["english"].encode("utf-8")).hexdigest() != row["english_sha256"]:
            parser.error("English source hash mismatch")
    references = defaultdict(list)
    scan = dict(chunk_indexes_scanned=0, voice_resources_scanned=0, resource_types={}, unmatched_voice_ids=[])
    type_counts = Counter()
    keys = {row["source_key"] for row in rows}
    unmatched = set()
    empty_refs = 0
    for installed_index in sorted((game / "base").glob("chunk*.index")):
        # Use immutable originals for chunk0 while a modified pilot may be running.
        index = args.original_chunk0 / installed_index.name if installed_index.stem == "chunk0" else installed_index
        archive = index.with_suffix(".resources")
        entries, info = records(index.read_bytes(), archive.stat().st_size)
        if info["trailing_bytes"]:
            raise ValueError("Unexpected bytes after chunk index")
        scan["chunk_indexes_scanned"] += 1
        with archive.open("rb") as source:
            for entry in entries:
                if entry["names"][0] not in ("voiceover", "voicetrack"):
                    continue
                data = payload(source, entry)
                scan["voice_resources_scanned"] += 1
                type_counts[entry["names"][0]] += 1
                ids = referenced_ids(data)
                if "#str_empty" in ids:
                    empty_refs += 1
                for key in sorted(ids):
                    if key not in keys:
                        unmatched.add(key)
                    references[key].append(dict(chunk=index.stem, ordinal=entry["ordinal"],
                                                type=entry["names"][0], resource=entry["names"][2]))
        print(index.stem, "voice resources scanned", scan["voice_resources_scanned"])
    scan.update(resource_types=dict(type_counts), unmatched_voice_ids=sorted(unmatched),
                voice_resources_referencing_empty_key=empty_refs)
    output.mkdir(parents=True, exist_ok=True)
    (output / "voice_references.local.json").write_text(json.dumps(references, indent=2), encoding="utf-8")
    summary = export(rows, references, output, scan)
    print(json.dumps({k: v for k, v in summary.items() if k != "unmatched_voice_ids"}, indent=2))
    print("Unmatched voice IDs:", len(summary["unmatched_voice_ids"]), "(see local summary)")


if __name__ == "__main__":
    main()
