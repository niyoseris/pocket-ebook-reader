/*
 * epd.cpp -- SSD1680 2.13" e-paper driver + logical Canvas.
 *
 * Register sequences and waveforms are the genuine Waveshare V3 reference
 * driver data (see src/epd_lut.h for the exact source URL and license).
 * Structure of the init sequence mirrors EPD_2in13_V3_Init() one-for-one so
 * that it stays auditable against the vendor file.
 */

#include "epd.h"
#include "epd_lut.h"
#include "font.h"
#include <SPI.h>
#include <string.h>

/* --------------------------------------------------------------------------
 * Framebuffers (static, so they never hit the heap):
 *   s_fb   -- the frame currently being drawn (what the Canvas writes into)
 *   s_base -- the frame that is already on the panel; becomes the 0x26
 *             "previous" bank so the controller can compute the partial diff
 * ------------------------------------------------------------------------ */
static uint8_t s_fb[EPD_FB_SIZE];
static uint8_t s_base[EPD_FB_SIZE];

Canvas canvas;

uint8_t* epdFramebuffer() { return s_fb; }

static bool s_spi_on = false;
static bool s_partial_waveform = false;   /* which waveform is currently loaded */
static bool s_slept = false;              /* panel is in deep sleep mode 1 */

/* Dirty rectangle in NATIVE coordinates (inclusive). Empty when x1 < x0. */
static int s_dx0, s_dy0, s_dx1, s_dy1;

/* ==========================================================================
 *  Low level SPI
 * ========================================================================== */

static inline void spiOn() {
    if (!s_spi_on) {
        SPI.beginTransaction(SPISettings(EPD_SPI_HZ, MSBFIRST, SPI_MODE0));
        s_spi_on = true;
    }
}

static inline void spiOff() {
    if (s_spi_on) {
        SPI.endTransaction();
        s_spi_on = false;
    }
}

static inline void epdCmd(uint8_t c) {
    digitalWrite(EPD_DC, LOW);
    digitalWrite(EPD_CS, LOW);
    SPI.transfer(c);
    digitalWrite(EPD_CS, HIGH);
}

static inline void epdData(uint8_t d) {
    digitalWrite(EPD_DC, HIGH);
    digitalWrite(EPD_CS, LOW);
    SPI.transfer(d);
    digitalWrite(EPD_CS, HIGH);
}

/* Bulk data transfer: keeps CS asserted for the whole block instead of
 * toggling it per byte like the vendor's DEV_SPI_WriteByte() does. */
static void epdDataBulk(const uint8_t* p, size_t n) {
    if (!n) return;
    digitalWrite(EPD_DC, HIGH);
    digitalWrite(EPD_CS, LOW);
    SPI.writeBytes(p, n);
    digitalWrite(EPD_CS, HIGH);
}

/* ==========================================================================
 *  Panel primitives (vendor names kept for cross-checking)
 * ========================================================================== */

void epdHwReset() {
    digitalWrite(EPD_RST, HIGH);
    delay(20);
    digitalWrite(EPD_RST, LOW);
    delay(2);
    digitalWrite(EPD_RST, HIGH);
    delay(20);
}

/* True while the panel is working. The polarity comes from config.h -- see the
 * note there and the README section on verifying it with a multimeter. */
static inline bool epdIsBusy() {
#if EPD_BUSY_ACTIVE_HIGH
    return digitalRead(EPD_BUSY) == HIGH;
#else
    return digitalRead(EPD_BUSY) == LOW;
#endif
}

bool epdBusyWait(uint32_t timeout_ms) {
    const uint32_t start = millis();
    while (epdIsBusy()) {
        if (millis() - start > timeout_ms) {
            /* Loud, specific, and actionable -- this is the single most likely
             * bring-up failure on a new board. */
            Serial.printf("[epd] BUSY TIMEOUT after %ums (pin level=%d, "
                          "EPD_BUSY_ACTIVE_HIGH=%d)\n",
                          (unsigned)timeout_ms, (int)digitalRead(EPD_BUSY),
                          (int)EPD_BUSY_ACTIVE_HIGH);
            Serial.println("[epd] *** BUSY polarity may be wrong -- change "
                           "EPD_BUSY_ACTIVE_HIGH in include/config.h ***");
            return false;
        }
        delay(10);
    }
    delay(10);   /* vendor: DEV_Delay_ms(10) after release */
    return true;
}

