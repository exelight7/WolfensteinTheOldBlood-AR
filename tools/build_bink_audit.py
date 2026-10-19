"""Build a read-only audit of every Bink2 .bik video: metadata + sampled frames.

Decodes each video with the game's own bink2w64.dll (see tools/bink2_decode.py),
saves representative frames as PNGs, and writes BINK_AUDIT.local.json.

Usage: python tools/build_bink_audit.py [substring-filter ...]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.bink2_decode import Bink2Movie, bgrx_to_png  # noqa: E402

if "WTOB_GAME_DIR" not in os.environ:
    raise SystemExit("Set WTOB_GAME_DIR to the Wolfenstein: The Old Blood directory")
GAME_DIR = Path(os.environ["WTOB_GAME_DIR"])
BINK_ROOT = str(GAME_DIR / "base" / "bink")
OUT_ROOT = str(ROOT / "workspace" / "coverage_hunt" / "video")
FRAMES_ROOT = os.path.join(OUT_ROOT, "frames")
AUDIT = os.path.join(OUT_ROOT, "BINK_AUDIT.local.json")
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
SAMPLES = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]


def find_biks():
    out = []
    for root, _dirs, files in os.walk(BINK_ROOT):
        for f in files:
            if f.lower().endswith(".bik"):
                out.append(os.path.join(root, f))
    return sorted(out)


def ffprobe_meta(path):
    try:
        r = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                           capture_output=True, text=True, timeout=60)
        info = {}
        for line in r.stderr.splitlines():
            line = line.strip()
            if line.startswith("Duration:"):
                info["duration"] = line.split(",")[0].split(":", 1)[1].strip()
            if line.startswith("Stream #") and "Video:" in line:
                info["video_stream"] = line.split(":", 2)[-1].strip()
            if line.startswith("Stream #") and "Audio:" in line:
                info.setdefault("audio_streams", []).append(line.split(":", 2)[-1].strip())
        return info
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def contact_sheet(frames, out_path, cols=7, cell_w=380):
    from PIL import Image, ImageDraw
    if not frames:
        return
    imgs = [(label, Image.open(p).convert("RGB")) for label, p in frames]
    ratio = cell_w / imgs[0][1].width
    cell_h = int(imgs[0][1].height * ratio)
    rows = (len(imgs) + cols - 1) // cols
    pad = 4
    label_h = 18
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad,
                              rows * (cell_h + label_h + pad) + pad), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        sheet.paste(im.resize((cell_w, cell_h)), (x, y + label_h))
        draw.text((x + 2, y + 2), label, fill=(255, 255, 0))
    sheet.save(out_path)


def process(path, records, force=False):
    rel = os.path.relpath(path, BINK_ROOT)
    name = os.path.splitext(os.path.basename(path))[0]
    outdir = os.path.join(FRAMES_ROOT, name)
    os.makedirs(outdir, exist_ok=True)
    print("=== %s ===" % rel, flush=True)
    rec = {"file": rel.replace("\\", "/"), "name": name,
           "size_bytes": os.path.getsize(path)}
    rec["ffmpeg"] = ffprobe_meta(path)
    try:
        m = Bink2Movie(path)
    except Exception as e:  # noqa: BLE001
        rec["error"] = "open: %s" % e
        records.append(rec)
        return
    rec["width"] = m.width
    rec["height"] = m.height
    rec["frames"] = m.frames
    rec["fps"] = m.fps
    rec["duration_s"] = round(m.frames / m.fps, 2) if m.fps else None
    targets = []
    for fr in SAMPLES:
        idx = min(m.frames - 1, int(m.frames * fr))
        if idx not in [t[0] for t in targets]:
            targets.append((idx, fr))
    saved = []
    target_map = dict(targets)
    import time as _t
    t0 = _t.time()
    last = max(t[0] for t in targets)
    for i in range(last + 1):
        m.grab_rgba(i)
        if i in target_map:
            pct = int(target_map[i] * 100)
            fp = os.path.join(outdir, "f%05d_%02dpct.png" % (i, pct))
            bgrx_to_png(m.snapshot()).save(fp)
            saved.append(("%d (%d%%)" % (i, pct), fp))
    dt = _t.time() - t0
    m.close()
    rec["frames_decoded"] = last + 1
    rec["decode_seconds"] = round(dt, 1)
    rec["decode_fps"] = round((last + 1) / dt, 1) if dt else None
    rec["sampled"] = [{"frame": i, "pct": p, "png": os.path.relpath(p2, OUT_ROOT).replace("\\", "/")}
                      for (i, p), (lab, p2) in zip(targets, saved)]
    sheet = os.path.join(outdir, "contact_sheet.png")
    contact_sheet(saved, sheet)
    rec["contact_sheet"] = os.path.relpath(sheet, OUT_ROOT).replace("\\", "/")
    print("   %dx%d %d frames %.1fs -> decode %.0f fps  sheet=%s"
          % (m.width, m.height, m.frames, rec["duration_s"], rec["decode_fps"], name), flush=True)
    records.append(rec)


def main():
    filters = [a for a in sys.argv[1:] if not a.startswith("-")]
    force = "--force" in sys.argv
    os.makedirs(FRAMES_ROOT, exist_ok=True)
    records = []
    if os.path.exists(AUDIT) and not force:
        with open(AUDIT, "r", encoding="utf-8") as fh:
            records = json.load(fh).get("videos", [])
    done = {r["file"] for r in records if "error" not in r}
    biks = find_biks()
    if filters:
        biks = [b for b in biks if any(f.lower() in b.lower() for f in filters)]
    for b in biks:
        rel = os.path.relpath(b, BINK_ROOT).replace("\\", "/")
        if rel in done:
            print("skip (done):", rel, flush=True)
            continue
        process(b, records, force)
        with open(AUDIT, "w", encoding="utf-8") as fh:
            json.dump({"tool": "bink2w64.dll (RAD, game-shipped) via tools/bink2_decode.py",
                       "videos": records}, fh, indent=2, ensure_ascii=False)
    print("AUDIT written:", AUDIT, "videos:", len(records))


if __name__ == "__main__":
    main()
