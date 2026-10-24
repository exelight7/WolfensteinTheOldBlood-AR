"""Package the offline Windows installer without redistributing game assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {"base/chunk0.index", "base/chunk0.resources", "base/graphicsdriverwarningloc.json"}


def validate_config(config: dict) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", config.get("app_version", "")):
        raise ValueError("invalid app_version")
    versions = config.get("supported_versions", [])
    if len(versions) != 1:
        raise ValueError("manual installer currently requires exactly one supported version")
    version = versions[0]
    hashes = [version.get("executable_sha256", "")]
    if version.get("executable") != "WolfOldBlood_x64.exe":
        raise ValueError("unsupported executable")
    for key in ("vanilla", "localized"):
        state = version.get(key, {})
        if set(state) != FILES:
            raise ValueError(f"{key} must name exactly the three affected files")
        hashes.extend(state.values())
    for state in version.get("also_accepted_states", []):
        if not {"base/chunk0.index", "base/chunk0.resources"}.issubset(state):
            raise ValueError("prior states must identify both archives")
        if set(state) - FILES - {"label"}:
            raise ValueError("unknown prior-state field")
        hashes.extend(value for key, value in state.items() if key != "label")
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes):
        raise ValueError("all hashes must be lowercase SHA256")


def build_package(sidecar: Path, config_path: Path, out: Path, templates: Path = ROOT / "release/manual") -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    if not sidecar.is_file() or sidecar.read_bytes()[:2] != b"MZ":
        raise ValueError("a frozen Windows wtob-build.exe is required")
    sources = {name: templates / name for name in ("Install.cmd", "Restore.cmd", "Manual.ps1", "README.md")}
    sources.update({"wtob-build.exe": sidecar, "supported_versions.json": config_path,
                    "licenses/IBM_Plex_OFL.txt": ROOT / "licenses/IBM_Plex_OFL.txt",
                    "licenses/LICENSE": ROOT / "LICENSE",
                    "licenses/THIRD_PARTY_NOTICES.md": ROOT / "THIRD_PARTY_NOTICES.md",
                    "licenses/PYTHON_DEPENDENCIES.txt": ROOT / "licenses/PYTHON_DEPENDENCIES.txt"})
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sources.items():
            raw = path.read_bytes()
            # Windows PowerShell 5.1 needs the BOM to read Arabic source reliably.
            if name == "Manual.ps1" and not raw.startswith(b"\xef\xbb\xbf"):
                raw = b"\xef\xbb\xbf" + raw
            archive.writestr(name, raw)
    return {"name": out.name, "version": config["app_version"], "size": out.stat().st_size,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar", type=Path, default=ROOT / "app/src-tauri/resources/sidecar/wtob-build.exe")
    parser.add_argument("--config", type=Path, default=ROOT / "config/supported_versions.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_package(args.sidecar, args.config, args.out), indent=2))


if __name__ == "__main__":
    main()
