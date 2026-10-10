#pragma once
/*
 * ===========================================================================
 *  Pocket Reader -- hardware configuration
 *  ESP32-C3 (bare ESP32-C3-MINI-1 PCB  |  Seeed XIAO ESP32C3 breadboard)
 * ===========================================================================
 *
 *  One pin map serves BOTH boards. On the XIAO only 11 GPIOs are broken out
 *  (GPIO2,3,4,5,6,7,8,9,10,20,21), so GPIO0 and GPIO1 are simply not wired.
 *
 *  Signal     GPIO  XIAO pad  Dir  Notes
 *  -------------------------------------------------------------------------
 *  EPD_SCK     4     D2       out  SPI clock, mode 0
 *  EPD_MOSI    6     D4       out  SPI COPI
 *  EPD_CS      7     D5       out  active LOW
 *  EPD_DC     10     D10      out  0 = command, 1 = data
 *  EPD_RST     8     D8       out  active LOW
 *  EPD_BUSY    9     D9       in   HIGH = idle, LOW = busy
 *  BTN_UP      3     D1       in   active LOW
 *  BTN_DOWN    2     D0       in   active LOW
 *  BTN_MENU   20     D7       in   active LOW
 *  VBAT_ADC    5     D3       in   battery divider
 *  (free)      0,1,21              not on the XIAO header
 *  USB D- / D+ 18 / 19             native USB-Serial-JTAG, handled by the core
 *
 *  -------------------------------------------------------------------------
 *  STRAPPING PINS (ESP32-C3: GPIO2, GPIO8, GPIO9) -- read the notes below,
 *  they are the difference between "it boots" and "it bricks itself into the
 *  serial bootloader every time".
 *
 *   GPIO8  = EPD_RST.  GPIO8 must be HIGH at boot for normal SPI-flash boot.
 *            A 100k external pull-up holds it high; EPD_RST is active LOW and
 *            idles HIGH anyway, so the panel is not reset at power-on and the
 *            strapping requirement is satisfied by design.
 *
 *   GPIO9  = EPD_BUSY. Also the boot-mode strapping pin and must be HIGH at
 *            boot. EPD_BUSY idles HIGH on the SSD1680, so the requirement is
 *            satisfied by the panel itself; add a 100k pull-up so the level is
 *            defined even if the panel is unplugged or held in reset.
 *            XIAO CAVEAT: on the XIAO, GPIO9 is ALSO the on-board BOOT button.
 *            Pressing that button makes the firmware see "panel busy" until
 *            the BUSY timeout in epdBusyWait() expires (harmless: ~10 s of a
 *            frozen refresh, then the refresh is abandoned). Holding it while
 *            powering on drops the chip into the ROM download mode -- that is
 *            the expected way to flash the XIAO, not a bug.
 *
 *   GPIO2  = BTN_DOWN. Must be HIGH at boot (that is why the buttons need the
 *            100k pull-ups). DO NOT HOLD DOWN WHILE POWERING ON: the chip will
 *            boot into the ROM download mode instead of the firmware.
 *
 *  -------------------------------------------------------------------------
 *  JTAG: GPIO6 is MTCK and GPIO7 is MTDI on the ESP32-C3. EPD_MOSI takes GPIO6
 *  and EPD_CS takes GPIO7, so the JTAG interface is GIVEN UP on this board.
 *  Debug with USB-Serial-JTAG / USB CDC (see the note about Serial below).
 *
 *  -------------------------------------------------------------------------
 *  BUTTONS: all three are active LOW, with 100k external pull-ups to 3V3 and a
 *  100nF cap to GND for hardware debounce (the firmware still debounces in
 *  software, 25 ms).
 *
 *  -------------------------------------------------------------------------
 *  DEEP SLEEP WAKE: only BTN_UP (GPIO3) and BTN_DOWN (GPIO2) live in the RTC
 *  domain on this board and can wake the chip from deep sleep. BTN_MENU (GPIO20)
 *  is U0RXD, a normal digital pin -- it CANNOT wake the device. After the
 *  device sleeps, press UP or DOWN to wake it and then use MENU. The wake mask
 *  is exactly two pins: (1<<2)|(1<<3) -- there is no third wake source.
 *
 *  -------------------------------------------------------------------------
 *  VBAT_ADC = GPIO5. On the ESP32-C3, ADC1 is only GPIO0-4 and none of those
 *  are free on the XIAO, so the battery divider lands on GPIO5 = ADC2_CH0.
 *  Unlike the classic ESP32, the ESP32-C3 ADC2 has a single channel and is NOT
 *  in conflict with the WiFi driver, so it can genuinely be used from
 *  application code while the radio is on. power.cpp drives it through
 *  analogReadMilliVolts().
 *
 *  -------------------------------------------------------------------------
 *  SERIAL: GPIO20 (BTN_MENU) is U0RXD and GPIO21 (U0TXD) must stay
 *  unconnected, so UART0 is never used: platformio.ini sets
 *  -DARDUINO_USB_CDC_ON_BOOT=1 and all `Serial` output goes over USB-CDC.
 * ===========================================================================
 */

