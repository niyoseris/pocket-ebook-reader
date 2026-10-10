/*
 * font.cpp -- .epf bitmap font loader and renderer (format in include/font.h).
 *
 * The header and the glyph index are parsed once into RAM; glyph bitmaps are
 * read from LittleFS on demand, so a large font costs only ~19 bytes of index
 * per glyph (a 400-glyph Turkish font is well under 8 KB of heap).
 */

#include "font.h"
#include <LittleFS.h>
#include <vector>
#include <algorithm>
#include <string.h>

#define EPF_MAGIC      "EPF1"
#define EPF_HEADER_LEN 12
#define EPF_GLYPH_LEN  10
#define EPF_MAX_BITMAP 512      /* covers a 64x64 glyph; bigger ones are skipped */

struct GlyphInfo {
    uint32_t cp;
    uint32_t offset;     /* absolute file offset of the bitmap */
    int8_t   advance;
    int8_t   left;
    uint8_t  width;
    uint8_t  height;
    uint8_t  top;
};

static File                    s_file;
static bool                    s_loaded = false;
static char                    s_path[80] = {0};
static uint8_t                 s_height = 0;
static int8_t                  s_ascent = 0;
static int8_t                  s_descent = 0;
static uint8_t                 s_spacing = 0;
static uint16_t                s_count = 0;
static std::vector<GlyphInfo>  s_glyphs;
static uint8_t                 s_bitmap[EPF_MAX_BITMAP];

/* --------------------------------------------------------------------------
 *  Built-in 3x5 fallback font.
 *
 *  Without this, "no font file found -- run tools/fontgen.py" could not be
 *  drawn at all, because drawing text needs a font. It covers A-Z, 0-9 and
 *  the punctuation an error message needs; Turkish letters are transliterated
 *  (c->C, g->G, i->I, o->O, s->S, u->U) and lower case is upshifted. It is
 *  only ever used when no .epf could be loaded.
 * ------------------------------------------------------------------------ */
#define FB_W 3
#define FB_H 5
#define FB_GAP 1

struct FbGlyph { char c; uint8_t rows[FB_H]; };

static const FbGlyph kFb[] = {
    { ' ', { 0,0,0,0,0 } },
    { 'A', { 2,5,7,5,5 } }, { 'B', { 6,5,6,5,6 } }, { 'C', { 3,4,4,4,3 } },
    { 'D', { 6,5,5,5,6 } }, { 'E', { 7,4,6,4,7 } }, { 'F', { 7,4,6,4,4 } },
    { 'G', { 3,4,5,5,3 } }, { 'H', { 5,5,7,5,5 } }, { 'I', { 7,2,2,2,7 } },
    { 'J', { 1,1,1,5,2 } }, { 'K', { 5,5,6,5,5 } }, { 'L', { 4,4,4,4,7 } },
    { 'M', { 5,7,7,5,5 } }, { 'N', { 5,7,7,7,5 } }, { 'O', { 2,5,5,5,2 } },
    { 'P', { 6,5,6,4,4 } }, { 'Q', { 2,5,5,7,3 } }, { 'R', { 6,5,6,5,5 } },
    { 'S', { 3,4,2,1,6 } }, { 'T', { 7,2,2,2,2 } }, { 'U', { 5,5,5,5,3 } },
    { 'V', { 5,5,5,5,2 } }, { 'W', { 5,5,7,7,5 } }, { 'X', { 5,5,2,5,5 } },
    { 'Y', { 5,5,2,2,2 } }, { 'Z', { 7,1,2,4,7 } },
    { '0', { 7,5,5,5,7 } }, { '1', { 2,6,2,2,7 } }, { '2', { 7,1,7,4,7 } },
    { '3', { 7,1,3,1,7 } }, { '4', { 5,5,7,1,1 } }, { '5', { 7,4,7,1,7 } },
    { '6', { 7,4,7,5,7 } }, { '7', { 7,1,1,1,1 } }, { '8', { 7,5,7,5,7 } },
    { '9', { 7,5,7,1,7 } },
    { '.', { 0,0,0,0,2 } }, { ',', { 0,0,0,2,4 } }, { ':', { 0,2,0,2,0 } },
    { '-', { 0,0,7,0,0 } }, { '?', { 7,1,3,0,2 } }, { '/', { 1,1,2,4,4 } },
    { '%', { 5,1,2,4,5 } }, { '!', { 2,2,2,0,2 } }, { '+', { 0,2,7,2,0 } },
};
static const int kFbCount = sizeof(kFb) / sizeof(kFb[0]);

