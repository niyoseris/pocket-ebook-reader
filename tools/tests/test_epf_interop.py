#!/usr/bin/env python3
"""Checks that the `.epf` generator (tools/fontgen.py) and the device reader
(firmware/src/font.cpp) AGREE with each other.

Why does this file exist?
-------------------------
Two separate agents wrote the two halves of the `.epf` format from the same
written specification: `tools/fontgen.py` produces the file, `firmware/src/font.cpp`
reads it.  The easiest place to misread the format is how the glyph bitmap is
packed: is it row-padded bytes, or a continuous bit stream?  The two give
different results for every glyph wider than 8 px.  This test does not assume
either; it READS the source of font.cpp, derives the rule from there, and opens
the file fontgen produces with that rule.

--------------------------------------------------------------------------------
FINDING 1 — Bitmap packing: COMPATIBLE
--------------------------------------------------------------------------------
`firmware/src/font.cpp` lines 301-309 (fontDrawGlyph):

    301    for (int row = 0; row < g->height; row++) {
    302        for (int col = 0; col < g->width; col++) {
    303            const uint32_t bit = (uint32_t)row * g->width + (uint32_t)col;
    304            if (!(s_bitmap[bit >> 3] & (uint8_t)(0x80 >> (bit & 7)))) continue;

and the size calculation on line 293:

    293    const uint32_t nbytes =
    294        ((uint32_t)g->width * (uint32_t)g->height + 7u) / 8u;

This is a **continuous MSB-first bit stream** — there is NO row padding:

    bit N = row * width + col   ->   byte[N >> 3],  mask 0x80 >> (N & 7)

A row-padded reader would expect `((width + 7) / 8) * height` bytes and index
`byte[row * stride + (col >> 3)]`; font.cpp does neither.  The `pack_bits()`/
`unpack_bits()` in `fontgen.py` use the same rule (`bit = y*width + x`,
`byte = bit >> 3`, `mask = 0x80 >> (bit & 7)`) and `build_epf()` writes the size
as `(width*height + 7) // 8`.
RESULT: both sides apply the same rule, these tests PASS.

--------------------------------------------------------------------------------
FINDING 2 — where the `top` field is measured from: WAS INCOMPATIBLE, NOW COMPATIBLE
--------------------------------------------------------------------------------
When this test was written the firmware assumed the `top` value was measured
**from the baseline upward** (the then line 28 of `font.h` and the then line 299
of `font.cpp`: `const int y0 = baseline_y - (int)g->top * scale;`).

`fontgen.py`, however, measures and writes the `top` value **from the top of the
glyph box (the line box)**, i.e. from the ascender line.  `fontgen._tighten()`
uses Pillow's `textbbox(..., anchor="la")` call; the origin of this anchor is
exactly the top-left corner of the line box, so the returned `bt` value is
already the distance from the top of the box.

The project specification says:

    "Glyphs are rendered into a box of `height` pixels; `top` is the y offset
     of the glyph bitmap **inside that box**"

"inside that box" = measured from the top of the box.  That is the rule fontgen
applies.  Also, the only tool in the repository that produces `.epf` is
`tools/fontgen.py` (the firmware's `font.h` file says so too), so `font.cpp` must
consume the file fontgen writes.

**The firmware was fixed.**  `firmware/src/font.cpp` is now (298-305):

    298    const int x0 = x + (int)g->left * scale;
    299    /* `top` is measured from the TOP of the glyph cell, NOT from the baseline.
    ...
    305    const int y0 = baseline_y - ((int)s_ascent - (int)g->top) * scale;

`firmware/include/font.h` was also updated to clarify the description of the
`top` field and that the bitmap is a continuous stream.

Why it mattered: the error was NOT a constant shift, it varied per glyph; i.e.
the text would be drawn not just slightly downward but vertically scattered.
The table measured for Arial at 16 px (height=19, ascent=15):

    glyph  top   old formula     correct         error
    '.'    14    baseline-14     baseline-1      -13 px  (flies upward)
    'A'     3    baseline-3      baseline-12      +9 px  (drops below the baseline)
    'a'     6    baseline-6      baseline-9       +3 px

This table sits pinned verbatim inside
`test_top_origin_matches_firmware_renderer`; the same test also shows that the
old formula does NOT produce these values, preventing the test from passing
vacuously.

This test file CHANGES nothing under firmware/; it only reads.
"""

from __future__ import annotations

import random
import re
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = TESTS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent

