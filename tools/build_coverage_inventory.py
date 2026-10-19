"""Phase 1 - PLAYER-VISIBLE COVERAGE INVENTORY.

Enumerates every resource across all game chunks plus loose files, classifies
each into a coverage class, and flags text-bearing image/UI candidates.

Outputs (local, git-ignored):
  workspace/coverage_hunt/PLAYER_VISIBLE_INVENTORY.local.json
"""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import records  # noqa: E402

if "WTOB_GAME_DIR" not in os.environ:
    raise SystemExit("Set WTOB_GAME_DIR to the Wolfenstein: The Old Blood directory")
GAME = Path(os.environ["WTOB_GAME_DIR"]) / "base"
OUT = ROOT / "workspace" / "coverage_hunt"

IMAGE_EXT = {".bimage", ".png", ".jpg", ".dds", ".tga", ".bmp"}
VIDEO_EXT = {".bik", ".bink", ".bk2", ".wmv", ".mp4", ".roq"}
SWF_EXT = {".bswf", ".swf", ".gfx"}
UI_EXT = {".guipage", ".gui", ".uires", ".font", ".idmaterial", ".material", ".decl"}
TEXT_EXT = {".lang", ".txt", ".json", ".cfg", ".langlist", ".csv"}

TEXT_KEYWORDS = re.compile(
    r"(tutorial|newspaper|news|letter|sign|book|poster|paper|loading|title|credit|"
    r"logo|menu|map|note|journal|enigma|code|stamp|label|help|tip|control|key|"
    r"hint|manual|intro|location|plate|banner|advert|newsp|briefing|paused|"
    r"hud|gui|hazard|warning)", re.I)


def classify(name, ext):
    low = name.lower()
    if low.endswith(".lang"):
        return "CONFIRMED_TEXT"
    if ext in SWF_EXT or "/swf/" in low:
        return "BSWF"
    if ext in VIDEO_EXT or "/bink/" in low:
        return "BINK_VIDEO"
    if ext in IMAGE_EXT:
        if "virtualtexture" in low or low.startswith("generated/textures/mega"):
            return "VIRTUAL_TEXTURE"
        return "IMAGE"
    if ext in TEXT_EXT:
        return "LOOSE_FILE"
    if ext in UI_EXT or "/guis/" in low or "gui" in low:
        return "UI_RESOURCE"
    if ext in {".script", ".as", ".h", ".cpp"}:
        return "SCRIPT"
    return "OTHER"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    ext_counter = Counter()
    class_counter = Counter()
    pref_counter = Counter()
    for index in sorted(GAME.glob("chunk*.index")):
        size_total = index.with_suffix(".resources").stat().st_size
        entries, _ = records(index.read_bytes(), size_total)
        for entry in entries:
            name = entry["names"][2]
            ext = Path(name).suffix.lower()
            cls = classify(name, ext)
            ext_counter[ext] += 1
            class_counter[cls] += 1
            pref_counter["/".join(name.split("/")[:2])] += 1
            rows.append(dict(
                chunk=index.stem, ordinal=entry["ordinal"], name=name,
                ext=ext, stored=entry["stored"], cls=cls,
                text_kw=bool(TEXT_KEYWORDS.search(name)),
            ))
    loose = []
    for f in GAME.rglob("*"):
        if f.is_file() and f.parent != GAME and f.name.lower().endswith(
                (".json", ".cfg", ".lang", ".txt", ".ini")):
            rel = f.relative_to(GAME).as_posix()
            loose.append(dict(path=rel, size=f.stat().st_size))
    summary = dict(
        archive_rows=len(rows),
        loose_rows=len(loose),
        classes=dict(class_counter),
        top_extensions=dict(ext_counter.most_common(40)),
        top_prefixes=dict(pref_counter.most_common(40)),
    )
    (OUT / "PLAYER_VISIBLE_INVENTORY.local.json").write_text(
        json.dumps(dict(summary=summary, resources=rows, loose=loose),
                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # text-bearing image/ui candidates
    candidates = [r for r in rows if r["cls"] in
                  ("IMAGE", "VIRTUAL_TEXTURE", "UI_RESOURCE", "BSWF", "BINK_VIDEO")
                  and r["text_kw"]]
    (OUT / "TEXT_BEARING_CANDIDATES.local.json").write_text(
        json.dumps(candidates, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("text-bearing candidates:", len(candidates))


if __name__ == "__main__":
    main()
