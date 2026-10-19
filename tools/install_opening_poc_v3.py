"""Install the verified Opening Runtime POC V3 with a verified pretest backup.

Never touches the vanilla backup (workspace/backups/menu_pilot_original).

Hierarchy:
  workspace/backups/menu_pilot_original      = untouched vanilla/original game (NEVER modified here)
  workspace/backups/subtitle_poc_pretest     = state before Subtitle POC testing (never deleted; not used here)
  workspace/backups/opening_runtime_pretest  = state before Opening Runtime POC v1 testing (never modified here)
  workspace/backups/opening_runtime_v3_pretest = state immediately before Opening Runtime POC v3 testing

V3 differs from v1 only by the Candidate C span-order correction applied to
#str_vo_agentone_dlc1_c01_123 and #str_vo_agentone_dlc1_c01_123_1.

Safety:
  * refuses to run while the game is executing
  * recognizes only known live states (vanilla, menu pilot, subtitle POC, opening POC v1)
  * skips if the requested build is already installed
  * verifies the V3 source hashes against BUILD_INFO.local.json
  * verifies/creates the pretest backup describing the exact pre-install state
  * stage -> verify staged -> atomic pair replace -> post-hash verify
  * automatic rollback from the pretest backup on any partial failure
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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
OPENING_POC_V1 = {
    "chunk0.index": "595334f75932b50e9ec31260c0f6dd183486d9ad693a98ac25d08a346c713546",
    "chunk0.resources": "8ae90ca5e02ceeec17ab27b25bf17aac65fdd691f030789ba248acd894d77a80",
}
OPENING_POC_V3 = {
    "chunk0.index": "595334f75932b50e9ec31260c0f6dd183486d9ad693a98ac25d08a346c713546",
    "chunk0.resources": "79c09ba561062bf39df3696b7ab75d2518cd591b8f8b4cbc9affc76e35cfe4c9",
}
KNOWN_STATES = (
    ("original", ORIGINAL),
    ("menu_pilot", MENU_PILOT),
    ("subtitle_poc", SUBTITLE_POC),
    ("opening_runtime_poc_v1", OPENING_POC_V1),
)
SPAN_ORDER_IDS = ["#str_vo_agentone_dlc1_c01_123", "#str_vo_agentone_dlc1_c01_123_1"]


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
    if all(state[n] == OPENING_POC_V3[n] for n in FILES):
        return "opening_runtime_poc_v3"
    return None


def replace_pair(sources, destinations, expected, rollback):
    """Stage each file next to its destination, verify, then atomically replace.

    Any failure rolls back every file already replaced from `rollback`."""
    staged = {}
    replaced = []
    try:
        for name in FILES:
            with tempfile.NamedTemporaryFile(prefix="arabic-v3-", suffix=".tmp",
                                             dir=destinations[name].parent, delete=False) as stream:
                staged[name] = Path(stream.name)
            shutil.copyfile(sources[name], staged[name])
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
                raise RuntimeError("Rollback verification failed; restore the pretest backup manually")
        raise
    finally:
        for path in staged.values():
            Path(path).unlink(missing_ok=True)


def check_build(build):
    manifest = json.loads((build / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    verify = json.loads((build / "VERIFY_REPORT.local.json").read_text(encoding="utf-8"))
    if manifest.get("stage") != "opening_runtime_poc_v3":
        raise ValueError("Unexpected build stage: %r" % manifest.get("stage"))
    if verify.get("status") != "static_build_verified" or verify.get("changed_rows") != 48:
        raise ValueError("V3 verification manifest does not pass")
    if verify.get("screenshot_check") != "PASS":
        raise ValueError("Screenshot-string assertion does not pass")
    if manifest.get("source_hashes") != ORIGINAL:
        raise ValueError("Build is not derived from the verified original archives")
    if set(manifest["output_hashes"]) != set(FILES):
        raise ValueError("Unexpected build manifest")
    if dict(manifest["output_hashes"]) != OPENING_POC_V3:
        raise ValueError("Build output hashes do not match the recognized V3 hashes")
    if manifest.get("span_order_corrected_ids") != SPAN_ORDER_IDS or \
            manifest.get("span_order_corrected_applied") != SPAN_ORDER_IDS:
        raise ValueError("Candidate C ids do not match the diagnostic records")
    if len(manifest.get("mapping", {})) != 98:
        raise ValueError("Unexpected glyph mapping size")
    for name in FILES:
        if digest(build / name) != manifest["output_hashes"][name]:
            raise ValueError("V3 file hash does not match BUILD_INFO.local.json: %s" % name)
    return manifest


def ensure_pretest(pretest, targets, current, state_label):
    """Create or verify the pretest backup describing the exact pre-install state."""
    if pretest.exists():
        for name in FILES:
            if not (pretest / name).is_file() or digest(pretest / name) != current[name]:
                raise ValueError("Existing pretest backup does not match current live state; refusing")
        return
    pretest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        with targets[name].open("rb") as source, (pretest / name).open("xb") as dest:
            shutil.copyfileobj(source, dest)
        if digest(pretest / name) != current[name]:
            raise ValueError("Pretest backup verification failed: %s" % name)
    state_copy = dict(current)
    state_copy["state_label"] = state_label
    (pretest / "backup_manifest.local.json").write_text(
        json.dumps(dict(game=str(targets[FILES[0]].parents[1]), pretest_hashes=state_copy),
                   indent=2) + "\n", encoding="utf-8")


def install(game, build=None, pretest=None):
    game = game.resolve(strict=True)
    build = (build or Path(__file__).resolve().parents[1] / "workspace" / "opening_runtime_poc_v3").resolve(strict=True)
    pretest = (pretest or Path(__file__).resolve().parents[1] / "workspace" / "backups" / "opening_runtime_v3_pretest").resolve()
    vanilla = (Path(__file__).resolve().parents[1] / "workspace" / "backups" / "menu_pilot_original").resolve()
    if pretest == vanilla or vanilla in pretest.parents or pretest in vanilla.parents:
        raise ValueError("Refusing to use the vanilla backup directory as the pretest")
    if game == pretest.parent or game in pretest.parents:
        raise ValueError("Backup must be outside the game installation")
    if not (game / "WolfOldBlood_x64.exe").is_file():
        raise ValueError("Game executable not found")

    manifest = check_build(build)
    outputs = dict(manifest["output_hashes"])

    targets = {n: game / "base" / n for n in FILES}
    current = {n: digest(targets[n]) for n in FILES}
    state_label = label(current)
    if state_label is None:
        raise ValueError("Current game hashes are unknown; refusing replacement")
    if current == outputs:
        print(json.dumps(dict(status="already_installed", live_label=state_label,
                              installed_hashes=current), indent=2))
        return
    if state_label not in [n for n, _ in KNOWN_STATES]:
        raise ValueError("Current game state %r is not a recognized pre-V3 state; refusing" % state_label)

    require_stopped()
    ensure_pretest(pretest, targets, current, state_label)

    require_stopped()
    replace_pair({n: build / n for n in FILES}, targets, outputs,
                 {n: (pretest / n) for n in FILES})
    after = {n: digest(targets[n]) for n in FILES}
    if any(after[n] != outputs[n] for n in FILES):
        raise ValueError("Installed file hash mismatch; rolled back")

    state = dict(game=str(game), build=str(build), pretest=str(pretest),
                 installed=True, pretest_label=state_label, in_game_verified=False,
                 installed_hashes=after)
    (pretest / "install_state.local.json").write_text(json.dumps(state, indent=2) + "\n",
                                                      encoding="utf-8")
    print(json.dumps(dict(status="installed", **state), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True,
                        help="Wolfenstein The Old Blood installation directory")
    parser.add_argument("--build", type=Path, default=None,
                        help="V3 build directory (default workspace/opening_runtime_poc_v3)")
    parser.add_argument("--pretest", type=Path, default=None,
                        help="pretest backup directory (default workspace/backups/opening_runtime_v3_pretest)")
    args = parser.parse_args()
    try:
        install(args.game, args.build, args.pretest)
    except Exception as exc:  # noqa: BLE001 - surface a clean failure
        print(json.dumps(dict(status="FAILED", error=str(exc)), indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