/* Map a codepoint onto the fallback font. */
static const FbGlyph* fbFind(uint32_t cp) {
    if (cp >= 'a' && cp <= 'z') cp -= 32;

    switch (cp) {
        /* Turkish letters, folded to their ASCII base. */
        case 0x00E7: case 0x00C7: cp = 'C'; break;   /* c, C with cedilla   */
        case 0x011F: case 0x011E: cp = 'G'; break;   /* g, G with breve     */
        case 0x0131: case 0x0130: cp = 'I'; break;   /* dotless i, dotted I */
        case 0x00F6: case 0x00D6: cp = 'O'; break;   /* o, O with umlaut    */
        case 0x015F: case 0x015E: cp = 'S'; break;   /* s, S with cedilla   */
        case 0x00FC: case 0x00DC: cp = 'U'; break;   /* u, U with umlaut    */
        default: break;
    }

    for (int i = 0; i < kFbCount; i++)
        if (kFb[i].c == (char)cp) return &kFb[i];
    return nullptr;
}

/* -------------------------------------------------------------------------- */

int utf8SeqLen(uint8_t c) {
    if (c >= 0xF0) return 4;
    if (c >= 0xE0) return 3;
    if (c >= 0xC0) return 2;
    return 1;
}

uint32_t utf8Next(const char*& s) {
    if (!s || !*s) return 0;
    const uint8_t c = (uint8_t)*s++;
    if (c < 0x80) return c;

    const int n = utf8SeqLen(c);
    uint32_t cp = (uint32_t)(c & (0xFF >> (n + 1)));
    for (int i = 1; i < n; i++) {
        if (((uint8_t)*s & 0xC0) != 0x80) return 0xFFFD;   /* broken sequence */
        cp = (cp << 6) | (uint32_t)((uint8_t)*s & 0x3F);
        s++;
    }
    return cp;
}

/* Binary search the glyph index. */
static const GlyphInfo* findGlyph(uint32_t cp) {
    if (!s_loaded || s_glyphs.empty()) return nullptr;
    size_t lo = 0, hi = s_glyphs.size();
    while (lo < hi) {
        const size_t mid = lo + (hi - lo) / 2;
        if (s_glyphs[mid].cp < cp) lo = mid + 1;
        else                       hi = mid;
    }
    if (lo < s_glyphs.size() && s_glyphs[lo].cp == cp) return &s_glyphs[lo];
    return nullptr;
}

/* Substitute for codepoints the font does not carry. */
static const GlyphInfo* findFallback() {
    const GlyphInfo* g = findGlyph('?');
    if (g) return g;
    g = findGlyph(' ');
    if (g) return g;
    return s_glyphs.empty() ? nullptr : &s_glyphs[0];
}

bool fontLoaded()   { return s_loaded; }
const char* fontPath() { return s_path; }
int  fontCellHeight() { return s_loaded ? s_height : FB_H; }
int  fontGlyphCount() { return s_loaded ? s_count : 0; }

int fontLineHeight(int scale) {
    if (!s_loaded) return (FB_H + 2) * scale;      /* fallback font */
    return ((int)s_ascent + (int)s_descent + (int)s_spacing) * scale;
}
int fontAscent(int scale)  { return s_loaded ? (int)s_ascent * scale  : FB_H * scale; }
int fontDescent(int scale) { return s_loaded ? (int)s_descent * scale : 2 * scale; }

bool fontHasGlyph(uint32_t cp) { return findGlyph(cp) != nullptr; }

void fontUnload() {
    if (s_file) s_file.close();
    s_glyphs.clear();
    s_glyphs.shrink_to_fit();
    s_loaded = false;
    s_count = 0;
    s_path[0] = 0;
}

