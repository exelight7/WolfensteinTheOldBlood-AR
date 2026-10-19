"""Install the verified runtime_complete build safely.

runtime_complete is built on top of the installed runtime_full corpus and adds:
  * 6 Enigma ids inserted into strings/english.lang
  * an Arabic paragraph in wtob_photosensitivity_row.bimage

Files replaced (both under <game>/base):
  * chunk0.index
  * chunk0.resources    (base/graphicsdriverwarningloc.json is untouched - already Arabic)

Safety: refuses to run while the game executes; recognizes only known live states;
skips if already installed; verifies against FULL_BUILD_MANIFEST + VERIFY_REPORT;
creates/validates a pretest backup; stage -> verify -> atomic replace -> post-hash
verify with rollback.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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
OPENING_POC_V1 = {
    "chunk0.index": "595334f75932b50e9ec31260c0f6dd183486d9ad693a98ac25d08a346c713546",
    "chunk0.resources": "8ae90ca5e02ceeec17ab27b25bf17aac65fdd691f030789ba248acd894d77a80",
}
OPENING_POC_V3 = {
    "chunk0.index": "595334f75932b50e9ec31260c0f6dd183486d9ad693a98ac25d08a346c713546",
    "chunk0.resources": "79c09ba561062bf39df3696b7ab75d2518cd591b8f8b4cbc9affc76e35cfe4c9",
}
OPENING_POC_V4 = {
    "chunk0.index": "85b441fdd0471f8ed8bad6c7d33d6cefc5fda15a3fd0c0e1579c920180ce22db",
    "chunk0.resources": "da3ab200295e144db74d74bed80359802146edb99d1d4bdbaa6ef8ec9473d16e",
}
RUNTIME_FULL = {
    "chunk0.index": "16e4124d8be2c5750a3d9d20fd6a3ce01daca5557ae5e4c6d0aab70dd2755a49",
    "chunk0.resources": "cd08ae5e44c9f026b44ad2329a56cf7d5277b673ce718ef6aa6f65b4a5973279",
}
RUNTIME_COMPLETE = {
    "chunk0.index": "1fe359341838300c4becbe73961b6c9ebf40d56e95b32259ea8fbaa5cd1312b3",
    "chunk0.resources": "9ed34c2c8746ceeaf04aa380d5ba5daeaf5cfb7d8feb702c9e76166a0abfbec4",
}
KNOWN_STATES = (
    ("original", ORIGINAL),
    ("menu_pilot", MENU_PILOT),
    ("subtitle_poc", SUBTITLE_POC),
    ("opening_runtime_poc_v1", OPENING_POC_V1),
    ("opening_runtime_poc_v3", OPENING_POC_V3),
    ("opening_runtime_poc_v4", OPENING_POC_V4),
    ("runtime_full", RUNTIME_FULL),
    ("runtime_complete", RUNTIME_COMPLETE),
)
RECOGNIZED_PRE_STATES = [n for n, _ in KNOWN_STATES if n != "runtime_complete"]


def digest(path):
    with Path(path).open("rb") as stream:
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
    for name, known in KNOWN_STATES:
        if all(state[n] == known[n] for n in FILES):
            return name
    return None


def replace_files(sources, destinations, expected, rollback):
    staged, replaced = {}, []
    try:
        for name in FILES:
            with tempfile.NamedTemporaryFile(prefix="arabic-complete-", suffix=".tmp",
                                             dir=destinations[name].parent, delete=False) as stream:
                staged[name] = Path(stream.name)
            shutil.copyfile(src=sources[name], dst=staged[name])
            if digest(staged[name]) != expected[name]:
                raise ValueError("Staged file hash mismatch: %s" % name)
        for name in FILES:
            os.replace(staged[name], destinations[name])
            replaced.append(name)
        for name in FILES:
            if digest(destinations[name]) != expected[name]:
                raise ValueError("Installed file hash mismatch: %s" % name)
    except Exception:
        for name in reversed(replaced):
            shutil.copyfile(rollback[name], destinations[name])
            if digest(destinations[name]) != digest(rollback[name]):
                raise RuntimeError("Rollback failed; restore manually from pretest backup")
        raise
    finally:
        for path in staged.values():
            Path(path).unlink(missing_ok=True)


def check_build(build):
    manifest = json.loads((build / "FULL_BUILD_MANIFEST.local.json").read_text(encoding="utf-8"))
    verify = json.loads((build / "VERIFY_REPORT.local.json").read_text(encoding="utf-8"))
    if manifest.get("stage") != "runtime_complete":
        raise ValueError("Unexpected build stage: %r" % manifest.get("stage"))
    if verify.get("status") != "static_build_verified" or verify.get("gate") is not True:
        raise ValueError("Build verification gate does not pass")
    if verify.get("only_intended_changed") is not True:
        raise ValueError("Build changed unintended resources")
    if verify.get("unintended_changed"):
        raise ValueError("Build has unintended changes: %r" % verify["unintended_changed"])
    if not verify.get("enigma_keys_present") or verify.get("image_change_region_ok") is not True:
        raise ValueError("Build content checks failed")
    if manifest.get("source_hashes", {}).get("chunk0.index") != RUNTIME_FULL["chunk0.index"] or \
            manifest.get("source_hashes", {}).get("chunk0.resources") != RUNTIME_FULL["chunk0.resources"]:
        raise ValueError("Build is not derived from the installed runtime_full archives")
    if set(manifest["output_hashes"]) & set(FILES) != set(FILES):
        raise ValueError("Manifest missing chunk0 outputs")
    for name in FILES:
        if digest(build / name) != manifest["output_hashes"][name]:
            raise ValueError("Build file hash mismatch: %s" % name)
    return manifest


def ensure_pretest(pretest, targets, current, state_label):
    if pretest.exists():
        for name in FILES:
            if not (pretest / name).is_file() or digest(pretest / name) != current[name]:
                raise ValueError("Existing pretest backup does not match live state; refusing")
        return
    pretest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(targets[name], pretest / name)
        if digest(pretest / name) != current[name]:
            raise ValueError("Pretest backup verification failed: %s" % name)
    state = dict(current)
    state["state_label"] = state_label
    (pretest / "backup_manifest.local.json").write_text(
        json.dumps(dict(game=str(targets[FILES[0]].parents[1]), pretest_hashes=state), indent=2) + "\n",
        encoding="utf-8")


def install(game, build=None, pretest=None):
    root = Path(__file__).resolve().parents[1]
    game = game.resolve(strict=True)
    build = (build or root / "workspace" / "runtime_complete").resolve(strict=True)
    pretest = (pretest or root / "workspace" / "backups" / "runtime_complete_originals").resolve()
    vanilla = (root / "workspace" / "backups" / "menu_pilot_original").resolve()
    if pretest == vanilla or vanilla in pretest.parents or pretest in vanilla.parents:
        raise ValueError("Refusing to use the vanilla backup directory as the pretest")
    if game == pretest.parent or game in pretest.parents:
        raise ValueError("Backup must be outside the game installation")
    if not (game / "WolfOldBlood_x64.exe").is_file():
        raise ValueError("Game executable not found")

    manifest = check_build(build)
    outputs = {n: manifest["output_hashes"][n] for n in FILES}
    targets = {n: game / "base" / n for n in FILES}
    for name in FILES:
        if not targets[name].is_file():
            raise ValueError("Live file missing: %s" % targets[name])
    current = {n: digest(targets[n]) for n in FILES}
    if current == outputs:
        print(json.dumps(dict(status="already_installed", live_label="runtime_complete",
                              installed_hashes=current), indent=2))
        return
    state_label = label(current)
    if state_label is None:
        raise ValueError("Current game hashes are unknown; refusing replacement")
    if state_label not in RECOGNIZED_PRE_STATES:
        raise ValueError("Current state %r is not recognized; refusing" % state_label)

    require_stopped()
    ensure_pretest(pretest, targets, current, state_label)
    require_stopped()
    replace_files({n: build / n for n in FILES}, targets, outputs, {n: pretest / n for n in FILES})
    after = {n: digest(targets[n]) for n in FILES}
    if any(after[n] != outputs[n] for n in FILES):
        raise ValueError("Installed file hash mismatch; rolled back")
    state = dict(game=str(game), build=str(build), pretest=str(pretest), installed=True,
                 pretest_label=state_label, in_game_verified=False, installed_hashes=after)
    (pretest / "install_state.local.json").write_text(json.dumps(state, indent=2) + "\n",
                                                      encoding="utf-8")
    print(json.dumps(dict(status="installed", **state), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--build", type=Path, default=None)
    parser.add_argument("--pretest", type=Path, default=None)
    args = parser.parse_args()
    try:
        install(args.game, args.build, args.pretest)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(dict(status="FAILED", error=str(exc)), indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
