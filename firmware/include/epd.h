#pragma once
#include <Arduino.h>
#include "config.h"

/*
 * ===========================================================================
 *  epd.h -- SSD1680 2.13" e-paper driver + logical Canvas
 * ===========================================================================
 *
 *  Panel: 250 x 122, controller RAM 122 (X) x 250 (Y), 16 bytes per row
 *  packed MSB-first, 1 = white. Framebuffer = 16 * 250 = 4000 bytes.
 *
 *  The UI never sees native RAM. It draws on a LOGICAL canvas (250x122 by
 *  default) and every pixel goes through epdMapLogicalToNative() below.
 * ===========================================================================
 */

/* ---------------------------------------------------------------------------
 * The one and only rotation/mirror mapping. If the picture is rotated or
 * flipped on your panel, this is the function to edit -- nothing else in the
 * firmware knows about the transform.
 *
 * Logical canvas (lx, ly) in [0,CANVAS_W) x [0,CANVAS_H)
 *   -> native controller RAM (nx, ny) in [0,122) x [0,250)
 *
 * Mirrors are applied in LOGICAL space first, so EPD_MIRROR_X always flips the
 * image left/right as the user sees it, independent of the rotation.
 * ------------------------------------------------------------------------- */
static inline void epdMapLogicalToNative(int lx, int ly, int* nx, int* ny) {
    const int mx = EPD_MIRROR_X ? (CANVAS_W - 1 - lx) : lx;
    const int my = EPD_MIRROR_Y ? (CANVAS_H - 1 - ly) : ly;

#if   EPD_ROTATION == 0
    /* Portrait: native axes == logical axes. */
    *nx = mx;
    *ny = my;
#elif EPD_ROTATION == 90
    /* Landscape: the 250-px native Y axis becomes the logical X axis. */
    *nx = my;
    *ny = mx;
#elif EPD_ROTATION == 180
    *nx = (EPD_NATIVE_W - 1) - mx;
    *ny = (EPD_NATIVE_H - 1) - my;
#elif EPD_ROTATION == 270
    *nx = (EPD_NATIVE_W - 1) - my;
    *ny = (EPD_NATIVE_H - 1) - mx;
#else
  #error "EPD_ROTATION must be one of 0, 90, 180, 270"
#endif
}

/* =========================================================================
 *  Canvas -- the 4000-byte framebuffer with a logical coordinate system.
 *  Colours: COL_BLACK (0) = ink, COL_WHITE (1) = paper.
 * ========================================================================= */
class Canvas {
public:
    Canvas();

    /* Bind an external buffer (must be EPD_FB_SIZE bytes). */
    void begin(uint8_t* buffer);

    uint8_t* buffer()            { return _buf; }
    const uint8_t* buffer() const { return _buf; }
    int  width()  const          { return CANVAS_W; }
    int  height() const          { return CANVAS_H; }

    void clear(uint8_t color);

    void drawPixel(int x, int y, uint8_t color);

    void fillRect(int x, int y, int w, int h, uint8_t color);
    void drawRect(int x, int y, int w, int h, uint8_t color);
    void drawHLine(int x, int y, int w, uint8_t color);
    void drawVLine(int x, int y, int h, uint8_t color);
    void invertRect(int x, int y, int w, int h);

    /* 1bpp bitmap, row-major, MSB-first, w bits per row, 1 = ink.
     * If `transparent` is true, 0-bits are skipped instead of painted in
     * `bg`. `fg` is the ink colour (normally COL_BLACK). */
    void drawBitmap1bpp(const uint8_t* bmp, int x, int y, int w, int h,
                        uint8_t fg, bool transparent = true,
                        uint8_t bg = COL_WHITE);

    /* Text through the font module. `x` is the pen start, `baseline_y` the
     * baseline. Implemented in epd.cpp so this header stays independent of
     * the font module (no circular include). */
    void drawText(const char* utf8, int x, int baseline_y, int scale = 1,
                  uint8_t color = COL_BLACK);
    int  textWidth(const char* utf8, int scale = 1);

    void setInk(uint8_t color)   { _ink = color; }
    uint8_t ink() const          { return _ink; }

    /* Clip rectangle -- all drawing is clipped to it while active. */
    void setClipRect(int x, int y, int w, int h);
    void clearClip()             { _clip = false; }

private:
    uint8_t* _buf;
    uint8_t  _ink;
    bool     _clip;
    int      _cx, _cy, _cw, _ch;
};

/* =========================================================================
 *  Driver API
 * ========================================================================= */
extern Canvas canvas;

/* The 4000-byte framebuffer the Canvas draws into. */
uint8_t* epdFramebuffer();

/* Bring up SPI + GPIOs, hardware-reset the panel, load the vendor init
 * register sequence and the full-quality waveform. Leaves the panel awake
 * and the framebuffer untouched (call epdClear() to fill it). */
bool epdInit();

/* SPI + pin release is a no-op in the Arduino core, but we do stop the SPI
 * transaction; kept for symmetry and future power gating. */
void epdSpiRelease();

/* Deep-sleep register 0x10 with A[1:0]=01 -> Deep Sleep Mode 1: about 1 uA,
 * and the RAM contents (the image) are RETAINED. Call this immediately before
 * esp_deep_sleep_start().
 *
 * IMPORTANT: deep sleep is exited ONLY by a hardware reset. A software reset
 * (0x12) does not wake the panel. epdInit() performs a hardware reset on
 * every boot, and epdFullRefresh()/epdPartialRefresh() do one automatically
 * if they are called after epdSleep(), so the normal flow is safe. */
void epdSleep();

/* RST pulse exactly as in the vendor driver (20 ms high, 2 ms low, 20 ms high). */
void epdHwReset();

/* Wait for BUSY to be released. The polarity is set by EPD_BUSY_ACTIVE_HIGH in
 * config.h and the wait always has a hard timeout: on timeout it prints the
 * observed pin level, names the likely cause and returns false, so a wrong
 * polarity or a missing panel can never hang the device. */
bool epdBusyWait(uint32_t timeout_ms = EPD_BUSY_TIMEOUT_MS);

/* Fill the framebuffer with black (true) or white (false) and mark it dirty. */
void epdClear(bool black);

/* Full refresh: re-runs the vendor init registers, loads the full-quality
 * waveform, writes the whole framebuffer to BOTH RAM banks (0x24 new, 0x26
 * previous) and runs the update sequence 0x22=0xC7 / 0x20. Clears ghosting;
 * takes ~2 s and flashes the panel. */
void epdFullRefresh();

/* Partial refresh: loads the fast waveform, enables RAM ping-pong (0x37),
 * and repaints ONLY the dirty rectangle (byte-aligned in native X). Uses the
 * 0x24 buffer for the new frame and the 0x26 buffer for the previous frame so
 * the controller can compute the difference. */
void epdPartialRefresh();

/* Accumulate a dirty rectangle in LOGICAL canvas coordinates. The union of
 * all calls until the next refresh is used as the partial window; a full
 * canvas rect forces a full-panel partial. */
void epdDirty(int x, int y, int w, int h);

/* Set an explicit partial window (logical coords) instead of accumulating. */
void epdSetPartialWindow(int x, int y, int w, int h);

/* Forget the dirty rectangle (called by the refresh functions). */
void epdClearDirty();

/* True if anything has been marked dirty since the last refresh. */
bool epdIsDirty();
