# 08 · Troubleshooting

Search by symptom. In each item **the most likely cause is written first**.

---

## Display

### No image at all, the screen is entirely white/black

| Possible cause | Check | Solution |
|---|---|---|
| Supply voltage wrong | Is there 3.3 V across `C4`? | Check `R5`/`R6`, `docs/04` §4 |
| FPC fitted backwards | Is the `BUSY` line idle-HIGH? | Remove the connector, turn it 180° and refit |
| FPC not fully seated | Is the connector's latch closed? | Push it all the way in and latch it |
| Firmware not flashed | Is there output on the serial port? | `pio run -e xiao -t upload` |
| No font file | Does the screen say "font not found"? | `tools/fontgen.py` + `uploadfs` |
| `EPD_RST` stuck LOW | Measure GPIO8 | Solder the 100 kΩ pull-up |
| `RST` and `CS` swapped | Compare with the schematic | Move them to the correct pins |

> If the screen goes **entirely black** this is usually good news: it means the
> panel is powered and being reset, but no data is arriving. The problem is in the
> `MOSI`, `SCK` or `DC` line — not the supply.

### The image is inverted / mirrored

Try these three lines in `firmware/include/config.h`:

```c
#define EPD_ROTATION   90
#define EPD_MIRROR_X   0
#define EPD_MIRROR_Y   0
```

There are 8 possible combinations; try them in turn. No code change is needed and
each attempt means a build + flash (~30 seconds). Save it once you find the right
combination.

**If the image is rotated 90°** change only the `EPD_ROTATION` value between
`0`/`180`/`270`. **If it is mirrored** set `EPD_MIRROR_X` or `EPD_MIRROR_Y` to `1`.

### There is text but smudges/shadow (ghosting)

| Cause | Solution |
|---|---|
| The partial refresh counter is too high | Lower the `DEFAULT_FULL_REFRESH_EVERY` value **20 → 10** |
| Regulator ripple is high | Move the `JP1` jumper from `GND` to `VINA` (forced PWM) |
| `C10` (100 µF) missing or far | Add it right at the panel connector |
| Panel ageing | Normal; increase the full refresh frequency |

Smudging is a natural consequence of e-ink technology. A full refresh every 20
pages manages it. If it bothers you, lower it to 10 — the cost is the screen
flashing for 2 seconds every 10 pages.

### Sometimes the screen refreshes halfway

The classic **`C10` problem**. At the moment of refresh the panel draws a brief
high current to fill its charge pump. If the buffer capacitor is missing or its
trace is long, the `3V3` rail collapses and the panel stops halfway.

- Is `C10` fitted? (100 µF, low ESR)
- Is `C10` **right at** the panel connector? (if it is further than 5 mm its effect
  is reduced)
- Did you use a smaller package instead of 0805/1206? (its ESR may be high)

### The screen refreshes very slowly

A full refresh is ~2 seconds — that is the nature of the panel. A partial refresh
is ~0.3 s. If it is constantly doing full refreshes, the `epdPartialRefresh()`
call is not in play; check the `partial_enabled` setting in `config.h`.

---

## Buttons and sleep

### The buttons work the wrong way round (back/forward swapped)

Swap the `BTN_UP` and `BTN_DOWN` pins (`config.h`) **or** swap the wires. This is
the most common mistake in the easy build: mixing up D0 and D1.

### The device doesn't wake from sleep

| Cause | Check |
|---|---|
| The MENU button is being pressed | GPIO20 is **not** in the RTC domain — it cannot wake. Use `BTN_UP` or `BTN_DOWN` |
| The buttons are not connected to GND | `ANY_LOW` wake requires a path that pulls the pin to GND |
| The battery is flat | Measure the voltage |
| The firmware doesn't enter sleep | Is there a "sleep" line on the serial port? |

### After waking the splash screen appears

The firmware is not reading the `was_deep_sleep` flag. This flag must be defined
with `RTC_DATA_ATTR`; an ordinary global variable is **reset** in deep sleep.
Verify that the `RtcState` structure in `power.h` is marked with `RTC_DATA_ATTR`.

### The device wakes on its own

| Cause | Solution |
|---|---|
| No 100 nF on the button line | The bounce at the moment of waking produces a false edge — add the capacitor |
| `VBAT_ADC` is on GPIO5, swapped with a button | Compare with the schematic |
| The button is mechanically stuck | Check the case |

---

## Power and battery

### It doesn't charge

