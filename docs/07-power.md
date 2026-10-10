# 07 · Power Management

The entire value of an e-ink reader is "when I open it six months later, the
charge isn't dead." This document explains where that target comes from and how it
is verified.

---

## 1. A realistic battery life model

Most projects calculate the "energy per page turn" and find astronomical numbers
(*"1.7 million pages!"*). This is misleading, because the real draw is **not the
screen refresh but the time the device stays awake**.

While reading, the device stays awake for another 60 seconds after turning a page
(adjustable sleep time). That is:

```
Dominant item = awake time × awake current
              = 25 hours × ~20 mA  (500 mAh battery)
```

| Usage | Duration | Description |
|---|---|---|
| **Standby (deep sleep)** | **13 months** (TPS63020) / **26 months** (TPS63900) | The device counts as off, it is only waiting for the button |
| **Continuous reading** | **~25 hours** | The screen is on, turning pages, 60 s sleep timeout |
| **Wi-Fi transfer** | **~5 hours** | The radio is on, the HTTP server is running |

For someone who reads 20 minutes a day: **~2.5 months** (reading every evening,
sleeping in between).

If you wonder about the cost of a single page turn: `0.3 s × 35 mA = 0.0029 mAh`.
If all of the 500 mAh were spent only on turning pages it would come to ~170,000
pages — but in reality the awake time is ~100 times that.

---

## 2. The deep-sleep breakdown

The standby time is determined by the **three largest items** in this table:

| Item | With TPS63020 | With TPS63900 | How to reduce it |
|---|---|---|---|
| Regulator quiescent current | **25 µA** | **0.075 µA** | Switch to the TPS63900 (the PCB is redrawn) |
| Battery divider (100k/100k) | 21 µA | 21 µA | 1 MΩ/1 MΩ → 2.1 µA |
| ESP32-C3 deep sleep | ~5 µA | ~5 µA | — |
| Regulator feedback divider (1M/180k) | 2.8 µA | 0 µA | There is no divider on the TPS63900 |
| Panel deep sleep (SSD1680 Mode 1) | 1 µA | 1 µA | 0.7 µA if Mode 2 is used |
| Charge controller (MCP73831) | ~0.5 µA | ~0.5 µA | — |
| **Total** | **~55 µA** | **~28 µA** | |

```
500 mAh / 55 µA = 9.090 hours = 379 days ≈ 12 months
500 mAh / 28 µA = 17.857 hours = 744 days ≈ 24 months
```

> **Panel deep sleep depends on a driver detail.** The SSD1680's `0x10` command
> in Mode 1 (A[1:0] = 01) draws **1 µA** while preserving the RAM; in Mode 2 it
> draws 0.7 µA but the framebuffer contents are lost. If the panel does not enter
> sleep (for example if `epdSleep()` is not called) the draw rises to **20 µA** —
> that means a third of the total budget. Verify that the `epdSleep()` call
> remains in the code.
>
> In addition the panel comes out of sleep **only with a hardware reset
> (HWRESET)**; a software reset (`0x12`) does not wake it. Make sure the firmware
> calls `epdHwReset()` on every wake.

> **Surprise:** The XIAO ESP32-C3 board (including the regulator, charging circuit
> and all the board electronics) draws **44 µA** of sleep current. So the easy
> build's standby time is **almost the same** as the default PCB build. The PCB
> build's advantage is not the standby time but the **thickness** (9.5 mm /
> 15 mm).

### The real limit: the cell's self-discharge

The calculation in the table hits a ceiling even if you reduce the draw to zero.
Li-Po cells self-discharge by ~2–3% per month:

```
500 mAh × 2.5%/month = 12.5 mAh/month ≈ 17 µA average equivalent
```

So **there is no practical benefit in going below ~17 µA.** The TPS63900 + 1 MΩ
divider (~7 µA) theoretically gives 8 years, but in reality the battery
self-discharges in 1.5–2 years. Therefore:

| Goal | Recommended |
|---|---|
| Simplicity, ordering from a single source | TPS63020 + 100k divider → 13 months |
| If a long standby is wanted | Make the divider 1 MΩ/1 MΩ → 21 months |
| If battery life is the project's main goal | TPS63900 + 1 MΩ divider → limited by cell discharge |

