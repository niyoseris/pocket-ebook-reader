# Changelog

This project uses [Semantic Versioning](https://semver.org/).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### To be added
- Build and measurement results on real hardware
- Illustrated assembly guide (`docs/04`)
- Generated Gerber files (`hardware/pcb/`)

---

## [1.0.0] — 2026-10-09

First release. The design and documentation are complete; **not tested on
physical hardware.**

### Added

**Hardware**
- Full schematic (SVG): USB-C input, MCP73831 charging, TPS63020 3.3 V
  buck-boost, ESP32-C3-MINI-1, 24-pin e-paper FPC, buttons, battery sensing
- Block diagram and breadboard wiring diagram
- `gen_netlist.py`: `connections.csv` (170 connections, 39 nets, 64 parts)
  generated from a single source, and a KiCad netlist
- `pinouts.md`: pin tables verified verbatim from official datasheets, with
  source URLs
- Parametric OpenSCAD case (62 × 32 × 13 mm) — the outer dimensions are derived
  from the panel glass
- Two build tiers: breadboard with ready-made modules and a custom PCB

**Firmware (ESP32-C3, Arduino C++ / PlatformIO)**
- SSD1680 driver (`src/epd.cpp`, `src/epd_lut.h`): our own SPI driver for the
  2.13" 250×122 panel; init, full refresh, partial refresh with dirty-rectangle
  tracking, deep sleep; the vendor's real init sequence and LUT tables (MIT),
  with source and licence attributed; the panel's typical draw noted as 3.5 mA
  (VCI = 3.0 V, 10.5 mW)
- **Configurable BUSY polarity:** `EPD_BUSY_ACTIVE_HIGH` (default 1, datasheet
  Rev 0.14 Table 5-2); `epdBusyWait()` has a fixed timeout (5 s full refresh,
  2 s partial) and on timeout logs the observed pin level, warns that the
  polarity may be wrong, and returns `false` — the device never hangs
- **Panel deep sleep** `0x10 = 0x01` (Mode 1, ~1 µA, RAM preserved); exit is
  possible only via a hardware reset, documented in `include/epd.h` and
  `README.md`; the driver runs HWRESET + the init sequence automatically on the
  first refresh after sleep
- **Rotation layer:** a 250×122 logical canvas over the 4000-byte native RAM,
  configured with `EPD_ROTATION` / `EPD_MIRROR_X` / `EPD_MIRROR_Y`
- Runtime-loaded `.epf` font system (`src/font.cpp`; full Turkish coverage, ×1/×2
  scaling, line wrapping); the `data/fonts/` folder and `tools/fontgen.py`
- `.epr` book format (`src/book.cpp`): header parsing, a streaming text reader,
  pagination, and a `/cache/*.idx` page-index cache with stale-cache detection
  and regeneration
- Interface (`src/ui.cpp`): SPLASH, LIBRARY, READER, MENU, WIFI, ERROR, INFO and
  SLEEP screens
- 3 buttons (`src/buttons.cpp`): 25 ms debounce, 700 ms long press, and
  pressed-key detection after waking from deep sleep
- Deep sleep + `ext1` wake from GPIO2/GPIO3 (UP/DOWN) + **smart wake that skips
  the boot screen** (it draws the next/previous page, or the library, directly
  according to the key held — a core UX detail)
- Power management (`src/power.cpp`): battery measurement over GPIO5 (ADC2_CH0,
  median + mean), Li-ion discharge curve, and RTC state kept across sleep
- Storage (`src/storage.cpp`): LittleFS + `Preferences` (NVS) settings
- Wi-Fi transfer (`src/wifi_xfer.cpp`): STA (15 s) → AP `PocketReader-XXXX`
  fallback WebServer, `GET /`, `POST /upload`, `GET /list`, `POST /delete`,
  `POST /wifi`, `GET /status`; dependency-free JSON and multipart
- English/Turkish interface (`include/i18n.h`; English by default, `-DLANG_TR`
  for Turkish)
- `tools/fontgen.py`: TTF → `.epf` converter

**Tools (Python)**
- `epub2epr.py` — EPUB 2/3 → `.epr`, standard library only
- `fontgen.py` — TTF/OTF → `.epf`, with Pillow, Turkish coverage
- `send.py` — upload, list, delete, Wi-Fi settings, folder batch processing
- `make_sample_books.py` — sample and stress-test books
- `unittest` test suite (`.epr` round-trip, small EPUB generator)

**Documentation**
- `docs/00`–`09`: architecture, BOM, schematic, PCB, assembly, firmware,
  books/fonts, power management, troubleshooting, roadmap
- `README.md`

**CI**
- GitHub Actions: building both hardware environments, Python tests, netlist
  consistency check, SVG validity check

### Fixed (errors found during verification)

**Fifteen errors** were found and fixed before this release was published —
none of them on real hardware, all of them by pointing documentation,
arithmetic and cross-checks at the design. They fall into three groups.

#### 1. Datasheet and design errors (6)

Found by reading the official datasheets against assumptions that had never
been checked:

| # | Finding | Initial design | Correct |
|---|---|---|---|
| 1 | TPS63020 package | VSON-10 | **VSON-14 (DSJ), 3 × 4 mm** |
| 2 | TPS63900 compatibility | "pin compatible" | **Not compatible** — the layout must be redrawn |
| 3 | Feedback resistors | 560 kΩ / 100 kΩ | **1 MΩ / 180 kΩ** (datasheet Table 3) |
| 4 | GPIO8 strapping | Must be HIGH at boot | **Free during SPI boot** (Table 4-3) |
| 5 | Panel supply | 3.3 V + capacitor only | **Also needs an external ±15 V boost** (GDR/RESE pins) |
| 6 | Panel BUSY polarity | HIGH = idle | Datasheet **HIGH = busy** — made configurable, a timeout added |

#### 2. Geometry and mechanical errors (4)

Found by validators written around the placement data — a part that overlaps a
mounting hole, or does not fit inside its own case, is invisible in a schematic:

| # | Finding | Symptom it would have caused | Fix |
|---|---|---|---|
| 7 | Body dimension | The case was 58 × 30 mm; the panel **glass is 59.2 × 29.2 mm** and cannot be assembled into it | **62 × 32 mm**, derived from the glass: glass + 2 × 1.4 mm bezel |
| 8 | FPC passage on the wrong case edge | The case cut the ribbon channel into the −Y edge while J2 sits on the PCB's +Y edge, so the FPC had to wrap the whole board | Channel moved to +Y. Caught by the drawing generator's geometry check |
| 9 | Mounting holes vs courtyards | The four M1.6 mounting holes overlapped the courtyards of `BT1`, `SW4`, `R13` and `R15` | The four hole zones are now reserved keep-out regions in `gen_placement.py`, and the placer refuses to put anything there |
| 10 | Buttons did not fit | Three 5 mm buttons cannot fit in the 15 mm of edge left between two mounting holes | Buttons reduced to 4.5 mm and re-spaced |

#### 3. Software and integration errors (2)

Found by cross-checks between the two halves of a format. Both were **silent** —
the device boots, nothing crashes, but the result would have been broken:

| # | Finding | Symptom | Fix |
|---|---|---|---|
| 11 | The `.epr` converter was deleting every paragraph end (`0x0A`) | **Every converted book** appeared as a single long paragraph; only the chapter ends remained | The unconditional `_trim_trailing_breaks()` call inside `TextBuilder.add_block` was restricted to run only at chapter openings. 6 new regression tests were added |
| 12 | In the `.epf` font, the reference point of the `top` field differed on the two sides | The firmware thought `top` was measured from the baseline; the error **varied per glyph**, so the text was scattered vertically (`.` 13 px up, `A` 9 px down) | `y0 = baseline_y - (ascent - top) * scale`. The `font.h` comments were clarified; `tools/tests/test_epf_interop.py` verifies with boundary widths (9/12/13/17 px) that both sides apply the same rule |

Error 12 arose from two different agents writing the two halves of the same
binary format — which is why `test_epf_interop.py` now parses the firmware source
at runtime and tests **the other side's** rule rather than its own assumption.

#### 4. Errors only a compiler could find (3)

These surfaced the first time the firmware was actually built, in CI. Nothing
else would have found them — not review, not reading the datasheet, not a test.
The project had been documented for weeks as "never compiled", which is exactly
the state they were hiding in.

| # | Finding | What it did | Fix |
|---|---|---|---|
| 13 | `BTN_UP`, `BTN_DOWN` and `BTN_MENU` were defined **twice**: as pin macros in `config.h` and as enum members in `buttons.h` | The preprocessor rewrote the enum members into numbers, so the enum did not parse and `buttons.cpp` did not compile at all | Pins keep the `BTN_` prefix; the button events are now `EV_UP` / `EV_DOWN` / `EV_MENU` / `EV_ANY_WAKE`. Two naming spaces, because they are two different things |
| 14 | The whole deep-sleep wake path was written against the **ESP32-classic ext1 API** | `SOC_PM_SUPPORT_EXT_WAKEUP` is undefined for the ESP32-C3, so `esp_sleep_enable_ext1_wakeup()`, `esp_sleep_get_ext1_wakeup_status()` and `ESP_SLEEP_WAKEUP_EXT1` are all absent. The C3 wakes through a separate GPIO deep-sleep block with its own entry points and its own wakeup cause | Switched to `esp_deep_sleep_enable_gpio_wakeup()`, `esp_sleep_get_gpio_wakeup_status()` and `ESP_SLEEP_WAKEUP_GPIO`. The `ESP_EXT1_WAKEUP_ANY_LOW` compatibility shim was deleted — it was papering over a naming difference on an API this chip never had |
| 15 | `docs/04` told easy-build readers that **external pull-ups were not needed** | IDF's GPIO wakeup does arm internal pull resistors, but its own note *strongly recommends* external ones for a low-level wakeup, and warns that internal and external together interfere. The failure mode is the unpleasant one: the device wakes intermittently | The three 100 kΩ resistors are now a required line in the easy build's bill of materials, with the failure mode stated plainly |

The power budget calculation was also fixed: the first design said
"1,300,000 pages per page turn"; the correct one is a realistic model in which
**awake time dominates** (~25 hours of continuous reading, 12 months standby).

### Known limitations

- Not tested on physical hardware
- **13 pin numbers unverified**: USB-C receptacle, USBLC6-2SC6, Si1308EDL
- The panel's external boost circuit not tested
- The firmware was not put through a compiler while this repository was being
  prepared
- No Turkish hyphenation-based word splitting
- The MENU button cannot wake the device from sleep (GPIO20 is not in the RTC
  domain)
- No frontlight (not available at this panel size)

---

## Version numbering policy

- **MAJOR** — a backward-incompatible change in the `.epr` or `.epf` format, a
  change in the pin map
- **MINOR** — a new feature, a new hardware variant, a new tool
- **PATCH** — a bug fix, a documentation fix, a value fix

Hardware revisions are additionally marked as `Rev X.Y` on the schematic.
