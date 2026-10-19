import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_sidecar  # noqa: E402
import prepare_release_data  # noqa: E402
import release_build  # noqa: E402


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def lang_record(key: str, english: str, arabic: str = "مرحبا") -> dict:
    return {
        "resource": "strings/english.lang",
        "id": f"default:{key}",
        "english_sha256": sha(english),
        "status": "translated",
        "arabic": arabic,
    }


def loose_record(location: str, english: str) -> dict:
    return {
        "resource": "base/graphicsdriverwarningloc.json",
        "location": location,
        "english_sha256": sha(english),
        "status": "translated",
        "arabic": "تحذير",
    }


def test_build_master_joins_lang_and_loose_text():
    rows = {
        "str_1": {
            "english": "Hello",
            "english_literal": "Hello",
            "english_sha256": sha("Hello"),
        }
    }
    records = [lang_record("str_1", "Hello"), loose_record("warning", "Warning")]
    master = release_build.build_master(rows, records, {"warning": "Warning"})
    assert len(master) == 1
    assert master[0]["english"] == "Hello"
    assert master[0]["arabic"] == "مرحبا"


def test_build_master_rejects_changed_english():
    rows = {"str_1": {"english": "Changed", "english_literal": "Changed", "english_sha256": sha("Changed")}}
    try:
        release_build.build_master(rows, [lang_record("str_1", "Hello")], {})
    except SystemExit as error:
        assert "hash mismatch" in str(error)
    else:
        raise AssertionError("changed English text must be rejected")


def test_build_master_rejects_missing_key():
    try:
        release_build.build_master({}, [lang_record("str_404", "Missing")], {})
    except SystemExit as error:
        assert "missing key" in str(error)
    else:
        raise AssertionError("missing keys must be rejected")


def test_build_master_rejects_changed_loose_text():
    try:
        release_build.build_master({}, [loose_record("warning", "Original")], {"warning": "Changed"})
    except SystemExit as error:
        assert "source hash mismatch" in str(error)
    else:
        raise AssertionError("changed loose text must be rejected")


def test_find_data_dir_honors_environment(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "BUILD_INFO.local.json").write_text("{}", encoding="utf-8")
    (data / "font.ttf").write_bytes(b"font")
    monkeypatch.setenv("WTOB_RELEASE_DATA", str(data))
    assert release_build.find_data_dir() == data


def test_sha_file_matches_hashlib(tmp_path):
    target = tmp_path / "payload.bin"
    target.write_bytes(b"payload")
    assert release_build.sha_file(target) == hashlib.sha256(b"payload").hexdigest()


def test_prepare_release_data_validates_mapping():
    mapping = prepare_release_data.validate_mapping({"U+060C": "U+E000"})
    assert mapping["U+060C"] == "U+E000"
    try:
        prepare_release_data.validate_mapping({"060C": "E000"})
    except SystemExit as error:
        assert "invalid" in str(error)
    else:
        raise AssertionError("mapping without U+ prefixes must be rejected")


def test_prepare_release_data_rejects_duplicate_targets():
    try:
        prepare_release_data.validate_mapping({"U+060C": "U+E000", "U+061B": "U+E000"})
    except SystemExit as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate PUA targets must be rejected")


def test_sidecar_excludes_keep_scipy_linalg():
    assert "scipy.linalg" not in build_sidecar.EXCLUDES
    assert "scipy.spatial" in build_sidecar.EXCLUDES
    assert build_sidecar.DIST.name == "sidecar"


def test_tracked_pua_mapping_is_valid():
    mapping = prepare_release_data.read_mapping(ROOT / "config" / "pua_mapping.json")
    assert len(mapping) == 98


def test_release_manifest_matches_installer_version():
    manifest = json.loads(
        (ROOT / "release" / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == "1.0.0"
    assert manifest["channel"] == "stable"
    assert manifest["gameVersion"] == "616161"
    assert manifest["files"]
    for file in manifest["files"]:
        assert len(file["sha256"]) == 64
        assert file["sha256"] == file["sha256"].lower()
        assert file["downloadUrl"].startswith("https://")
