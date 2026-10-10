> Türkçe sürüm: [02-schematic.tr.md](02-schematic.tr.md)

# 02 · Schematic — Block-by-Block Description

Schematic: [`hardware/schematic/pocket-reader-schematic.svg`](../hardware/schematic/pocket-reader-schematic.svg)
Connection table (170 connections / 39 nets / 64 parts): [`hardware/schematic/connections.csv`](../hardware/schematic/connections.csv)
Verified datasheet data: [`hardware/schematic/pinouts.md`](../hardware/schematic/pinouts.md)

> Colour code: **thick orange** = power path · thin black = signal ·
> **blue label** = net name (same name = connected) · **red box** = information
> that must be verified.

---

## A · USB-C input and ESD protection

| Part | Value | Function |
|---|---|---|
| `J1` | TYPE-C-31-M-12 | 5 V input + data. Works only as a sink (UFP) |
| `R1`, `R2` | 5.1 kΩ | Pull CC1 and CC2 to GND |
| `U1` | USBLC6-2SC6 | ESD protection on the D+/D− lines |

**Why are the 5.1 kΩ resistors mandatory?** In USB-C, a device signals that it is
a sink by placing a resistor of 5.1 kΩ between the CC line and GND. Without these
resistors a typical USB-C charger **never supplies 5 V** — this is the most
common USB-C mistake, and its symptom is "the cable is plugged in but nothing
happens."

**Why is ESD protection necessary?** A person touching the USB cable carries a
static charge of a few kV, and this goes directly to the ESP32-C3's GPIO18/19.
`U1` damps it. It can be skipped, but the death of the chip is silent and
irreversible.

`U1` is also connected to `VBUS` (for the reference of the TVS diodes inside it).

---

## B · Li-Po charging (MCP73831)

| Part | Value | Calculation |
|---|---|---|
| `U2` | MCP73831T-2ACI/OT | `-2` = fixed 4.20 V (the correct variant for Li-Po) |
| `R3` | **2 kΩ** | `I_charge = 1000 V / R3` → **500 mA** |
| `C1` | 4.7 µF | `VDD` bypass (datasheet: min 4.7 µF) |
| `C2` | 4.7 µF | `VBAT` bypass (datasheet: min 4.7 µF, **mandatory**) |
| `R4` + `D1` | 470 Ω + green LED | Charge indicator |
| `STAT` pin | — | **Tri-state**: LOW while charging, HIGH when full |

**SOT-23-5 pinout** (datasheet Table 3-1): `1` = STAT · `2` = VSS · `3` = VBAT ·
`4` = VDD · `5` = PROG. **The DFN package's pinout is completely different**
(1/2 = VDD, 3/4 = VBAT, 5 = STAT, 6 = VSS, 8 = PROG, 9 = EP) — using the numbers
of the wrong package breaks the charging circuit.

**The choice of `R3` depends on your battery.** For a 500 mAh battery, 500 mA ≈ 1C
is a healthy value. If your battery is 250 mAh, make `R3` **4 kΩ** (250 mA). The
valid range is **2 kΩ … 67 kΩ** (≈500 mA … 15 mA). If `PROG` is left open,
charging is completely disabled.

**Why is `STAT` tri-state?** While charging it pulls the pin to GND, and when full
it pulls it to HIGH. This way the LED is connected **between VDD and STAT**: while
charging, the current follows the path VDD → `R4` → LED → STAT → GND and the LED
lights; when full, both ends become ~5 V and the LED goes out. (If you connect the
LED to GND it never lights — the classic mistake.) The MCP73832's STAT is
**open-drain**; this connection does not work with it.

**Why is `C2` mandatory?** The datasheet requires at least 4.7 µF on `VBAT` — so
that the charge cycle stays stable when the battery is not installed (or when the
protection circuit cuts off). If omitted, charging behaves unstably in the
battery-less state.

> The MCP73831 is thermally protected. At 500 mA, with a 5 V input and a 3.0 V
> battery voltage, it dissipates ~1 W. The small SOT-23-5 package tolerates this
> for **short periods**; leave ventilation in the plastic case or lower the
> charge current.

---

## C · Battery and protection

| Part | Function |
|---|---|
| `BT1` | 1S Li-Po, 3.0–4.2 V, 500 mAh |
| `U4` + `Q1` | DW01A + FS8205A — **only if you use an unprotected cell** |
| `SW1` | SPDT slide switch: between the battery and the regulator |

It is deliberate that `SW1` is **between the battery and the regulator**. If it
were at the regulator's input, the charging circuit could not charge the battery
while the device is off. In this position, if USB-C is plugged in while the device
is off, the battery charges normally.