---

## 3. Regulator comparison

> ⚠️ **Correction:** In the first design a note was made that "the TPS63900 is
> pin-compatible with the TPS63020." **This was wrong.** When the datasheets were
> verified it turned out that the TPS63020 is **14-pin VSON (DSJ), 3 × 4 mm**
> (SLVS916I Section 3/5), while the TPS63900 is **10-pin WSON (DSK), 2.5 × 2.5 mm**
> (SLVSET3D Table 5-1). The pin count, names and layout are different — **the PCB
> layout has to change.** If you want to switch you have to draw the layout in
> `docs/03` from scratch; this is not a "part swap" but a "redesign."

| | **TPS63020** (default) | **TPS63900** (low-power option) |
|---|---|---|
| Quiescent current | 25 µA (max 50 µA) | **75 nA** (max 1 µA) |
| Shutdown current | 0.1 µA | 60 nA |
| Package | **VSON-14 (DSJ), 3 × 4 mm** | **WSON-10 (DSK), 2.5 × 2.5 mm** |
| Input range | 1.8–5.5 V | 1.8–5.5 V |
| Output | 2 A at 3.3 V | >400 mA (VI ≥ 2.0 V, VO = 3.3 V) |
| Output setting | Two-resistor divider (`R5`/`R6`) | **CFG1/2/3 resistors** with 32 preset levels |
| Setting for 3.3 V | `R5` = 1 MΩ, `R6` = 180 kΩ | **`CFG1` = 36.5 kΩ (1%), `CFG2` = 0 Ω, `CFG3` = 0 Ω, `SEL` = High** |
| Continuous divider current | 2.8 µA | **0** (no divider) |
| Mode pin | `PS/SYNC` (GND = save, VIN = PWM) | **None** — it runs single-mode, it has a `SEL` pin |
| External components | 1.5 µH, 2 × 10 µF, 3 × 22 µF, 0.1 µF | 2.2 µH, 10 µF, 22 µF |
| Verification status | ✅ pinout verified | ✅ pinout verified |

**Why the TPS63020 by default?** The output voltage is set with two resistors, its
calculation is transparent, and thanks to the `PS/SYNC` pin you can choose the
ripple/efficiency balance with a solder jumper. The TPS63900's `CFG1/2/3`
resistors require **1% tolerance and ±200 ppm/°C**; an ordinary 5% resistor can
shift the output voltage and puts the panel at risk.

**If you want to switch** the gain is large: 25 µA → 0.075 µA, so the total sleep
current falls from ~51 µA to ~26 µA and the standby time doubles. But you have to
redraw the PCB in `docs/03`, re-verify the `EPD` supply, and source 1% `CFG`
resistors.

---

## 4. Wake flow

```
                    ┌─ 60 s inactivity ───────────────────┐
                    ▼                                      │
  ┌──────────┐   ┌───────────────────┐   ┌─────────────┐    │
  │  AWAKE   │──>│ epdSleep()        │──>│ DEEP SLEEP  │    │
  │ ~20 mA   │   │ turn off RF, panel│   │ ~51 µA      │    │
  │          │   │ to sleep, write   │   │             │    │
  │          │   │ state to RTC      │   │             │    │
  └──────────┘   └───────────────────┘   └──────┬──────┘    │
       ▲                                        │           │
       │                    GPIO2 or GPIO3 LOW  │           │
       └────────────────────────────────────────┘           │
              (ext1, ANY_LOW)
```

Before shutting down, in order:

1. `epdSleep()` — the deep sleep command to the panel (`0x10`). It turns off the
   panel's charge pump; otherwise the panel continues to draw on the order of
   ~mW.
2. Turn off the Wi-Fi radio (`WiFi.mode(WIFI_OFF)`) — it causes a draw above
   100 µA.
3. Write the library position and the page number to `RTC_DATA_ATTR` variables.
   This area is preserved in deep sleep; there is no need to write to flash (flash
   writes are both slow and consume lifetime).
4. `esp_deep_sleep_enable_ext1_wakeup(BIT(GPIO2) | BIT(GPIO3), ANY_LOW)`
5. `esp_deep_sleep_start()`

