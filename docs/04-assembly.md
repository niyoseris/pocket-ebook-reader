# 04 · Assembly

Two parts, ordered by difficulty and risk. If you are on the easy build go to
§1; if you are on the PCB, go to §3.

---

## 0 · Safety (do not skip)

> 🔋 **Li-Po batteries can cause fires.**
> - Do not connect the polarity in reverse (double-check the `+` and `−` markings)
> - While soldering, **do not short the ends together** (a short = instant high
>   current, the cell swells)
> - **Do not use** a punctured, swollen or worn cell
> - On the first attempt power it from USB-C and connect the battery last
> - Do not leave it unattended while charging (the first time)

> 🖥️ **Connect the panel last.** If the panel is fitted before the supply voltage
> is verified, the panel dies permanently. See §4.

---

## 1 · Easy build (XIAO + breakout module)

You need: soldering iron, solder, 30 AWG wire, side cutters, multimeter. Time
~1 hour.

### 1.1 Prepare the parts

The XIAO ESP32-C3 **does not come with the pins fitted** — solder the 2.54 mm male
headers or solder the wire directly to the pad (it comes out thinner).

### 1.2 E-paper connection

On the panel module's 8-pin header **the pin names are written — connect by the
names, not by the order.** The order can change between revisions.

| XIAO pad | GPIO | Panel module pin (name) | Wire colour (suggestion) |
|---|---|---|---|
| `D2` | 4 | **CLK** (SCK) | yellow |
| `D4` | 6 | **DIN** (SDA/MOSI) | blue |
| `D5` | 7 | **CS** | green |
| `D10` | 10 | **DC** | orange |
| `D8` | 8 | **RST** | purple |
| `D9` | 9 | **BUSY** | white |
| `3V3` | — | **VCC** | red |
| `GND` | — | **GND** | black |

> ⚠️ The panel module's `VCC` pin is the supply voltage. Waveshare modules accept
> 3.3 V and 5 V, but **because the logic level in this project is 3.3 V, connect
> `VCC` to the XIAO's `3V3` output** — not to the `5V` pin.
> If you connect it to `5V`, the level shifter on the module kicks in and the
> `BUSY` line is pulled to 5 V; this can damage the ESP32-C3's input.

### 1.3 Buttons

One leg of each button to a GPIO, the other to GND:

| Button | XIAO pad | GPIO | Function |
|---|---|---|---|
| `SW2` | `D1` | 3 | Page back |
| `SW3` | `D0` | 2 | Page forward |
| `SW4` | `D7` | 20 | Menu / library |

**Fit external pull-ups — three 100 kΩ resistors, one from each button GPIO to
3V3.** A 100 nF capacitor from each GPIO to GND is optional here but
recommended, for the same reason the PCB has it.

The reason is a property of the chip, not a preference. **ESP32-C3 has no RTCIO
subsystem** (`SOC_RTCIO_PIN_COUNT` is 0) and ESP-IDF declares no `gpio_sleep_*`
API for it, so `rtc_gpio_pullup_en()` — the way an ESP32 arms an RTC pull-up
before sleeping — does not exist on this part. The C3 wakes from deep sleep
through its GPIO block instead (`esp_deep_sleep_enable_gpio_wakeup`), and that
block *does* enable internal pull resistors by default, so a device with nothing
but `INPUT_PULLUP` will usually still wake.

"Usually" is not good enough here. ESP-IDF's own note on that function says
external resistors are **strongly recommended** for a low-level wakeup, because
the internal ones are only armed at the moment `esp_deep_sleep_start()` runs.
It also warns that internal and external resistors together interfere, so if you
fit the 100 kΩ parts you may want to switch the internal ones off
(`CONFIG_ESP_SLEEP_GPIO_ENABLE_INTERNAL_RESISTORS`).

