"""Install or restore the experimental menu pilot with verified backups."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


FILES = ("chunk0.index", "chunk0.resources")
ORIGINAL = {
    "chunk0.resources": "7a76fa93c0f122c556dcf8eeac94630a1d4a657db94c57cc15e41c506735e5b4",
    "chunk0.index": "3aa93b17e2d2167e686758428bdcc84c1895b61f1512a01814f0e62314cba750",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_stopped():
    if os.name == "nt":
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "if (Get-Process WolfOldBlood_x64 -ErrorAction SilentlyContinue) { exit 1 }"],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError("Close Wolfenstein: The Old Blood before installing or restoring.")


def replace_pair(sources, destinations, expected, rollback):
    staged = {}
    replaced = []
    try:
        for name in FILES:
            with tempfile.NamedTemporaryFile(prefix="arabic-pilot-", suffix=".tmp",
                                             dir=destinations[name].parent, delete=False) as stream:
                staged[name] = Path(stream.name)
            shutil.copyfile(sources[name], staged[name])
            if digest(staged[name]) != expected[name]:
                raise ValueError("Staged file hash mismatch")
        for name in FILES:
            os.replace(staged[name], destinations[name])
            replaced.append(name)
        if any(digest(destinations[n]) != expected[n] for n in FILES):
            raise ValueError("Installed file hash mismatch")
    except Exception:
        for name in reversed(replaced):
            shutil.copyfile(rollback[name], destinations[name])
            if digest(destinations[name]) != digest(rollback[name]):
                raise RuntimeError("Rollback verification failed; restore verified backups manually")
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)


def install(game, build, backup, uninstall=False):
    game, build, backup = game.resolve(strict=True), build.resolve(strict=True), backup.resolve()
    if game == backup or game in backup.parents:
        raise ValueError("Backup must be outside the game installation")
    if not (game / "WolfOldBlood_x64.exe").is_file():
        raise ValueError("Game executable not found")
    manifest = json.loads((build / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    if manifest["source_hashes"] != ORIGINAL or set(manifest["output_hashes"]) != set(FILES):
        raise ValueError("Unexpected build manifest")
    outputs = manifest["output_hashes"]
    targets = {n: game / "base" / n for n in FILES}
    build_files = {n: build / n for n in FILES}
    backups = {n: backup / n for n in FILES}
    require_stopped()
    desired = ORIGINAL if uninstall else outputs
    current = {n: digest(targets[n]) for n in FILES}
    if current == desired:
        print("Original files already restored." if uninstall else "Pilot already installed and verified.")
        return
    if current != (outputs if uninstall else ORIGINAL):
        raise ValueError("Current game hashes are unknown; refusing replacement")
    if any(digest(build_files[n]) != outputs[n] for n in FILES):
        raise ValueError("Build hashes do not match manifest (required for rollback)")
    if uninstall:
        if any(not backups[n].is_file() or digest(backups[n]) != ORIGINAL[n] for n in FILES):
            raise ValueError("Original backups are missing or corrupted")
        replace_pair(backups, targets, ORIGINAL, build_files)
    else:
        backup.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            if backups[name].exists():
                if digest(backups[name]) != ORIGINAL[name]:
                    raise ValueError("Existing backup has wrong hash; refusing overwrite")
            else:
                # Exclusive creation prevents accidental replacement of an existing backup.
                with targets[name].open("rb") as source, backups[name].open("xb") as dest:
                    shutil.copyfileobj(source, dest)
            if digest(backups[name]) != ORIGINAL[name]:
                raise ValueError("Backup verification failed")
        (backup / "backup_manifest.local.json").write_text(
            json.dumps(dict(game=str(game), original_hashes=ORIGINAL), indent=2) + "\n", encoding="utf-8")
        require_stopped()
        replace_pair(build_files, targets, outputs, backups)
    state = dict(game=str(game), build=str(build), backup=str(backup),
                 installed=not uninstall, in_game_verified=False,
                 installed_hashes={n: digest(targets[n]) for n in FILES})
    (backup / "install_state.local.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--build", type=Path, default=Path("workspace/menu_pilot"))
    parser.add_argument("--backup", type=Path, default=Path("workspace/backups/menu_pilot_original"))
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    install(args.game, args.build, args.backup, args.uninstall)


if __name__ == "__main__":
    main()
