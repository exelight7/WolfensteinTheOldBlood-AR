"""Development-only Arabic glyph metric simulator.

Renders words using the EXACT generated idf+ atlas glyphs, the EXACT idf+
horizontal metrics, and the EXACT PUA sequence the game receives - never from
the TTF directly for the primary comparison. The TTF reference render is a
separate image used only as the visual target.

Purpose: reveal horizontal positioning and join gaps so the physical-join defect
can be measured numerically instead of guessed.

Layout convention (derived from native glyphs, see workspace/diagnostics):
    bitmap_top_left = (pen + left, baseline - top)
    pen += advance
    ink within the bitmap is inset by `padding` on every side.

Usage:
    python tools/render_arabic_metrics_debug.py --build <dir> --out <dir> \
        --images current_metrics.png,ttf_reference.png
"""
import argparse
import io
import json
import struct
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_inventory import records, payload  # noqa: E402

from PIL import Image, ImageDraw, ImageFont, ImageChops  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PADDING = 8
FONT_PATH = ROOT / "workspace" / "research" / "IBMPlexSansArabic-Regular.ttf"

DEFAULT_WORDS = ["ينتقل", "الدماء", "التي", "يسفكها", "المحاربون",
                 "بيبي", "تتتت", "سلسلة", "محمد", "مكتب", "العربية"]


def parse_font(data):
    if data[:4] != b"idf+":
        raise ValueError("not an idf+ font")
    count = struct.unpack_from(">H", data, 10)[0]
    glyphs = [data[12 + i * 12:24 + i * 12] for i in range(count)]
    codes = list(struct.unpack_from("<" + "I" * count, data, 12 + count * 12))
    end = 12 + count * 16
    total = struct.unpack_from(">H", data, end)[0]
    kerning = [(codes[a], codes[b], adj)
               for a, b, adj in (struct.unpack_from("<HHf", data, end + 2 + i * 8)
                                 for i in range(total))]
    return glyphs, codes, kerning


def unpack(g):
    w, h, top, left, adv, x, y, extra = struct.unpack("<BBbbHHHh", g)
    return dict(width=w, height=h, top=top, left=left, advance=adv,
                atlas_x=x, atlas_y=y, extra=extra)


def load_build(build):
    idx = (build / "chunk0.index").read_bytes()
    res = (build / "chunk0.resources").read_bytes()
    entries, _ = records(idx, len(res))
    bp = {e["names"][2]: e for e in entries}
    glyphs, codes, kerning = parse_font(payload(io.BytesIO(res), bp["fonts/futura_com_book/64_df.dat"]))
    kern = {(a, b): adj for a, b, adj in kerning}
    header_off = None
    header, atlas = None, None
    img = payload(io.BytesIO(res), bp["generated/textures/borderclamp_alpha_fonts/futura_com_book/64_df.bimage"])
    hdr = list(struct.unpack(">18I", img[:72]))
    w, h = hdr[3], hdr[4]
    atlas = Image.frombytes("L", (w, h), img[72:72 + w * h])
    info = json.loads((build / "BUILD_INFO.local.json").read_text(encoding="utf-8"))
    mapping = {int(k[2:], 16): int(v[2:], 16) for k, v in info["mapping"].items()}
    metrics = {c: unpack(glyphs[i]) for i, c in enumerate(codes)}
    return dict(metrics=metrics, atlas=atlas, mapping=mapping, kerning=kern)


def form_of(ch):
    name = unicodedata.name(ch, "")
    if name.endswith("FORM"):
        return name.split()[-2]
    return None


def joins_forward(ch):
    return form_of(ch) in ("INITIAL", "MEDIAL")


def pua_word(build, word):
    import arabic_reshaper
    from bidi.algorithm import get_display
    visual = get_display(arabic_reshaper.reshape(word))
    pua = []
    for ch in visual:
        code = build["mapping"].get(ord(ch))
        if code is None:
            return visual, None
        pua.append(code)
    return visual, pua


def layout(build, pua):
    glyphs = []
    pen = 0
    previous = None
    for code in pua:
        m = build["metrics"][code]
        if previous is not None:
            pen += build["kerning"].get((previous, code), 0.0)
        glyphs.append(dict(code=code, pen=pen, **m))
        pen += m["advance"]
        previous = code
    return glyphs