/* ------------------------------------------------------------------ */
/* E-paper panel                                                       */
/* ------------------------------------------------------------------ */
#define EPD_SCK     4
#define EPD_MOSI    6
#define EPD_CS      7
#define EPD_DC      10
#define EPD_RST     8
#define EPD_BUSY    9

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */
#define BTN_UP      3
#define BTN_DOWN    2
#define BTN_MENU    20

/* ------------------------------------------------------------------ */
/* Battery                                                             */
/* ------------------------------------------------------------------ */
#define VBAT_ADC    5

/* Deep-sleep wake mask: GPIO2 + GPIO3 only (see the notes above).
 *
 * NOTE: this is NOT the ESP32-classic ext1 mask. The ESP32-C3 has no
 * SOC_PM_SUPPORT_EXT_WAKEUP, so esp_sleep_enable_ext1_wakeup() does not exist
 * here; the mask goes to esp_deep_sleep_enable_gpio_wakeup() instead. */
#define BTN_WAKE_MASK   ((1ULL << BTN_DOWN) | (1ULL << BTN_UP))

/* ------------------------------------------------------------------ */
/* Panel geometry -- 2.13" 250x122 SSD1680 (GDEY0213B74 / WS V3)       */
/* ------------------------------------------------------------------ */
/* Native controller RAM: X axis 0..121 packed MSB-first into 16 bytes per
 * row, Y axis 250 rows  ->  16 * 250 = 4000 bytes framebuffer.          */
#define EPD_NATIVE_W     122
#define EPD_NATIVE_H     250
#define EPD_ROW_BYTES    ((EPD_NATIVE_W + 7) / 8)          /* 16  */
#define EPD_FB_SIZE      (EPD_ROW_BYTES * EPD_NATIVE_H)    /* 4000 */

/* SPI clock. 10 MHz is comfortably inside the SSD1680 spec and keeps the
 * breadboard wiring (dupont jumpers) reliable; raise to 20000000 if your
 * wires are short. */
#define EPD_SPI_HZ       10000000

/* ------------------------------------------------------------------ */
/* BUSY polarity                                                       */
/* ------------------------------------------------------------------ */
/* SSD1680 BUSY polaritesi. Datasheet (Rev 0.14, Table 5-2) BUSY'yi aktif-HIGH
 * tanimlar: HIGH = mesgul, LOW = bos. Bazi satici suruculeri tersini varsayar.
 * Yanlissa: multimetreyle olcun (README > "BUSY polaritesini 30 saniyede
 * dogrulama") ve bu degeri degistirin. */
#define EPD_BUSY_ACTIVE_HIGH  1   /* 1 = HIGH mesgul (datasheet), 0 = LOW mesgul */

/* Hard BUSY ceilings. If the panel does not release BUSY within these, the
 * refresh is abandoned with a loud error instead of hanging the device.
 * A full refresh of this panel takes roughly 2 s, a partial one ~0.3 s. */
