import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"


def test_versions_are_in_sync():
    package = json.loads((APP / "package.json").read_text(encoding="utf-8"))
    tauri = json.loads((APP / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    cargo = (APP / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    supported = json.loads((ROOT / "config" / "supported_versions.json").read_text(encoding="utf-8"))
    cargo_version = re.search(r'^version = "([^"]+)"', cargo, re.MULTILINE).group(1)
    assert package["version"] == "1.0.1"
    assert tauri["version"] == "1.0.1"
    assert cargo_version == "1.0.1"
    assert supported["app_version"] == "1.0.1"


def test_tauri_bundles_sidecar_resources_for_nsis():
    tauri = json.loads((APP / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    assert tauri["identifier"] == "com.exelight7.wtob.arabic"
    assert tauri["bundle"]["targets"] == ["nsis"]
    assert "resources/**/*" in tauri["bundle"]["resources"]
    assert tauri["build"]["frontendDist"] == "../dist"


def test_capabilities_allow_dialog_and_opener():
    capabilities = json.loads(
        (APP / "src-tauri" / "capabilities" / "default.json").read_text(encoding="utf-8")
    )
    assert {"core:default", "dialog:default", "opener:default"} <= set(capabilities["permissions"])


def test_supported_versions_has_v1_hashes():
    supported = json.loads((ROOT / "config" / "supported_versions.json").read_text(encoding="utf-8"))
    entry = supported["supported_versions"][0]
    assert entry["steam_app_id"] == 350080
    assert entry["game_build"] == "616161"
    assert entry["localized"]["base/chunk0.index"].startswith("c29a2b83")
    assert entry["localized"]["base/chunk0.resources"] == (
        "f14edf906c0358d5d35dc8bb592a6bfaebd88ff6c9df458e2d8805e5376bb061"
    )
    prior = {state["base/chunk0.resources"] for state in entry["also_accepted_states"]}
    assert "46a3dfccaf83c3bf89c1d07c1271155c5144429a8c9b665d331b772fe23f6f60" in prior
    assert "14f1a1cd2d986706916c9f139fee165e79e71049f15e671684de9bd92eb00155" in prior
    assert entry["localized"]["base/graphicsdriverwarningloc.json"].startswith("d995be90")
    assert entry["vanilla"]["base/chunk0.index"].startswith("3aa93b17")


def test_sidecar_resolution_covers_both_tauri_layouts():
    payload = (APP / "src-tauri" / "src" / "payload.rs").read_text(encoding="utf-8")
    assert 'join("resources")' in payload
    assert 'join("sidecar")' in payload
