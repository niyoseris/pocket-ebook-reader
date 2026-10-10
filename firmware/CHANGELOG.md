# Changelog — Pocket Reader

This project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-10-09

First release. Complete, ready-to-compile firmware, not tested on hardware.

### Added
- **Configurable BUSY polarity**: `EPD_BUSY_ACTIVE_HIGH` (default 1, datasheet
  Rev 0.14 Table 5-2). `epdBusyWait()` has a fixed timeout
  (5 s full refresh, 2 s partial); on timeout it logs the observed pin level,
  says the polarity may be wrong and returns `false` — the device never hangs.
  README has a "Verifying BUSY polarity in 30 seconds" section.
- **Panel deep sleep** `0x10 = 0x01` (Mode 1, ~1 µA, RAM preserved). That exit is
  possible only via a hardware reset is documented explicitly in `include/epd.h`
  and `README.md`; the driver automatically runs the HWRESET + init sequence on
  the first refresh after sleep.
- The `data/fonts/` folder (for font generation) and `tools/fontgen.py`.

- **SSD1680 driver** (`src/epd.cpp`, `src/epd_lut.h`): our own SPI driver for the
  2.13" 250x122 panel. The real init sequence and LUT tables taken from the
  Waveshare reference driver (MIT). Full + partial refresh, dirty-rectangle
  tracking. The panel's typical draw is noted as 3.5 mA (VCI = 3.0 V, 10.5 mW).
- **Rotation layer**: a 250x122 logical canvas over the 4000-byte native RAM.
  Configured with `EPD_ROTATION` / `EPD_MIRROR_X` / `EPD_MIRROR_Y`.
- **Font engine** (`src/font.cpp`): the `.epf` binary font format loaded from
  LittleFS at runtime, Turkish character support, x1/x2 scaling, line wrapping.
- **`.epr` book parser** (`src/book.cpp`): header reading, a streaming text
  reader, pagination and a `/cache/*.idx` page-index cache (stale-cache detection
  + regeneration).
- **Buttons** (`src/buttons.cpp`): 25 ms debounce, 700 ms long press, detection
  of the held key after waking from deep sleep.
- **Power management** (`src/power.cpp`): battery measurement over GPIO5
  (ADC2_CH0) (median + mean), Li-ion discharge curve, deep sleep via `ext1` from
  GPIO2/GPIO3 (UP/DOWN), state kept in RTC.
- **Storage** (`src/storage.cpp`): LittleFS + `Preferences` (NVS) settings.
- **WiFi transfer** (`src/wifi_xfer.cpp`): STA (15 s) → AP `PocketReader-XXXX`
  fallback WebServer, `GET /`, `POST /upload`, `GET /list`, `POST /delete`,
  `POST /wifi`, `GET /status`. Dependency-free JSON and multipart.
- **Interface** (`src/ui.cpp`): SPLASH, LIBRARY, READER, MENU, WIFI, ERROR, INFO,
  SLEEP screens; English texts by default (`include/i18n.h`; `-DLANG_TR` for
  Turkish).
- **Direct action from deep sleep**: no splash is shown on wake; depending on the
  key held, the next/previous page or the library is drawn directly (the core UX
  detail).
- `tools/fontgen.py`: a TTF → `.epf` converter.

### Known gaps
- Not tested on hardware (see README, "What has not been tested").
- The MENU key (GPIO20) **cannot wake** the device from deep sleep because it is
  not in the RTC domain; UP or DOWN must be used to wake it.
- GPIO6 is given up as JTAG (MTCK); debugging is done over UART/USB-CDC.