**Why is Li-Po protection mandatory?** If you take an unprotected Li-Po below
3.0 V the cell is permanently damaged, and if you take it above 4.25 V it swells
and a fire risk arises. Buying a ready protected cell (recommended) or adding
`U4`+`Q1` is mandatory. The `U4`+`Q1` block is marked in the schematic with a
**dashed outline (DNP — do not populate)**.

---

## D · 3.3 V buck-boost (TPS63020)

> ⚠️ **The package has 14 pins, not 10.** TPS63020 = **VSON-14 (DSJ), 3 × 4 mm**
> (datasheet SLVS916I, Section 3/5). Pinout: 1 = `VINA`, 2 = `GND`,
> 3 = `FB`, 4–5 = `VOUT`, 6–7 = `L2`, 8–9 = `L1`, 10–11 = `VIN`, 12 = `EN`,
> 13 = `PS/SYNC`, 14 = `PG`, the thermal pad underneath = `PGND`.

| Part | Value | Source / rationale |
|---|---|---|
| `U3` | TPS63020DSJR | 1.8–5.5 V input → 3.3 V, 2 A (VIN > 2.5 V) |
| `L1` | **1.5 µH**, ≥2 A saturation | Datasheet Table 4: `XFL4020-152ML`. 2.2 µH also works at light load |
| `R5` / `R6` | **1 MΩ / 180 kΩ** | Datasheet **Table 3**, the exact row for a 3.3 V output |
| `R7` | 100 kΩ | `EN` pull-up. `EN` **must not be left open** |
| `C3`, `C4` | 2 × 10 µF | Input capacitors (Table 4) |
| `C5` | 0.1 µF | `VINA` bypass. **Must not exceed 0.22 µF** (Section 8.2.2.5) |
| `C6`, `C7`, `C8` | 3 × 22 µF | Output capacitors (Table 4) |
| `C9` | 0.1 µF | High-frequency bypass |
| `JP1` | 0 Ω jumper | `PS/SYNC` selection |

### Feedback resistors

The TPS63020's feedback reference is **V_FB = 500 mV** (min 495, max 505 mV) and
the output is set with a two-resistor divider:

```
R1 = R2 × (Vout / V_FB − 1)
Vout = 0.5 V × (1 + 1M / 180k) = 0.5 × 6.556 = 3.28 V
```

Datasheet Table 3 gives `R5 = 1 MΩ`, `R6 = 180 kΩ` for a 3.3 V output — and we use
exactly that row. The datasheet recommends keeping `R6` around ~200 kΩ (smaller
increases the divider current, larger makes it susceptible to noise).

The divider's continuous current is `0.5 V / 180 kΩ = 2.8 µA` — it must be taken
into account in the sleep budget (see `docs/07`).

### PS/SYNC jumper (`JP1`)

| Connection | Behaviour | When |
|---|---|---|
| `GND` (default) | Power-save mode. High efficiency at light load, output ripple a bit high | Normal use |
| `VINA` | Forced PWM. Low ripple, lower efficiency at light load | If you see ghosting/instability on the display |

Why ripple matters for e-paper: the charge pump inside the panel generates ±15 V
from `VDD`. If there is large ripple at the input, the pump becomes unstable and
smudges/ghosting appear in the image. The default design is `GND`; if you see a
problem, move the jumper to `VINA`.

### Why buck-boost?

The battery swings between 4.2 V → 3.0 V. Since a constant 3.3 V is required:

- The battery is **above** 3.3 V → the voltage must be stepped down (buck)
- The battery is **below** 3.3 V → the voltage must be stepped up (boost)

If an LDO were used, the last 20–25% of the battery would be unusable. It would
also be dissipated as heat: `(Vbatt − 3.3) × I`.

---

## E · ESP32-C3-MINI-1

| Part | Value | Function |
|---|---|---|
| `U5` | ESP32-C3-MINI-1-N4 | RISC-V 160 MHz, 4 MB flash, Wi-Fi/BLE, 13.2 × 16.6 × 2.4 mm |
| `R8` | 10 kΩ | `EN` pull-up (datasheet: R = 10 kΩ) |
| `C10` | 1 µF | `EN` RC delay (datasheet: C = 1 µF) |
| `C11` | 10 µF | Module 3V3 buffer (datasheet Fig. 9-1) |
| `C12` | 0.1 µF | High-frequency bypass, placed **right at the module** |

The `R8`+`C10` combination (10 kΩ / 1 µF = 10 ms time constant) prevents the chip
from starting at an unstable voltage while the supply is rising. Without this RC,
the chip randomly restarts on some power supplies. Espressif's datasheet also
gives exactly these values.

### The rationale of the pin assignment

The full rationale is in `docs/00-overview.md` §2. Summary:

