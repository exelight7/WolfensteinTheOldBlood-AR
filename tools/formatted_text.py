"""Token-aware Arabic shaping and .lang value serialization.

Pure library: no file access, no side effects. The subtitle POC builder
(tools/build_subtitle_poc.py) draws on this module; build_menu_pilot.py is
left untouched as the regression anchor.
"""
import re
import arabic_reshaper
from bidi.algorithm import get_display

# Protected control tokens observed in the translated corpus.
# Census over the 3,572 confirmed english values:
#   brackets 1287 ([eng]/[ger]/timings like [1.33]/[]), printf 44 (%d %s %02d),
#   angle 11 (<JOYn>), brace 1 ({0}), ident 91, var 0 in games text, caret 23.
BRACKET_RE = re.compile(r"\[[^\]\r\n]*\]")
ANGLE_RE = re.compile(r"<[^<>\r\n]*>")
BRACE_RE = re.compile(r"\{[^{}\r\n]*\}")
PRINTF_RE = re.compile(
    r"%[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLzjt]*[diuoxXfFeEgGaAcspn]|%\d")
IDENT_RE = re.compile(r"(?<![\w$])_[A-Za-z][A-Za-z0-9_]*")
VAR_RE = re.compile(r"(?<![\w$])\$[A-Za-z][A-Za-z0-9_]*")
CARET_RE = re.compile(r"\^[0-9]")
NEWLINE_RE = re.compile("\n")
TOKEN_RE = re.compile(
    r"\[[^\]\r\n]*\]"
    r"|%[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLzjt]*[diuoxXfFeEgGaAcspn]|%\d"
    r"|<[^<>\r\n]*>"
    r"|\{[^{}\r\n]*\}"
    r"|(?<![\w$])_[A-Za-z][A-Za-z0-9_]*"
    r"|(?<![\w$])\$[A-Za-z][A-Za-z0-9_]*"
    r"|\^[0-9]"
    r"|\n")

# .lang escape rules as decoded by tools/local_reference.py:
#   inside a quoted value only \\n and \\\" exist; a raw backslash followed by
#   anything else cannot be represented (TOKEN regex restricts to \\["n]).
def encode_lang_value(value):
    """Serialize a decoded logical value into the literal stored in english.lang."""
    if "\\" in value:
        raise ValueError("Encoded values cannot contain a raw backslash: %r" % value)
    return value.replace("\n", "\\n").replace('"', '\\"')


def decode_lang_value(literal):
    """Inverse of encode_lang_value with the documented escape set."""
    return literal.replace("\\n", "\n").replace('\\"', '"')


def tokens_in(text):
    """Protected control tokens occurring in a logical string, in order."""
    return [m.group(0) for m in TOKEN_RE.finditer(text)]


def _classify(ch):
    """Direction class of one character for run splitting (simplified UAX9)."""
    code = ord(ch)
    if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0xFE70 <= code <= 0xFEFF:
        return 'R'
    if (ch.isalnum() and ch.isascii()) or 0xAA <= code <= 0xFF and ch.isalpha():
        return 'L'
    if ch == '\n':
        raise ValueError("Newline must be split before run shaping")
    return 'N'


