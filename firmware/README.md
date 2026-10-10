# Pocket Reader — firmware

An open-source e-ink ebook reader based on the ESP32-C3.
2.13" 250×122 SSD1680 panel, three keys, Li-ion cell, book transfer over WiFi.

The panel image is preserved in deep sleep; when the device wakes it draws the
requested page directly, **showing no boot screen at all**.

---

## 1. Quick start

```bash
cd firmware

# 1) Build and upload (PCB / DevKitM-1)
pio run -e esp32-c3-devkitm-1 -t upload

#    For the breadboard (Seeed XIAO ESP32C3)
pio run -e seeed_xiao_esp32c3 -t upload

#    Shortcut
pio run -e xiao -t upload

# 2) Upload the filesystem (fonts, books)
pio run -e esp32-c3-devkitm-1 -t uploadfs

# 3) Monitor the serial port  (NOT UART0, USB-CDC)
pio device monitor
```

`lib_deps =` is **deliberately empty**: the SSD1680 driver, the JSON generation
and the font engine are all written by us in this project. GxEPD2 is not needed;
you can still use it if you want (see below).

### About the serial console

GPIO20 is `BTN_MENU`, and GPIO21 is U0TXD. That is why **UART0 is never used**.
`-DARDUINO_USB_CDC_ON_BOOT=1` is set in `platformio.ini`; all `Serial` output
comes over USB-Serial-JTAG / USB-CDC. Because GPIO6 is given up as JTAG (MTCK)
(EPD_MOSI is there), hardware debugging is done via USB-CDC.

---

## 2. Generating a font

The reading screen loads the file `/fonts/book.epf` from LittleFS at runtime. If
there is no font, the screen shows the message **"Font bulunamadı /
tools/fontgen.py çalıştırıp yükleyin"** (a 3×5 fallback font is embedded in the
firmware for this message; otherwise we could not draw text and the error could
not be shown either).

```bash
# The font generator lives in exactly ONE place in the repo: ../tools/fontgen.py
pip install -r ../tools/requirements.txt
python3 ../tools/fontgen.py DejaVuSans.ttf --size 16 \
        --out data/fonts/reader-16.epf --preview /tmp/onizleme.png
pio run -t uploadfs
```

The default `--ranges` set covers ASCII + Latin-1 + Latin Extended-A + Turkish
(`çÇğĞıİöÖşŞüÜ`). The Turkish letters are present in the font as separate code
points.

The file format is fully described in the header `include/font.h`
(a 12-byte header + a fixed 10-byte record per glyph + 1bpp bitmap). Sizes that
work well: **14–18**. The large-text setting draws this file at ×2 scale.

---

## 3. Book format and upload

The `.epr` v1 format is defined in the header `include/book.h`:
`"EPR1"` + version + flags + text/TOC offsets + title/author/language +
text block (0x0A paragraph, 0x0B end of chapter) + optional table of contents.

Books are loaded in two ways:

* **Over WiFi** (see below).
* By uploading a filesystem over the serial port and copying into the `/books/`
  folder.

---

## 4. First boot and WiFi transfer

1. The device boots, the splash appears, the library is listed.
2. **Long-press the MENU key** (700 ms) → the menu opens.
3. Choose *WiFi transfer*.
4. The device first tries to connect to the saved network (15 s). If it fails it
   opens its own access point:

   | | |
   |---|---|
   | Network name | `PocketReader-XXXX` (XXXX = the last two bytes of the MAC) |
   | Password | `readbooks` |
   | Address | `http://192.168.4.1/` |

5. Open the address in a browser; the page is Turkish, and files are uploaded by
   drag-and-drop.
6. Press **MENU** to exit. The device turns WiFi off completely.

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Upload page (single file, no external assets) |
| POST | `/upload` | multipart file, or a raw body with the `X-Filename` header |
| GET | `/list` | JSON list of the books |
| POST | `/delete` | `{"name":"kitap.epr"}` (a form field is also accepted) |
| POST | `/wifi` | `{"ssid":"..","pass":".."}` |
| GET | `/status` | Version, free RAM, free space, battery mV/%, uptime |

**Important:** The radio is on only in transfer mode and is turned off
completely before sleeping (`WiFi.mode(WIFI_OFF)`). This is what keeps the
standby current at the ~5 µA level; an associated but idle WiFi stack draws
milliamps and drains the cell in a day.

During upload the first 4 bytes are checked against `EPR1`. If invalid, the file
is not left as garbage in `/books/.upload.tmp`, it is deleted. The upload is first
written to a temporary file and only moved to its real name after it is
validated — an interrupted transfer does not corrupt the library.

