"""Read-only joining-metric diagnostic: quantifies the physical-join defect and
the V4 fix by simulating the engine's idf+ layout on the real builds.

Writes workspace/diagnostics/arabic_join_metrics.local.json and prints a summary.
Does not modify any build, archive, or the live game.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_arabic_metrics_debug as R  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "workspace" / "opening_runtime_poc_v3"
AFTER = ROOT / "workspace" / "opening_runtime_poc_v4"
OUT = ROOT / "workspace" / "diagnostics" / "arabic_join_metrics.local.json"


def valid_pair_gaps(build):
    """Gaps for every render-adjacent join where the joining glyph is an
    INITIAL/MEDIAL form and its render-previous is a MEDIAL/FINAL/LIGATURE."""
    import unicodedata
    rev = {v: k for k, v in build["mapping"].items()}
    metrics = build["metrics"]

    def form(code):
        name = unicodedata.name(chr(rev[code]), "")
        for suffix, value in (("INITIAL FORM", "INITIAL"), ("MEDIAL FORM", "MEDIAL"),
                              ("FINAL FORM", "FINAL"), ("ISOLATED FORM", "ISOLATED")):
            if name.endswith(suffix):
                return value
        return "LIGATURE" if "LIGATURE" in name else None

    def ink(code):
        m = metrics[code]
        crop = np.asarray(build["atlas"].crop((m["atlas_x"], m["atlas_y"],
                                               m["atlas_x"] + m["width"], m["atlas_y"] + m["height"])))
        columns = np.where((crop >= 128).any(axis=0))[0]
        return (int(columns.min()), int(columns.max())) if len(columns) else None

    forms = {c: form(c) for c in rev}
    inkc = {c: ink(c) for c in rev}
    gaps = []
    for following in rev:
        if forms[following] not in ("INITIAL", "MEDIAL") or not inkc[following]:
            continue
        left = metrics[following]["left"] + inkc[following][0]
        for previous in rev:
            if forms[previous] not in ("MEDIAL", "FINAL", "LIGATURE") or not inkc[previous]:
                continue
            right = metrics[previous]["left"] + inkc[previous][1]
            gaps.append(metrics[previous]["advance"] + left - right
                        + build["kerning"].get((previous, following), 0.0))
    return gaps


def word_gaps(build, word):
    shaped, pua = R.pua_word(build, word)
    if pua is None:
        return None
    glyphs = R.layout(build, pua)
    rows = []
    for i in range(len(glyphs) - 1):
        a, b = glyphs[i], glyphs[i + 1]
        if not R.joins_forward(shaped[i + 1]):
            continue
        sa, sb = R.contour_span(build, a), R.contour_span(build, b)
        if sa and sb:
            rows.append(round(sb[0] - sa[1], 2))
    return rows


def font_view(build):
    from archive_inventory import records, payload
    import io
    import struct
    idx = (build / "chunk0.index").read_bytes()
    res = (build / "chunk0.resources").read_bytes()
    entries, _ = records(idx, len(res))
    bp = {e["names"][2]: e for e in entries}
    font = payload(io.BytesIO(res), bp["fonts/futura_com_book/64_df.dat"])
    count = struct.unpack_from(">H", font, 10)[0]
    glyphs = [font[12 + i * 12:24 + i * 12] for i in range(count)]
    end = 12 + count * 16
    total = struct.unpack_from(">H", font, end)[0]
    kerning = {(struct.unpack_from("<H", font, end + 2 + i * 8)[0],
                struct.unpack_from("<H", font, end + 2 + i * 8 + 2)[0]):
               struct.unpack_from("<f", font, end + 2 + i * 8 + 4)[0] for i in range(total)}
    atlas = payload(io.BytesIO(res), bp["generated/textures/borderclamp_alpha_fonts/futura_com_book/64_df.bimage"])
    return glyphs, kerning, atlas


def main():
    before = R.load_build(BEFORE)
    after = R.load_build(AFTER)
    words = R.DEFAULT_WORDS

    test = {}
    for w in words:
        test[w] = {"before": word_gaps(before, w), "after": word_gaps(after, w)}

    bg, ag = valid_pair_gaps(before), valid_pair_gaps(after)
    bg_kern, akern = len(before["kerning"]), len(after["kerning"])

    gb, kb, ab = font_view(BEFORE)
    ga, ka, aa = font_view(AFTER)
    common = set(kb) & set(ka)

    report = dict(
        model=("idf+ glyph records <BBbbHHHh>, engine layout pen+=advance(+kern), "
               "RTL via bidi, ink = SDF contour >=128; join exists iff the "
               "logical-first glyph (render-second) is an INITIAL/MEDIAL form"),
        builds={"before": str(BEFORE.relative_to(ROOT)), "after": str(AFTER.relative_to(ROOT))},
        gap_sign_convention=("gap = next.left_ink - previous.right_ink; 0 = 1px overlap, "
                             "1 = touching, >1 = visible gap"),
        all_valid_joining_pairs=dict(
            count=len(bg),
            before_max_gap=round(max(bg), 2), before_min_gap=round(min(bg), 2),
            before_histogram=sorted(Counter(int(g) for g in bg).items()),
            after_max_gap=round(max(ag), 2), after_min_gap=round(min(ag), 2),
            after_histogram=sorted(Counter(int(g) for g in ag).items())),
        test_words=test,
        kerning_table=dict(native_pairs=len(kb),
                           before_total=bg_kern, after_total=akern,
                           added_pairs=akern - bg_kern,
                           native_preserved=all(ka[k] == v for k, v in kb.items())),
        font_diff=dict(glyph_records_identical=(gb == ga), atlas_identical=(ab == aa),
                       only_kerning_changed=(gb == ga and ab == aa and kb != ka)),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("valid joining pairs:", report["all_valid_joining_pairs"]["count"])
    print("  before gaps:", report["all_valid_joining_pairs"]["before_histogram"],
          "max", report["all_valid_joining_pairs"]["before_max_gap"])
    print("  after  gaps:", report["all_valid_joining_pairs"]["after_histogram"],
          "max", report["all_valid_joining_pairs"]["after_max_gap"])
    print("kerning:", report["kerning_table"])
    print("font diff:", report["font_diff"])
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