def _runs(line):
    """Split a line into maximal same-class runs, resolving neutrals.

    Neutrals between two runs of the same class merge into that class.
    Edge neutrals attach to the nearest run. Only neutrals separating an
    L run from an R run remain standalone, and they stay between both
    islands after the RTL reversal, exactly as the Unicode bidi model
    places paragraph-level neutrality.
    """
    classes = [_classify(c) for c in line]
    segments = []
    start = 0
    for i in range(1, len(classes) + 1):
        if i == len(classes) or classes[i] != classes[start]:
            segments.append([classes[start], line[start:i]])
            start = i
    resolved = []
    for i, (cls, text) in enumerate(segments):
        if cls != 'N':
            resolved.append([cls, text])
            continue
        prev_cls = resolved[-1][0] if resolved else None
        next_cls = segments[i + 1][0] if i + 1 < len(segments) else None
        if prev_cls is not None and next_cls is not None and prev_cls != next_cls:
            resolved.append(['N', text])
        else:
            anchor = next_cls if prev_cls is None else prev_cls
            if anchor is None or anchor == 'N':
                anchor = 'N'
            if resolved and resolved[-1][0] == anchor:
                resolved[-1][1] += text
            else:
                resolved.append([anchor, text])
    # Adjacent same-class runs can survive forward attachment (a leading
    # neutral anchored to the following run); fold them together.
    merged = []
    for cls, text in resolved:
        if merged and merged[-1][0] == cls:
            merged[-1][1] += text
        else:
            merged.append([cls, text])
    return [(cls, text) for cls, text in merged]


def _shape_r_run(text):
    return get_display(arabic_reshaper.reshape(text), base_dir='R')


def _shape_text_segment(segment):
    """Shape one token-free text segment (a piece between control tokens).

    The segment is split into direction runs; when Arabic is present the
    run sequence is reversed (RTL base direction) and each Arabic run is
    shaped on its own, so Latin islands, digits and neutrals land in the
    visually correct slot without ever running through python-bidi as a
    whole mixed string.
    """
    runs = _runs(segment)
    if any(cls == 'R' for cls, _ in runs):
        runs = list(reversed(runs))
    return "".join(_shape_r_run(text) if cls == 'R' else text for cls, text in runs)


# ---------------------------------------------------------------------------
# Token classification (corpus-evidenced, see README notes in tests).
#
# TRANSPARENT_JOIN  invisible runtime metadata scanned by the engine for
#                   timing/language grouping ([eng], [2.4], [400], ^colours).
#                   The engine never draws these bytes; removing one must not
#                   change which Arabic contextual forms the neighbouring
#                   letters wear, so shaping looks through them (ZWJ logic).
# HARD_BOUNDARY     real line break (\n). Resets joining and layout.
# VISIBLE_LTR       specifier/identifier/variable/angle/brace tokens that the
#                   engine substitutes with visible Latin-ish text at the
#                   logical byte position; they are islands, not joiners.
# LINE_BOUNDARY     alias of HARD_BOUNDARY (same semantics, kept explicit).
# ---------------------------------------------------------------------------
TRANSPARENT_JOIN_RE = re.compile(r"\[[^\]\r\n]*\]|\^[0-9]")
VISIBLE_LTR_RE = re.compile(
    r"%[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLzjt]*[diuoxXfFeEgGaAcspn]|%\d"
    r"|<[^<>\r\n]*>"
    r"|\{[^{}\r\n]*\}"
    r"|(?<![\w$])_[A-Za-z][A-Za-z0-9_]*"
    r"|(?<![\w$])\$[A-Za-z][A-Za-z0-9_]*")

ZWJ = "\u200d"

# Arabic base letters that connect to the FOLLOWING letter (dual-joining),
# per the Unicode ArabicShaping joining classes (tatweel included).
JOINS_FORWARD = set(
    "\u0626\u0628\u062A\u062B\u062C\u062D\u062E\u0633\u0634\u0635\u0636"
    "\u0637\u0638\u0639\u063A\u0640\u0641\u0642\u0643\u0644\u0645\u0646"
    "\u0647\u064A\u06CC\u0691\u06BA\u06BE\u06C1\u06C2\u06C3\u06CD\u06CF\u06D0")
# Any Arabic letter can RECEIVE a connection from the preceding letter
# (dual-joining letters on both sides, right-joining letters from the left):
RECEIVES_JOIN_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF))
# Combining marks are transparent when looking for the "last/first letter":
COMBINING_RANGES = ((0x0610, 0x061A), (0x064B, 0x065F), (0x0670, 0x0670))

