"""Phase 14 - runtime_complete: unified player-visible build.

Built on top of the installed runtime_full (100% confirmed text corpus):

  TEXT   - additive insertion of the 6 SWF-referenced Enigma ids that are absent
           from every .lang table (values shaped to the full-corpus PUA mapping).
  IMAGES - re-rendered wtob_photosensitivity_row.bimage with an Arabic paragraph.
  FONT   - unchanged (inherited from runtime_full).
  BSWF / VIDEO_OVERLAYS / LOOSE_FILES - empty (no rebuild required; see report).

Outputs into workspace/runtime_complete/.
"""
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import records, payload  # noqa: E402
from build_menu_pilot import rebuild  # noqa: E402
import bimage_codec as bc  # noqa: E402
import formatted_text as ft  # noqa: E402

BASE = ROOT / "workspace" / "runtime_full"
OUT = ROOT / "workspace" / "runtime_complete"
FONT = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"

LANG_ORDINAL = 22456
IMAGE_ORDINAL = 19434  # generated/textures/textures/guis/wtob_photosensitivity_row.bimage

ENIGMA = [
    ("#str_menu_enigma_crack_it", "فُكّ الشفرة"),
    ("#str_menu_enigma_tab0", "الشفرات"),
    ("#str_menu_enigma_tab1", "الرسائل"),
    ("#str_menu_enigma_tab2", "الوثائق"),
    ("#str_menu_enigma_tab3", "الكنوز"),
    ("#str_menu_enigma_you_cracked_it", "لقد فككتَ الشفرة"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mapping_from_build():
    info = json.loads((BASE / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    return {chr(int(ch[2:], 16)): int(code[2:], 16) for ch, code in info["mapping"].items()}


def shape_arabic(text, mapping):
    visual = ft.shape_formatted_ordered(text, mapping)
    return ft.encode_lang_value(visual)


def insert_enigma(lang_bytes, mapping):
    text = lang_bytes.decode("utf-8-sig")
    lines = text.splitlines(True)
    closing = next(i for i, l in enumerate(lines) if l.strip() == "}")
    rows = []
    for key, arabic in ENIGMA:
        value = shape_arabic(arabic, mapping)
        rows.append('\t"%s"\t"%s"\r\n' % (key, value))
        if ('"#str_%s"' % key[5:]) in text:
            raise SystemExit("key already present: " + key)
    lines[closing:closing] = ["\r\n"] + rows + ["\r\n"]
    out = ("".join(lines)).encode("utf-8")
    return b"\xef\xbb\xbf" + out


def build_photosensitivity():
    blob = payload(io.BytesIO((BASE / "chunk0.resources").read_bytes()),
                   records((BASE / "chunk0.index").read_bytes(),
                           (BASE / "chunk0.resources").stat().st_size)[0][IMAGE_ORDINAL])
    hdr = bc.read_header(blob)
    w, h = hdr["width"], hdr["height"]
    rgba = bc.decode(blob[0x48:], w, h, hdr["fmt"])
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(str(FONT), 27)
    red = (210, 22, 29, 255)
    right, y, lh = 1720, 958, 34

    def rtl(t, yy, color):
        draw.text((right, yy), get_display(arabic_reshaper.reshape(t)), font=font,
                  fill=color, anchor="ra")

    rtl("تحذير من حساسية الضوء:", y, red); y += lh
    body = ("قد يعاني عدد قليل من الأشخاص من نوبات عند التعرّض لأضواء أو أنماط أو صور "
            "معيّنة، حتى مع عدم وجود تاريخ للإصابة بالصرع أو النوبات. يُرجى مراجعة معلومات "
            "السلامة في دليل المنتج، والمتوفّرة أيضاً على الموقع manuals.bethsoft.com.")
    cur = ""
    for wd in body.split(" "):
        trial = (cur + " " + wd).strip()
        if font.getlength(get_display(arabic_reshaper.reshape(trial))) > 1500 and cur:
            rtl(cur, y, (255, 255, 255, 255)); y += lh; cur = wd
        else:
            cur = trial
    if cur:
        rtl(cur, y, (255, 255, 255, 255))
    mask = np.asarray(overlay)[:, :, 3] > 0
    comp = Image.alpha_composite(Image.fromarray(rgba, "RGBA"), overlay)
    return bc.rebuild(blob, np.asarray(comp).copy(), mask)


def main():
    (OUT / "text").mkdir(parents=True, exist_ok=True)
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    index = (BASE / "chunk0.index").read_bytes()
    archive = (BASE / "chunk0.resources").read_bytes()
    entries, _ = records(index, len(archive))

    mapping = mapping_from_build()
    lang = payload(io.BytesIO(archive), entries[LANG_ORDINAL])
    new_lang = insert_enigma(lang, mapping)
    new_image = build_photosensitivity()
    (OUT / "text" / "english.lang").write_bytes(new_lang)
    (OUT / "images" / "wtob_photosensitivity_row.bimage").write_bytes(new_image)

    changes = {LANG_ORDINAL: new_lang, IMAGE_ORDINAL: new_image}
    out_index, out_archive = rebuild(index, archive, changes)
    (OUT / "chunk0.index").write_bytes(out_index)
    (OUT / "chunk0.resources").write_bytes(out_archive)

    manifest = dict(
        stage="runtime_complete",
        base="runtime_full",
        changed_resources=["strings/english.lang",
                           "generated/textures/textures/guis/wtob_photosensitivity_row.bimage"],
        source_hashes={"chunk0.index": sha(index), "chunk0.resources": sha(archive),
                       "english.lang": sha(lang)},
        output_hashes={"chunk0.index": sha(out_index), "chunk0.resources": sha(out_archive),
                       "english.lang": sha(new_lang),
                       "wtob_photosensitivity_row.bimage": sha(new_image)},
        enigma_keys=[k for k, _ in ENIGMA],
        enigma_rows_added=len(ENIGMA),
        records=len(entries),
        bswf_stage="empty (UI text is #str_-driven)",
        video_overlays_stage="empty (overlay text inherited from corpus)",
        loose_files_stage="unchanged (base/graphicsdriverwarningloc.json already Arabic)",
    )
    (OUT / "FULL_BUILD_MANIFEST.local.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest["output_hashes"], indent=1))
    print("enigma rows added:", manifest["enigma_rows_added"])


if __name__ == "__main__":
    main()