bool fontLoad(const char* path) {
    fontUnload();
    if (!path) return false;

    s_file = LittleFS.open(path, "r");
    if (!s_file) {
        Serial.printf("[font] cannot open %s\n", path);
        return false;
    }

    uint8_t hdr[EPF_HEADER_LEN];
    if (s_file.read(hdr, EPF_HEADER_LEN) != EPF_HEADER_LEN) {
        Serial.printf("[font] %s: short header\n", path);
        fontUnload();
        return false;
    }
    if (memcmp(hdr, EPF_MAGIC, 4) != 0) {
        Serial.printf("[font] %s: bad magic\n", path);
        fontUnload();
        return false;
    }
    if (hdr[4] != 1) {
        Serial.printf("[font] %s: unsupported version %u\n", path, (unsigned)hdr[4]);
        fontUnload();
        return false;
    }

    s_height  = hdr[5];
    s_ascent  = (int8_t)hdr[6];
    s_descent = (int8_t)hdr[7];
    s_spacing = hdr[8];
    s_count   = (uint16_t)hdr[10] | ((uint16_t)hdr[11] << 8);

    const uint32_t file_size = s_file.size();
    uint32_t off = EPF_HEADER_LEN;
    s_glyphs.reserve(s_count);

    for (uint16_t i = 0; i < s_count; i++) {
        if (off + EPF_GLYPH_LEN > file_size) break;      /* truncated file */
        if (!s_file.seek(off)) break;

        uint8_t g[EPF_GLYPH_LEN];
        if (s_file.read(g, EPF_GLYPH_LEN) != EPF_GLYPH_LEN) break;

        GlyphInfo gi;
        gi.cp      = (uint32_t)g[0] | ((uint32_t)g[1] << 8) |
                     ((uint32_t)g[2] << 16) | ((uint32_t)g[3] << 24);
        gi.advance = (int8_t)g[4];
        gi.left    = (int8_t)g[5];
        gi.width   = g[6];
        gi.height  = g[7];
        gi.top     = g[8];
        gi.offset  = off + EPF_GLYPH_LEN;

        const uint32_t nbytes =
            ((uint32_t)gi.width * (uint32_t)gi.height + 7u) / 8u;
        off = gi.offset + nbytes;
        s_glyphs.push_back(gi);
    }

    if (s_glyphs.empty()) {
        Serial.printf("[font] %s: no glyphs\n", path);
        fontUnload();
        return false;
    }

    std::sort(s_glyphs.begin(), s_glyphs.end(),
              [](const GlyphInfo& a, const GlyphInfo& b) { return a.cp < b.cp; });

    s_loaded = true;
    strncpy(s_path, path, sizeof(s_path) - 1);
    s_path[sizeof(s_path) - 1] = 0;

    Serial.printf("[font] %s: %u glyphs, cell %u, asc %d, desc %d, gap %u\n",
                  path, (unsigned)s_glyphs.size(), (unsigned)s_height,
                  (int)s_ascent, (int)s_descent, (unsigned)s_spacing);
    return true;
}

/* -------------------------------------------------------------------------- */

int fontGlyphAdvance(uint32_t cp, int scale) {
    if (!s_loaded) return (FB_W + FB_GAP) * scale;
    const GlyphInfo* g = findGlyph(cp);
    if (!g) g = findFallback();
    if (!g) return 4 * scale;
    return (int)g->advance * scale;
}

int fontTextWidth(const char* utf8, int scale) {
    if (!utf8) return 0;
    int w = 0;
    const char* s = utf8;
    for (;;) {
        const uint32_t cp = utf8Next(s);
        if (cp == 0) break;
        if (cp == '\n') break;              /* width of the first line only */
        w += fontGlyphAdvance(cp, scale);
    }
    return w;
}