def _is_arabic_letter(ch):
    code = ord(ch)
    return (any(lo <= code <= hi for lo, hi in RECEIVES_JOIN_RANGES)
            and not any(lo <= code <= hi for lo, hi in COMBINING_RANGES)
            and ch not in "\u061f\u060c\u061b\u061d\u060d\u066a\u066c\u066d\u066b\u06d4")

def _last_arabic_letter(text):
    for ch in reversed(text):
        if _is_arabic_letter(ch):
            return ch
        if any(lo <= ord(ch) <= hi for lo, hi in COMBINING_RANGES):
            continue
        return None
    return None

def _first_arabic_letter(text):
    for ch in text:
        if _is_arabic_letter(ch):
            return ch
        if any(lo <= ord(ch) <= hi for lo, hi in COMBINING_RANGES):
            continue
        return None
    return None

def _joins_forward(ch):
    return ch in JOINS_FORWARD

def _shape_line_spans(line):
    """Split a logical line into (spans, token list).

    Returns a list of items: ("text", string) and ("token", string), in
    logical byte order; consecutive tokens become ("tokens", [..]).
    """
    items = []
    cursor = 0
    pending = []
    for match in TOKEN_RE.finditer(line):
        tok = match.group(0)
        if tok == "\n":
            raise ValueError("Newline must be split before token shaping")
        if match.start() > cursor:
            if pending:
                items.append(("tokens", pending))
                pending = []
            items.append(("text", line[cursor:match.start()]))
        pending.append(tok)
        cursor = match.end()
    if cursor < len(line):
        if pending:
            items.append(("tokens", pending))
            pending = []
        items.append(("text", line[cursor:]))
    if pending:
        items.append(("tokens", pending))
    return items


def _transparent_gap(gap_tokens):
    """Shaping-transparent group of consecutive tokens ([] tags, ^colours)."""
    return gap_tokens and all(TRANSPARENT_JOIN_RE.fullmatch(t) for t in gap_tokens)


def shape_line(line, mapping):
    """Shape one logical line into the visual bytes the engine renders.

    Control tokens are kept at their logical byte positions and never
    reshaped: the engine scans them in byte order — bracket tags start timed
    subtitle segments and a specifier like "%d" must remain one parseable
    unit. Text between tokens is shaped through _shape_text_segment, so
    layout is identical to the pre-transparency pipeline wherever tokens do
    not touch Arabic letters.

    Token transparency: a group of consecutive invisible metadata tokens
    ([eng], [2.4], [400], ^colour, ...) does not itself occupy screen space,
    so Arabic letters that would be visually adjacent across such a gap keep
    their joining context: a zero-width joiner is injected on each side of
    the gap when (and only when) both neighbourhood letters demand it —
    deterministic, no destructive token removal, token byte positions are
    untouched. Visible-Latin tokens and newlines stay hard boundaries.
    Every non-ASCII visual character is finally mapped to its PUA glyph.
    """
    if not line:
        return ""
    if "\r" in line or "\t" in line:
        raise ValueError("Carriage returns or tabs are not representable")
    items = _shape_line_spans(line)
    # zwj_left[i], zwj_right[i]: whether text span i receives/emits a joiner
    # across the adjacent token gap. Gaps of consecutive invisible tokens
    # ([eng][2.4]...) are one transparent unit; visible-Latin tokens and
    # newlines are hard boundaries.
    n_text = sum(1 for kind, _ in items if kind == "text")
    zwj_left = [False] * n_text
    zwj_right = [False] * n_text
    span_idx = -1
    for index, (kind, payload) in enumerate(items):
        if kind != "tokens":
            if kind == "text":
                span_idx += 1
            continue
        next_item = items[index + 1] if index + 1 < len(items) else None
        prev_item = items[index - 1] if index > 0 else None
        if next_item is None or next_item[0] != "text":
            continue
        if prev_item is None or prev_item[0] != "text":
            continue
        if not _transparent_gap(payload):
            continue
        left = _last_arabic_letter(prev_item[1])
        right = _first_arabic_letter(next_item[1])
        if left is not None and right is not None and _joins_forward(left):
            zwj_right[span_idx] = True
            zwj_left[span_idx + 1] = True
    parts = []
    span_idx = -1
    for kind, payload in items:
        if kind != "text":
            parts.append("".join(payload))
            continue
        span_idx += 1
        span = payload
        if zwj_left[span_idx]:
            span = ZWJ + span
        if zwj_right[span_idx]:
            span = span + ZWJ
        parts.append(_shape_text_segment(span))
    visual = "".join(parts)
    if ZWJ in visual:
        raise AssertionError("Zero-width joiner leaked into the visual stream")
    if mapping:
        visual = "".join(chr(mapping[c]) if c in mapping else c for c in visual)
    return visual


