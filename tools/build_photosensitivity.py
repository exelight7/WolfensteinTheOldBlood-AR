"""Phase 6 - inject an Arabic paragraph into wtob_photosensitivity_row.bimage.

The vanilla image bakes the photosensitivity warning in 7 languages (no Arabic).
We decode the DXT1 image, render an Arabic paragraph (bidi + shaping) into the
free space below the existing text, and re-encode only the touched DXT1 blocks
(untouched blocks keep their original bytes -> crisp original text preserved).

Outputs into workspace/runtime_complete/images/.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bimage_codec as bc  # noqa: E402
from archive_inventory import records, payload  # noqa: E402

if "WTOB_GAME_DIR" not in os.environ:
    raise SystemExit("Set WTOB_GAME_DIR to the Wolfenstein: The Old Blood directory")
GAME = Path(os.environ["WTOB_GAME_DIR"]) / "base"
ASSET = "generated/textures/textures/guis/wtob_photosensitivity_row.bimage"
FONT = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"
OUT = ROOT / "workspace" / "runtime_complete" / "images"

LABEL = "تحذير من حساسية الضوء:"
BODY = ("قد يعاني عدد قليل من الأشخاص من نوبات عند التعرّض لأضواء أو أنماط أو صور "
        "معيّنة، حتى مع عدم وجود تاريخ للإصابة بالصرع أو النوبات. يُرجى مراجعة معلومات "
        "السلامة في دليل المنتج، والمتوفّرة أيضاً على الموقع manuals.bethsoft.com.")


def shape(text):
    return get_display(arabic_reshaper.reshape(text))


def fetch_asset():
    for index in sorted(GAME.glob("chunk*.index")):
        entries, _ = records(index.read_bytes(), index.with_suffix(".resources").stat().st_size)
        with index.with_suffix(".resources").open("rb") as stream:
            for entry in entries:
                if entry["names"][2] == ASSET:
                    return payload(stream, entry)
    raise SystemExit("asset not found: " + ASSET)


def sample_label_color(rgba):
    band = rgba[139:161, 189:900, :3].reshape(-1, 3)
    red = band[(band[:, 0] > 120) & (band[:, 1] < 80) & (band[:, 2] < 80)]
    return tuple(int(v) for v in red.mean(axis=0)) if len(red) else (200, 30, 30)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    blob = fetch_asset()
    hdr = bc.read_header(blob)
    w, h = hdr["width"], hdr["height"]
    rgba = bc.decode(blob[0x48:], w, h, hdr["fmt"])
    red = sample_label_color(rgba)
    print("dims", w, h, "fmt", hex(hdr["fmt"]), "label color", red)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    size = 27
    font = ImageFont.truetype(str(FONT), size)
    right = 1720
    y = 958
    line_h = 34

    def rtl_line(text, y, color):
        s = shape(text)
        return draw.text((right, y), s, font=font, fill=color, anchor="ra")

    # label then wrapped body
    rtl_line(LABEL, y, red + (255,))
    y += line_h
    words = BODY.split(" ")
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if font.getlength(shape(trial)) > 1500 and cur:
            rtl_line(cur, y, (255, 255, 255, 255)); y += line_h; cur = wd
        else:
            cur = trial
    if cur:
        rtl_line(cur, y, (255, 255, 255, 255)); y += line_h

    alpha = np.asarray(overlay)[:, :, 3]
    mask = alpha > 0
    rows = np.where(mask.any(axis=1))[0]
    print("arabic text drawn rows", int(rows.min()), "-", int(rows.max()))
    if rows.max() >= h:
        raise SystemExit("Arabic text overflows the image")

    comp = Image.alpha_composite(Image.fromarray(rgba, "RGBA"), overlay)
    new_rgba = np.asarray(comp).copy()
    changed = mask.copy()
    new_blob = bc.rebuild(blob, new_rgba, changed)

    (OUT / "wtob_photosensitivity_row.bimage").write_bytes(new_blob)
    comp.convert("RGB").save(OUT / "wtob_photosensitivity_row.preview.png")
    print("wrote", OUT / "wtob_photosensitivity_row.bimage", len(new_blob))
    print("original", len(blob), "changed bytes",
          sum(1 for a, b in zip(new_blob, blob) if a != b))


if __name__ == "__main__":
    main()