| Cause | Check |
|---|---|
| **The USB-C CC resistors are missing/wrong** | Are `R1`, `R2` = 5.1 kΩ? (The most common cause) |
| The cable is for charging only | Try another cable |
| The charge LED never lights | The orientation of `R4`/`D1` and the `STAT` connection |
| LED reversed | LED cathode to `STAT`, anode to `VBUS` through `R4` |
| The battery is full | The LED doesn't light — normal |
| The battery protection circuit has cut off | Disconnect the battery and measure it directly |

### The battery percentage is wrong

| Cause | Solution |
|---|---|
| The measurement is taken during a refresh | The firmware must take the measurement **before** the refresh |
| The divider value is wrong | It should be 100 kΩ / 100 kΩ (ratio 1:2) |
| ADC attenuation missing | `analogSetPinAttenuation(VBAT_ADC, ADC_11db)` |
| The battery curve doesn't fit | Different chemistries need a different curve; adjust the table in `power.cpp` |
| ADC2 is not being used | GPIO5 = **ADC2_CH0**; the ADC1 pins are not in use |

### The battery runs out in 1 day

Expected: ~13 months. If it runs out in a day:

| Cause | Check |
|---|---|
| The device doesn't enter sleep | Wait 60 s and measure the current |
| Wi-Fi doesn't turn off | Is `WiFi.mode(WIFI_OFF)` called before sleep? |
| The panel doesn't enter sleep | Is `epdSleep()` called? (the panel draws on the order of mW) |
| The serial port stays open | With USB not plugged in the serial output draws no current, but if USB-serial is active it does |
| The user LED on the XIAO | On some boards the brightness LED stays lit continuously |

---

## Wi-Fi

### `pocketreader.local` doesn't open

| Cause | Solution |
|---|---|
| mDNS not supported | Type the IP from the screen directly: `http://192.168.1.42` |
| The device is asleep | Press a button, long-press MENU |
| The computer is on a different network | Both must be on the same network |
| In AP mode | First connect to the `PocketReader-XXXX` network (password: `readbooks`) |

### The device can't find the home network

Re-enter the Wi-Fi password:

```bash
cd tools
python3 send.py --wifi "EvAgi" "sifre123"
```

It can also be done from the browser in AP mode. **Use a 2.4 GHz network** — the
ESP32-C3 does not support 5 GHz. This is the most common cause: trying to connect
to the modem's 5 GHz SSID.

### The upload is interrupted halfway

| Cause | Solution |
|---|---|
| The book is too large | Is there free space in LittleFS? (`send.py --status`) |
| The device went to sleep | Sleep must be disabled in transfer mode; check the firmware |
| Weak signal | Move the device closer to the router |

---

## Build and software

| Error | Solution |
|---|---|
| `epd_lut.h: No such file` | The file is missing; `docs/05` §7 |
| `'EPD_FB_SIZE' undeclared` | `config.h` not included |
| `Failed to connect to ESP32-C3` | The BOOT + RESET sequence (`docs/05` §2) |
| `LittleFS mount failed` | `pio run -t uploadfs` |
| `#include <Arduino.h> file not found` | You are using a plain compiler instead of PlatformIO — use `pio run` |
| The font is loaded but there are blanks on the screen | The `.epf` is corrupt; verify with `fontgen.py --preview` |

> **Note:** This project was not put through a compiler while this repo was being
> prepared. The first `pio run` invocation may need small fixes. Report the error
> you find as described in `CONTRIBUTING.md`.

---

## Books and fonts

| Symptom | Cause | Solution |
|---|---|---|
| Turkish letters are empty squares | The font doesn't cover `latin-ext` | Add it with `fontgen.py --ranges` |
| The mark on top of `ğ` is cut off | The font overflows the box | Does your version of `fontgen.py` use the `top`/`left` offsets? |
| The book won't open | An `.epub` was uploaded | Convert it first |
| The title is empty | No EPUB metadata | `--title`/`--author` |
| The page numbers are wrong | The font changed, the cache is stale | Delete `/cache/*.idx` or re-upload the book |

The device checks whether the cache is valid using the book size + font metrics;
on a mismatch it re-paginates itself. If you still see a problem, delete the book
and upload it again.

---

## Still not working

When reporting the problem include the following — the time to a solution is
halved:

1. **Serial port output** (`pio device monitor`, `CORE_DEBUG_LEVEL=4`)
2. **A photograph of the screen** (how it is broken tells you a lot)
3. **Measurements**: `3V3` voltage, battery voltage, sleep current
4. **Hardware**: easy build or PCB, the panel's exact model
5. **What changed**: what did you change last?

Template: [`.github/ISSUE_TEMPLATE`](../.github) (if present) or just open an
issue.

---

Back: [07 · Power](07-power.md) · Next: [09 · Roadmap](09-roadmap.md)