void fontDrawGlyph(Canvas& canvas, uint32_t cp, int x, int baseline_y,
                   int scale, uint8_t ink) {
    if (!s_loaded) {
        /* No .epf at all: draw with the built-in 3x5 font so error messages
         * are actually legible on the panel. */
        const FbGlyph* fg = fbFind(cp);
        if (!fg) return;
        const int x0 = x;
        const int y0 = baseline_y - FB_H * scale;
        for (int row = 0; row < FB_H; row++) {
            const uint8_t bits = fg->rows[row];
            for (int col = 0; col < FB_W; col++) {
                if (!(bits & (uint8_t)(1 << (FB_W - 1 - col)))) continue;
                if (scale <= 1) canvas.drawPixel(x0 + col, y0 + row, ink);
                else            canvas.fillRect(x0 + col * scale, y0 + row * scale,
                                                scale, scale, ink);
            }
        }
        return;
    }

    const GlyphInfo* g = findGlyph(cp);
    if (!g) return;                          /* missing glyphs render blank */
    if (g->width == 0 || g->height == 0) return;

    const uint32_t nbytes = ((uint32_t)g->width * (uint32_t)g->height + 7u) / 8u;
    if (nbytes > EPF_MAX_BITMAP) return;
    if (!s_file.seek(g->offset)) return;
    if (s_file.read(s_bitmap, nbytes) != nbytes) return;

    const int x0 = x + (int)g->left * scale;
    /* `top` is measured from the TOP of the glyph cell, NOT from the baseline.
     * The baseline sits s_ascent pixels below the cell top, so the ink's top
     * edge is (s_ascent - top) pixels ABOVE the baseline. Getting this wrong
     * is not a constant shift: the error is per-glyph, so text ends up
     * vertically scrambled and glyphs collide with neighbouring lines.
     * Cross-checked by tools/tests/test_epf_interop.py. */
    const int y0 = baseline_y - ((int)s_ascent - (int)g->top) * scale;

    for (int row = 0; row < g->height; row++) {
        for (int col = 0; col < g->width; col++) {
            const uint32_t bit = (uint32_t)row * g->width + (uint32_t)col;
            if (!(s_bitmap[bit >> 3] & (uint8_t)(0x80 >> (bit & 7)))) continue;
            if (scale <= 1) canvas.drawPixel(x0 + col, y0 + row, ink);
            else            canvas.fillRect(x0 + col * scale, y0 + row * scale,
                                            scale, scale, ink);
        }
    }
}

void fontDrawText(Canvas& canvas, const char* utf8, int x, int baseline_y,
                  int scale, uint8_t ink) {
    if (!utf8) return;
    int pen = x;
    const char* s = utf8;
    for (;;) {
        const uint32_t cp = utf8Next(s);
        if (cp == 0) break;
        if (cp == '\n') {
            pen = x;
            baseline_y += fontLineHeight(scale);
            continue;
        }
        fontDrawGlyph(canvas, cp, pen, baseline_y, scale, ink);
        pen += fontGlyphAdvance(cp, scale);
    }
}

/* -------------------------------------------------------------------------- */

int fontWrapLine(const char* utf8, int max_width, int scale, int* consumed_bytes) {
    if (consumed_bytes) *consumed_bytes = 0;
    if (!utf8 || !*utf8) return 0;
    if (max_width <= 0) return 0;

    const char* p        = utf8;
    const char* line_end = utf8;    /* end of the last char that fits */
    const char* brk      = nullptr; /* just past the last space that fits */
    int width = 0;

    while (*p) {
        if (*p == '\n') break;

        const char* start = p;
        const uint32_t cp = utf8Next(p);
        if (cp == 0) break;
        if (cp == '\r') continue;

        const int adv = fontGlyphAdvance(cp, scale);

        if (cp == ' ') {
            if (width + adv > max_width) break;   /* trailing space that overflows */
            width += adv;
            brk = p;                              /* break AFTER this space */
            line_end = p;
            continue;
        }

        if (width + adv > max_width) {
            if (brk) {
                /* Break at the last space. The line is everything before it. */
                int len = (int)(brk - utf8) - 1;
                if (len < 0) len = 0;
                if (consumed_bytes) *consumed_bytes = (int)(brk - utf8);
                return len;
            }
            /* A single word wider than the line: hard-break mid-word. */
            const int len = (int)(start - utf8);
            if (consumed_bytes) *consumed_bytes = len;
            return len;
        }

        width += adv;
        line_end = p;
    }

    int len = (int)(line_end - utf8);
    if (len < 0) len = 0;

    if (consumed_bytes) {
        if (*p == '\n')          *consumed_bytes = (int)(p - utf8) + 1;  /* skip it */
        else if (*p == 0)        *consumed_bytes = len;
        else                     *consumed_bytes = (int)(p - utf8);
    }
    return len;
}