- **Strapping pins (datasheet Table 4-3).** For SPI boot (normal operation)
  **GPIO2 = 1** and **GPIO9 = 1** must hold; **GPIO8's value does not matter** —
  GPIO8 must be 1 only in *joint download boot* mode, and it is also used for ROM
  message suppression.
  - `GPIO2` → `BTN_DOWN`: the 100 kΩ pull-up provides the startup condition
  - `GPIO9` → `EPD_BUSY`: **because the panel `BUSY` is idle-HIGH, the condition
    is satisfied by itself** (`R10` was added for assurance)
  - `GPIO8` → `EPD_RST`: does not need a pull-up, but `R9` was added to keep the
    panel reset line defined
- **GPIO3 and GPIO2** are in the RTC domain → the page buttons wake the device
  from sleep
- **GPIO5** = `ADC2_CH0` → battery measurement (all ADC1 pins are in use)
- **GPIO20** = `U0RXD`, input only → menu button (cannot wake)

> ⚠️ **The BUSY polarity is disputed in this panel family.** The SSD1680
> datasheet (Rev 0.14, Table 5-2) defines `BUSY` as active-HIGH (HIGH = busy), but
> some vendor drivers assume the opposite. The firmware makes this configurable
> with `EPD_BUSY_ACTIVE_HIGH` in `config.h` and **if it falls through to a timeout
> it writes to the screen that the polarity may be wrong** — the hardware under no
> condition locks up in an infinite loop. How to verify:
> [`docs/05`](05-firmware-setup.md) and `firmware/README.md`.

### Antenna keep-out area

The module's antenna must overhang the PCB edge, and there must be **no copper and
no parts** under or around it. If this area is violated the range drops seriously.
The exact dimensions are in `pinouts.md` §2; typically 15 mm of clear space ahead
of the antenna tip and 5–10 mm on the sides along the antenna width are required.

---

## F · E-paper interface (24-pin FPC)

> ✅ **This table is now verified.** The pin numbers are taken directly from the
> GoodDisplay GDEY0213B74 datasheet (Section 5, p.8). Source:
> [`pinouts.md`](../hardware/schematic/pinouts.md) §1.

### FPC pin table (1–24)

| Pin | Name | Direction | Our net | Description |
|----:|---|---|---|---|
| 1 | NC | — | — | **Left unconnected** |
| 2 | `GDR` | → | `GDR` | N-MOSFET gate drive (external boost) |
| 3 | `RESE` | ← | `RESE` | Boost current-sense input |
| 4 | NC | — | — | **Left unconnected** |
| 5 | `VSH2` | — | `VSH2` | Positive source drive — 1 µF/25 V |
| 6 | `TSCL` | — | — | Temperature sensor I²C (not used) |
| 7 | `TSDA` | — | — | Temperature sensor I²C (not used) |
| 8 | `BS1` | ← | `GND` | **L = 4-wire SPI** (the mode we use) |
| 9 | `BUSY` | ← | `EPD_BUSY` | Busy output |
| 10 | `RES#` | ← | `EPD_RST` | Reset, active **low** |
| 11 | `D/C#` | ← | `EPD_DC` | HIGH = data, LOW = command |
| 12 | `CS#` | ← | `EPD_CS` | Chip select, active low |
| 13 | `SCL` | ← | `EPD_SCK` | SPI clock |
| 14 | `SDA` | ← | `EPD_MOSI` | SPI data |
| 15 | `VDDIO` | — | `3V3` | **Must be tied to VCI** |
| 16 | `VCI` | — | `3V3` | Chip supply (2.2–3.7 V, typ 3.0 V) |
| 17 | `VSS` | — | `GND` | Ground |
| 18 | `VDD` | — | `VDD_CORE` | Core logic (regulated from VCI) — 1 µF/25 V |
| 19 | `VPP` | — | — | **For test only** |
| 20 | `VSH1` | — | `VSH1` | Positive source drive — 1 µF/25 V |
| 21 | `VGH` | — | `VGH` | Positive gate drive — boost output |
| 22 | `VSL` | — | `VSL` | Negative source drive — 1 µF/25 V |
| 23 | `VGL` | — | `VGL` | Negative gate drive — 1 µF/25 V |
| 24 | `VCOM` | — | `VCOM` | VCOM drive — 1 µF/25 V |

### The external capacitor network — cannot be skipped

The datasheet's reference circuit (Section 12, p.29) requires **eight 1 µF / 25 V**
capacitors: `VCI`, `VDDIO`, `VDD`, `VSH1`, `VSH2`, `VSL`, `VGL`, `VCOM`. Also
4.7 µF / 25 V for the input.

**These are the reservoirs of the ±15 V charge pump inside the panel.** If they
are missing or of the wrong value, the image comes out faint, smudged or
half-drawn. All of them must be rated at 25 V — the charge pump output reaches
±15 V and a 6.3 V capacitor is punctured.

