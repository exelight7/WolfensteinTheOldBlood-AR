#!/usr/bin/env python3
"""Generate the camelCase update manifest consumed by the app updater."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

REPO = "https://github.com/exelight7/WolfensteinTheOldBlood-AR"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--tag", default=None)
    parser.add_argument("--output", type=Path, default=Path("release/release-manifest.json"))
    parser.add_argument("--minimum-app-version", default="1.0.0")
    parser.add_argument("--game-version", default="616161")
    args = parser.parse_args()

    version = args.version.removeprefix("v")
    tag = args.tag or f"v{version}"
    installer = args.installer.resolve()
    if not installer.is_file():
        raise SystemExit(f"installer not found: {installer}")

    name = installer.name
    url = f"{REPO}/releases/download/{tag}/{quote(name, safe='')}"
    manifest = {
        "version": version,
        "channel": "stable",
        "minimumAppVersion": args.minimum_app_version,
        "gameVersion": args.game_version,
        "releaseDate": datetime.now(timezone.utc).date().isoformat(),
        "files": [
            {
                "name": name,
                "kind": "installer",
                "size": installer.stat().st_size,
                "sha256": sha256(installer),
                "downloadUrl": url,
            }
        ],
        "changelogUrl": f"{REPO}/blob/main/CHANGELOG.md",
        "downloadUrl": url,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
