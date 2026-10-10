#!/usr/bin/env python3
"""TTF/OTF -> .epf converter (Pocket Reader bitmap font generator).

The device runs no font engine when drawing text on screen; every glyph is
rasterised in advance and embedded into the `.epf` file.  This script uses
Pillow to rasterise a TrueType/OpenType font at the requested pixel size and
writes the tightly packed `.epf` container that the device reads.

    python3 fontgen.py DejaVuSans.ttf --size 14 \\
        --out firmware/data/fonts/reader-14.epf --preview onizleme.png

Setup:  ``python3 -m venv .venv && .venv/bin/pip install -r requirements.txt``
(Pillow is required; none of the other tools need any extra packages.)

Format notes (English, low level)
----------------------------------------
All integers little-endian, structures packed with no padding.

    header (12 bytes):
        char   magic[4] = "EPF1"
        uint8  version  = 1
        uint8  height            // line box height in pixels
        int8   ascent
        int8   descent
        uint8  line_spacing      // extra leading added between lines
        uint8  reserved          // 0
        uint16 glyph_count

    then glyph_count entries, each:
        uint32 codepoint
        int8   advance           // pen movement in pixels
        int8   left              // x offset of the bitmap inside the box
        uint8  width
        uint8  height
        uint8  top               // y offset of the bitmap inside the box
        uint8  reserved          // 0
        ceil(width*height/8) bytes, row-major, MSB-first, bit set = ink

Judgement calls where the spec was ambiguous
--------------------------------------------
* **The bitmap is a continuous MSB-first BIT STREAM, not row padded.**  The
  spec fixes the size at ``ceil(width*height/8)`` bytes, which is only equal to
  a padded layout when ``width`` is a multiple of 8 (for w=9, h=3 that is 4
  bytes, while two padded rows would need 6).  So bit N of the glyph occupies
  byte ``N >> 3``, mask ``0x80 >> (N & 7)``, with ``N = y*width + x``.
  A row-padded reader would mis-render every glyph wider than 8 px.
* **`descent` is stored POSITIVE**, matching ``ImageFont.getmetrics()`` and
  ``height == ascent + descent``.  If the firmware expects the FreeType
  convention (negative descent) it must negate the field; the sidecar JSON
  records ``"descent_sign": "positive"`` so this is easy to spot.
* ``top`` is the offset from the TOP OF THE LINE BOX (the ascender line, which
  is what Pillow's ``anchor="la"`` uses as its origin), *not* from the baseline.
  Baseline-relative readers should use ``ascent - top`` differently: the ink
  occupies rows ``top .. top+height`` of the line box.
* The nominal box comes from ``ImageDraw.textbbox``; it is then tightened to
  the actual rendered ink (and clamped into the line box) so no glyph wastes
  blank rows/columns in the packed stream.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - setup error
    sys.stderr.write(
        "ERROR: Pillow not found. To install it:\n"
        "    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
        f"(detail: {exc})\n"
    )
    raise SystemExit(4)

__all__ = [
    "MAGIC",
    "VERSION",
    "Glyph",
    "FontData",
    "EpfError",
    "build_epf",
    "read_epf",
    "glyphs_to_rows",
    "pack_bits",
    "unpack_bits",
    "main",
]

MAGIC = b"EPF1"
VERSION = 1
HEADER_SIZE = 12
GLYPH_HEADER_SIZE = 10

MAX_U8 = 0xFF
MAX_I8 = 127
MIN_I8 = -128
MAX_U16 = 0xFFFF


class EpfError(Exception):
    """Error during `.epf` production/parsing."""


# --- codepoint ranges -------------------------------------------------------

# Named ranges.  `--ranges` takes them comma-separated.
RANGES: dict[str, list[tuple[int, int]]] = {
    "ascii": [(0x0020, 0x007E)],
    "latin1": [(0x00A0, 0x00FF)],
    "latin-ext": [(0x0100, 0x017F)],
    # Letters specific to Turkish (also inside latin-ext; can be used on its own).
    "turkish": [(0x011E, 0x011F), (0x0130, 0x0131), (0x015E, 0x015F)],
    "punct": [
        (0x00A1, 0x00A1),
        (0x00A9, 0x00A9),
        (0x00AB, 0x00AB),
        (0x00AD, 0x00AD),  # soft hyphen
        (0x00AE, 0x00AE),
        (0x00B0, 0x00B0),
        (0x00B7, 0x00B7),
        (0x00BB, 0x00BB),
        (0x00BF, 0x00BF),
        (0x2010, 0x2015),  # hyphen variants
        (0x2018, 0x201F),  # single/double smart quotes
        (0x2020, 0x2022),  # dagger, double dagger, bullet
        (0x2026, 0x2026),  # …
        (0x2032, 0x2033),
        (0x2039, 0x203A),
        (0x2044, 0x2044),
        (0x2116, 0x2116),
        (0x2122, 0x2122),
        (0x2212, 0x2212),
    ],
    "digits": [(0x0030, 0x0039)],
    # Non-ASCII auxiliary ranges
    "currency": [(0x00A2, 0x00A5), (0x20A8, 0x20A8), (0x20AC, 0x20AC), (0x20BA, 0x20BA)],
    "greek": [(0x0384, 0x03CE)],
    "cyrillic": [(0x0400, 0x045F)],
}

DEFAULT_RANGES = ["ascii", "latin1", "latin-ext", "turkish", "punct"]


def expand_ranges(names: Sequence[str]) -> list[int]:
    """Expand range names into a sorted, de-duplicated list of code points."""
    if not names:
        names = DEFAULT_RANGES
    codepoints: set[int] = set()
    for name in names:
        key = name.strip().lower().replace("_", "-")
        if not key:
            continue
        if key == "all":
            for spans in RANGES.values():
                for lo, hi in spans:
                    codepoints.update(range(lo, hi + 1))
            continue
        spans = RANGES.get(key)
        if spans is None:
            raise EpfError(
                f"Unknown range: '{name}'. Valid names: "
                + ", ".join(sorted(RANGES))
                + ", all"
            )
        for lo, hi in spans:
            codepoints.update(range(lo, hi + 1))
    return sorted(cp for cp in codepoints if cp > 0 and cp <= 0x10FFFF and not (0xD800 <= cp <= 0xDFFF))


# --- bit packing ------------------------------------------------------------


def pack_bits(rows: Sequence[Sequence[bool]]) -> bytes:
    """Pack a row matrix into an MSB-first, row-unpadded bit stream.

    Bit N (N = y*width + x) -> byte ``N >> 3``, mask ``0x80 >> (N & 7)``.
    The length is exactly ``ceil(width*height/8)``.
    """
    if not rows:
        return b""
    width = len(rows[0])
    height = len(rows)
    out = bytearray((width * height + 7) // 8)
    idx = 0
    for row in rows:
        for ink in row:
            if ink:
                out[idx >> 3] |= 0x80 >> (idx & 7)
            idx += 1
    return bytes(out)


def unpack_bits(data: bytes, width: int, height: int) -> list[list[bool]]:
    """The inverse of `pack_bits`: unfolds the bit stream into a row matrix."""
    rows: list[list[bool]] = []
    idx = 0
    for _y in range(height):
        row: list[bool] = []
        for _x in range(width):
            byte = data[idx >> 3] if (idx >> 3) < len(data) else 0
            row.append(bool(byte & (0x80 >> (idx & 7))))
            idx += 1
        rows.append(row)
    return rows


def _bitmap_to_rows(bitmap: "Image.Image", threshold: int = 128) -> list[list[bool]]:
    """Threshold a Pillow `L` image and turn it into a boolean row matrix."""
    width, height = bitmap.size
    pixels = bitmap.load()
    rows: list[list[bool]] = []
    for y in range(height):
        rows.append([pixels[x, y] >= threshold for x in range(width)])
    return rows


# --- data model -------------------------------------------------------------


@dataclass
class Glyph:
    codepoint: int
    advance: int
    left: int
    width: int
    height: int
    top: int
    bits: bytes = b""

    def rows(self) -> list[list[bool]]:
        return unpack_bits(self.bits, self.width, self.height)


@dataclass
class FontData:
    height: int
    ascent: int
    descent: int
    line_spacing: int
    glyphs: list[Glyph] = field(default_factory=list)
    reserved: int = 0
    version: int = VERSION
    source: str = ""

    def by_codepoint(self) -> dict[int, Glyph]:
        return {g.codepoint: g for g in self.glyphs}

    def size_bytes(self) -> int:
        return HEADER_SIZE + sum(
            GLYPH_HEADER_SIZE + len(g.bits) for g in self.glyphs
        )


# --- writing / reading ------------------------------------------------------


def build_epf(font: FontData) -> bytes:
    """Turn `FontData` into an `.epf` byte string (with strict bounds checking)."""
    if not (0 <= font.height <= MAX_U8):
        raise EpfError(f"height is not in the uint8 range: {font.height} (0..255).")
    if not (MIN_I8 <= font.ascent <= MAX_I8):
        raise EpfError(
            f"ascent is not in the int8 range: {font.ascent} ({MIN_I8}..{MAX_I8}). "
            f"Use a smaller --size."
        )
    if not (MIN_I8 <= font.descent <= MAX_I8):
        raise EpfError(
            f"descent is not in the int8 range: {font.descent} ({MIN_I8}..{MAX_I8})."
        )
    if not (0 <= font.line_spacing <= MAX_U8):
        raise EpfError(f"line_spacing is not in the uint8 range: {font.line_spacing}.")
    if len(font.glyphs) > MAX_U16:
        raise EpfError(
            f"Too many glyphs: {len(font.glyphs)} (at most {MAX_U16}). "
            f"Narrow the coverage with --ranges."
        )

    out = bytearray()
    # header: magic(4) version(1) height(1) ascent(1) descent(1) spacing(1) reserved(1) count(2)
    out += struct.pack(
        "<4sBBbbBBH",
        MAGIC,
        font.version,
        font.height,
        font.ascent,
        font.descent,
        font.line_spacing,
        font.reserved,
        len(font.glyphs),
    )
    for g in font.glyphs:
        if not (0 <= g.codepoint <= 0x10FFFF):
            raise EpfError(f"Invalid code point: U+{g.codepoint:04X}")
        if not (0 <= g.advance <= MAX_I8):
            raise EpfError(
                f"U+{g.codepoint:04X} advance is not in the int8 range: {g.advance}. "
                f"Use a smaller --size."
            )
        if not (MIN_I8 <= g.left <= MAX_I8):
            raise EpfError(f"U+{g.codepoint:04X} left is not in the int8 range: {g.left}.")
        for name, value in (("width", g.width), ("height", g.height), ("top", g.top)):
            if not (0 <= value <= MAX_U8):
                raise EpfError(
                    f"U+{g.codepoint:04X} {name} is not in the uint8 range: {value}."
                )
        need = (g.width * g.height + 7) // 8
        if g.width == 0 or g.height == 0:
            if g.bits:
                raise EpfError(f"U+{g.codepoint:04X} is an empty glyph but has bitmap data.")
        elif len(g.bits) != need:
            raise EpfError(
                f"U+{g.codepoint:04X} bitmap size is wrong: {len(g.bits)} != {need}."
            )
        out += struct.pack(
            "<IBbBBBB",
            g.codepoint,
            g.advance,
            g.left,
            g.width,
            g.height,
            g.top,
            0,
        )
        out += g.bits
    return bytes(out)


def read_epf(data: bytes) -> FontData:
    """Parse and validate an `.epf` byte string."""
    if len(data) < HEADER_SIZE:
        raise EpfError(f"File is too small: {len(data)} bytes (at least {HEADER_SIZE}).")
    magic, version, height, ascent, descent, line_spacing, reserved, count = struct.unpack(
        "<4sBBbbBBH", data[:HEADER_SIZE]
    )
    if magic != MAGIC:
        raise EpfError(f"Invalid magic number: {magic!r} (expected 'EPF1').")
    if version != VERSION:
        raise EpfError(f"Unsupported version: {version} (expected {VERSION}).")

    pos = HEADER_SIZE
    glyphs: list[Glyph] = []
    for i in range(count):
        if pos + GLYPH_HEADER_SIZE > len(data):
            raise EpfError(f"File ended while reading glyph header {i}.")
        cp, advance, left, width, gh, top, _res = struct.unpack(
            "<IBbBBBB", data[pos : pos + GLYPH_HEADER_SIZE]
        )
        pos += GLYPH_HEADER_SIZE
        need = (width * gh + 7) // 8
        if pos + need > len(data):
            raise EpfError(f"File ended while reading the U+{cp:04X} bitmap.")
        bits = bytes(data[pos : pos + need])
        pos += need
        glyphs.append(Glyph(cp, advance, left, width, gh, top, bits))

    if pos != len(data):
        raise EpfError(
            f"There are {len(data) - pos} leftover bytes in the file; the glyph count may be wrong."
        )

    return FontData(
        height=height,
        ascent=ascent,
        descent=descent,
        line_spacing=line_spacing,
        glyphs=glyphs,
        reserved=reserved,
        version=version,
    )


# --- rasterising ------------------------------------------------------------


def _tighten(
    font: "ImageFont.FreeTypeFont",
    ch: str,
    line_height: int,
    threshold: int = 128,
    margin: int = 2,
) -> tuple[int, int, int, int, list[list[bool]]] | None:
    """Rasterise a single character.

    Returns: ``(left, top, width, height, rows)`` -- the position relative to the
    line box and the thresholded row matrix.  Returns ``None`` for an empty glyph
    (e.g. a space).
    """
    probe = Image.new("L", (1, 1), 0)
    bbox = ImageDraw.Draw(probe).textbbox((0, 0), ch, font=font, anchor="la")
    bl, bt, br, bb = bbox
    if br <= bl or bb <= bt:
        return None

    w = br - bl
    h = bb - bt
    canvas = Image.new("L", (w + 2 * margin, h + 2 * margin), 0)
    # anchor="la": (0,0) = left/ascender line, i.e. the top-left corner of the line box.
    ImageDraw.Draw(canvas).text((margin - bl, margin - bt), ch, font=font, fill=255, anchor="la")

    ink = canvas.getbbox()
    if ink is None:
        return None
    il, it, ir, ib = ink

    left = il - margin + bl
    top = it - margin + bt
    width = ir - il
    height = ib - it
    rows = _bitmap_to_rows(canvas.crop(ink), threshold)

    # Trim rows that stick out of the line box (e.g. the tail of Q in some fonts).
    if top < 0:
        drop = min(-top, height)
        rows = rows[drop:]
        height -= drop
        top = 0
    if top + height > line_height:
        height = max(0, line_height - top)
        rows = rows[:height]
    if height <= 0 or width <= 0:
        return None
    if height != len(rows) or (rows and len(rows[0]) != width):
        raise EpfError(
            f"'{ch}' (U+{ord(ch):04X}) internal inconsistency while rasterising: "
            f"{len(rows)}x{len(rows[0]) if rows else 0} != {height}x{width}"
        )
    return left, top, width, height, rows


def rasterise(
    font_path: str | Path,
    size: int,
    codepoints: Sequence[int],
    line_spacing: int = 2,
    threshold: int = 128,
) -> FontData:
    """Rasterise the font at `size` pixels and produce `FontData`."""
    if size < 4:
        raise EpfError("--size must be at least 4.")
    try:
        font = ImageFont.truetype(str(font_path), size)
    except OSError as exc:
        raise EpfError(
            f"Could not open font: {font_path} ({exc}). "
            f"Make sure you are giving a correct .ttf/.otf path."
        ) from exc

    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    if line_height > MAX_U8:
        raise EpfError(
            f"Line height is {line_height} px; .epf supports at most 255 px. "
            f"Reduce the --size value."
        )
    if ascent > MAX_I8 or descent > MAX_I8:
        raise EpfError(
            f"ascent={ascent} / descent={descent} exceeds the int8 limit. "
            f"Reduce the --size value."
        )

    glyphs: list[Glyph] = []
    skipped: list[int] = []
    for cp in codepoints:
        ch = chr(cp)
        advance = int(round(font.getlength(ch)))
        if advance < 0:
            advance = 0
        if advance > MAX_I8:
            raise EpfError(
                f"U+{cp:04X} advance={advance} px exceeds the int8 limit. "
                f"Reduce the --size value."
            )
        tight = _tighten(font, ch, line_height, threshold)
        if tight is None:
            # Spaces and combining marks: record the advance only.
            if advance == 0:
                skipped.append(cp)
                continue
            glyphs.append(Glyph(cp, advance, 0, 0, 0, 0, b""))
            continue
        left, top, width, height, rows = tight
        bits = pack_bits(rows)
        if left < MIN_I8:
            left = MIN_I8
        glyphs.append(Glyph(cp, advance or width, left, width, height, top, bits))

    if not glyphs:
        raise EpfError("No glyphs could be produced; the given ranges may be empty.")

    glyphs.sort(key=lambda g: g.codepoint)
    data = FontData(
        height=line_height,
        ascent=ascent,
        descent=descent,
        line_spacing=line_spacing,
        glyphs=glyphs,
        source=str(font_path),
    )
    data.skipped = skipped  # type: ignore[attr-defined]  # for diagnostics
    return data


# --- self test --------------------------------------------------------------


def self_test(font: FontData, raw: bytes | None = None) -> tuple[bool, str]:
    """Verify the packing and, if given, the written file by reading it back."""
    for g in font.glyphs:
        if g.width == 0 or g.height == 0:
            if g.bits:
                return False, f"U+{g.codepoint:04X}: empty glyph but has data"
            continue
        expected_len = (g.width * g.height + 7) // 8
        if len(g.bits) != expected_len:
            return False, (
                f"U+{g.codepoint:04X}: size {len(g.bits)} != {expected_len}"
            )
        rows = unpack_bits(g.bits, g.width, g.height)
        if len(rows) != g.height or any(len(r) != g.width for r in rows):
            return False, f"U+{g.codepoint:04X}: unfolded matrix size is wrong"
        if pack_bits(rows) != g.bits:
            return False, f"U+{g.codepoint:04X}: pack/unpack roundtrip is inconsistent"

    if raw is not None:
        again = read_epf(raw)
        if len(again.glyphs) != len(font.glyphs):
            return False, f"glyph count {len(again.glyphs)} != {len(font.glyphs)}"
        if (again.height, again.ascent, again.descent, again.line_spacing) != (
            font.height,
            font.ascent,
            font.descent,
            font.line_spacing,
        ):
            return False, "header metrics differ when read back"
        for a, b in zip(font.glyphs, again.glyphs):
            if (a.codepoint, a.advance, a.left, a.width, a.height, a.top) != (
                b.codepoint,
                b.advance,
                b.left,
                b.width,
                b.height,
                b.top,
            ):
                return False, f"U+{a.codepoint:04X}: glyph header differs"
            if a.bits != b.bits:
                return False, f"U+{a.codepoint:04X}: bitmap bytes differ"
    return True, f"{len(font.glyphs)} glyphs verified"


# --- preview ----------------------------------------------------------------

# Deliberately Turkish: this sample is a fixture that proves the generated
# font covers the Turkish glyphs, and the preview PNG is meant to show them.
# It stays Turkish.
SAMPLE_TEXT = (
    "Çılgın şair İbrahim, ğ ve ı harfleriyle öykü yazar; üşenmez. "
    "Şu çorba güzelmiş, öğle ışığında içelim. "
    "ĞÜŞİÖÇ ğüşiöç 0123456789 — “tırnak” (parantez)…"
)


def _draw_from_epf(font: FontData, text: str, max_width: int, scale: int = 2) -> "Image.Image":
    """Draw the text using only the .epf bitmaps (a stand-in for the device)."""
    index = font.by_codepoint()
    fallback = index.get(ord("?"))
    line_h = font.height + font.line_spacing

    lines: list[list[tuple[Glyph, int]]] = []
    cur: list[tuple[Glyph, int]] = []
    pen = 0
    for ch in text:
        cp = ord(ch)
        if ch == "\n":
            lines.append(cur)
            cur, pen = [], 0
            continue
        g = index.get(cp)
        if g is None:
            g = fallback
        if g is None:
            continue
        adv = g.advance if g.advance else max(1, g.width)
        if pen + adv > max_width and cur:
            lines.append(cur)
            cur, pen = [], 0
        cur.append((g, pen))
        pen += adv
    if cur:
        lines.append(cur)

    width = max_width
    height = max(line_h, line_h * len(lines))
    img = Image.new("L", (width, height), 255)  # white paper
    inv = Image.new("L", (width, height), 0)
    for row, items in enumerate(lines):
        base_y = row * line_h
        for g, x in items:
            if g.width == 0 or g.height == 0:
                continue
            if base_y + g.top + g.height > height:
                continue
            if x + g.left < 0 or x + g.left + g.width > width:
                continue
            glyph_img = Image.new("L", (g.width, g.height), 0)
            glyph_img.putdata(
                [255 if ink else 0 for r in g.rows() for ink in r]
            )
            inv.paste(glyph_img, (x + g.left, base_y + g.top), glyph_img)

    if scale > 1:
        inv = inv.resize((width * scale, height * scale), Image.NEAREST)
    # Black ink / white paper
    return Image.eval(inv, lambda v: 255 - v)


def render_preview(font: FontData, out_path: str | Path, max_width: int = 250, scale: int = 2) -> Path:
    """Write a sample Turkish paragraph out as a PNG."""
    img = _draw_from_epf(font, SAMPLE_TEXT, max_width=max_width, scale=scale)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p)
    return p


# --- sidecar ----------------------------------------------------------------


def write_sidecar(font: FontData, path: str | Path) -> Path:
    """Write a .json metrics file for manual debugging on the firmware side."""
    p = Path(path)
    payload = {
        "format": "EPF1",
        "version": font.version,
        "source_font": font.source,
        "height": font.height,
        "ascent": font.ascent,
        "descent": font.descent,
        "descent_sign": "positive",  # height == ascent + descent
        "line_spacing": font.line_spacing,
        "line_advance": font.height + font.line_spacing,
        "glyph_count": len(font.glyphs),
        "bitstream": "continuous MSB-first, no row padding: bit N=y*width+x -> byte N>>3, mask 0x80>>(N&7)",
        "top_origin": "top of the line box (ascender line)",
        "glyphs": {
            f"U+{g.codepoint:04X}": {
                "char": chr(g.codepoint) if g.codepoint > 0x1F else "",
                "advance": g.advance,
                "left": g.left,
                "width": g.width,
                "height": g.height,
                "top": g.top,
                "bytes": len(g.bits),
            }
            for g in font.glyphs
        },
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


# --- CLI --------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fontgen.py",
        description=(
            "Convert a TTF/OTF font into Pocket Reader's .epf bitmap font format. "
            "The device runs no font engine; that is why the glyphs are rasterised in advance."
        ),
        epilog=(
            "Range names: " + ", ".join(sorted(RANGES)) + ", all\n"
            "Examples:\n"
            "  fontgen.py DejaVuSans.ttf --size 14 --out reader-14.epf --preview onizleme.png\n"
            "  fontgen.py NotoSans-Regular.ttf --size 12 --ranges ascii,latin1,latin-ext,turkish,punct\n"
            "  fontgen.py font.ttf --size 16 --ranges all --line-spacing 3\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("font", help="source TTF/OTF file")
    p.add_argument("--size", type=int, default=14, help="font size in pixels (default: 14)")
    p.add_argument("--out", required=True, help="the .epf file to write")
    p.add_argument(
        "--ranges",
        default=",".join(DEFAULT_RANGES),
        help=(
            "code point ranges to include, as comma-separated names. "
            f"Default: {','.join(DEFAULT_RANGES)}"
        ),
    )
    p.add_argument(
        "--line-spacing",
        type=int,
        default=2,
        help="extra leading between lines (px). Line advance = height + line_spacing (default: 2)",
    )
    p.add_argument(
        "--extra-codepoints",
        default="",
        help='extra characters to add to the list, e.g. --extra-codepoints "₺≥×"',
    )
    p.add_argument("--preview", help="draw the sample paragraph into this PNG file (visual check)")
    p.add_argument(
        "--preview-width",
        type=int,
        default=250,
        help="preview width (px). The device screen is 250 px (default: 250)",
    )
    p.add_argument("--json", help="path of the sidecar .json metrics file (default: <out>.json)")
    p.add_argument("--no-json", action="store_true", help="do not write the sidecar .json file")
    p.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    font_path = Path(args.font)
    if not font_path.exists():
        print(f"ERROR: font not found: {font_path}", file=sys.stderr)
        return 2

    try:
        names = [n for n in args.ranges.split(",") if n.strip()]
        codepoints = expand_ranges(names)
        for ch in args.extra_codepoints:
            cp = ord(ch)
            if cp not in codepoints:
                codepoints.append(cp)
        codepoints = sorted(set(codepoints))

        font = rasterise(
            font_path,
            args.size,
            codepoints,
            line_spacing=args.line_spacing,
        )
        raw = build_epf(font)

        ok, message = self_test(font, raw)
        if not ok:
            print(f"SELF TEST FAILED: {message}", file=sys.stderr)
            return 5

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)

        if not args.no_json:
            side = Path(args.json) if args.json else out.with_suffix(".json")
            write_sidecar(font, side)
    except EpfError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: could not write file ({exc})", file=sys.stderr)
        return 3

    skipped = getattr(font, "skipped", [])
    total_bits = sum(g.width * g.height for g in font.glyphs)
    print(f"Font          : {font_path.name} @ {args.size}px")
    print(f"Output        : {out} ({len(raw)} bytes)")
    print(f"Glyph count   : {len(font.glyphs)}")
    print(f"Bytes/glyph   : {len(raw) / len(font.glyphs):.1f}")
    print(f"height        : {font.height}  ascent: {font.ascent}  descent: {font.descent}")
    print(f"Line advance  : {font.height + font.line_spacing} px")
    print(f"Pixels        : {total_bits} bit ({total_bits / 8:.0f} bytes raw)")
    if skipped:
        print(f"Skipped (zero advance, empty): {len(skipped)} code points")
    if not args.no_json:
        side = Path(args.json) if args.json else out.with_suffix(".json")
        print(f"Metrics JSON  : {side}")
    if args.preview:
        try:
            p = render_preview(font, args.preview, max_width=args.preview_width)
            print(f"Preview       : {p}")
        except OSError as exc:
            print(f"WARNING: could not write preview ({exc})", file=sys.stderr)
    if args.verbose:
        print("--- first 16 glyphs ---")
        for g in font.glyphs[:16]:
            printable = chr(g.codepoint) if 0x20 < g.codepoint < 0x7F else "?"
            print(
                f"  U+{g.codepoint:04X} {printable!r:5} adv={g.advance:3d} "
                f"left={g.left:3d} w={g.width:3d} h={g.height:3d} top={g.top:3d} "
                f"{len(g.bits)}B"
            )
    print(f"Self test     : OK ({message})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
