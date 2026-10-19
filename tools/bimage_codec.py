"""Minimal .bimage codec for id Tech 5 (DXT1/BC1 and DXT5/BC3).

Header (observed, big-endian fields):
  0x00 4 bytes  checksum/hash (copied verbatim)
  0x04 ...       constant "MIB" family tag
  0x0E u16 BE    width
  0x12 u16 BE    height
  0x23 u8        pixel format (0x0A = BC1/DXT1, 0x0B = BC3/DXT5)
  0x38 u32 BE    base-level data size (bytes)
  0x48 ...       base-level pixel data (no mip chain stored)

Only the base mip level is stored, so a rebuild is header-copy + new pixel data.
"""
import struct
import numpy as np

HEADER_SIZE = 0x48


def read_header(blob):
    return dict(
        width=struct.unpack(">H", blob[0x0E:0x10])[0],
        height=struct.unpack(">H", blob[0x12:0x14])[0],
        fmt=blob[0x23],
        data_size=struct.unpack(">I", blob[0x40:0x44])[0],
    )


def _dxt1_palette(c0, c1):
    r0 = ((c0 >> 11) & 0x1F) * 255 // 31
    g0 = ((c0 >> 5) & 0x3F) * 255 // 63
    b0 = (c0 & 0x1F) * 255 // 31
    r1 = ((c1 >> 11) & 0x1F) * 255 // 31
    g1 = ((c1 >> 5) & 0x3F) * 255 // 63
    b1 = (c1 & 0x1F) * 255 // 31
    if c0 > c1:
        return np.array([
            [r0, g0, b0, 255],
            [r1, g1, b1, 255],
            [(2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255],
            [(r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255],
        ], dtype=np.int32)
    return np.array([
        [r0, g0, b0, 255],
        [r1, g1, b1, 255],
        [(r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255],
        [0, 0, 0, 0],
    ], dtype=np.int32)


def decode(rgba_bytes, width, height, fmt):
    """Return HxWx4 uint8 RGBA."""
    out = np.zeros((height, width, 4), dtype=np.uint8)
    if fmt == 0x0A:
        _decode_dxt1(rgba_bytes, width, height, out)
    elif fmt == 0x0B:
        _decode_dxt5(rgba_bytes, width, height, out)
    else:
        raise ValueError("unsupported bimage format 0x%02X" % fmt)
    return out


def _decode_dxt1(data, width, height, out):
    bw = (width + 3) // 4
    bh = (height + 3) // 4
    arr = np.frombuffer(data, dtype=np.uint8)[: bw * bh * 8].reshape(bh, bw, 8)
    c0 = arr[:, :, 0].astype(np.int32) | (arr[:, :, 1].astype(np.int32) << 8)
    c1 = arr[:, :, 2].astype(np.int32) | (arr[:, :, 3].astype(np.int32) << 8)
    idx = (arr[:, :, 4].astype(np.uint32)
           | (arr[:, :, 5].astype(np.uint32) << 8)
           | (arr[:, :, 6].astype(np.uint32) << 16)
           | (arr[:, :, 7].astype(np.uint32) << 24))
    for by in range(bh):
        for bx in range(bw):
            pal = _dxt1_palette(int(c0[by, bx]), int(c1[by, bx]))
            im = int(idx[by, bx])
            for py in range(4):
                y = by * 4 + py
                if y >= height:
                    break
                for px in range(4):
                    x = bx * 4 + px
                    if x >= width:
                        break
                    out[y, x] = pal[(im >> ((py * 4 + px) * 2)) & 3]


def _decode_dxt5(data, width, height, out):
    bw = (width + 3) // 4
    bh = (height + 3) // 4
    arr = np.frombuffer(data, dtype=np.uint8)[: bw * bh * 16].reshape(bh, bw, 16)
    c0 = arr[:, :, 8].astype(np.int32) | (arr[:, :, 9].astype(np.int32) << 8)
    c1 = arr[:, :, 10].astype(np.int32) | (arr[:, :, 11].astype(np.int32) << 8)
    idx = (arr[:, :, 12].astype(np.uint32)
           | (arr[:, :, 13].astype(np.uint32) << 8)
           | (arr[:, :, 14].astype(np.uint32) << 16)
           | (arr[:, :, 15].astype(np.uint32) << 24))
    for by in range(bh):
        for bx in range(bw):
            pal = _dxt1_palette(int(c0[by, bx]), int(c1[by, bx]))
            im = int(idx[by, bx])
            for py in range(4):
                y = by * 4 + py
                if y >= height:
                    break
                for px in range(4):
                    x = bx * 4 + px
                    if x >= width:
                        break
                    out[y, x, :3] = pal[(im >> ((py * 4 + px) * 2)) & 3][:3]
    # alpha self-consistent with _dxt1_palette (255 opaque)


def encode_dxt1(rgba, orig_data, changemask):
    """Encode BC1. Blocks where changemask is False reuse orig_data bytes.

    rgba: HxWx4 uint8. changemask: HxW bool (True where we re-encode).
    Returns bytes.
    """
    height, width = rgba.shape[:2]
    bw = (width + 3) // 4
    bh = (height + 3) // 4
    src = rgba.astype(np.int32)
    if orig_data is not None:
        arr = np.frombuffer(orig_data, dtype=np.uint8)[: bw * bh * 8].reshape(bh, bw, 8).copy()
    else:
        arr = np.zeros((bh, bw, 8), dtype=np.uint8)
    # block needs re-encode if any pixel flagged
    padded = np.zeros((bh * 4, bw * 4), dtype=bool)
    padded[:height, :width] = changemask
    pmask = padded.reshape(bh, 4, bw, 4).any(axis=(1, 3))

    for by in range(bh):
        for bx in range(bw):
            if not pmask[by, bx]:
                continue
            block = np.zeros((4, 4, 4), dtype=np.int32)
            blk = src[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4]
            block[: blk.shape[0], : blk.shape[1]] = blk
            rgb = block[:, :, :3].reshape(-1, 3)
            # pick endpoints by principal axis (range fit)
            lo = rgb.min(axis=0)
            hi = rgb.max(axis=0)
            if np.array_equal(lo, hi):
                c0 = _to565(hi)
                c1 = _to565(lo)
                if c0 <= c1:
                    c0, c1 = c1, c0
                idxs = np.zeros(16, dtype=np.uint32)
            else:
                c0 = _to565(hi)
                c1 = _to565(lo)
                if c0 == c1:
                    c1 = c1 ^ 0x0001 & 0xFFFF
                    c0, c1 = (c0, c1) if c0 > c1 else (c1, c0)
                pal = _dxt1_palette(int(c0), int(c1))
                palc = pal[:, :3]
                d = ((rgb[:, None, :] - palc[None, :, :]) ** 2).sum(axis=2)
                best = d.argmin(axis=1).astype(np.uint32)
                idxs = np.zeros(16, dtype=np.uint32)
                for p in range(16):
                    idxs[p] = best[p] << ((p % 4) * 2 + (p // 4) * 8)
            word = int(idxs.sum())
            arr[by, bx, 0] = c0 & 0xFF
            arr[by, bx, 1] = (c0 >> 8) & 0xFF
            arr[by, bx, 2] = c1 & 0xFF
            arr[by, bx, 3] = (c1 >> 8) & 0xFF
            arr[by, bx, 4] = word & 0xFF
            arr[by, bx, 5] = (word >> 8) & 0xFF
            arr[by, bx, 6] = (word >> 16) & 0xFF
            arr[by, bx, 7] = (word >> 24) & 0xFF
    return arr.tobytes()


def _to565(c):
    r = int(c[0]) * 31 // 255
    g = int(c[1]) * 63 // 255
    b = int(c[2]) * 31 // 255
    return (r << 11) | (g << 5) | b


def rebuild(orig_blob, rgba, changemask):
    """Header is copied verbatim (dimensions/format/size are unchanged)."""
    hdr = read_header(orig_blob)
    assert hdr["fmt"] == 0x0A, "rebuild supports DXT1 only"
    newpix = encode_dxt1(rgba, orig_blob[HEADER_SIZE:], changemask)
    assert len(newpix) == len(orig_blob) - HEADER_SIZE
    return orig_blob[:HEADER_SIZE] + newpix
