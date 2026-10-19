#!/usr/bin/env python3
"""Assemble the sidecar's ``release_data`` from tracked data and the pinned font.

This is safe to run in CI: it copies only public translation partitions and the
pinned OFL font, then converts the tracked PUA mapping into the internal
``BUILD_INFO.local.json`` shape expected by the frozen build pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASE_FILES = (
    "main_menu.json",
    "phase_25.json",
    "phase_50.json",
    "phase_75.json",
    "phase_100.json",
)
FONT_REMOTE = "fonts/complete/ttf/IBMPlexSansArabic-Regular.ttf"
FONT_NAME = "IBMPlexSansArabic-Regular.ttf"
FONT_SHA256 = "8e0f1046c736bf939d4939ee3ae0116acf61cbcd6592deae7656761627080981"
FONT_REVISION = "39276912b05f700ee1dd491950c35d8697214208"
FONT_BASE = (
    f"https://raw.githubusercontent.com/IBM/plex/{FONT_REVISION}/"
    "packages/plex-sans-arabic/"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_mapping(mapping: object) -> dict[str, str]:
    if not isinstance(mapping, dict) or not mapping:
        raise SystemExit("config/pua_mapping.json must contain a non-empty 'mapping' object")
    for source, target in mapping.items():
        if not (isinstance(source, str) and isinstance(target, str)):
            raise SystemExit("PUA mapping keys and values must be strings")
        if not source.startswith("U+") or not target.startswith("U+"):
            raise SystemExit(f"invalid PUA mapping entry {source!r} -> {target!r}")
    if len(set(mapping.values())) != len(mapping):
        raise SystemExit("PUA mapping has duplicate target code points")
    return mapping


def read_mapping(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"cannot read {path}: {error}") from error
    return validate_mapping(payload.get("mapping") if isinstance(payload, dict) else None)


def load_font(explicit: Path | None) -> bytes:
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.extend(
        (
            ROOT / "workspace" / "research" / FONT_NAME,
            ROOT / "release_data" / "font.ttf",
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            data = candidate.read_bytes()
            if sha256(data) != FONT_SHA256:
                raise SystemExit(f"font hash mismatch for {candidate}; refusing to use it")
            return data
    url = FONT_BASE + FONT_REMOTE
    print(f"downloading pinned font from {url}", file=sys.stderr)
    try:
        data = urllib.request.urlopen(url, timeout=60).read()
    except OSError as error:
        raise SystemExit(f"cannot download the pinned font: {error}") from error
    if sha256(data) != FONT_SHA256:
        raise SystemExit("downloaded font hash mismatch; refusing to use it")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "release_data")
    parser.add_argument("--font", type=Path, default=None)
    args = parser.parse_args()

    out = args.out.resolve()
    (out / "translation" / "arabic").mkdir(parents=True, exist_ok=True)
    (out / "font.ttf").write_bytes(load_font(args.font))

    for name in PHASE_FILES:
        source = ROOT / "translation" / "arabic" / name
        if not source.is_file():
            raise SystemExit(f"missing translation partition {source}")
        shutil.copy2(source, out / "translation" / "arabic" / name)

    mapping = read_mapping(ROOT / "config" / "pua_mapping.json")
    (out / "BUILD_INFO.local.json").write_text(
        json.dumps({"mapping": mapping}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "font": FONT_NAME,
                "mapping": len(mapping),
                "partitions": len(PHASE_FILES),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
