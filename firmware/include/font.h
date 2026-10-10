#pragma once
#include <Arduino.h>
#include "epd.h"

/*
 * ===========================================================================
 *  font.h -- runtime-loaded .epf bitmap fonts
 * ===========================================================================
 *
 *  File format (little-endian, packed, no padding):
 *
 *  header, 12 bytes:
 *      char   magic[4]   = "EPF1"
 *      uint8  version    = 1
 *      uint8  height          glyph cell height in pixels
 *      int8   ascent          baseline above the top of the cell
 *      int8   descent         baseline to the bottom of the cell
 *      uint8  line_spacing    extra pixels between lines
 *      uint8  reserved
 *      uint16 glyph_count
 *
 *  then glyph_count entries:
 *      uint32 codepoint
 *      int8   advance         pen movement
 *      int8   left            bitmap x offset from the pen position
 *      uint8  width
 *      uint8  height
 *      uint8  top             bitmap y offset from the TOP of the glyph cell
 *      uint8  reserved
 *      ------------------------------------------ 10-byte fixed header
 *      uint8  bitmap[ceil(width*height/8)]
 *                             CONTINUOUS MSB-first bit stream, NOT row-padded.
 *                             bit N = y*width + x  ->  byte N>>3, mask 0x80>>(N&7).
 *                             1 = ink (black). A row-padded reader (which would
 *                             need ceil(width/8)*height bytes) renders every
 *                             glyph wider than 8 px as garbage.
 *
 *  Note on `top`: it is measured from the cell top, so the ink's top edge sits
 *  (ascent - top) pixels above the baseline. Renderers must use that expression,
 *  not `baseline - top`. The two differ per glyph, which scrambles text.
 *  Cross-checked against tools/fontgen.py by tools/tests/test_epf_interop.py.
 *
 *  Turkish characters are ordinary codepoints in this file, so c/g/i/I/o/s/u
 *  and their dotted/capital forms work as long as the generator included them
 *  (tools/fontgen.py does).
 * ===========================================================================
 */

/* Load a font and keep the file open for glyph reads. Replaces any previously
 * loaded font. Returns false if the file is missing or malformed. */
bool fontLoad(const char* path);
void fontUnload();
bool fontLoaded();

/* Metrics (all scaled by `scale`, which is 1 or 2). */
int  fontLineHeight(int scale = 1);   /* ascent + descent + line_spacing */
int  fontAscent(int scale = 1);
int  fontDescent(int scale = 1);
int  fontCellHeight();                /* raw `height` field, unscaled */
int  fontGlyphCount();

/* Width of a UTF-8 string when rendered at `scale`. */
int  fontTextWidth(const char* utf8, int scale = 1);
/* Pen advance of a single codepoint (falls back to the space glyph). */
int  fontGlyphAdvance(uint32_t cp, int scale = 1);
bool fontHasGlyph(uint32_t cp);

/* Draw one glyph: `x` is the pen position, `baseline_y` the baseline.
 * `ink` is the colour of the glyph pixels (COL_BLACK by default). */
void fontDrawGlyph(Canvas& canvas, uint32_t cp, int x, int baseline_y,
                   int scale = 1, uint8_t ink = COL_BLACK);

/* Draw a whole string with the pen starting at `x`. */
void fontDrawText(Canvas& canvas, const char* utf8, int x, int baseline_y,
                  int scale = 1, uint8_t ink = COL_BLACK);

/* UTF-8 decoder: returns the next codepoint and advances `s`; 0 at the end. */
uint32_t utf8Next(const char*& s);
/* Number of bytes in the UTF-8 sequence that starts with `c` (1..4). */
int utf8SeqLen(uint8_t c);

/* Greedy word wrap.
 *   returns          number of BYTES of `utf8` that fit in one line
 *   consumed_bytes   bytes the caller should skip to reach the next line
 *                    (line bytes + the space that was broken at)
 * Stops at '\n' as well. Returns 0 for an empty string. */
int fontWrapLine(const char* utf8, int max_width, int scale,
                 int* consumed_bytes = nullptr);

/* The path that was loaded (for error messages). */
const char* fontPath();