/* 0x44 / 0x45 -- RAM X/Y address start/end (X in BYTES on the wire). */
static void epdSetWindows(int x_start, int y_start, int x_end, int y_end) {
    epdCmd(0x44);
    epdData((x_start >> 3) & 0xFF);
    epdData((x_end   >> 3) & 0xFF);
    epdCmd(0x45);
    epdData(y_start & 0xFF);
    epdData((y_start >> 8) & 0xFF);
    epdData(y_end & 0xFF);
    epdData((y_end   >> 8) & 0xFF);
}

/* 0x4E / 0x4F -- RAM address counter (X in BYTES). */
static void epdSetCursor(int x_byte, int y) {
    epdCmd(0x4E);
    epdData(x_byte & 0xFF);
    epdCmd(0x4F);
    epdData(y & 0xFF);
    epdData((y >> 8) & 0xFF);
}

/*
 * Load a 159-byte vendor waveform record.
 *
 * This is EPD_2IN13_V2_LUT_by_host() from the vendor file, byte for byte:
 *   lut[0..152] -> 0x32 (LUT data)
 *   lut[153]    -> 0x3F
 *   lut[154]    -> 0x03 (gate voltage)
 *   lut[155..157]-> 0x04 (VSH, VSH2, VSL)
 *   lut[158]    -> 0x2C (VCOM)
 */
static void epdLoadWaveform(const uint8_t* lut) {
    epdCmd(0x32);                       /* WRITE_LUT_REGISTER */
    for (uint8_t i = 0; i < 153; i++) epdData(lut[i]);
    epdBusyWait();

    epdCmd(0x3F);
    epdData(lut[153]);
    epdCmd(0x03);                       /* gate voltage */
    epdData(lut[154]);
    epdCmd(0x04);                       /* source voltage */
    epdData(lut[155]);                  /* VSH  */
    epdData(lut[156]);                  /* VSH2 */
    epdData(lut[157]);                  /* VSL  */
    epdCmd(0x2C);                       /* VCOM */
    epdData(lut[158]);
}

/* Display Update Control + Activate, full quality (0x22 = 0xC7). */
static void epdTurnOnDisplay() {
    epdCmd(0x22);
    epdData(0xC7);
    epdCmd(0x20);
    epdBusyWait();
}

/* Display Update Control + Activate, fast partial (0x22 = 0x0F). */
static void epdTurnOnDisplayPartial() {
    epdCmd(0x22);
    epdData(0x0F);      /* vendor comment: fast:0x0c, quality:0x0f, 0xcf */
    epdCmd(0x20);
    epdBusyWait(EPD_BUSY_TIMEOUT_PARTIAL_MS);
}

/*
 * EPD_2in13_V3_Init(): the panel's register bring-up.
 * Called from epdInit() and again from every epdFullRefresh(), because a
 * partial refresh overwrites 0x3F/0x03/0x04/0x2C with the partial waveform's
 * voltages -- re-running this restores the full-quality operating point.
 */
static void epdInitRegisters() {
    epdHwReset();
    delay(100);

    epdBusyWait();
    epdCmd(0x12);                       /* SWRESET */
    epdBusyWait();

    epdCmd(0x01);                       /* Driver output control: 250 gates */
    epdData(0xF9);
    epdData(0x00);
    epdData(0x00);

    epdCmd(0x11);                       /* Data entry mode: X+ Y+ (AM=X) */
    epdData(0x03);                      /* -> rows are filled left to right */

    epdSetWindows(0, 0, EPD_NATIVE_W - 1, EPD_NATIVE_H - 1);
    epdSetCursor(0, 0);

    epdCmd(0x3C);                       /* Border waveform */
    epdData(0x05);

    epdCmd(0x21);                       /* Display update control */
    epdData(0x00);
    epdData(0x80);

    epdCmd(0x18);                       /* Read built-in temperature sensor */
    epdData(0x80);

    epdBusyWait();
    epdLoadWaveform(WS_20_30_2IN13_V3);
    s_partial_waveform = false;
}

/* ==========================================================================
 *  Public driver API
 * ========================================================================== */

