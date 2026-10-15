"""Audit every indexed chunk payload and preserve local text-source candidates."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from archive_inventory import records, payload
from extract_dialogue import referenced_ids


def analyze(data):
    ids = referenced_ids(data)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = None
    if text is not None and sum(ord(c) < 32 and c not in "\r\n\t" for c in text) > len(text) // 100:
        text = None
    return ids, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("workspace/text_audit"))
    parser.add_argument("--original-chunk0", type=Path, default=Path("workspace/backups/menu_pilot_original"))
    args = parser.parse_args()
    game = args.game.resolve(strict=True)
    out = args.output.resolve()
    if out == game or game in out.parents:
        parser.error("Audit output must be outside the game")
    out.mkdir(parents=True, exist_ok=True)
    master = [json.loads(line) for line in Path("reference/translation_master.local.jsonl").read_text(encoding="utf-8").splitlines() if line]
    known = {row["source_key"] for row in master}
    references, unknown = defaultdict(list), defaultdict(list)
    results, failures, sources = [], [], []
    cache = {}
    total = decoded = 0
    for installed_index in sorted((game / "base").glob("chunk*.index")):
        index = args.original_chunk0 / installed_index.name if installed_index.stem == "chunk0" else installed_index
        archive = index.with_suffix(".resources")
        entries, info = records(index.read_bytes(), archive.stat().st_size)
        if info["trailing_bytes"]:
            raise ValueError("Index trailing bytes")
        total += len(entries)
        with archive.open("rb") as stream:
            for entry in entries:
                record = dict(chunk=index.stem, ordinal=entry["ordinal"], type=entry["names"][0], resource=entry["names"][2])
                try:
                    data = payload(stream, entry)
                except Exception as error:
                    failures.append(dict(record, error=str(error)))
                    continue
                decoded += 1
                digest = hashlib.sha256(data).hexdigest()
                # Repeated resources still receive coverage records and provenance.
                if digest not in cache:
                    ids, text = analyze(data)
                    cache[digest] = ids
                    if text is not None:
                        name = f"source_{len(sources):05d}.local.txt"
                        (out / name).write_bytes(data)
                        sources.append(dict(record, sha256=digest, file=name, size=len(data)))
                    if Path(record["resource"]).suffix.lower() in (".bswf", ".swf"):
                        name = f"binary_{len(sources):05d}.local.bin"
                        (out / name).write_bytes(data)
                        sources.append(dict(record, sha256=digest, file=name, size=len(data)))
                ids = cache[digest]
                for key in ids:
                    (references if key in known else unknown)[key].append(record)
                results.append(dict(record, sha256=digest, decoded_size=len(data), localization_refs=len(ids)))
        print(index.stem, f"{decoded}/{total} decoded", "failures", len(failures), flush=True)
    for name, value in (("coverage", results), ("failures", failures), ("sources", sources),
                        ("references", references), ("unknown_references", unknown)):
        (out / f"{name}.local.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = dict(indexed_records=total, decoded_records=decoded, payload_scan_percent=round(decoded / total * 100, 4),
                   unique_payloads=len(cache), decode_failures=len(failures), known_localization_ids_referenced=len(references),
                   unknown_reference_ids=len(unknown), preserved_candidate_sources=len(sources),
                   record_types=dict(Counter(r["type"] for r in results)),
                   full_game_text_completion="UNVERIFIED; raw-payload scanning is not proof of image/video/runtime-only text coverage")
    (out / "summary.local.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "record_types"}, indent=2))


if __name__ == "__main__":
    main()
