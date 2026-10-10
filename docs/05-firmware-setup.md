> Türkçe sürüm: [05-firmware-setup.tr.md](05-firmware-setup.tr.md)

# 05 · Firmware Setup

## 1 · Requirements

| Tool | Version | Note |
|---|---|---|
| Python | 3.9+ | For PlatformIO and the `tools/` scripts |
| PlatformIO | 6.x | The VS Code extension or `pip install platformio` |
| USB-C cable | **data-capable** | Some cables are for charging only — the most common mistake |

Installing PlatformIO:

```bash
# Option A: command line
pip install -U platformio

# Option B: VS Code
# Install "PlatformIO IDE" from the extension marketplace
```

The first `pio run` invocation downloads Espressif's toolchain (~250 MB). It is a
one-time thing.

---

## 2 · Building and flashing

```bash
cd firmware

# Easy build (Seeed XIAO ESP32-C3)
pio run -e xiao -t upload

# PCB build (ESP32-C3-MINI-1)
pio run -e esp32-c3-devkitm-1 -t upload

# Build only (without flashing)
pio run -e xiao
```

PlatformIO defines two environments and both compile **the same source code**;
the difference is only the board definition and (if present) the `BOARD_XIAO`
macro.

### If flashing fails

The ESP32-C3 uses USB-Serial-JTAG; most of the time it enters download mode
automatically. If it doesn't:

1. Hold down the **BOOT** button on the XIAO
2. Press and release **RESET**
3. Release BOOT
4. Repeat the `pio run -e xiao -t upload` command

> ⚠️ The GPIO9 = `EPD_BUSY` line is in parallel with the BOOT button on the XIAO.
> Pressing BOOT makes the panel appear "busy" — the firmware falls through to a
> timeout, harmless. But if you hold it down at startup the device enters download
> mode (the desired behaviour).

---

## 3 · Filesystem (fonts and books)

The fonts and books are not inside the firmware, they are in the LittleFS
partition. A separate upload step is needed:

```bash
# 1. Generate the font (see docs/06)
cd ../tools
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
        --size 14 --out ../firmware/data/fonts/reader-14.epf

# 2. Upload the filesystem to the device
cd ../firmware
pio run -t uploadfs
```

The structure of the `data/` folder:

```
firmware/data/
├── fonts/
│   ├── reader-14.epf        (generated with fontgen.py)
│   └── reader-20.epf        (optional, for large text)
└── books/
    └── ornek-turkce.epr     (generated with tools/make_sample_books.py)
```

`firmware/data/fonts/*.epf` **is not included in the repo** (it's in
`.gitignore`); each user generates their own font. This is deliberate: font files
are licensed and depend on the user's choice.

> ⚠️ `uploadfs` **erases and rewrites the entire filesystem.** Books you uploaded
> to the device over Wi-Fi are lost. Do the book upload over Wi-Fi; use `uploadfs`
> only when updating the font.

---

## 4 · Serial port and debugging

```bash
pio device monitor -b 115200
```

The console runs over **USB-Serial-JTAG** (`ARDUINO_USB_CDC_ON_BOOT=1`). UART0
(GPIO20/21) is deliberately left silent because those pins are used for the
button/display.

Typical output you will see:

```
Pocket Reader 1.0.0
LittleFS: 3.0 MB total, 2.8 MB free
Font: /fonts/reader-14.epf — 342 glyph, 14 px
Buttons ready (GPIO3, GPIO2, GPIO20)
Battery: 3.94 V (78%)
Wake: ext1 (GPIO3) — from deep sleep
Book: ornek-turkce.epr — page 12/48
```

### Debug level

`CORE_DEBUG_LEVEL` in `platformio.ini`:
`0` = silent · `1` = error · `2` = warning (default) · `3` = info ·
`4` = verbose · `5` = everything

Use `4` when debugging SPI communication.

---

## 5 · Changing the settings

Almost all settings are in `firmware/include/config.h`.

### If the screen comes out inverted/flipped

```c
#define EPD_ROTATION   90      // 0 / 90 / 180 / 270
#define EPD_MIRROR_X   0       // 0 or 1
#define EPD_MIRROR_Y   0       // 0 or 1
```

If the image is in the wrong orientation, find the right combination by trying
these three lines — the number of combinations is limited (8 possibilities). You
don't need to touch the rest of the code; the rotation is done in a single inline
function.

### Changing a pin

```c
#define EPD_SCK    4
#define EPD_MOSI   6
// ...
```

> ⚠️ When changing a pin remember these constraints: for the buttons to be able to
> wake from sleep they must be **in the RTC domain (GPIO0–5)**; the strapping pins
> (GPIO2, GPIO8, GPIO9) must be HIGH at startup. Details: `docs/00` §2.

### Sleep duration and refresh frequency

```c
#define DEFAULT_SLEEP_SEC          60   // sleep after inactivity
#define DEFAULT_FULL_REFRESH_EVERY  20   // after how many partial refreshes a full refresh
```

### Turkish interface

English is the default. To build the Turkish interface, pass the `LANG_TR` build
flag:

```bash
pio run -e xiao -t upload --build-flag="-DLANG_TR=1"
```

---

## 6 · Switching to GxEPD2 (optional)

If you want to use a mature library instead of our own SSD1680 driver:

1. Add to `platformio.ini`:
   ```ini
   lib_deps = zinggjm/GxEPD2@^1.6.0
   ```
2. In `src/epd.cpp`, redirect the `Canvas` class's drawing methods to GxEPD2's
   `GxEPD2_213_GDEY0213B74` driver.
3. Replace the `epdFullRefresh()` / `epdPartialRefresh()` calls with
   `display.display(false)` / `display.displayWindow(...)`.

**The cost:** ~30 KB of flash, some of the control over the partial refresh
window, and the transparency in `epd_lut.h`. **The gain:** ease of switching
between panel variants and community-tested code.

---

## 7 · Common build errors

| Error | Cause | Solution |
|---|---|---|
| `fatal error: epd_lut.h: No such file` | The file has not been created | Check whether `src/epd_lut.h` exists |
| `'EPD_FB_SIZE' undeclared` | `config.h` not included | `#include "config.h"` at the top of `epd.cpp` |
| `region 'iram0_0_seg' overflowed` | Flash/RAM partition wrong | Check `board_build.partitions = default.csv` |
| `A fatal error occurred: Failed to connect` | It doesn't enter download mode | The BOOT/RESET sequence in §2 |
| `LittleFS mount failed` | The filesystem was never uploaded | `pio run -t uploadfs` |
| "Font not found" screen | `.epf` missing | Run `tools/fontgen.py` then `uploadfs` |

**This project was not put through a compiler while this repo was being
prepared.** The first `pio run` invocation may need small fixes similar to the
above; open the ones you find as an issue or fix them and send a PR.

---

## 8 · Post-setup verification

```bash
# Is the device up?
cd tools
python3 send.py --status
```

Expected output:

```json
{"fw":"1.0.0","heap":245000,"free":2870000,"batt_mv":3940,"batt_pct":78,"uptime":142}
```

If the device doesn't respond it is most likely asleep — press a page button or
toggle the switch off and on.

---

Back: [04 · Assembly](04-assembly.md) · Next: [06 · Books and Fonts](06-books-and-fonts.md)
