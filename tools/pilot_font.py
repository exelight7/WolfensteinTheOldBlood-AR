"""Experimental, append-only Arabic distance-field glyphs for WTOB idf+ fonts."""
import struct
import unicodedata

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt

# The engine's idf+ kerning table is a flat, (glyph_a, glyph_b)-sorted list of
# 8-byte entries: u16 little-endian "previous glyph index", u16 little-endian
# "next glyph index", f32 little-endian pixel adjustment. The pair is keyed in
# reading order (previous, next) and the adjustment is added to the pen after
# advancing over the previous glyph. Native Latin lives on this table; the
# append-only Arabic glyphs leave joining strokes open because the per-glyph
# advance cannot encode a per-pair join correction, so Arabic joining pairs are
# emitted here as measured negative adjustments.
KERN_ENTRY = struct.Struct("<HHf")


def inspect_font(data):
    if data[:4] != b"idf+" or len(data) < 14:
        raise ValueError("Unsupported font signature")
    count = struct.unpack_from(">H", data, 10)[0]
    end = 12 + count * 16
    if end + 2 > len(data):
        raise ValueError("Truncated font")
    glyphs = [data[12 + i * 12:24 + i * 12] for i in range(count)]
    codes = list(struct.unpack_from("<" + "I" * count, data, 12 + count * 12))
    kernings = struct.unpack_from(">H", data, end)[0]
    if codes != sorted(set(codes)) or len(data) != end + 2 + kernings * 8:
        raise ValueError("Unexpected character map or kerning table")
    return glyphs, codes, data[end:]


def parse_kerning(metrics):
    """Return the kerning table as a sorted list of (previous, next, px)."""
    count = struct.unpack_from(">H", metrics, 10)[0]
    end = 12 + count * 16
    total = struct.unpack_from(">H", metrics, end)[0]
    return [KERN_ENTRY.unpack_from(metrics, end + 2 + i * 8) for i in range(total)]


def pack_kerning(pairs):
    """Serialize a (previous, next, px) table; must already be uniquely sorted."""
    pairs = sorted(pairs)
    if len({(a, b) for a, b, _ in pairs}) != len(pairs):
        raise ValueError("Duplicate kerning pair")
    return struct.pack(">H", len(pairs)) + b"".join(KERN_ENTRY.pack(*p) for p in pairs)


def glyph_form(character):
    """Contextual class of a presentation-form codepoint (None if not a form)."""
    name = unicodedata.name(character, "")
    for suffix, form in (("INITIAL FORM", "INITIAL"), ("MEDIAL FORM", "MEDIAL"),
                         ("FINAL FORM", "FINAL"), ("ISOLATED FORM", "ISOLATED")):
        if name.endswith(suffix):
            return form
    return "LIGATURE" if "LIGATURE" in name else None


def ink_columns(bitmap):
    columns = np.where((np.asarray(bitmap) >= 128).any(axis=0))[0]
    return int(columns.min()), int(columns.max())


def joining_kernings(additions, overlap):
    """Measure the negative adjustment each forward-joining render pair needs so
    the two glyphs' visible ink overlaps by `overlap` pixels.

    Arabic is written right-to-left, so bidi puts the logical first letter of a
    join on the RIGHT: in the engine's left-to-right render order the pair is
    (previous = logical next, next = logical first). A join exists iff the
    logical first glyph -- the render-second glyph -- is an INITIAL/MEDIAL form.
    The adjustment is keyed (render-previous, render-next) and reduces the pen
    after the render-previous glyph; only pairs that would otherwise leave a
    visible gap are emitted."""
    pairs = []
    for following in additions:                      # logical first (render-second)
        if following["form"] not in ("INITIAL", "MEDIAL"):
            continue
        left = following["left"] + ink_columns(following["bitmap"])[0]
        for previous in additions:                   # logical next (render-first)
            if previous["form"] not in ("MEDIAL", "FINAL", "LIGATURE"):
                continue
            right = previous["left"] + ink_columns(previous["bitmap"])[1]
            gap = previous["advance"] + left - right
            adjustment = -(gap + overlap)
            if adjustment < -0.05:
                pairs.append((previous["glyph_index"], following["glyph_index"],
                              round(adjustment, 3)))
    return pairs


def inspect_image(data):
    if len(data) < 72:
        raise ValueError("Truncated image")
    header = list(struct.unpack(">18I", data[:72]))
    width, height = header[3:5]
    if (header[1] != 0x094D4942 or header[6] != 1 or header[8] != 5
            or header[15:18] != [width, height, width * height]
            or len(data) != 72 + width * height):
        raise ValueError("Unsupported atlas layout (expected one raw alpha image)")
    return header, Image.frombytes("L", (width, height), data[72:])


