> Türkçe sürüm: [00-overview.tr.md](00-overview.tr.md)

# 00 · Overview and Design Decisions

This document answers not "what did we build" but **"why did we build it this
way."** If you want to change a part, read this first; most of the decisions are
interdependent.

---

## 1. Why ESP32-C3?

| Candidate | Sleep current | Size | Verdict |
|---|---|---|---|
| **ESP32-C3** | ~5 µA (chip) | 13.2 × 16.6 mm module | ✅ chosen |
| ESP32 (classic) | ~10 µA but the board ~1 mA | large module | ❌ board-level draw is high |
| ESP32-S3 | ~8 µA | larger, more expensive | ➖ more powerful than needed, no PSRAM required |
| Raspberry Pi Zero 2 W | **~120 mA** | 65 × 30 mm | ❌ ~4 hours on a 500 mAh battery |
| ATmega328P | ~0.1 µA | small | ➖ no Wi-Fi, transferring books needs an SD card + physical access |

The determining constraint is **sleep current**. The entire value of an e-ink
reader is "when I open it, the charge isn't dead." The Pi Zero W structurally
cannot achieve this: the current Linux draws while idle wipes out the biggest
advantage of an e-ink display (static image = zero power).

The ESP32-C3's second advantage: **RTC-domain GPIO** and **RTC memory**. While
the device is in deep sleep, it can wake on one of the buttons and continue from
whichever page of whichever book you were on without losing it from RAM.

---

## 2. Why this pin map? (The most critical design constraint)

The XIAO ESP32-C3 breaks out only **11 GPIOs** of the ESP32-C3-MINI-1's 53 pads
to the header:

```
GPIO2, GPIO3, GPIO4, GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO20, GPIO21
```

The number of signals we need: `SCK, MOSI, CS, DC, RST, BUSY, UP, DOWN, MENU, ADC` = **10**.

So 10 of the 11 pins are used, GPIO21 is left free. But the real difficulty is
not the count, it is **two separate constraints**:

### Constraint A: pins that can wake from sleep

On the ESP32-C3, the pins that can wake from deep sleep via `ext1` are in the RTC
domain: **GPIO0–GPIO5**. Of these, the XIAO header has only **2, 3, 4, 5**:

- GPIO4 → SPI clock (indispensable)
- Remaining: GPIO2, GPIO3, GPIO5

We have to fit three things into these: two page buttons + battery measurement.
ADC1 is only on GPIO0–4; GPIO0/1 are not on the header, GPIO4 is on SPI. So
battery measurement **must be GPIO5 = ADC2_CH0**. That leaves GPIO2 and GPIO3 for
the buttons — and since both are in the RTC domain, **both page buttons can wake
the device**. That is exactly what is critical.

> The ESP32-C3's ADC2 is single-channel and, unlike the classic ESP32, does not
> conflict with Wi-Fi. That is why we can safely use GPIO5 for battery
> measurement.

### Constraint B: strapping pins

GPIO2, GPIO8 and GPIO9 are strapping pins. The condition from datasheet
Table 4-3 for normal (SPI) boot: **GPIO2 = 1, GPIO9 = 1, GPIO8 = don't care**. A
wrong level at startup = the device does not boot or enters download mode.

The assignment that solves both constraints at once:

| Pin | Role | Why it works |
|---|---|---|
| GPIO2 | `BTN_DOWN` | RTC ✓. Strapping: must be HIGH at startup → the 100k pull-up provides it. The button must not be held down at startup |
| GPIO3 | `BTN_UP` | RTC ✓. Not strapping, free |
| GPIO5 | `VBAT_ADC` | ADC2_CH0 ✓ |
| GPIO8 | `EPD_RST` | Strapping, **but its value does not matter for SPI boot** (it must be 1 only in download mode). It is the ROM message suppression pin |
| GPIO9 | `EPD_BUSY` | Strapping: must be HIGH at startup → **because the panel BUSY is idle-HIGH, the condition is satisfied by itself** |
| GPIO20 | `BTN_MENU` | U0RXD, input only. Not RTC → cannot wake from sleep |

Giving GPIO9 to BUSY is the most elegant part of the design: two constraints are
solved at once, without any extra part.

### The cost

- **The MENU button cannot wake the device from sleep.** It is pressed after
  waking. (One of the page buttons is used to wake — and the user wants to
  continue reading anyway, not return to the menu. In practice it is not
  bothersome.)
- **Because GPIO6 (MTCK) is used for SPI, classic JTAG is lost.** USB-Serial-JTAG
  (GPIO18/19, over USB-C) is sufficient for debugging.
- On the XIAO, GPIO9 is also connected to the board's BOOT button. Pressing BOOT
  makes the panel appear "busy" (harmless, it falls through to a timeout), and if
  it is held down at startup it puts the device into download mode.

---

## 3. Why buck-boost for power, not an LDO?

