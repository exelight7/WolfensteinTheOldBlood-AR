"""Phase 15/21 - static verification for runtime_complete.

Re-derives the build from workspace/runtime_full and asserts that exactly the
two intended resources changed, that the Enigma keys exist, and that the
photosensitivity image changed only in the Arabic region.
"""
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import records, payload  # noqa: E402
import bimage_codec as bc  # noqa: E402

BASE = ROOT / "workspace" / "runtime_full"
BUILD = ROOT / "workspace" / "runtime_complete"
LANG_ORDINAL = 22456
IMAGE_ORDINAL = 19434
ENIGMA_KEYS = ["#str_menu_enigma_crack_it", "#str_menu_enigma_tab0",
               "#str_menu_enigma_tab1", "#str_menu_enigma_tab2",
               "#str_menu_enigma_tab3", "#str_menu_enigma_you_cracked_it"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(root):
    index = (root / "chunk0.index").read_bytes()
    archive = (root / "chunk0.resources").read_bytes()
    entries, _ = records(index, len(archive))
    return index, archive, entries


def main():
    _, abase, ebase = load(BASE)
    _, abuild, ebuild = load(BUILD)
    assert len(ebase) == len(ebuild)
    changed = []
    with io.BytesIO(abase) as s0, io.BytesIO(abuild) as s1:
        for eb, en in zip(ebase, ebuild):
            if eb["ordinal"] in (LANG_ORDINAL, IMAGE_ORDINAL):
                continue
            if payload(s0, eb) != payload(s1, en):
                changed.append(en["ordinal"])
    changed = sorted(changed)

    lang = payload(io.BytesIO(abuild), ebuild[LANG_ORDINAL]).decode("utf-8-sig")
    rows = [l for l in lang.splitlines() if l.lstrip().startswith('"#str_')]
    keys = set(re.findall(r'"(#str_[A-Za-z0-9_]+)"', lang))
    enigma_ok = all(k in keys for k in ENIGMA_KEYS)

    img = payload(io.BytesIO(abuild), ebuild[IMAGE_ORDINAL])
    base_img = payload(io.BytesIO(abase), ebase[IMAGE_ORDINAL])
    hdr = bc.read_header(img)
    ra = bc.decode(base_img[0x48:], hdr["width"], hdr["height"], hdr["fmt"])
    rb = bc.decode(img[0x48:], hdr["width"], hdr["height"], hdr["fmt"])
    diff = np.abs(ra.astype(int) - rb.astype(int)).sum(axis=2) > 0
    rows_diff = np.where(diff.any(axis=1))[0]
    region_ok = len(rows_diff) == 0 or int(rows_diff.min()) >= 940

    report = dict(
        status="static_build_verified",
        intended_changed=[LANG_ORDINAL, IMAGE_ORDINAL],
        unintended_changed=changed,
        only_intended_changed=(changed == []),
        lang_rows=len(rows),
        lang_keys=len(keys),
        enigma_keys_present=enigma_ok,
        image_size=[hdr["width"], hdr["height"]],
        image_changed_rows=[int(rows_diff.min()), int(rows_diff.max())] if len(rows_diff) else [],
        image_change_region_ok=region_ok,
        output_hashes={"chunk0.index": sha((BUILD / "chunk0.index").read_bytes()),
                       "chunk0.resources": sha((BUILD / "chunk0.resources").read_bytes())},
    )
    gate = (report["only_intended_changed"] and report["enigma_keys_present"]
            and report["image_change_region_ok"] and report["lang_rows"] == 3578)
    report["gate"] = bool(gate)
    (BUILD / "VERIFY_REPORT.local.json").write_text(
        json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