for candidate in (str(TOOLS_DIR), str(TESTS_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    import fontgen
except SystemExit:  # pragma: no cover - Pillow yok
    fontgen = None  # type: ignore[assignment]

FONT_CPP = REPO_ROOT / "firmware" / "src" / "font.cpp"
FONT_H = REPO_ROOT / "firmware" / "include" / "font.h"

# If a real TTF is found we also try the CLI path (optional).
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Verdana.ttf",
]


# ---------------------------------------------------------------------------
#  read font.cpp and derive the unpacking rule FROM THE SOURCE
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FirmwareConvention:
    """The unpacking rule read from font.cpp (not a guess, but from the source)."""

    byte_shift: int          # s_bitmap[bit >> N]
    mask_base: int           # (0xNN >> (bit & N))
    mask_bits: int
    size_add: int            # ((w * h + N) / M)
    size_div: int
    bit_index: str           # "row * width + col"
    lines: dict[str, int]    # source line numbers (to show in the report)

    def unpack(self, data: bytes, width: int, height: int) -> list[list[bool]]:
        """Unfold the bitmap into a row matrix with font.cpp's rule."""
        rows: list[list[bool]] = []
        for row in range(height):
            line: list[bool] = []
            for col in range(width):
                bit = row * width + col                      # font.cpp:303
                byte = data[bit >> self.byte_shift]           # font.cpp:304
                line.append(bool(byte & (self.mask_base >> (bit & self.mask_bits))))
            rows.append(line)
        return rows

    def bitmap_size(self, width: int, height: int) -> int:
        """The size formula of font.cpp:293-294."""
        return (width * height + self.size_add) // self.size_div


def row_padded_unpack(data: bytes, width: int, height: int) -> list[list[bool]]:
    """Counter-example: the row-padded (wrong) interpretation.  It exists so the test is not vacuous.

    A row-padded reader expects `ceil(width/8) * height` bytes; since the buffer
    we have is `ceil(width*height/8)` bytes, we treat the overflow part as zero (a
    real reader would interpret the buffer that way too).
    """
    stride = (width + 7) // 8
    rows: list[list[bool]] = []
    for row in range(height):
        line: list[bool] = []
        for col in range(width):
            index = row * stride + (col >> 3)
            byte = data[index] if index < len(data) else 0
            line.append(bool(byte & (0x80 >> (col & 7))))
        rows.append(line)
    return rows


def row_padded_size(width: int, height: int) -> int:
    """The number of bytes the row-padded layout requires."""
    return ((width + 7) // 8) * height


def _line_of(src: str, pattern: str, what: str) -> tuple[re.Match[str], int]:
    match = re.search(pattern, src)
    if not match:
        raise AssertionError(
            f"could not read {what} from font.cpp (pattern: {pattern!r}).\n"
            "firmware/src/font.cpp may have changed; update this test's patterns "
            "and confirm that both sides still use the same rule."
        )
    line_no = src.count("\n", 0, match.start()) + 1
    return match, line_no


def read_firmware_convention(path: Path = FONT_CPP) -> FirmwareConvention:
    """Parse font.cpp and return the glyph unpacking rule."""
    src = path.read_text(encoding="utf-8", errors="replace")

    m_bit, l_bit = _line_of(
        src,
        r"const uint32_t bit = \(uint32_t\)row \* g->width \+ \(uint32_t\)col;",
        "bit index (line 303)",
    )
    assert m_bit  # silence the unused warning

    m_byte, l_byte = _line_of(src, r"s_bitmap\[bit >> (\d+)\]", "byte index (line 304)")
    byte_shift = int(m_byte.group(1))

    m_mask, l_mask = _line_of(
        src,
        r"\(uint8_t\)\s*\((0[xX][0-9A-Fa-f]+|0[bB][01]+|\d+)\s*>>\s*\(bit & (\d+)\)\)",
        "bit mask (line 304)",
    )
    mask_base = int(m_mask.group(1), 0)
    mask_bits = int(m_mask.group(2))

    m_size, l_size = _line_of(
        src,
        r"\(\(uint32_t\)g->width \* \(uint32_t\)g->height \+ (\d+)u\) / (\d+)u",
        "bitmap size (lines 293-294)",
    )
    size_add = int(m_size.group(1))
    size_div = int(m_size.group(2))

    return FirmwareConvention(
        byte_shift=byte_shift,
        mask_base=mask_base,
        mask_bits=mask_bits,
        size_add=size_add,
        size_div=size_div,
        bit_index="row * width + col",
        lines={
            "bit_index": l_bit,
            "byte_index": l_byte,
            "mask": l_mask,
            "size": l_size,
        },
    )


def read_firmware_header_offsets(path: Path = FONT_CPP) -> dict[str, int]:
    """Derive which byte font.cpp reads each header/glyph field from."""
    src = path.read_text(encoding="utf-8", errors="replace")
    wanted = {
        "version": r"if \(hdr\[(\d+)\] != 1\)",
        "height": r"s_height\s*=\s*hdr\[(\d+)\]",
        "ascent": r"s_ascent\s*=\s*\(int8_t\)hdr\[(\d+)\]",
        "descent": r"s_descent\s*=\s*\(int8_t\)hdr\[(\d+)\]",
        "line_spacing": r"s_spacing\s*=\s*hdr\[(\d+)\]",
        "glyph_count_lo": r"s_count\s*=\s*\(uint16_t\)hdr\[(\d+)\]",
        "advance": r"gi\.advance\s*=\s*\(int8_t\)g\[(\d+)\]",
        "left": r"gi\.left\s*=\s*\(int8_t\)g\[(\d+)\]",
        "width": r"gi\.width\s*=\s*g\[(\d+)\]",
        "height_g": r"gi\.height\s*=\s*g\[(\d+)\]",
        "top": r"gi\.top\s*=\s*g\[(\d+)\]",
    }
    out: dict[str, int] = {}
    for key, pattern in wanted.items():
        match, _line = _line_of(src, pattern, f"{key} field")
        out[key] = int(match.group(1))
    # codepoint: g[0] | g[1]<<8 | g[2]<<16 | g[3]<<24  -> starts at 0, LE
    out["codepoint"] = 0
    return out


def strip_c_comments(src: str) -> str:
    """Strip C/C++ comments; PRESERVES THE LINE COUNT.

    So that the patterns do not shift when comment blocks are added/removed, the
    searched text is cleared of comments.  Block comments are replaced by the same
    number of line breaks, so that `_line_of` still reports the real line number.
    """

    def blank_block(match: "re.Match[str]") -> str:
        return "\n" * match.group(0).count("\n")

    src = re.sub(r"/\*.*?\*/", blank_block, src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    return src


@dataclass(frozen=True)
class TopOrigin:
    """How font.cpp interprets the `top` field."""

    expression: str        # the expression in font.cpp (source text)
    cell_relative: bool    # True: from the top of the box (the CORRECT rule)
    line: int

    def describe(self) -> str:
        return (
            f"font.cpp:{self.line} treats the `top` value as "
            + (
                "measured from the TOP of the glyph box (correct)"
                if self.cell_relative
                else "measured from the baseline (WRONG)"
            )
        )


def read_firmware_top_origin(path: Path = FONT_CPP) -> TopOrigin:
    """Extract the vertical placement expression inside `fontDrawGlyph` from font.cpp.

    The line we look for is (it works even if a comment block is in between):

        const int y0 = baseline_y - <EXPRESSION> * scale;

    In the correct version <EXPRESSION> = `((int)s_ascent - (int)g->top)`; in the
    old buggy version it is only `(int)g->top`.

    NOTE: the file has ANOTHER placement matching the same pattern — the fallback
    (framebuffer) glyph path `baseline_y - FB_H * scale`.  So the match whose
    expression contains `g->top` is chosen; if there is not exactly one, it fails
    loudly.
    """
    src = strip_c_comments(path.read_text(encoding="utf-8", errors="replace"))
    # The expression is captured INCLUDING the `* scale` FACTOR, so that the
    # evaluator directly gives "how many pixels above the baseline" and the
    # old/new formulas can be compared on the same scale.
    pattern = r"const int y0\s*=\s*baseline_y\s*-\s*(.+?)\s*;"
    matches = list(re.finditer(pattern, src))
    if not matches:
        raise AssertionError(
            f"the pattern {pattern!r} was not found in font.cpp.  The file may "
            "have changed; update this test's pattern."
        )
    glyph_matches = [m for m in matches if "g->top" in m.group(1)]
    if len(glyph_matches) != 1:
        found = [m.group(1).strip() for m in matches]
        raise AssertionError(
            "exactly one placement expression containing 'g->top' was expected "
            f"in font.cpp; {len(glyph_matches)} were found.  "
            f"All expressions matching the pattern: {found}"
        )
    match = glyph_matches[0]
    expression = match.group(1).strip()
    line = src.count("\n", 0, match.start()) + 1
    return TopOrigin(
        expression=expression,
        cell_relative=("s_ascent" in expression) and ("g->top" in expression),
        line=line,
    )


def eval_top_expression(expression: str, ascent: int, top: int, scale: int) -> int:
    """Evaluate the placement expression in font.cpp NUMERICALLY with the given values.

    The returned value is HOW MANY PIXELS ABOVE the baseline the ink's top edge is
    (`* scale` factor included; the expression is already captured with the factor
    by `read_firmware_top_origin`).

    Instead of pattern-matching on text it really evaluates the expression; thus
    the test does not merely search for a string, it exercises behaviour.  The
    expression is simplified down to arithmetic only and `eval` is called with a
    restricted namespace.
    """
    text = expression
    text = text.replace("(int)s_ascent", "__A").replace("s_ascent", "__A")
    text = text.replace("(int)g->top", "__T").replace("g->top", "__T")
    text = re.sub(r"\bscale\b", "__S", text)
    text = (
        text.replace("__A", str(ascent))
        .replace("__T", str(top))
        .replace("__S", str(scale))
    )
    if not re.fullmatch(r"[0-9+\-*/() .]+", text):
        raise AssertionError(
            f"unexpected placement expression in font.cpp: {expression!r} -> {text!r}"
        )
    return int(eval(text, {"__builtins__": {}}, {}))  # noqa: S307 - simplified arithmetic


# ---------------------------------------------------------------------------
#  Independent framing reader (does NOT trust fontgen.read_epf)
# ---------------------------------------------------------------------------


@dataclass
class RawGlyph:
    codepoint: int
    advance: int
    left: int
    width: int
    height: int
    top: int
    bits: bytes


@dataclass
class RawFont:
    height: int
    ascent: int
    descent: int
    line_spacing: int
    reserved: int
    glyphs: list[RawGlyph]


def parse_epf_independently(
    data: bytes, conv: FirmwareConvention, offs: dict[str, int]
) -> RawFont:
    """Split the .epf from its framing using the OFFSETS font.cpp reads.

    It deliberately does not use fontgen.read_epf(): the point is to see whether
    the written bytes are where the firmware looks for them.

    NOTE — there are two separate index spaces in font.cpp:
      * `hdr[i]` is the 12-byte file header; its indices are relative to the FILE.
      * `g[i]`   is the 10-byte glyph record; its indices are relative to the RECORD.
    Mixing the two silently leads to garbage parsing, so the offsets are checked
    separately below.
    """
    if data[:4] != b"EPF1":
        raise AssertionError(f"magic number is not 'EPF1': {data[:4]!r}")
    if data[offs["version"]] != 1:
        raise AssertionError("version is not 1")

    # hdr[...] indices must be relative to the file.
    for key in ("height", "ascent", "descent", "line_spacing", "glyph_count_lo"):
        if not 0 <= offs[key] < 12:
            raise AssertionError(f"hdr[{offs[key]}] is outside the 12-byte header ({key})")
    # g[...] indices must be relative to the 10-byte glyph record.
    for key in ("advance", "left", "width", "height_g", "top"):
        if not 0 <= offs[key] < 10:
            raise AssertionError(f"g[{offs[key]}] is outside the 10-byte glyph record ({key})")

    glyph_count = data[offs["glyph_count_lo"]] | (data[offs["glyph_count_lo"] + 1] << 8)

    def s8(value: int) -> int:
        return value - 256 if value > 127 else value

    pos = 12  # EPF_HEADER_LEN (font.cpp:16)
    glyphs: list[RawGlyph] = []
    for _ in range(glyph_count):
        if pos + 10 > len(data):  # EPF_GLYPH_LEN (font.cpp:17)
            raise AssertionError("file ended while reading the glyph header")
        g = data[pos : pos + 10]
        codepoint = g[0] | (g[1] << 8) | (g[2] << 16) | (g[3] << 24)  # font.cpp:211-212
        advance = s8(g[offs["advance"]])                              # font.cpp:213
        left = s8(g[offs["left"]])                                    # font.cpp:214
        width = g[offs["width"]]                                      # font.cpp:215
        height = g[offs["height_g"]]                                  # font.cpp:216
        top = g[offs["top"]]                                          # font.cpp:217
        pos += 10
        nbytes = conv.bitmap_size(width, height)                      # font.cpp:220-221
        if pos + nbytes > len(data):
            raise AssertionError(f"the U+{codepoint:04X} bitmap runs past the end of the file")
        bits = data[pos : pos + nbytes]
        pos += nbytes
        glyphs.append(RawGlyph(codepoint, advance, left, width, height, top, bits))

    if pos != len(data):
        raise AssertionError(f"{len(data) - pos} leftover bytes remain in the file")

    return RawFont(
        height=data[offs["height"]],
        ascent=s8(data[offs["ascent"]]),
        descent=s8(data[offs["descent"]]),
        line_spacing=data[offs["line_spacing"]],
        reserved=data[9],
        glyphs=glyphs,
    )


# ---------------------------------------------------------------------------
#  Adversarial font generation
# ---------------------------------------------------------------------------

# Widths that deliberately exceed the 8 px boundary: the continuous stream and
# the row-padded interpretation DIVERGE at these widths.
ADVERSARIAL_GLYPHS = [
    # (codepoint, width, height)
    (ord("A"), 9, 5),
    (ord("B"), 12, 5),
    (ord("C"), 13, 11),
    (ord("D"), 17, 9),
]


def make_adversarial_rows(width: int, height: int, seed: int) -> list[list[bool]]:
    """A pattern that is NOT contiguous/uniform: a wrong interpretation shows up at once."""
    rng = random.Random(seed)
    rows: list[list[bool]] = []
    for y in range(height):
        rows.append([rng.random() < 0.5 for _ in range(width)])
    # Add a frame + diagonal so the pattern is structured.
    for x in range(width):
        rows[0][x] = True
        rows[height - 1][x] = True
    for y in range(height):
        rows[y][0] = True
        if y < width:
            rows[y][y % width] = True
    return rows


def build_adversarial_fontdata() -> tuple["fontgen.FontData", list[tuple[int, list[list[bool]]]]]:
    """Return a FontData with adversarial glyphs and their expected patterns."""
    assert fontgen is not None
    glyphs: list["fontgen.Glyph"] = []
    expected: list[tuple[int, list[list[bool]]]] = []
    for index, (cp, width, height) in enumerate(ADVERSARIAL_GLYPHS):
        rows = make_adversarial_rows(width, height, seed=1000 + index)
        bits = fontgen.pack_bits(rows)
        glyphs.append(
            fontgen.Glyph(
                codepoint=cp,
                advance=width + 1,
                left=0,
                width=width,
                height=height,
                top=4,
                bits=bits,
            )
        )
        expected.append((cp, rows))
    font = fontgen.FontData(
        height=19, ascent=15, descent=4, line_spacing=2, glyphs=glyphs
    )
    return font, expected


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


@unittest.skipIf(fontgen is None, "Pillow is not installed; fontgen could not be imported.")
@unittest.skipUnless(FONT_CPP.exists(), f"{FONT_CPP} is missing; the interop test was skipped.")
class TestEpfInterop(unittest.TestCase):
    """fontgen.py <-> firmware/src/font.cpp format compatibility."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.conv = read_firmware_convention()
        cls.offs = read_firmware_header_offsets()

    # -- FINDING 1: packing (compatible) -------------------------------------

    def test_firmware_uses_continuous_bitstream_not_row_padded(self) -> None:
        """font.cpp's rule must be a continuous stream (not row padding)."""
        conv = self.conv
        self.assertEqual(
            conv.byte_shift,
            3,
            f"font.cpp:{conv.lines['byte_index']} byte index is not 'bit >> 3'; "
            "this may be a row-padded layout",
        )
        self.assertEqual(
            (conv.mask_base, conv.mask_bits),
            (0x80, 7),
            f"font.cpp:{conv.lines['mask']} mask is not '0x80 >> (bit & 7)'; "
            "an MSB-first bit stream was expected",
        )
        self.assertEqual(
            (conv.size_add, conv.size_div),
            (7, 8),
            f"font.cpp:{conv.lines['size']} size formula is not ceil(w*h/8); "
            "with row padding it would be ((w+7)/8)*h",
        )
        # The row-padded interpretation CONTRADICTS this formula: the proof.
        w, h = 9, 5
        self.assertEqual(conv.bitmap_size(w, h), (w * h + 7) // 8)
        self.assertNotEqual(conv.bitmap_size(w, h), ((w + 7) // 8) * h)

    def test_fontgen_packs_the_same_way_as_firmware_unpacks(self) -> None:
        """Adversarial glyphs: when the bytes fontgen writes are opened with the
        firmware rule, the pattern fontgen intended must come out."""
        font, expected = build_adversarial_fontdata()
        raw = fontgen.build_epf(font)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adversarial.epf"
            path.write_bytes(raw)
            self.assertEqual(path.read_bytes(), raw)

        parsed = parse_epf_independently(raw, self.conv, self.offs)

        # Are the framing fields where the firmware reads them?
        self.assertEqual(parsed.height, font.height)
        self.assertEqual(parsed.ascent, font.ascent)
        self.assertEqual(parsed.descent, font.descent)
        self.assertEqual(parsed.line_spacing, font.line_spacing)
        self.assertEqual(len(parsed.glyphs), len(expected))

        by_cp = {g.codepoint: g for g in parsed.glyphs}
        for codepoint, rows in expected:
            with self.subTest(codepoint=chr(codepoint)):
                glyph = by_cp[codepoint]
                self.assertEqual(glyph.width, len(rows[0]))
                self.assertEqual(glyph.height, len(rows))
                self.assertEqual(
                    len(glyph.bits),
                    (glyph.width * glyph.height + 7) // 8,
                    "the bitmap must be ceil(w*h/8) bytes",
                )
                # THE MAIN CLAIM: the firmware's rule yields the pattern fontgen intended.
                self.assertEqual(
                    self.conv.unpack(glyph.bits, glyph.width, glyph.height),
                    rows,
                    f"{chr(codepoint)}: the bitmap opened with the firmware rule "
                    f"differs from the pattern fontgen intended",
                )

    def test_adversarial_glyphs_actually_discriminate(self) -> None:
        """Prove that the test is NOT vacuous: the two interpretations must diverge at these widths.

        Otherwise the test would also let through a reader that misreads the rule.
        """
        font, expected = build_adversarial_fontdata()
        raw = fontgen.build_epf(font)
        parsed = parse_epf_independently(raw, self.conv, self.offs)
        by_cp = {g.codepoint: g for g in parsed.glyphs}

        for codepoint, rows in expected:
            with self.subTest(codepoint=chr(codepoint)):
                bits = by_cp[codepoint].bits
                width, height = by_cp[codepoint].width, by_cp[codepoint].height
                stream = self.conv.unpack(bits, width, height)
                padded = row_padded_unpack(bits, width, height)
                self.assertEqual(stream, rows)
                # Framing difference: the two layouts require different byte counts.
                self.assertNotEqual(
                    len(bits),
                    row_padded_size(width, height),
                    f"{chr(codepoint)} ({width}x{height}): the continuous stream and "
                    "the row-padded layout require the same byte count; this width "
                    "is not discriminating",
                )
                self.assertNotEqual(
                    padded,
                    rows,
                    f"{chr(codepoint)} ({width}x{height}): the row-padded interpretation "
                    "gives the same result — this glyph is not discriminating and makes "
                    "the test vacuous. Change the width/height choice.",
                )

    def test_bitmap_size_formula_matches_fontgen(self) -> None:
        """For every adversarial glyph the two sides' size formula must be the same."""
        for cp, width, height in ADVERSARIAL_GLYPHS:
            with self.subTest(codepoint=chr(cp)):
                self.assertEqual(
                    self.conv.bitmap_size(width, height),
                    (width * height + 7) // 8,
                )

    def test_fontgen_reader_agrees_three_ways(self) -> None:
        """fontgen.read_epf(), the firmware rule and fontgen's intent must all three agree."""
        font, expected = build_adversarial_fontdata()
        raw = fontgen.build_epf(font)
        again = fontgen.read_epf(raw)
        self.assertEqual(len(again.glyphs), len(expected))
        by_cp = {g.codepoint: g for g in again.glyphs}
        for codepoint, rows in expected:
            glyph = by_cp[codepoint]
            self.assertEqual(glyph.rows(), rows)
            self.assertEqual(self.conv.unpack(glyph.bits, glyph.width, glyph.height), rows)

    def test_full_cli_output_is_firmware_readable(self) -> None:
        """The real fontgen CLI path (if a TTF exists) must produce a file the
        firmware can read; every glyph wider than 8 px is a discriminating test."""
        ttf = next((Path(p) for p in FONT_CANDIDATES if Path(p).exists()), None)
        if ttf is None:
            self.skipTest("No known TTF was found on the system.")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reader-16.epf"
            # The CLI prints a summary; keep it from polluting the test output.
            import contextlib
            import io

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                rc = fontgen.main(
                    [
                        str(ttf),
                        "--size",
                        "16",
                        "--out",
                        str(out),
                        "--ranges",
                        "ascii,turkish",
                        "--no-json",
                    ]
                )
            self.assertEqual(rc, 0, "fontgen CLI failed")
            raw = out.read_bytes()
            parsed = parse_epf_independently(raw, self.conv, self.offs)
            self.assertGreater(len(parsed.glyphs), 50)

            wide = [g for g in parsed.glyphs if g.width > 8]
            self.assertTrue(wide, "no glyph wider than 8 px; the interop test is weak")

            # fontgen's own reader and the firmware rule must yield the same pattern.
            again = {g.codepoint: g for g in fontgen.read_epf(raw).glyphs}
            for glyph in wide:
                with self.subTest(codepoint=chr(glyph.codepoint)):
                    self.assertEqual(
                        self.conv.unpack(glyph.bits, glyph.width, glyph.height),
                        again[glyph.codepoint].rows(),
                    )

    # -- FINDING 2: where the `top` field is measured from (INCOMPATIBLE) --------

    def test_firmware_reader_finds_the_glyph_offsets_it_documents(self) -> None:
        """The header/glyph field offsets must be the same on both sides (this part is compatible)."""
        offs = self.offs
        self.assertEqual(offs["version"], 4)
        self.assertEqual(offs["height"], 5)
        self.assertEqual(offs["ascent"], 6)
        self.assertEqual(offs["descent"], 7)
        self.assertEqual(offs["line_spacing"], 8)
        self.assertEqual(offs["glyph_count_lo"], 10)
        # glyph header is 10 bytes: cp(4) advance(1) left(1) width(1) height(1) top(1) res(1)
        self.assertEqual(offs["advance"], 4)
        self.assertEqual(offs["left"], 5)
        self.assertEqual(offs["width"], 6)
        self.assertEqual(offs["height_g"], 7)
        self.assertEqual(offs["top"], 8)

    def test_top_origin_matches_firmware_renderer(self) -> None:
        """font.cpp must measure the `top` value from the top of the glyph box.

        Rule: `top` is measured from the top of the glyph box (the
        `height`-pixel cell); the baseline sits `ascent` pixels below the cell
        top.  Therefore the ink's top edge is `(ascent - top)` pixels ABOVE the
        baseline:

            y0 = baseline_y - (s_ascent - g->top) * scale

        Why it is pinned: this was the only assumption that silently diverged
        between the two halves of the format.  The error is NOT a constant shift
        — it varies per glyph, so the text is drawn vertically scattered and
        glyphs spill into neighbouring lines.

        The table measured for Arial at 16 px (height=19, ascent=15); the `CASES`
        below are exactly these values:

            glyph  top   old formula     correct         error
            '.'    14    baseline-14     baseline-1      -13 px  (flies upward)
            'A'     3    baseline-3      baseline-12      +9 px  (drops below the baseline)
            'a'     6    baseline-6      baseline-9       +3 px
        """
        origin = read_firmware_top_origin()

        # 1) The expression must interpret `top` relative to the box (not the baseline).
        self.assertTrue(
            origin.cell_relative,
            f"{origin.describe()} — expected expression: "
            "`baseline_y - ((int)s_ascent - (int)g->top) * scale`",
        )

        baseline_y = 100
        ascent = 15  # Arial 16 px measurement
        # (codepoint, top, expected top edge relative to the baseline)
        cases = [
            (ord("."), 14, -1),   # period: just above the baseline
            (ord("A"), 3, -12),   # capital letter: high up
            (ord("a"), 6, -9),    # lowercase letter: x-height
        ]

        errors: list[int] = []
        for codepoint, top, expected_offset in cases:
            with self.subTest(codepoint=chr(codepoint)):
                y0 = baseline_y - eval_top_expression(
                    origin.expression, ascent, top, 1
                )
                self.assertEqual(
                    y0,
                    baseline_y + expected_offset,
                    f"{chr(codepoint)} (top={top}): font.cpp y0={y0}, "
                    f"should be {baseline_y + expected_offset}",
                )
                # Scaling must also be applied correctly: scale=2 -> twice the offset.
                y0_scaled = baseline_y - eval_top_expression(
                    origin.expression, ascent, top, 2
                )
                self.assertEqual(y0_scaled, baseline_y + 2 * expected_offset)
                errors.append(y0 - (baseline_y + expected_offset))

        # 2) The error varies per glyph — i.e. this is not "a constant shift".
        self.assertEqual(set(errors), {0})

        # 3) COUNTER-EXAMPLE: the old (buggy) formula must NOT give these values;
        #    otherwise this test would also let through a reader that misreads the rule.
        legacy_expression = "(int)g->top * scale"
        self.assertNotIn(
            "s_ascent",
            legacy_expression,
            "the counter-example must really be the old formula",
        )
        for codepoint, top, expected_offset in cases:
            with self.subTest(codepoint=chr(codepoint), formula="legacy"):
                legacy_y0 = baseline_y - eval_top_expression(
                    legacy_expression, ascent, top, 1
                )
                self.assertNotEqual(
                    legacy_y0,
                    baseline_y + expected_offset,
                    f"{chr(codepoint)}: the old formula also gives the correct result — "
                    "the test is not discriminating",
                )

        # The old formula's errors must also vary per glyph (the proof of the scatter).
        # Sign convention: error = old_y0 - correct_y0.  Negative = the old formula
        # draws the glyph HIGHER than it should, positive = LOWER.
        legacy_errors = [
            (baseline_y - eval_top_expression(legacy_expression, ascent, top, 1))
            - (baseline_y + expected_offset)
            for _cp, top, expected_offset in cases
        ]
        self.assertEqual(
            legacy_errors,
            [-13, 9, 3],
            "the old formula's per-glyph errors must match the table in the report",
        )
        self.assertGreater(len(set(legacy_errors)), 1)

    def test_top_parser_is_robust_to_comment_blocks(self) -> None:
        """The parser must find the correct expression even if a comment block is in between.

        While the firmware side was being fixed a comment block was added above
        the line; since the parser strips comments, this must not break the pattern.
        """
        snippet = (
            "void fontDrawGlyph(Canvas& canvas, uint32_t cp, int x, int baseline_y,\n"
            "                   int scale, uint8_t ink) {\n"
            "    const int x0 = x + (int)g->left * scale;\n"
            "    /* `top` is measured from the TOP of the glyph cell, NOT from the\n"
            "     * baseline.  The baseline sits s_ascent pixels below the cell top,\n"
            "     * so the ink's top edge is (s_ascent - top) pixels ABOVE it. */\n"
            "    const int y0 = baseline_y - ((int)s_ascent - (int)g->top) * scale;\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake_font.cpp"
            path.write_text(snippet, encoding="utf-8")
            origin = read_firmware_top_origin(path)

        self.assertTrue(origin.cell_relative, origin.describe())
        self.assertIn("s_ascent", origin.expression)
        self.assertIn("g->top", origin.expression)
        # The line number must not shift when the comment block is removed.
        self.assertEqual(origin.line, 7)
        # The evaluator must derive the correct result from this expression.
        self.assertEqual(eval_top_expression(origin.expression, 15, 14, 1), 1)
        self.assertEqual(eval_top_expression(origin.expression, 15, 3, 2), 24)

    def test_top_parser_rejects_the_old_baseline_relative_form(self) -> None:
        """The parser must NOT accept the old (buggy) formula as correct.

        This proves the regression protection above is not vacuous: if the
        formula is reverted to its old form the test turns red.
        """
        snippet = (
            "void fontDrawGlyph(Canvas& canvas, uint32_t cp, int x, int baseline_y,\n"
            "                   int scale, uint8_t ink) {\n"
            "    const int x0 = x + (int)g->left * scale;\n"
            "    const int y0 = baseline_y - (int)g->top * scale;\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old_font.cpp"
            path.write_text(snippet, encoding="utf-8")
            origin = read_firmware_top_origin(path)

        self.assertFalse(
            origin.cell_relative,
            "the old formula must not count as 'relative to the box'",
        )
        # The old formula must give the per-glyph errors from the report.
        ascent, baseline_y = 15, 100
        cases = [(ord("."), 14, -1), (ord("A"), 3, -12), (ord("a"), 6, -9)]
        legacy_errors = [
            (baseline_y - eval_top_expression(origin.expression, ascent, top, 1))
            - (baseline_y + expected_offset)
            for _cp, top, expected_offset in cases
        ]
        self.assertEqual(legacy_errors, [-13, 9, 3])
        self.assertGreater(len(set(legacy_errors)), 1)

    def test_top_parser_fails_loudly_when_shape_changes(self) -> None:
        """If the pattern disappears it must not give a wrong result silently, it must RAISE."""
        snippet = "void f() {\n    int y = somewhere_else(cp);\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken_font.cpp"
            path.write_text(snippet, encoding="utf-8")
            with self.assertRaises(AssertionError) as ctx:
                read_firmware_top_origin(path)
        self.assertIn("not found", str(ctx.exception))

    def test_top_is_cell_relative_in_a_real_font(self) -> None:
        """Independently verifies that `top` is box-relative in a real font.

        Discriminating observation: `top` is the TOPMOST pixel of the ink and is
        measured from the top of the cell; the baseline is `ascent` pixels below
        the cell top.  The ink of a glyph with a descender ('p', 'g') crosses the
        baseline downward, i.e. `top + height > ascent`.  For a glyph without a
        descender ('A', 'l'), `top + height <= ascent` remains.

        If `top` were measured relative to the baseline a negative value would be
        needed for descender glyphs; since `top` is uint8 that is impossible — so
        this distinction really separates the two rules.
        """
        ttf = next((Path(p) for p in FONT_CANDIDATES if Path(p).exists()), None)
        if ttf is None:
            self.skipTest("No known TTF was found on the system.")

        font = fontgen.rasterise(ttf, 16, [ord(c) for c in "Alpg"], line_spacing=2)
        by_cp = {g.codepoint: g for g in font.glyphs}

        ascenders = [c for c in "Al" if ord(c) in by_cp]
        descenders = [c for c in "pg" if ord(c) in by_cp]
        self.assertTrue(ascenders and descenders, "test glyphs not found")

        for ch in ascenders:
            glyph = by_cp[ord(ch)]
            with self.subTest(char=ch, kind="ascender"):
                self.assertLessEqual(
                    glyph.top + glyph.height,
                    font.ascent,
                    f"'{ch}': top+height={glyph.top + glyph.height} <= "
                    f"ascent={font.ascent} must hold; this glyph does not cross the baseline",
                )
        for ch in descenders:
            glyph = by_cp[ord(ch)]
            with self.subTest(char=ch, kind="descender"):
                self.assertGreater(
                    glyph.top + glyph.height,
                    font.ascent,
                    f"'{ch}': top+height={glyph.top + glyph.height} > "
                    f"ascent={font.ascent} must hold; the ink drops below the baseline",
                )

        # General invariant: `top` must be inside the cell and must not overflow.
        for glyph in font.glyphs:
            with self.subTest(codepoint=chr(glyph.codepoint), kind="bounds"):
                self.assertGreaterEqual(glyph.top, 0)
                self.assertLessEqual(glyph.top + glyph.height, font.height)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
#  NOTE (end of file): summary of the interop status
# ---------------------------------------------------------------------------
#  COMPATIBLE (pinned by tests):
#    * glyph bitmap packing - a continuous MSB-first stream, NO row padding;
#      size ceil(w*h/8).  font.cpp:307-313 and fontgen.pack_bits use the same rule.
#    * bitmap size formula ((w * h + 7) / 8)
#    * header and glyph header field offsets (hdr[4..11], g[0..9])
#    * version and magic number; packed, unpadded layout
#    * where the `top` field is measured from - the top of the glyph box, i.e.
#      the layout `y0 = baseline_y - (s_ascent - g->top) * scale`.  This was the
#      only assumption on which the two halves silently diverged; the firmware
#      was fixed and it is here under regression protection.
#  INCOMPATIBLE: no known incompatibility remains.
#  This file changes nothing under firmware/; it only reads.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
