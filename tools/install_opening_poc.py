"""Install the verified opening-runtime POC with verified backups. Never touch vanilla backup.

Hierarchy:
  workspace/backups/menu_pilot_original     = untouched vanilla/original game (never modified here)
  workspace/backups/subtitle_poc_pretest    = state before Subtitle POC testing (never deleted; not used here)
  workspace/backups/opening_runtime_pretest = state immediately before Opening Runtime POC testing

Behavior:
  * refuses to run while the game is executing
  * accepts only recognized live states (vanilla, menu pilot, subtitle POC; skips if POC already installed)
  * stage -> hash -> atomic pair replace -> post-hash verify -> rollback on failure
  * automatic rollback source is the pretest backup taken immediately before the test
"""
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
    "chunk0.index": "3aa93b17e2d2167e686758428bdcc84c1895b61f1512a01814f0e62314cba750",
    "chunk0.resources": "7a76fa93c0f122c556dcf8eeac94630a1d4a657db94c57cc15e41c506735e5b4",
}
MENU_PILOT = {
    "chunk0.index": "15c551baaa051a95a994f114a2ed1ee2061983e37edeac6ae4ebf18ec8ad4464",
    "chunk0.resources": "5a61ac1d59fd10d4339bca4398324c08b09a149c75d5c6c82a1aa96a19801bc9",
}
SUBTITLE_POC = {
    "chunk0.index": "7fa60970e9a173fbf6400e86f103b5876350b04b5e6a113e98cf31d87f92feba",
    "chunk0.resources": "ed6b0ec46d11e652819d3185637568a41c18572b6045eacd61e108975869b302",
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


def label(state):
    for name, known in (("original", ORIGINAL), ("menu_pilot", MENU_PILOT), ("subtitle_poc", SUBTITLE_POC)):
        if all(state[n] == known[n] for n in FILES):
            return name
    return None


def replace_pair(sources, destinations, expected, rollback):
    staged = {}
    replaced = []
    try:
        for name in FILES:
            with tempfile.NamedTemporaryFile(prefix="arabic-opening-", suffix=".tmp",
                                             dir=destinations[name].parent, delete=False) as stream:
                staged[name] = Path(stream.name)
            shutil.copyfile(sources[name], staged[name])
            if digest(staged[name]) != expected[name]:
                raise ValueError("Staged file hash mismatch")
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


def install(game, build=None, pretest=None):
    game = game.resolve(strict=True)
    build = (build or Path(__file__).resolve().parents[1] / "workspace" / "opening_runtime_poc").resolve(strict=True)
    pretest = (pretest or Path(__file__).resolve().parents[1] / "workspace" / "backups" / "opening_runtime_pretest").resolve()
    if game == pretest.parent or game in pretest.parents:
        raise ValueError("Backup must be outside the game installation")
    if not (game / "WolfOldBlood_x64.exe").is_file():
        raise ValueError("Game executable not found")
    manifest = json.loads((build / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    verify = json.loads((build / "VERIFY_REPORT.local.json").read_text(encoding="utf-8"))
    if manifest.get("stage") != "opening_runtime_poc":
        raise ValueError("Unexpected build stage")
    if verify.get("status") != "static_build_verified" or verify.get("changed_rows") != 48:
        raise ValueError("Opening POC verification manifest does not pass")
    if verify.get("screenshot_check") != "PASS":
        raise ValueError("Screenshot-string assertion does not pass")
    if manifest["source_hashes"] != ORIGINAL:
        raise ValueError("Build is not derived from the verified original archives")
    outputs = manifest["output_hashes"]
    if set(outputs) != set(files := FILES):
        raise ValueError("Unexpected build manifest")
    if any(digest(build / n) != outputs[n] for n in FILES):
        raise ValueError("Opening POC hashes do not match BUILD_INFO.local.json")

    targets = {n: game / "base" / n for n in FILES}
    current = {n: digest(targets[n]) for n in FILES}
    state_label = label(current)
    if state_label is None:
        raise ValueError("Current game hashes are unknown; refusing replacement")
    if current == outputs:
        print(json.dumps(dict(status="already_installed", live_label=state_label,
                              installed_hashes={n: digest(targets[n]) for n in FILES}), indent=2))
        return
    recognized = (ORIGINAL, MENU_PILOT, SUBTITLE_POC)
    if not any(all(current[n] == known[n] for n in FILES) for known in recognized):
        raise ValueError("Current game hashes are not recognized; refusing replacement")

    require_stopped()
    # Capture the live state as the pretest rollback point (exclusive creation;
    # refuse an existing pretest whose hashes no longer match the live state).
    if pretest.exists():
        for name in FILES:
            if not (pretest / name).is_file() or digest(pretest / name) != current[name]:
                raise ValueError("Existing pretest backup does not match current live state; refusing")
    else:
        pretest.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            with targets[name].open("rb") as source, (pretest / name).open("xb") as dest:
                shutil.copyfileobj(source, dest)
            if digest(pretest / name) != current[name]:
                raise ValueError("Pretest backup verification failed")
        state_copy = dict(current)
        state_copy["state_label"] = state_label
        (pretest / "backup_manifest.local.json").write_text(
            json.dumps(dict(game=str(game), pretest_hashes=state_copy), indent=2) + "\n",
            encoding="utf-8")

    require_stopped()
    replace_pair({n: build / n for n in FILES}, targets, outputs,
                 {n: (pretest / n) for n in FILES})
    after = {n: digest(targets[n]) for n in FILES}
    if any(after[n] != outputs[n] for n in FILES):
        raise ValueError("Installed file hash mismatch; rolled back")
    state = dict(game=str(game), build=str(build), pretest=str(pretest),
                 installed=True, pretest_label=state_label, in_game_verified=False,
                 installed_hashes=after)
    (pretest / "install_state.local.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True,
                        help="Wolfenstein The Old Blood installation directory")
    parser.add_argument("--build", type=Path, default=None,
                        help="opening POC build directory (default workspace/opening_runtime_poc)")
    parser.add_argument("--pretest", type=Path, default=None,
                        help="pretest backup directory (default workspace/backups/opening_runtime_pretest)")
    args = parser.parse_args()
    install(args.game, args.build, args.pretest)


if __name__ == "__main__":
    main()