**The critical UX detail after waking:** inside `setup()` the `was_deep_sleep`
flag is read and the device **skips the splash screen**. Which button is pressed
is read and it goes directly to the relevant page. The user presses the button and
within ~1 second sees the continuation of the page they were reading — the boot
logo, the library list or the menu do not get in the way. Because this is the
action a reader does most often, it is the part given the most care.

**GPIO20 (menu) cannot wake** — it is not in the RTC domain. It is pressed after
waking.

---

## 5. Battery voltage and percentage

`power.cpp` measures the battery voltage in this way:

1. `analogReadMilliVolts(VBAT_ADC)` — uses the ESP32-C3's internal calibration
2. The **median** of 15 samples (discards outliers)
3. The average of 8 samples (reduces noise)
4. `× 2` — divider ratio 1:2

The Li-Po voltage→percentage mapping is **not** linear; the voltage drops under
load. The table used:

| Voltage | Percentage | Note |
|---|---|---|
| 4.20 V | 100% | Full |
| 4.05 V | 90% | |
| 3.95 V | 75% | |
| 3.87 V | 60% | |
| 3.80 V | 45% | Nominal |
| 3.72 V | 30% | |
| 3.65 V | 15% | |
| 3.55 V | 5% | |
| 3.40 V | 0% | **A warning screen is shown** |
| 3.30 V | — | The protection circuit cuts off the battery |

> **Note:** The voltage measurement must be made while the device is **awake and
> unloaded**. If you measure during a page refresh and the current the panel draws
> pulls the voltage down, you see a wrong value like "5%". The firmware takes the
> measurement before the refresh.

---

## 6. Measurement: how do you find out what it really draws?

The numbers in this document are **calculations**, not measurements. To measure
your own device:

### Method 1 — USB power meter (easiest, coarse)

Plug in a USB-C power meter. You see the current while the device is awake; in
sleep the meter shows almost zero (most meters' resolution is not enough for µA).

### Method 2 — multimeter (mandatory for sleep current)

```
USB-C ──> [measurement point] ──> device
              ▲
         multimeter (mA/µA range)
```

Disconnect the device from USB and connect a multimeter in series with the battery
(µA range). Wait with the power switch on; read the current once it goes to sleep
after 60 seconds.

> ⚠️ The multimeter's **burden voltage** (the voltage drop across its internal
> resistance) can reset the device on the current spikes at the moment of waking.
> If the device resets during measurement, switch the multimeter to a higher range
> or wake it by shorting briefly.

### Method 3 — Nordic Power Profiler Kit II (the most accurate)

It shows the sleep/wake transitions on a graph. ~$100; buy it once and use it for
life. If you want to shorten the wake time, you see with this device how long
which piece of code takes.

### Comparison table

| Measurement | Expected | What you measured | Likely cause |
|---|---|---|---|
| Deep sleep, TPS63020 | ~51 µA | >200 µA | Wi-Fi didn't turn off, or the panel didn't enter sleep |
| Deep sleep, XIAO | ~44 µA | >500 µA | On-board LEDs like NeoPixel, or the serial port is active |
| Awake, idle | ~20 mA | >60 mA | Wi-Fi was left on |
| Transfer mode | ~90 mA | | |

---

## 7. Improvement ideas

| Idea | Gain | Cost |
|---|---|---|
| Switch to the TPS63900 | 25 µA → 0.075 µA | Configuration resistor table, pinout check |
| Make the divider 1 MΩ/1 MΩ | 21 µA → 2.1 µA | The `C11` value and a measurement wait |
| Cut the divider with a MOSFET | 21 µA → ~0 | 1 GPIO (none free) + measurement with a 1% duty cycle |
| MAX17048 fuel gauge | More accurate % + ~3 µA | No I²C pin (GPIO8/9 are taken) |
| Shorten the wake time | Awake time | Complex code — partial refresh is already 0.3 s |
| Adaptive sleep time | 10 s instead of 60 s while turning pages | A user setting |
| Verify the panel sleep | mW → µW | Make sure the `epdSleep()` call remains in the code |

**The single highest-yield change** is to make the divider 1 MΩ/1 MΩ: two resistors
change, 19 µA is gained, and no new part is needed.

---

Back: [06 · Books and Fonts](06-books-and-fonts.md) · Next: [08 · Troubleshooting](08-troubleshooting.md)