The raw-body path (`X-Filename`) is limited to **64 KB** because it keeps the
body in RAM; the real path is multipart and is streamed straight to flash.

---

## 5. Deep-sleep behaviour

* When the idle period (default **60 s**, from the menu 30/60/120/300/unlimited)
  elapses, the panel is put into **Deep Sleep Mode 1** with `0x10 = 0x01`: ~1 µA,
  the image is preserved in RAM and stays on the screen.
* Waking happens only via **UP (GPIO3)** and **DOWN (GPIO2)**; both are in the RTC
  domain and trigger `ANY_LOW` with `ext1`.
  **MENU (GPIO20) cannot wake it** — it is not in the RTC domain because it is
  U0RXD. After waking you can use MENU.
* On wake **no splash is shown**: the book is restored silently (instantly,
  thanks to the page-index cache) and only the single action corresponding to the
  pressed key is performed:

  | Wake | On the reader screen | In the library |
  |---|---|---|
  | DOWN | next page | down the list |
  | UP | previous page | up the list |

  Then the device goes back to sleep. Opening the cover and pressing DOWN gives
  the next page in ~1 second.

### When the battery is low

If the voltage drops below 3.40 V the screen shows **"Pil zayıf / Cihazı şarj
edin"** and the device **turns wake-on-key off completely**; it only wakes once
an hour on a timer to re-measure the state. This way a device left in a bag
cannot drain its cell through a wake loop.

---

## 6. Rotation and mirroring settings

The interface always draws to a **logical** canvas (default 250×122, landscape).
The controller's real RAM is 122×250; the conversion between them is **in a
single inline function**: `epdMapLogicalToNative()` (`include/epd.h`).

```c
#define EPD_ROTATION   90    // 0 / 90 / 180 / 270
#define EPD_MIRROR_X   0     // 1 = mirror the image horizontally
#define EPD_MIRROR_Y   0     // 1 = mirror the image vertically
```

If the image comes out upside-down or rotated, **do not touch the driver**: try
flipping the mirrors first. Mirroring is applied in **logical space before**
rotation, so `EPD_MIRROR_X` always flips the left/right direction you see on the
screen.

---

## 7. Changing pins

All pins are in `include/config.h`, and a **single map for both boards** is used
(the XIAO only breaks out 11 GPIOs).

| Signal | GPIO | XIAO | Direction | Notes |
|---|---|---|---|---|
| EPD_SCK | 4 | D2 | output | SPI CLK, mode 0 |
| EPD_MOSI | 6 | D4 | output | GPIO6 = MTCK → **JTAG given up** |
| EPD_CS | 7 | D5 | output | active LOW |
| EPD_DC | 10 | D10 | output | 0 = command |
| EPD_RST | 8 | D8 | output | GPIO8 strapping, 100k pull-up |
| EPD_BUSY | 9 | D9 | input | GPIO9 strapping/boot; BOOT key on the XIAO |
| BTN_UP | 3 | D1 | input | RTC → wakes |
| BTN_DOWN | 2 | D0 | input | RTC → wakes; GPIO2 strapping |
| BTN_MENU | 20 | D7 | input | U0RXD; **cannot wake** |
| VBAT_ADC | 5 | D3 | input | ADC2_CH0, 100k/100k divider |

Strapping warnings:

* **GPIO8** (EPD_RST) and **GPIO9** (EPD_BUSY) must be HIGH at boot. Both are
  naturally HIGH (RST inactive, BUSY idle), but fit a 100k pull-up.
* **GPIO2** (BTN_DOWN) must be HIGH at boot — **do not hold the DOWN key during
  boot** or the device enters ROM download mode.
* On the XIAO, GPIO9 is connected to the on-board BOOT key. Pressing that key
  looks to the firmware like "panel busy"; `epdBusyWait()` times out (harmless,
  ~2–5 s) and the refresh is cancelled.

The keys are active-LOW; an external 100k pull-up and 100nF (to GND) are
recommended. The firmware also enables the internal pull-ups and applies a 25 ms
software debounce.

---

## 8. Verifying BUSY polarity in 30 seconds

BUSY polarity is the **most common mistake** in the bring-up of a new board and
varies among vendor drivers. We go by the datasheet (Rev 0.14, Table 5-2: BUSY
active-HIGH), but this is an **assumption that must be verified**:

```c
// include/config.h
#define EPD_BUSY_ACTIVE_HIGH  1   // 1 = HIGH busy (datasheet), 0 = LOW busy
```

### Verifying by measurement