#define EPD_BUSY_TIMEOUT_MS           5000
#define EPD_BUSY_TIMEOUT_PARTIAL_MS   2000

/* ------------------------------------------------------------------ */
/* Canvas rotation                                                     */
/* ------------------------------------------------------------------ */
/* The UI always draws on a LOGICAL canvas. The native controller RAM is
 * 122x250, which is portrait; rotating it 90 degrees gives the 250x122
 * landscape canvas the reader UI wants.
 *
 *   EPD_ROTATION = 90  -> canvas 250 wide x 122 tall  (default, landscape)
 *                   0  -> canvas 122 wide x 250 tall  (portrait)
 *                 180  -> canvas 122 x 250, upside down
 *                 270  -> canvas 250 x 122, landscape, other way round
 *
 * IF THE IMAGE COMES OUT FLIPPED, you do not need to touch the driver: just
 * flip EPD_MIRROR_X and/or EPD_MIRROR_Y below. Mirroring is applied in
 * LOGICAL space *before* the rotation, so EPD_MIRROR_X swaps left/right as
 * you see it on the screen, not as it sits in RAM. The whole mapping is the
 * single inline function epdMapLogicalToNative() in include/epd.h -- that is
 * the one and only place to change if you need a different transform.        */
#define EPD_ROTATION   90
#define EPD_MIRROR_X   0    /* 1 = mirror the visible image horizontally */
#define EPD_MIRROR_Y   0    /* 1 = mirror the visible image vertically   */

#if   (EPD_ROTATION == 0) || (EPD_ROTATION == 180)
  #define CANVAS_W  EPD_NATIVE_W   /* 122 */
  #define CANVAS_H  EPD_NATIVE_H   /* 250 */
#elif (EPD_ROTATION == 90) || (EPD_ROTATION == 270)
  #define CANVAS_W  EPD_NATIVE_H   /* 250 */
  #define CANVAS_H  EPD_NATIVE_W   /* 122 */
#else
  #error "EPD_ROTATION must be one of 0, 90, 180, 270"
#endif

/* ------------------------------------------------------------------ */
/* Framebuffer colours                                                 */
/* ------------------------------------------------------------------ */
/* Raw SSD1680 RAM bit: 1 = WHITE, 0 = BLACK (the vendor driver clears the
 * panel by filling RAM with 0xFF). The Canvas API keeps that convention:
 * COL_BLACK == 0, COL_WHITE == 1. */
#define COL_BLACK   0
#define COL_WHITE   1

/* ------------------------------------------------------------------ */
/* UI layout (logical pixels)                                          */
/* ------------------------------------------------------------------ */
#define UI_HEADER_H     14   /* header band, underlined by a 2 px rule */
#define UI_STATUS_H     12   /* bottom status band, 1 px rule above   */
#define UI_MARGIN       3

/* ------------------------------------------------------------------ */
/* Storage paths                                                       */
/* ------------------------------------------------------------------ */
#define FS_MOUNT_POINT   "/littlefs"
#define BOOKS_DIR        "/books"
#define FONT_DIR         "/fonts"
#define CACHE_DIR        "/cache"
#define DEFAULT_FONT     "/fonts/book.epf"

/* ------------------------------------------------------------------ */
/* Defaults (overridable at runtime via NVS "pocketrdr")               */
/* ------------------------------------------------------------------ */
#define DEF_SLEEP_SEC           60    /* idle timeout before deep sleep   */
#define DEF_FULL_REFRESH_EVERY  20    /* partials before a full refresh   */
#define DEF_FONT_SCALE          1
#define DEF_PARTIAL_ENABLED     1

/* Low-battery guard: below this the device refuses to enter button-wake deep
 * sleep (a wake loop would drain what is left of the cell). */
#define BATTERY_LOW_MV          3400

/* ------------------------------------------------------------------ */
/* Firmware version (set from platformio.ini)                          */
/* ------------------------------------------------------------------ */
#ifndef POCKET_READER_VERSION
  #define POCKET_READER_VERSION "1.0.0"
#endif