def contour_span(build, g):
    """Leftmost/rightmost column of visible ink (SDF >= 128) in engine space."""
    crop = np.asarray(build["atlas"].crop((g["atlas_x"], g["atlas_y"],
                                           g["atlas_x"] + g["width"], g["atlas_y"] + g["height"])))
    columns = np.where((crop >= 128).any(axis=0))[0]
    if len(columns) == 0:
        return None
    return (g["pen"] + g["left"] + int(columns.min()),
            g["pen"] + g["left"] + int(columns.max()))


def gap_report(build, word):
    shaped, pua = pua_word(build, word)
    if pua is None:
        return dict(word=word, shaped=shaped, error="unmapped")
    glyphs = layout(build, pua)
    rows = []
    for i in range(len(glyphs) - 1):
        a, b = glyphs[i], glyphs[i + 1]
        sa, sb = contour_span(build, a), contour_span(build, b)
        if sa is None or sb is None:
            continue
        rows.append(dict(
            a="U+%04X" % a["code"], b="U+%04X" % b["code"],
            join_expected=joins_forward(shaped[i + 1]),
            gap=round(sb[0] - sa[1], 2), origin_gap=round(b["pen"] - a["pen"], 2),
            adv_a=a["advance"]))
    return dict(word=word, shaped=shaped, pua=["U+%04X" % c for c in pua], pairs=rows)


def render_metrics(build, words, scale=3):
    line_h = 96 * scale
    lines = []
    gap_rows = []
    for w in words:
        shaped, pua = pua_word(build, w)
        if pua is None:
            continue
        glyphs = layout(build, pua)
        gap_rows.append(gap_report(build, w))
        img = Image.new("L", (1400, line_h), 255)
        baseline = 70 * scale
        for g in glyphs:
            x = round((g["pen"] + g["left"]) * scale)
            y = round(baseline - g["top"] * scale)
            bw, bh = g["width"] * scale, g["height"] * scale
            crop = build["atlas"].crop((g["atlas_x"], g["atlas_y"],
                                        g["atlas_x"] + g["width"], g["atlas_y"] + g["height"]))
            crop = crop.resize((bw, bh), Image.NEAREST)
            layer = Image.new("L", (1400, line_h), 0)
            layer.paste(crop, (x, y))
            img = ImageChops.subtract(img, layer)  # composite glyphs (max ink)
        d = ImageDraw.Draw(img)
        d.line([(0, baseline), (1400, baseline)], fill=200)
        lines.append(img)
    total = Image.new("L", (1400, line_h * len(lines)), 255)
    for i, im in enumerate(lines):
        total.paste(im, (0, i * line_h))
    return total, gap_rows


def render_ttf(words, scale=3):
    line_h = 96 * scale
    font = ImageFont.truetype(str(FONT_PATH), 64 * scale)
    img = Image.new("L", (1400, line_h * len(words)), 255)
    d = ImageDraw.Draw(img)
    for i, w in enumerate(words):
        import arabic_reshaper
        from bidi.algorithm import get_display
        vis = get_display(arabic_reshaper.reshape(w))
        baseline = i * line_h + 70 * scale
        d.text((40, baseline), vis, font=font, fill=0, anchor="ls")
        d.line([(0, baseline), (1400, baseline)], fill=200)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "workspace" / "diagnostics" / "arabic_metrics")
    ap.add_argument("--words", nargs="*", default=DEFAULT_WORDS)
    ap.add_argument("--prefix", default="current_metrics")
    args = ap.parse_args()
    build = load_build(args.build.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    png, gaps = render_metrics(build, args.words)
    png.save(args.out / (args.prefix + ".png"))
    render_ttf(args.words).save(args.out / "ttf_reference.png")
    (args.out / (args.prefix + "_gaps.local.json")).write_text(
        json.dumps(gaps, ensure_ascii=False, indent=2), encoding="utf-8")
    joining = [p for g in gaps for p in g["pairs"] if p["join_expected"]]
    if joining:
        avg = sum(p["gap"] for p in joining) / len(joining)
        print("join pairs: %d  mean gap %.2f px  min %.2f  max %.2f"
              % (len(joining), avg, min(p["gap"] for p in joining), max(p["gap"] for p in joining)))
    print("wrote", args.out / (args.prefix + ".png"))


if __name__ == "__main__":
    main()