1. Connect the panel, power the board **without sending any command**.
2. Measure the BUSY pad with a multimeter. An idle panel stays at **its released
   level**. According to the datasheet this is LOW.
3. In the firmware, change the screen and trigger a **full refresh** (for
   example *Full refresh* from the menu).
4. **While the screen is visibly refreshing**, whichever level the needle rests
   at is BUSY. You will see the needle twitch as it inverts; the level it stays
   at steadily is the busy level.

### What happens if it is wrong

* If it is set the wrong way round, the firmware either never waits (the refresh
  is left unsynchronised and the image comes out corrupted/partial) or times out
  every time.
* On timeout the device **does not hang**: `epdBusyWait()` writes the observed pin
  level and the `EPD_BUSY_ACTIVE_HIGH` value to the serial port and returns
  `false`.

```
[epd] BUSY TIMEOUT after 5000ms (pin level=0, EPD_BUSY_ACTIVE_HIGH=1)
[epd] *** BUSY polaritesi yanlis olabilir -- include/config.h icindeki
         EPD_BUSY_ACTIVE_HIGH degerini degistirin ***
```

If you see this message, flip `EPD_BUSY_ACTIVE_HIGH` between 1 ↔ 0 and re-upload.
If you still get a timeout after changing the value, the problem is not the
polarity but the wiring (the BUSY line may be broken).

---

## 9. Electrical notes

* **Panel current:** for the GDEY0213B74 the typical power is 10.5 mW, typical
  current **3.5 mA** (VCI = 3.0 V). Peak currents during refresh are above that
  and the panel's pump circuits draw sudden bursts — so put **10 µF + 100 nF**
  decoupling on the VCI line and a sufficient trace width in the supply path.
* **Deep sleep:** the panel draws 1 µA (Mode 1, RAM preserved), the ESP32-C3
  draws ~5 µA in deep sleep. The divider resistors (100k+100k) draw **~21 µA**
  continuously; this is the largest item of the remaining current — acceptable,
  but if you will keep the cell on the shelf for months you must switch the
  divider with a MOSFET.
* **Charging:** the Li-ion cell is taken as 0% at 3.30 V and 100% at 4.20 V
  (the table in `src/power.cpp`).

---

## 10. Switching to GxEPD2 (optional)

If you want to drop our own driver and use GxEPD2: add `zinggjm/GxEPD2` to
`lib_deps`, and replace the bodies of `epdInit() / epdFullRefresh() /
epdPartialRefresh()` in `src/epd.cpp` with `GxEPD2_213_GDEY0213B74` calls.
`src/epd_lut.h` becomes unnecessary because GxEPD2 carries the same waveforms
internally. **The upper layers (Canvas, book, interface) are independent of the
driver** — they only touch the framebuffer, `epdDirty()` and
`epdPartialRefresh()`.

---

## 11. What has not been tested (the honest list)

This firmware has **not been run** on hardware; it was written as code that is
ready to compile and whose logic is complete. In particular, the following are
unverified:

1. **The partial-refresh path.** The waveform and init sequence are taken
   verbatim from the vendor source, but the decision to write the `0x24`/`0x26`
   pair together with the dirty rectangle is ours. If you see ghosting or a
   half-updated area, first turn the `partial_enabled` setting off and try with a
   full refresh, then switch the windowed write to a full-screen write.
2. **BUSY polarity** — see section 8; it must be measured.
3. **Battery measurement via ADC2 (GPIO5).** On the ESP32-C3, ADC2 is
   single-channel and, unlike the classic ESP32, there is no WiFi conflict;
   nevertheless real accuracy may need calibration. If the divider is not
   fitted, the reading is clamped to 4400 mV and the percentage is misleading.
4. **Measured sleep current.** The ~5 µA figure is calculated for ESP32-C3 +
   panel + divider, not measured.
5. **The multipart upload flow** and WebServer's `arg("plain")` behaviour may
   change with the core version; the JSON path is therefore written so that it
   can also fall back to form fields.
6. **The font generator** (`../tools/fontgen.py`) uses Pillow's `anchor="ls"`
   feature; it is not supported on very old Pillow versions.

### Version warning

`platform = espressif32@^6.9.0` is pinned in `platformio.ini` (as requested). This
platform brings the 2.0.x line of the Arduino core. The code is written to
compile with both 2.0.x and 3.x (for example the return type of `File::name()`
changes between versions, so it is wrapped with `String(...)`). If you want the
whole of Arduino core 3.x, switch the platform in `platformio.ini` to the
[pioarduino](https://github.com/pioarduino/platform-espressif32) fork;
`build_flags` stay the same.