bool epdInit() {
    pinMode(EPD_CS, OUTPUT);
    pinMode(EPD_DC, OUTPUT);
    pinMode(EPD_RST, OUTPUT);
    pinMode(EPD_BUSY, INPUT);           /* 100k external pull-up: idle HIGH */
    digitalWrite(EPD_CS, HIGH);
    digitalWrite(EPD_DC, HIGH);
    digitalWrite(EPD_RST, HIGH);

    SPI.begin(EPD_SCK, -1 /* MISO unused */, EPD_MOSI, -1 /* no hw CS */);
    spiOn();

    /* White panel + white base before the first refresh. */
    memset(s_fb, 0xFF, sizeof(s_fb));
    memset(s_base, 0xFF, sizeof(s_base));
    epdClearDirty();

    epdInitRegisters();

    Serial.printf("[epd] SSD1680 up (%dx%d native, canvas %dx%d, rot %d)\n",
                  EPD_NATIVE_W, EPD_NATIVE_H, CANVAS_W, CANVAS_H, EPD_ROTATION);
    return true;
}

void epdSpiRelease() {
    spiOff();
}

void epdSleep() {
    spiOn();
    epdCmd(0x10);                       /* DEEP_SLEEP */
    epdData(0x01);                      /* A[1:0]=01 -> Mode 1: ~1 uA, RAM kept */
    delay(100);
    s_slept = true;
    Serial.println("[epd] panel in deep sleep mode 1 (~1uA, image retained)");
    Serial.println("[epd] only a hardware reset (HWRESET) exits it; a software "
                   "reset (0x12) does not");
}

void epdClear(bool black) {
    memset(s_fb, black ? 0x00 : 0xFF, sizeof(s_fb));
    memset(s_base, black ? 0x00 : 0xFF, sizeof(s_base));
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

/* --------------------------------------------------------------------------
 *  Dirty rectangle bookkeeping
 * ------------------------------------------------------------------------ */

static void epdNativeDirtyUnion(int x0, int y0, int x1, int y1) {
    if (x1 < x0 || y1 < y0) return;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > EPD_NATIVE_W - 1) x1 = EPD_NATIVE_W - 1;
    if (y1 > EPD_NATIVE_H - 1) y1 = EPD_NATIVE_H - 1;

    if (s_dx1 < s_dx0) {                /* was empty */
        s_dx0 = x0; s_dy0 = y0; s_dx1 = x1; s_dy1 = y1;
        return;
    }
    if (x0 < s_dx0) s_dx0 = x0;
    if (y0 < s_dy0) s_dy0 = y0;
    if (x1 > s_dx1) s_dx1 = x1;
    if (y1 > s_dy1) s_dy1 = y1;
}

void epdDirty(int x, int y, int w, int h) {
    if (w <= 0 || h <= 0) return;
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > CANVAS_W) w = CANVAS_W - x;
    if (y + h > CANVAS_H) h = CANVAS_H - y;
    if (w <= 0 || h <= 0) return;

    /* Map the two opposite corners through the rotation and take the
     * bounding box in native space. */
    int nx0, ny0, nx1, ny1;
    epdMapLogicalToNative(x,         y,         &nx0, &ny0);
    epdMapLogicalToNative(x + w - 1, y + h - 1, &nx1, &ny1);
    const int ax0 = (nx0 < nx1) ? nx0 : nx1;
    const int ax1 = (nx0 < nx1) ? nx1 : nx0;
    const int ay0 = (ny0 < ny1) ? ny0 : ny1;
    const int ay1 = (ny0 < ny1) ? ny1 : ny0;
    epdNativeDirtyUnion(ax0, ay0, ax1, ay1);
}

void epdSetPartialWindow(int x, int y, int w, int h) {
    epdClearDirty();
    epdDirty(x, y, w, h);
}

void epdClearDirty() {
    s_dx0 = 0; s_dy0 = 0; s_dx1 = -1; s_dy1 = -1;
}

bool epdIsDirty() {
    return s_dx1 >= s_dx0;
}

/* --------------------------------------------------------------------------
 *  Refresh
 * ------------------------------------------------------------------------ */

void epdFullRefresh() {
    spiOn();

    /* A sleeping panel only wakes on a hardware reset (0x12 does NOT exit
     * deep sleep mode 1), and a preceding partial refresh left the partial
     * waveform's voltages programmed. Both are fixed by re-running the
     * vendor init register block. */
    if (s_slept || s_partial_waveform) {
        epdInitRegisters();
        s_slept = false;
    }

    epdSetWindows(0, 0, EPD_NATIVE_W - 1, EPD_NATIVE_H - 1);
    epdSetCursor(0, 0);

    epdCmd(0x24);                       /* write new image to RAM bank A */
    epdDataBulk(s_fb, EPD_FB_SIZE);

    epdCmd(0x26);                       /* write same image to RAM bank B */
    epdDataBulk(s_fb, EPD_FB_SIZE);

    epdTurnOnDisplay();

    /* The panel now shows s_fb, so that becomes the diff base. */
    memcpy(s_base, s_fb, EPD_FB_SIZE);
    epdClearDirty();
}

