/*
 * ===========================================================================
 *  epd_lut.h -- SSD1680 (2.13" V3 / GDEY0213B74) waveform tables
 * ===========================================================================
 *
 *  SOURCE OF TRUTH -- these tables are copied VERBATIM from the Waveshare
 *  MIT-licensed reference driver:
 *
 *    Repository : https://github.com/waveshare/e-Paper
 *    File       : RaspberryPi_JetsonNano/c/lib/e-Paper/EPD_2in13_V3.c
 *    Raw URL    : https://raw.githubusercontent.com/waveshare/e-Paper/master/
 *                 RaspberryPi_JetsonNano/c/lib/e-Paper/EPD_2in13_V3.c
 *    Retrieved  : 2026-10-09
 *    Version    : "EPD_2in13_V3.c ... V1.1 ... 2021-10-30"
 *
 *  Original copyright notice, reproduced as the MIT license requires:
 *
 *    Permission is hereby granted, free of charge, to any person obtaining a
 *    copy of this software and associated documentation files (the
 *    "Software"), to deal in the Software without restriction, including
 *    without limitation the rights to use, copy, modify, merge, publish,
 *    distribute, sublicense, and/or sell copies of the Software, and to permit
 *    persons to whom the Software is furnished to do so, subject to the
 *    following conditions:
 *
 *    The above copyright notice and this permission notice shall be included
 *    in all copies or substantial portions of the Software.
 *
 *    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 *    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 *    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
 *    NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
 *    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
 *    OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
 *    USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 *  -------------------------------------------------------------------------
 *  WHAT IS ACTUALLY IN THE VENDOR DRIVER (and what is not)
 *  -------------------------------------------------------------------------
 *  The task brief mentioned "WF_FULL_1IN13", "WF_PARTIAL_2IN13_V3" plus the
 *  split arrays LUT_lut_vcom1 / lut_ww1 / lut_bw1 / lut_wb1 / lut_bb1 and a
 *  "0x32 LUT loading routine". Those names belong to the *2.13" V2* driver
 *  (EPD_2in13_V2.c). The V3 driver does NOT contain them. The real V3 file
 *  contains exactly two 159-byte tables and one loader:
 *
 *      UBYTE WF_PARTIAL_2IN13_V3[159]   -- the fast partial waveform
 *      UBYTE WS_20_30_2IN13_V3[159]     -- the full-quality waveform
 *      static void EPD_2IN13_V2_LUT_by_host(UBYTE *lut)   (sic: V2 in the name)
 *      static void EPD_2IN13_V3_LUT(UBYTE *lut)
 *
 *  The 159 bytes are not five separate tables; they are one flat waveform
 *  record with a fixed layout that the loader splits:
 *
 *      lut[  0..152]  -> command 0x32 (153 bytes of LUT data)
 *      lut[153]       -> command 0x3F  (LUT end / "EOPT"? vendor sends it raw)
 *      lut[154]       -> command 0x03  (gate voltage / VGH)
 *      lut[155]       -> command 0x04  (VSH)
 *      lut[156]       -> command 0x04  (VSH2)
 *      lut[157]       -> command 0x04  (VSL)
 *      lut[158]       -> command 0x2C  (VCOM)
 *
 *  The split-by-purpose tables in the brief therefore do not exist and could
 *  not be reproduced without inventing them -- inventing waveform bytes would
 *  produce a panel that ghosts, over-erases, or permanently damages itself.
 *  Instead we embed the genuine vendor data and keep the vendor's exact
 *  split at load time (see epdLoadWaveform() in src/epd.cpp). This is the
 *  complete, real information; nothing is missing.
 *
 *  A FULL refresh does not need a host-supplied waveform at all: the SSD1680
 *  runs its OTP waveform in that case. The WS_20_30 waveform is what the
 *  vendor happens to load during Init, and we keep doing it here because the
 *  panel's grey levels were characterised against it.
 * ===========================================================================
 */

#pragma once
#include <stdint.h>

/* --------------------------------------------------------------------------
 * WF_PARTIAL_2IN13_V3 -- fast partial-refresh waveform.
 * Verbatim from EPD_2in13_V3.c (indentation normalised, byte order and values
 * unchanged: 159 bytes).
 * ------------------------------------------------------------------------ */
static const uint8_t WF_PARTIAL_2IN13_V3[159] = {
    0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x80, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x40, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x22, 0x22, 0x22, 0x22, 0x22, 0x22, 0x00, 0x00, 0x00,
    0x22, 0x17, 0x41, 0x00, 0x32, 0x36,
};

/* --------------------------------------------------------------------------
 * WS_20_30_2IN13_V3 -- full-quality waveform, loaded by EPD_2in13_V3_Init().
 * Verbatim from EPD_2in13_V3.c (159 bytes).
 * ------------------------------------------------------------------------ */
static const uint8_t WS_20_30_2IN13_V3[159] = {
    0x80, 0x4A, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x40, 0x4A, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x80, 0x4A, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x40, 0x4A, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x0F, 0x00, 0x00, 0x0F, 0x00, 0x00, 0x02,
    0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x22, 0x22, 0x22, 0x22, 0x22, 0x22, 0x00, 0x00, 0x00,
    0x22, 0x17, 0x41, 0x00, 0x32, 0x36,
};