### External VGH/VGL boost circuit

The panel brings out the `GDR` (pin 2) and `RESE` (pin 3) pins exactly for this
job: the generation of VGH/VGL is done externally. Datasheet reference circuit:

| Part | Value |
|---|---|
| `L2` | 47 µH / 500 mA |
| `D2`, `D3`, `D4` | MBR0530 Schottky |
| `Q2` | Si1308EDL N-MOSFET (drives the `GDR` pin) |
| `C23`, `C24` | 4.7 µF / 25 V, 1 µF / 25 V |
| `R18`, `R19` | 1 MΩ, 2.2 Ω (`RESE`) |

> ⚠️ This block is **the highest-risk part** in this project: the values are taken
> from the datasheet's reference circuit and it is a switching step-up converter.
> While building the first prototype it is strongly recommended that you use a
> **ready-made adapter board** (see the table below), and only put this block on
> your own PCB after comparing it one-to-one with your panel datasheet.

### Buffer capacitor

`C22` (100 µF, low ESR) absorbs the current spike at the moment of a panel
refresh. The panel typically draws **3.5 mA** (datasheet: 10.5 mW @ VCI = 3.0 V)
but the peak current at the moment of refresh is much higher. If `C22` is missing
or far from `J2`, you get the "sometimes the screen stays half-drawn" fault — and
its cause is very hard to find.

### Raw panel or breakout module?

| | Raw panel + your own circuit | **Adapter board** (recommended for the first try) |
|---|---|---|
| Thickness | ~1.05 mm (glass only) | ~5 mm (board + connector) |
| Connection | 24-pin 0.5 mm FPC | 8-pin 2.54 mm header |
| External boost | **You have to build it** | Provided on the board |
| External capacitors | **You have to build them** | Provided on the board |
| Difficulty | High | Low — just jumper wires |
| Target | PCB build (final) | Easy build **and first PCB prototype** |

> 💡 **Practical suggestion:** On your PCB, leave room for an **8-pin 2.54 mm
> header** next to the 24-pin FPC connector. If you have trouble building the
> boost circuit, you plug the adapter board into this header and bring it up; then
> you populate the boost block and switch to the raw panel. The same firmware
> works with both.

---

## G · Buttons

| Button | GPIO | Function | Wakes? |
|---|---|---|---|
| `SW2` | 3 (`BTN_UP`) | Page back | ✅ |
| `SW3` | 2 (`BTN_DOWN`) | Page forward | ✅ |
| `SW4` | 20 (`BTN_MENU`) | Menu / library | ❌ |

Each button: 100 kΩ pull-up (to 3V3) + 100 nF (to GND).

**Why is the 100 nF there?** Mechanical buttons bounce for a few hundred
microseconds while closing, producing dozens of edges. Software debounce solves
this but is of no use **at the moment of waking**: while the chip is waking it
reads a line that is still bouncing and detects the wrong button. The capacitor
eliminates this bounce in hardware. That is why each button has both a 100 nF and
software debounce.

**Wake mask:** `ext1` watches only GPIO2 and GPIO3
(`ESP_EXT1_WAKEUP_ANY_LOW`). GPIO20 cannot be put into the mask because it is not
in the RTC domain.

---

## H · Battery sensing

| Part | Value | Calculation |
|---|---|---|
| `R16`, `R17` | 100 kΩ / 100 kΩ | Divider ratio 1:2 |
| `C11` | 100 nF | ADC input filter |

```
V_adc = V_batt × R17/(R16+R17) = V_batt / 2
4.20 V → 2.10 V   (within the ESP32-C3 ADC's measurement range)
3.00 V → 1.50 V
```

The software multiplies the value it reads by 2. The continuous current is
`4.2 V / 200 kΩ = 21 µA` — the second largest consumption item in sleep.

**To reduce it:** use 1 MΩ/1 MΩ (2.1 µA). However, the input impedance is limited
by the ADC's need to charge its sampling capacitor; in that case lower `C11` to
10 nF and add a short wait before the measurement. Alternative: the `MAX17048`
I²C fuel gauge (with its own divider inside, ~3 µA) — in `docs/09`.

---

## Verification

Check the connection list for consistency:

```bash
cd hardware/schematic
python3 gen_netlist.py --check
```

This command reports:
- An undefined part or pin
- A single-node (unconnected) net
- A part connected to no net
- **Parts whose pin numbers have not yet been verified** (`UNVERIFIED`)

Both the `connections.csv` and `pocket-reader.net` files are generated from this
script; do not edit them by hand.

---

Back: [01 · Bill of Materials](01-bill-of-materials.md) · Next: [03 · PCB](03-pcb.md)