void epdPartialRefresh() {
    spiOn();

    /* No dirty rect -> nothing to do. An empty rect that spans the whole
     * canvas is legitimate (it just costs a full-window partial update). */
    if (!epdIsDirty()) return;

    /* Byte-align the native window in X (the controller addresses X in
     * bytes) and clamp. */
    int xbs = s_dx0 >> 3;
    int xbe = s_dx1 >> 3;
    int y0  = s_dy0;
    int y1  = s_dy1;
    if (xbe > EPD_ROW_BYTES - 1) xbe = EPD_ROW_BYTES - 1;
    if (y1  > EPD_NATIVE_H  - 1) y1  = EPD_NATIVE_H  - 1;
    if (xbs < 0) xbs = 0;
    if (y0  < 0) y0  = 0;
    if (xbe < xbs || y1 < y0) { epdClearDirty(); return; }

    const int row_bytes = xbe - xbs + 1;
    const int rows      = y1 - y0 + 1;

    /* ---- vendor partial preamble: EPD_2in13_V3_Display_Partial() ---- */
    if (s_slept) {
        /* Deep sleep is only exited by HWRESET; the vendor's partial routine
         * pulses RST anyway, but the register block has to be restored too. */
        epdInitRegisters();
        s_slept = false;
    }
    digitalWrite(EPD_RST, LOW);
    delay(1);
    digitalWrite(EPD_RST, HIGH);

    if (!s_partial_waveform) {
        epdLoadWaveform(WF_PARTIAL_2IN13_V3);
        s_partial_waveform = true;

        epdCmd(0x37);                   /* RAM ping-pong enable + others */
        epdData(0x00);
        epdData(0x00);
        epdData(0x00);
        epdData(0x00);
        epdData(0x00);
        epdData(0x40);                  /* RAM ping-pong enable */
        epdData(0x00);
        epdData(0x00);
        epdData(0x00);
        epdData(0x00);

        epdCmd(0x3C);                   /* Border waveform for partial */
        epdData(0x80);

        epdCmd(0x22);                   /* Enable clock + analog */
        epdData(0xC0);
        epdCmd(0x20);
        epdBusyWait(EPD_BUSY_TIMEOUT_PARTIAL_MS);
    }

    epdSetWindows(xbs << 3, y0, (xbe << 3) | 0x07, y1);
    epdSetCursor(xbs, y0);

    /* 0x26 = the frame that is currently on the panel (the diff base).
     * 0x24 = the frame we want to show. Written in that order, so 0x24 is
     * the last thing the controller sees. Both banks are supplied
     * explicitly, so the diff does not depend on ping-pong state -- which is
     * also why this stays correct after an interrupted refresh. */
    const bool whole_ram = (row_bytes == EPD_ROW_BYTES && rows == EPD_NATIVE_H);

    epdCmd(0x26);
    if (whole_ram) {
        epdDataBulk(s_base, EPD_FB_SIZE);
    } else {
        for (int y = y0; y <= y1; y++)
            epdDataBulk(s_base + (size_t)y * EPD_ROW_BYTES + xbs, row_bytes);
    }

    epdCmd(0x24);
    if (whole_ram) {
        epdDataBulk(s_fb, EPD_FB_SIZE);
    } else {
        for (int y = y0; y <= y1; y++)
            epdDataBulk(s_fb + (size_t)y * EPD_ROW_BYTES + xbs, row_bytes);
    }

    epdTurnOnDisplayPartial();

    /* The dirty region is now on the panel: promote it into the base. */
    for (int y = y0; y <= y1; y++) {
        memcpy(s_base + (size_t)y * EPD_ROW_BYTES + xbs,
               s_fb   + (size_t)y * EPD_ROW_BYTES + xbs,
               row_bytes);
    }

    epdClearDirty();
}

/* ==========================================================================
 *  Canvas
 * ========================================================================== */

