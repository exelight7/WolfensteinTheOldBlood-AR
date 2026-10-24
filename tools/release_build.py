#!/usr/bin/env python3
"""Release sidecar: build the localization payload from the user's own files.

The public installer never ships ``chunk0.index`` / ``chunk0.resources``. Instead
this tool:

1. reads the user's verified vanilla ``chunk0`` archives (or the app's verified
   backup of them),
2. extracts ``strings/english.lang`` from those archives,
3. joins every row with the shipped Arabic translation by ID **and validates the
   shipped English SHA-256**, so no English source text is shipped,
4. runs the frozen localization build pipeline against a temporary workspace,
5. emits ``chunk0.index``, ``chunk0.resources``,
   ``graphicsdriverwarningloc.json`` and a hash manifest.

The app verifies every output hash before touching the game.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
GAME_VERSION = "616161"


def find_data_dir() -> Path:
    candidates = []
    override = os.environ.get("WTOB_RELEASE_DATA")
    if override:
        candidates.append(Path(override))
    if getattr(sys, "frozen", False):
        frozen_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(frozen_root / "release_data")
        candidates.append(Path(sys.executable).parent / "release_data")
    candidates.append(TOOLS.parent / "release_data")
    candidates.append(TOOLS / "release_data")
    for candidate in candidates:
        if (candidate / "BUILD_INFO.local.json").is_file() and (candidate / "font.ttf").is_file():
            return candidate
    raise SystemExit(
        "release_data is missing (need BUILD_INFO.local.json, font.ttf and translation/arabic/*.json)"
    )


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_partitions(data_dir: Path, target: Path, phase_files) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name in phase_files:
        shutil.copy2(data_dir / "translation" / "arabic" / name, target / name)


def build_master(lang_rows, records, loose_json):
    master = []
    for record in records:
        if record["resource"] == "strings/english.lang":
            key = record["id"].rsplit(":", 1)[1]
            row = lang_rows.get(key)
            if row is None:
                raise SystemExit(f"english.lang is missing key {key}")
            if row["english_sha256"] != record["english_sha256"]:
                raise SystemExit(f"english source hash mismatch for {key}; unsupported game text")
            master.append(
                {
                    "source_key": key,
                    "english": row["english"],
                    "english_literal": row["english_literal"],
                    "english_sha256": row["english_sha256"],
                    "status": record["status"],
                    "arabic": record["arabic"],
                }
            )
        elif record["resource"] == "base/graphicsdriverwarningloc.json":
            value = loose_json.get(record["location"])
            if value is None:
                raise SystemExit(f"graphicsdriverwarningloc.json is missing {record['location']}")
            if sha_bytes(value.encode("utf-8")) != record["english_sha256"]:
                raise SystemExit(
                    f"graphicsdriverwarningloc.json source hash mismatch for {record['location']}"
                )
        else:
            raise SystemExit(f"unexpected resource in canonical data: {record['resource']}")
    return master


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True, help="game root, or a folder holding base/")
    parser.add_argument("--baseline", type=Path, default=None,
                        help="flat folder with verified vanilla chunk0.index/resources")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--version", default="1.0.1")
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()

    data_dir = find_data_dir()
    game = args.game.resolve()
    baseline = args.baseline.resolve() if args.baseline else None

    archive_dir = baseline if baseline is not None else game / "base"
    source_index = archive_dir / "chunk0.index"
    source_resources = archive_dir / "chunk0.resources"
    if not source_index.is_file() or not source_resources.is_file():
        raise SystemExit(f"vanilla chunk0 files not found in {archive_dir}")

    loose_candidates = []
    if baseline is not None:
        loose_candidates.append(baseline / "graphicsdriverwarningloc.json")
    loose_candidates.append(game / "base" / "graphicsdriverwarningloc.json")
    loose_path = next((path for path in loose_candidates if path.is_file()), None)

    raw_index = source_index.read_bytes()
    raw_resources = source_resources.read_bytes()

    sys.path.insert(0, str(TOOLS))
    from archive_inventory import records, payload  # noqa: E402
    from local_reference import parse_lang  # noqa: E402
    import build_runtime_localization as brl  # noqa: E402
    import build_runtime_complete as brc  # noqa: E402

    if sha_bytes(raw_index) != brl.SOURCE_HASHES["chunk0.index"] or \
            sha_bytes(raw_resources) != brl.SOURCE_HASHES["chunk0.resources"]:
        raise SystemExit(
            "chunk0 archives are not the supported vanilla build; refusing to build"
        )

    entries, _ = records(raw_index, len(raw_resources))
    lang_entry = next((entry for entry in entries if entry["names"][2] == "strings/english.lang"), None)
    if lang_entry is None:
        raise SystemExit("strings/english.lang not found in the archive")
    raw_lang = payload(io.BytesIO(raw_resources), lang_entry)
    lang_rows = {row["source_key"]: row for row in parse_lang(raw_lang)}

    canonical = []
    for name in brl.PHASE_FILES[100]:
        canonical += json.loads(
            (data_dir / "translation" / "arabic" / name).read_text(encoding="utf-8")
        )
    if len({row["id"] for row in canonical}) != len(canonical):
        raise SystemExit("duplicate IDs in shipped canonical data")

    loose_json = {}
    if loose_path is not None:
        loose_json = json.loads(loose_path.read_bytes().decode("utf-8-sig"))

    master = build_master(lang_rows, canonical, loose_json)

    work = Path(tempfile.mkdtemp(prefix="wtob-release-"))
    try:
        (work / "reference").mkdir(parents=True)
        (work / "translation" / "arabic").mkdir(parents=True)
        copy_partitions(data_dir, work / "translation" / "arabic", brl.PHASE_FILES[100])
        (work / "reference" / "translation_master.local.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in master),
            encoding="utf-8",
            newline="\n",
        )

        backup_dir = work / "workspace" / "backups" / "menu_pilot_original"
        backup_dir.mkdir(parents=True)
        shutil.copy2(source_index, backup_dir / "chunk0.index")
        shutil.copy2(source_resources, backup_dir / "chunk0.resources")

        font_dir = work / "workspace" / "research"
        font_dir.mkdir(parents=True)
        font_path = font_dir / "IBMPlexSansArabic-Regular.ttf"
        shutil.copy2(data_dir / "font.ttf", font_path)

        v4_dir = work / "workspace" / "opening_runtime_poc_v4"
        v4_dir.mkdir(parents=True)
        shutil.copy2(data_dir / "BUILD_INFO.local.json", v4_dir / "BUILD_INFO.local.json")

        if loose_path is None:
            raise SystemExit("graphicsdriverwarningloc.json is missing; cannot build loose text")
        game_view = work / "game"
        (game_view / "base").mkdir(parents=True)
        shutil.copy2(loose_path, game_view / "base" / "graphicsdriverwarningloc.json")

        out_full = work / "out" / "runtime_full"
        out_complete = work / "out" / "runtime_complete"

        brl.ROOT = work
        brl.BACKUP_DIR = backup_dir
        brl.FONT_PATH = font_path
        brl.V4_INFO = v4_dir / "BUILD_INFO.local.json"
        brl.DEFAULT_GAME = game_view

        previous_argv = sys.argv
        try:
            sys.argv = [
                "release-build", "--phase", "100", "--out", str(out_full),
                "--stage", "runtime_full", "--game", str(game_view),
            ]
            brl.main()
        finally:
            sys.argv = previous_argv

        brc.ROOT = work
        brc.BASE = out_full
        brc.OUT = out_complete
        brc.FONT = font_path
        brc.main()

        args.out.mkdir(parents=True, exist_ok=True)
        files = {}
        for name in ("chunk0.index", "chunk0.resources", "graphicsdriverwarningloc.json"):
            source = (out_full if name == "graphicsdriverwarningloc.json" else out_complete) / name
            target = args.out / name
            shutil.copy2(source, target)
            files[name] = sha_file(target)

        manifest = {
            "schema": 1,
            "version": args.version,
            "channel": "stable",
            "gameVersion": GAME_VERSION,
            "generatedAt": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "sourceHashes": {
                "chunk0.index": sha_bytes(raw_index),
                "chunk0.resources": sha_bytes(raw_resources),
            },
            "files": files,
            "note": "generated from the user's own vanilla game files; no game assets are redistributed",
        }
        (args.out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({"ok": True, "out": str(args.out), "version": args.version,
                          "files": files}, indent=2))
    finally:
        if args.keep_work:
            print(f"work directory kept at {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