def glyph_bitmap(font_path, character):
    scale, padding = 4, 8
    font = ImageFont.truetype(str(font_path), 64 * scale, layout_engine=ImageFont.Layout.BASIC)
    left, top, right, bottom = font.getbbox(character, anchor="ls")
    left, top = left // scale, top // scale
    right, bottom = (right + scale - 1) // scale, (bottom + scale - 1) // scale
    width, height = right - left + 2 * padding, bottom - top + 2 * padding
    if not (0 < width < 256 and 0 < height < 256):
        raise ValueError("Glyph exceeds byte-sized dimensions")
    mask = Image.new("L", (width * scale, height * scale))
    ImageDraw.Draw(mask).text(((padding - left) * scale, (padding - top) * scale),
                             character, font=font, fill=255, anchor="ls")
    inside = np.asarray(mask) >= 128
    if not inside.any():
        raise ValueError(f"Empty glyph for U+{ord(character):04X}")
    distance = (distance_transform_edt(inside) - distance_transform_edt(~inside)) / scale
    sdf = Image.fromarray(np.clip(128 + distance * 16, 0, 255).astype(np.uint8))
    sdf = sdf.resize((width, height), Image.Resampling.LANCZOS)
    advance = round(font.getlength(character) / scale)
    return sdf, -top + padding, left - padding, advance


def extend_font(metrics, image, font_path, mapping, joining_kern=False, kern_overlap=1.0):
    glyphs, codes, kerning = inspect_font(metrics)
    header, atlas = inspect_image(image)
    native = parse_kerning(metrics)
    additions = []
    x, y, row_height = 0, atlas.height, 0
    for character, code in sorted(mapping.items(), key=lambda item: item[1]):
        if code <= max(codes):
            raise ValueError("New glyphs must append after existing codepoints")
        bitmap, top, left, advance = glyph_bitmap(font_path, character)
        if x + bitmap.width > atlas.width:
            x, y, row_height = 0, y + row_height + 2, 0
        packed = struct.pack("<BBbbHHHh", bitmap.width, bitmap.height,
                             top, left, advance, x, y, -1)
        additions.append(dict(code=code, packed=packed, bitmap=bitmap, x=x, y=y,
                              top=top, left=left, advance=advance,
                              glyph_index=len(glyphs) + len(additions),
                              form=glyph_form(character)))
        x += bitmap.width + 2
        row_height = max(row_height, bitmap.height)
    if not additions:
        return metrics, image
    pair_table = native
    if joining_kern:
        emitted = joining_kernings(additions, kern_overlap)
        assert not any(a < len(glyphs) for a, _, _ in emitted), "kern pair must target appended glyphs"
        pair_table = sorted(native + emitted)
        kerning = pack_kerning(pair_table)
        starts = {}
        for index, (previous, _, _) in enumerate(pair_table):
            starts.setdefault(previous, index)
        for addition in additions:
            # idf+ readers enter the pair table through this per-glyph offset.
            start = starts.get(addition["glyph_index"], -1)
            if start > 32767:
                raise ValueError("Kerning start exceeds signed glyph index")
            packed = bytearray(addition["packed"])
            struct.pack_into("<h", packed, 10, start)
            addition["packed"] = bytes(packed)
    height = (y + row_height + 15) // 16 * 16
    expanded = Image.new("L", (atlas.width, height))
    expanded.paste(atlas, (0, 0))
    for addition in additions:
        glyphs.append(addition["packed"])
        codes.append(addition["code"])
        expanded.paste(addition["bitmap"], (addition["x"], addition["y"]))
    result = bytearray(metrics[:12])
    struct.pack_into(">H", result, 10, len(codes))
    result += b"".join(glyphs) + struct.pack("<" + "I" * len(codes), *codes) + kerning
    header[4] = header[16] = height
    header[17] = atlas.width * height
    texture = struct.pack(">18I", *header) + expanded.tobytes()
    new_glyphs, new_codes, new_kerning = inspect_font(result)
    old_glyphs, old_codes, old_kerning = inspect_font(metrics)
    assert new_glyphs[:len(old_glyphs)] == old_glyphs
    assert new_codes[:len(old_codes)] == old_codes
    assert parse_kerning(result) == sorted(pair_table)
    assert set(native) <= set(parse_kerning(result)), "native kerning must be preserved"
    assert texture[72:72 + atlas.width * atlas.height] == image[72:]
    inspect_image(texture)
    return bytes(result), texture
