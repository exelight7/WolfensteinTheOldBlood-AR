"""Experimental, append-only Arabic distance-field glyphs for WTOB idf+ fonts."""
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt


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


def extend_font(metrics, image, font_path, mapping):
    glyphs, codes, kerning = inspect_font(metrics)
    header, atlas = inspect_image(image)
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
        additions.append((code, packed, bitmap, x, y))
        x += bitmap.width + 2
        row_height = max(row_height, bitmap.height)
    if not additions:
        return metrics, image
    height = (y + row_height + 15) // 16 * 16
    expanded = Image.new("L", (atlas.width, height))
    expanded.paste(atlas, (0, 0))
    for code, packed, bitmap, x, y in additions:
        glyphs.append(packed)
        codes.append(code)
        expanded.paste(bitmap, (x, y))
    result = bytearray(metrics[:12])
    struct.pack_into(">H", result, 10, len(codes))
    result += b"".join(glyphs) + struct.pack("<" + "I" * len(codes), *codes) + kerning
    header[4] = header[16] = height
    header[17] = atlas.width * height
    texture = struct.pack(">18I", *header) + expanded.tobytes()
    new_glyphs, new_codes, new_kerning = inspect_font(result)
    old_glyphs, old_codes, old_kerning = inspect_font(metrics)
    assert new_glyphs[:len(old_glyphs)] == old_glyphs
    assert new_codes[:len(old_codes)] == old_codes and new_kerning == old_kerning
    assert texture[72:72 + atlas.width * atlas.height] == image[72:]
    inspect_image(texture)
    return bytes(result), texture