def shape_formatted(text, mapping):
    """Shape a full logical string (may contain real newlines)."""
    lines = text.split("\n")
    shaped = "\n".join(shape_line(line, mapping) for line in lines)
    assert shaped.count("\n") == text.count("\n")
    return shaped


# ---------------------------------------------------------------------------
# Candidate C — span-order correction for RTL across timed control tokens.
#
# shape_line() keeps every text span at its logical byte slot, so a record
# split into timed chunks ([2.4] ... [7.6] ...) is emitted chunk-by-chunk in
# LOGICAL order. An LTR-only renderer that draws the whole record as one
# left-to-right glyph stream then shows those chunks in the wrong visual
# order for Arabic (the first phrase ends up furthest left). Correcting that
# means the concatenation of the visible text must equal the visual order of
# the token-free line, which is exactly what reversing the span order gives
# (proven equal to shaping the whole line as one RTL paragraph). Control
# tokens keep their byte order, positions and values, so the engine's timing
# scanner is unaffected.
# ---------------------------------------------------------------------------
def _span_is_pure_rtl(text):
    """True when a span has no Latin *letter* island.

    Digits and neutrals are allowed: they are contained within the span and
    are laid out the same way whether the span is shaped alone or as part of
    the whole line, so reversing the span order stays equivalent to shaping
    the token-free line. A Latin word (e.g. an untranslated island) is not,
    so such spans force the safe fallback.
    """
    for cls, run in _runs(text):
        if cls == 'L' and any(c.isalpha() and c.isascii() for c in run):
            return False
    return True


def shape_line_spans_ordered(line, mapping):
    """Shape one line with Candidate C span-order correction.

    Falls back to shape_line() when the correction is not provably safe:
    a span carries a Latin island (reordering would move it), or a
    transparent token gap sits between two joining letters (the joiner
    context is position-dependent).
    """
    if not line:
        return ""
    items = _shape_line_spans(line)
    spans = [p for k, p in items if k == "text"]
    if not spans or not all(_span_is_pure_rtl(s) for s in spans):
        return shape_line(line, mapping)
    for index, (kind, payload) in enumerate(items):
        if kind != "tokens" or not _transparent_gap(payload):
            continue
        nxt = items[index + 1] if index + 1 < len(items) else None
        prv = items[index - 1] if index > 0 else None
        if nxt and prv and nxt[0] == "text" and prv[0] == "text":
            left = _last_arabic_letter(prv[1])
            right = _first_arabic_letter(nxt[1])
            if left is not None and right is not None and _joins_forward(left):
                return shape_line(line, mapping)
    shaped = [_shape_text_segment(span) for span in spans]
    shaped.reverse()
    stream = iter(shaped)
    parts = []
    for kind, payload in items:
        parts.append("".join(payload) if kind == "tokens" else next(stream))
    visual = "".join(parts)
    if mapping:
        visual = "".join(chr(mapping[c]) if c in mapping else c for c in visual)
    return visual


def shape_formatted_ordered(text, mapping):
    """shape_formatted() variant applying Candidate C per line."""
    lines = text.split("\n")
    shaped = "\n".join(shape_line_spans_ordered(line, mapping) for line in lines)
    assert shaped.count("\n") == text.count("\n")
    return shaped