Canvas::Canvas() : _buf(nullptr), _ink(COL_BLACK), _clip(false),
                   _cx(0), _cy(0), _cw(0), _ch(0) {}

void Canvas::begin(uint8_t* buffer) {
    _buf = buffer;
    clearClip();
}

void Canvas::clear(uint8_t color) {
    if (!_buf) return;
    memset(_buf, (color == COL_BLACK) ? 0x00 : 0xFF, EPD_FB_SIZE);
    clearClip();
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

void Canvas::drawPixel(int x, int y, uint8_t color) {
    if (!_buf) return;
    if (_clip && (x < _cx || y < _cy || x >= _cx + _cw || y >= _cy + _ch)) return;
    if (x < 0 || y < 0 || x >= CANVAS_W || y >= CANVAS_H) return;

    int nx, ny;
    epdMapLogicalToNative(x, y, &nx, &ny);
    if (nx < 0 || ny < 0 || nx >= EPD_NATIVE_W || ny >= EPD_NATIVE_H) return;

    const uint32_t idx = (uint32_t)ny * EPD_ROW_BYTES + (uint32_t)(nx >> 3);
    const uint8_t  bit = (uint8_t)(0x80 >> (nx & 7));
    if (color == COL_BLACK) _buf[idx] &= (uint8_t)~bit;
    else                    _buf[idx] |= bit;
}

void Canvas::fillRect(int x, int y, int w, int h, uint8_t color) {
    if (w <= 0 || h <= 0) return;
    for (int j = 0; j < h; j++)
        for (int i = 0; i < w; i++)
            drawPixel(x + i, y + j, color);
}

void Canvas::drawRect(int x, int y, int w, int h, uint8_t color) {
    if (w <= 0 || h <= 0) return;
    drawHLine(x, y, w, color);
    drawHLine(x, y + h - 1, w, color);
    drawVLine(x, y, h, color);
    drawVLine(x + w - 1, y, h, color);
}

void Canvas::drawHLine(int x, int y, int w, uint8_t color) {
    if (w <= 0) return;
    for (int i = 0; i < w; i++) drawPixel(x + i, y, color);
}

void Canvas::drawVLine(int x, int y, int h, uint8_t color) {
    if (h <= 0) return;
    for (int j = 0; j < h; j++) drawPixel(x, y + j, color);
}

void Canvas::invertRect(int x, int y, int w, int h) {
    if (w <= 0 || h <= 0) return;
    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            const int px = x + i, py = y + j;
            if (_clip && (px < _cx || py < _cy ||
                          px >= _cx + _cw || py >= _cy + _ch)) continue;
            if (px < 0 || py < 0 || px >= CANVAS_W || py >= CANVAS_H) continue;
            int nx, ny;
            epdMapLogicalToNative(px, py, &nx, &ny);
            if (nx < 0 || ny < 0 || nx >= EPD_NATIVE_W || ny >= EPD_NATIVE_H) continue;
            const uint32_t idx = (uint32_t)ny * EPD_ROW_BYTES + (uint32_t)(nx >> 3);
            _buf[idx] ^= (uint8_t)(0x80 >> (nx & 7));
        }
    }
}

void Canvas::drawBitmap1bpp(const uint8_t* bmp, int x, int y, int w, int h,
                            uint8_t fg, bool transparent, uint8_t bg) {
    if (!bmp || w <= 0 || h <= 0) return;
    const int stride = (w + 7) / 8;
    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            const uint8_t b = bmp[(size_t)j * stride + (i >> 3)];
            const bool on = (b >> (7 - (i & 7))) & 1;
            if (on)               drawPixel(x + i, y + j, fg);
            else if (!transparent) drawPixel(x + i, y + j, bg);
        }
    }
}

void Canvas::setClipRect(int x, int y, int w, int h) {
    _clip = true;
    _cx = x; _cy = y; _cw = w; _ch = h;
}

void Canvas::drawText(const char* utf8, int x, int baseline_y, int scale,
                      uint8_t color) {
    if (!utf8) return;
    int pen = x;
    const char* s = utf8;
    for (;;) {
        const uint32_t cp = utf8Next(s);
        if (cp == 0) break;
        fontDrawGlyph(*this, cp, pen, baseline_y, scale, color);
        pen += fontGlyphAdvance(cp, scale);
    }
}

int Canvas::textWidth(const char* utf8, int scale) {
    return fontTextWidth(utf8, scale);
}
