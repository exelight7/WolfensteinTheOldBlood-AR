"""Collect confirmed English text plus unreviewed literals without claiming visual coverage."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re


def binary_strings(data):
    found = {}
    for offset in range(len(data) - 4):
        size = int.from_bytes(data[offset:offset + 4], "little")
        if not 3 <= size <= 8192 or offset + 4 + size > len(data):
            continue
        raw = data[offset + 4:offset + 4 + size]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            continue
        if not re.search(r"[A-Za-z]{3}", text):
            continue
        found[offset + 4] = text
    return sorted(found.items())


def record(resource, location, english, kind):
    return dict(id=f"{resource}:{location}", resource=resource, location=location,
                english=english, english_sha256=hashlib.sha256(english.encode("utf-8")).hexdigest(),
                arabic="", status="untranslated" if kind == "confirmed" else "needs_classification",
                source_kind=kind)


def native_candidates(game):
    results = []
    for path in sorted(game.glob("*.exe")) + sorted(game.glob("*.dll")):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        for encoding, pattern in (("ascii", rb"[ -~]{6,}"), ("utf-16le", rb"(?:[ -~]\x00){6,}")):
            for match in re.finditer(pattern, data):
                value = match.group().decode(encoding)
                if not re.search(r"[A-Za-z]{3}", value):
                    continue
                item = record(path.name, f"{encoding}_{match.start()}", value, "native_binary_candidate")
                item["source_sha256"] = digest
                results.append(item)
    return results


def collect(master, game, audit):
    confirmed = [dict(row, source_kind="confirmed") for row in master]
    warning = game / "base" / "graphicsdriverwarningloc.json"
    for key, value in json.loads(warning.read_text(encoding="utf-8-sig")).items():
        if key.startswith("english_"):
            confirmed.append(record("base/graphicsdriverwarningloc.json", key, value, "confirmed"))
    candidates = []
    sources = json.loads((audit / "sources.local.json").read_text(encoding="utf-8"))
    quoted = re.compile(r'"((?:[^"\\]|\\.)*)"')
    for source in sources:
        resource = source["resource"]
        data = (audit / source["file"]).read_bytes()
        if resource.endswith(".lang"):
            continue
        if resource.endswith(".bswf"):
            strings = binary_strings(data)
        elif resource.endswith(".swf"):
            # Preserve HTML EditText candidates in original FWS assets; no glyph-outline decoding claim.
            strings = [(m.start(), m.group().decode("utf-8")) for m in re.finditer(rb"<p\b[^\x00]*?</p>", data)
                       if m.group().isascii()]
        else:
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            strings = [(m.start(1), m[1]) for m in quoted.finditer(text)]
        for offset, value in strings:
            if not value.strip() or value.startswith("#str_"):
                continue
            item = record(resource, f"offset_{offset}", value, "literal_candidate")
            item["source_sha256"] = source["sha256"]
            item["provenance_chunk"] = source["chunk"]
            if resource.endswith(".swf"):
                item["plain_text_hint"] = html.unescape(re.sub(r"<[^>]+>", "", value))
            candidates.append(item)
    unknown = json.loads((audit / "unknown_references.local.json").read_text(encoding="utf-8"))
    trimmed = {row["source_key"].strip(): row["source_key"] for row in master}
    unresolved, anomalies = [], []
    for key, refs in sorted(unknown.items()):
        if key in trimmed:
            anomalies.append(dict(referenced_key=key, preserved_source_key=trimmed[key], reason="source key has whitespace"))
        else:
            unresolved.append(dict(id="unresolved:" + key, source_key=key, english=None, arabic="", status="blocked_missing_source", references=refs))
    return confirmed, candidates, unresolved, anomalies


def preserve_external_translations(confirmed, previous, primary_ids):
    previous_by_id = {row["id"]: row for row in previous}
    for row in confirmed:
        if row["id"] in primary_ids or row["id"] not in previous_by_id:
            continue
        old = previous_by_id[row["id"]]
        if old["english_sha256"] != row["english_sha256"] or old["english"] != row["english"]:
            raise ValueError("External English source changed; explicit migration required")
        for key in ("arabic", "status", "notes", "context"):
            if key in old:
                row[key] = old[key]
    return confirmed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    args = parser.parse_args()
    master = [json.loads(line) for line in Path("reference/translation_master.local.jsonl").read_text(encoding="utf-8").splitlines()]
    audit = Path("workspace/text_audit")
    confirmed, candidates, unresolved, anomalies = collect(master, args.game, audit)
    native = native_candidates(args.game)
    output = Path("workspace/all_text")
    output.mkdir(parents=True, exist_ok=True)
    existing = output / "ALL_CONFIRMED_TEXT.local.jsonl"
    if existing.exists():
        previous = [json.loads(line) for line in existing.read_text(encoding="utf-8").splitlines() if line]
        confirmed = preserve_external_translations(confirmed, previous, {row["id"] for row in master})
    for filename, rows in (("ALL_CONFIRMED_TEXT", confirmed), ("LITERAL_CANDIDATES", candidates), ("UNRESOLVED_IDS", unresolved), ("NATIVE_CANDIDATES", native)):
        (output / f"{filename}.local.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    lines = ["# All confirmed electronic text (local)", "", "Includes the complete English localization table and loose graphics-driver warnings. Additional literal candidates and unresolved references are separate; this is not a claim of all visual or audio text.", ""]
    for row in confirmed:
        lines += ["## " + row["id"], "", "AR:", row["arabic"], "", "EN:", row["english"], ""]
    (output / "ALL_CONFIRMED_TEXT.local.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    known_values = {row["english"].strip() for row in master}
    phrases = {}
    for item in candidates:
        text = item.get("plain_text_hint", item["english"]).strip()
        if text in known_values or not re.search(r"[A-Za-z]{2} [A-Za-z]{2}", text):
            continue
        if any(c in text for c in ("/", "\\", "_", "{", "}", ";", "=")) or len(text) > 1500:
            continue
        phrases.setdefault(text, item)
    (output / "PHRASE_REVIEW.local.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in phrases.values()), encoding="utf-8")
    summary = dict(confirmed_text_records=len(confirmed), localization_table_records=len(master),
                   additional_confirmed_loose_records=len(confirmed) - len(master),
                   literal_candidates=len(candidates), native_binary_candidates=len(native),
                   distinct_phrase_candidates=len(phrases), unresolved_source_ids=len(unresolved),
                   source_key_anomalies=anomalies, archive_payload_audit_percent=100,
                   full_game_text_extraction_percent=None, translation_gate="SEE_PROJECT_STATE",
                   pending=["Classify embedded UI/declaration literals and distinguish runtime text from authoring/debug strings.",
                            "Resolve or document absent localization IDs without fabricating their text.",
                            "Review image, virtualtexture, video and native-executable text scope; raw scans cannot certify these."])
    (output / "summary.local.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