The failure mode if you skip them is the unpleasant one: the device wakes
*intermittently*. Sometimes every press works, sometimes one in ten does
nothing, and there is nothing in the log to look at because the chip is asleep.

The PCB build carries the 100 kΩ + 100 nF for the same reason, and there the
capacitor additionally cleans the line at the instant of waking, before the
software debounce is running.

### 1.4 Power

```
Li-Po (+) ──> [power switch] ──> XIAO BAT+
Li-Po (−) ─────────────────────> XIAO BAT−
```

The XIAO ESP32-C3 **has its own charging circuit** (380 mA fast / 40 mA trickle).
When USB-C is plugged in it charges the battery itself. **Do not connect a
separate TP4056 module** — if two charging circuits run in parallel the battery is
damaged.

The switch disconnects the battery from the XIAO; charging continues while USB-C
is plugged in (the XIAO's charging input is independent of the switch).

### 1.5 First power-up

1. Plug in USB-C (with the battery not connected)
2. The power LED on the XIAO should light
3. Measure 3.3 V at the `3V3` pad
4. If correct, fit the panel
5. Flash the firmware (`docs/05`)

---

## 2 · Rules for handling the FPC cable

If you are using the raw panel this section is a lifesaver. FPC cables are fragile
and cannot be repaired once torn.

| Don't | Do |
|---|---|
| Fold the cable sharply | Fold it with a radius of at least **3 mm** |
| Pull the cable out by tugging | Open the connector's latch and pull straight |
| Insert it halfway into the connector | Push it all the way in until the ends are no longer visible |
| Touch the contact surface with your fingers | Hold it by the edges (skin oil contact = poor contact) |
| Try bending it before soldering | Do a dry fit first, then solder |

**Contact direction:** whether the connector is "top contact" or "bottom contact"
determines which way the cable's blue/black face looks. If you fit it wrong the
panel is connected backwards and gives no image at all.

**Verification:** With the panel fitted but the supply off, measure continuity with
a multimeter — there should be a short from the panel's `GND` pin to the board's
GND, and there should **not** be one between `VDD` and GND. If it is fitted the
wrong way round you catch it here.

---

## 3 · PCB assembly (SMD)

### 3.1 Order

If you are soldering by hand, do **the hardest first** — while the board is clean
and there is room around it:

| # | Part | Package | Note |
|---|---|---|---|
| 1 | `U3` TPS63020 | VSON-10, 0.5 mm pitch | **The hardest.** The thermal pad underneath has to be soldered |
| 2 | `U5` ESP32-C3-MINI-1 | module, 1.27 mm pitch | Edge pads; be careful that solder does not flow under the module |
| 3 | `U2` MCP73831 | SOT-23-5 | |
| 4 | `U1` USBLC6-2SC6 | SOT-23-6 | |
| 5 | `L1` | 3×3 mm | |
| 6 | 0603 passives | 0603 | Resistors and small capacitors |
| 7 | 0805 passives | 0805 | `C1`, `C2`, `C4`, `C5`, `C7`, `C10` |
| 8 | `J1` USB-C | 16-pin | Edge pads, it soaks up heat — a little longer |
| 9 | `J2` FPC | 24-pin 0.5 mm | The panel is fitted last |
| 10 | `SW1`–`SW4` | | Last |

**Method:** solder paste + hot air (or a controlled toaster oven) is the most
reliable. If you are soldering by hand, use a fine tip, 0.5 mm solder wire and
plenty of flux; for VSON-10 and SOT-23-5 hot air is almost mandatory.

> **The easy way:** use JLCPCB's assembly service and have them solder `U3`,
> `U2`, `U5`. Do the rest by hand. See `docs/03` §6.

### 3.2 Common mistakes in component placement

| Mistake | Consequence |
|---|---|
| `C2` (10 µF) far from U3 | Efficiency drops, the regulator runs unstably |
| `C9` (0.1 µF) far from the module | The module resets randomly |
| `C10` (100 µF) far from J2 | The screen sometimes refreshes halfway |
| `R5`/`R6` wrong value | The output is not 3.3 V → **the panel dies** |
| `U1` orientation reversed | USB doesn't work |
| A 100 Ω resistor instead of 100 kΩ | The buttons appear permanently pressed |

After every solder joint **measure continuity on the relevant net**; verify before
moving on to the next part.

---

## 4 · 🛑 First power-up (without panel)

Do not skip this section. A wrong voltage kills the panel within seconds.

| Step | Action | Expected |
|---|---|---|
| 1 | USB-C plugged in, **battery not connected**, **panel not connected** | — |
| 2 | Measure the voltage across `C4` | **3.25 – 3.35 V** |
| 3 | If wrong, check `R5`/`R6` and their solder joints | Stop, do not touch the panel |
| 4 | Measure at the `U5` 3V3 pin | The same voltage |
| 5 | Unplug USB, connect the battery, switch on | The same measurement |
| 6 | Plug in USB, is the charge LED (`D1`) lit? | If the battery is full it doesn't light — normal |
| 7 | **Now** fit the panel | — |
| 8 | Flash the firmware (`docs/05`) | The screen shows an image within a few seconds |

**If the screen gives no image at all:** first check the `RST` and `BUSY` lines
with an oscilloscope or multimeter. `BUSY` should be idle-HIGH. If it stays LOW it
means it thinks the panel is busy — most likely the FPC has been fitted backwards.

---

## 5 · Case assembly

```bash
# Edit the case file (dimensions according to your own parts)
open hardware/enclosure/case.scad

# Generate the STL
openscad -o case_body.stl -D 'PART="body"' hardware/enclosure/case.scad
openscad -o case_lid.stl  -D 'PART="lid"'  hardware/enclosure/case.scad
```

**Print settings:** 0.2 mm layer, 3 perimeters, 20% infill, PLA or PETG, no
supports needed.

**Order:**

1. **First print only the panel bed** (if there is an option like
   `PART="panel_test"`) — see whether it fits the panel without waiting for a
   40-minute print to finish. If it doesn't fit, correct the parameters.
2. Print the full body.
3. Seat the panel in the bed, pass the FPC through from behind.
4. Screw the PCB to the standoffs (4× M1.6 × 4 mm).
5. Place the battery in the pocket (secure it with thin double-sided tape).
6. Check that the buttons are aligned with the case holes.
7. Close the lid, screw it.
8. Plug in the USB-C cable and verify that charging works.

**Thickness budget** (why is the case 13 mm?):

| Layer | mm |
|---|---|
| Front wall (over the panel edge) | 1.2 |
| Panel glass | 1.05 |
| FPC fold clearance | 0.8 |
| PCB | 1.6 |
| Tallest part on the PCB's back side (the module) | 2.5 |
| Li-Po cell (402025) | 4.0 |
| Back wall | 1.6 |
| **Total** | **~12.8 → 13.0** |

If you change the panel or the battery, recalculate this table; the `case_h`
parameter in `case.scad` is derived from this total.

---

## 6 · Post-assembly checklist

- [ ] The screen shows an image, the text is readable
- [ ] The image is not inverted (if inverted, `config.h` → `EPD_MIRROR_X`/`Y`)
- [ ] All three buttons do the correct function
- [ ] Page turning uses partial refresh (the full screen doesn't flash)
- [ ] It goes to sleep after 60 seconds of no touch
- [ ] It wakes with the page button and **the splash screen is skipped**
- [ ] Wi-Fi transfer mode starts, the IP appears on the screen
- [ ] `http://pocketreader.local` opens from the browser
- [ ] Charging works (the LED lights when USB is plugged in)
- [ ] The battery percentage shows a reasonable value on the screen

---

Back: [03 · PCB](03-pcb.md) · Next: [05 · Firmware Setup](05-firmware-setup.md)