A Li-Po is full at 4.2 V and empty at 3.0 V. The e-paper panel and the ESP32-C3
want **3.3 V**.

- **LDO** (e.g. MCP1700): its output begins to droop below 3.4 V. The last
  20–25% of the battery is unusable. It also produces as much heat as
  (4.2−3.3) × current.
- **Boost only**: it does not work while the battery is above 3.3 V.
- **Buck-boost (TPS63020)**: a constant 3.3 V at a 2.5–5.5 V input. **All** of the
  battery is used. The output does not dip on the current spikes during a panel
  refresh — the ±15 V charge pump inside an e-paper panel is sensitive to a low
  input voltage.

The TPS63020's 2 A output is more than the need (ESP32 Wi-Fi TX peak current
~350 mA, panel refresh ~20 mA). The reason: there are few **solderable**
buck-boost options that give a constant 3.3 V; the TPS63020 is both VSON-10
(hand-solderable) and a part that is in stock. Cheaper/smaller alternatives are
in `docs/09`.

---

## 4. Why did we write our own SSD1680 driver, instead of using GxEPD2?

GxEPD2 is a mature and good library; **if you want to use it, you can switch**
(`firmware/README.md` explains how this is done). Our reasons for writing our own
driver:

1. **Partial refresh must be under our control.** Ghosting management (a full
   refresh every 20 pages), dirty-rectangle tracking and panel sleep determine
   the main UX.
2. **No dependencies.** In a place with 4 MB of flash and 400 KB of RAM, carrying
   a 30 KB library is unnecessary.
3. **Transparency.** The vendor's init sequence and LUT tables sit in the repo
   together with their source URL; what they are can be seen.

**The LUT tables were not made up.** Partial refresh requires a panel-specific
waveform (LUT); a wrong LUT slowly degrades the panel. The tables were taken
verbatim from the MIT-licensed vendor reference driver, and the source URL is
noted at the top of `src/epd_lut.h`.

---

## 5. Why do we have our own book format, `.epr`?

The device has neither the RAM nor the CPU to parse EPUB — and it is not needed
either. The conversion is done on the computer **once**:

```
EPUB  ──(epub2epr.py, on the computer)──>  .epr  ──(Wi-Fi)──>  device
```

The work left on the device side: reading UTF-8, line wrapping, page splitting,
caching the page positions as a `uint32` array. In a 200 KB book, ~4,000 page
positions = 16 KB RAM. Not a problem for the ESP32-C3.

`TXT` could also have been used, but then the title, author, language and table
of contents information would be lost; the library screen and chapter skipping
would not work.

---

## 6. Why is the font file in LittleFS, not embedded in the firmware?

An embedded font means you cannot change the typeface without recompiling the
firmware. Yet font size/typeface is the setting most often changed on a reader.

The cost of this: if the device cannot find a font on first boot, it cannot run.
That is why the firmware shows an **explicit error screen** if there is no font
("run `tools/fontgen.py`"), and does not silently leave a blank screen.

---

## 7. Deliberately not done

| Not done | Why |
|---|---|
| Touchscreen | On a 2.13" panel the cost of a touch layer is more expensive than the panel itself; 3 buttons are enough |
| Frontlight | There is no frontlit panel at this size (the smallest are 4.2"+) |
| SD card | On 4 MB of flash there is ~3 MB of usable space ≈ 15–30 books; Wi-Fi transfer already exists. There is no free GPIO either |
| External PSRAM | 250×122×1 bit = 3.9 KB buffer. Absurdly small |
| Real-time clock | We do not show a clock. If wanted, the MAX17048 already reserves a place on I²C |
| Multilingual UI | Turkish + English via a build flag; `i18n.h` is extensible |

---

## 8. Data flow

```
┌─ COMPUTER ─────────────────────────────────┐
│  book.epub                                 │
│      │ epub2epr.py                         │
│      ▼                                     │
│  book.epr ──┐                              │
│              │ send.py / browser           │
└──────────────┼─────────────────────────────┘
               │ HTTP (Wi-Fi, transfer mode)
┌──────────────▼─────────────────────────────┐
│  DEVICE                                    │
│  wifi_xfer.cpp  ──> LittleFS /books/       │
│                          │                 │
│  book.cpp  <── open ─────┘                 │
│      │ read header, stream text            │
│      │ wrap lines with font.cpp            │
│      ▼                                     │
│  page positions (uint32 array)             │
│      │                                     │
│      ▼                                     │
│  ui.cpp  ──> Canvas (4000 bytes)  ──> epd.cpp ──SPI──> panel
│                    ▲                       │
│  buttons.cpp ──────┘                       │
│  power.cpp (sleep/wake, RTC memory) ───────┘
└────────────────────────────────────────────┘
```

---

Next: [01 · Bill of Materials](01-bill-of-materials.md)
