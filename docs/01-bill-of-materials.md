# 01 · Bill of Materials (BOM)

Separate lists for the two build levels. If you choose the easy build, do not
look at the PCB list at all; the two lists **share the common parts** (buttons,
battery, wire).

> The prices are **approximate** single-unit values as of 2026 and are in USD.
> Shipping, tax and exchange rate are not included. Check stock before ordering.

---

## A · Easy build (breadboard / protoboard)

A soldering iron and ~1 hour are enough. Easy to debug, low portability.

| # | Part | Recommended | Qty | ~Price | Note |
|---|---|---|---|---|---|
| 1 | MCU board | **Seeed XIAO ESP32-C3** | 1 | $6 | Charging circuit and 3.3 V regulator are already on it |
| 2 | E-paper module | **Waveshare 2.13&quot; e-Paper Module (V3)** | 1 | $18 | SSD1680 driver, with breakout board. Get the *Module*, not the *HAT* |
| 3 | Li-Po battery | 1S, 500–1000 mAh, **internally protected** | 1 | $5 | 502030 or 402025. If you buy an unprotected one, DW01A+FS8205A is required |
| 4 | Button | 6×6 mm tactile button | 3 | $0.5 | Page back / forward / menu |
| 5 | Protoboard | 5×7 cm single-sided | 1 | $1 | A breadboard will do too, but it isn't portable |
| 6 | Wire | 30 AWG silicone-coated, female-female jumper | 1 | $2 | |
| 7 | Header | 2.54 mm female header strip | 1 | $0.5 | For the XIAO and the e-paper module |
| 8 | Switch | Small SPDT slide switch | 1 | $0.5 | Power switch |
| | | | | **~$34** | |

**Critical warning:** The XIAO ESP32-C3 has its own charging circuit (380 mA fast /
40 mA trickle). Also, **do not buy** a TP4056 module — it is unnecessary, and if
two charging circuits are connected in parallel it damages the battery.

**When choosing a panel:** Waveshare has three different products and they get
confused:

| Product name | Contents | For us |
|---|---|---|
| 2.13inch e-Paper **Module** | Raw panel + breakout board | ✅ **get this one** |
| 2.13inch e-Paper **HAT** | Module + Raspberry Pi 40-pin header | ➖ works, unnecessarily large |
| 2.13inch e-Paper **HAT (B)** | Red/black/yellow/white 4-colour panel | ❌ its driver is different (not SSD1680), it does not support partial refresh |

**The V3 revision is mandatory.** V1/V2 use a different controller (UC8151D) and
the LUT tables in `firmware/src/epd_lut.h` do not fit.

---

## B · PCB build (thin, permanent device)

| # | Part | Part number | Qty | ~Price | Footprint |
|---|---|---|---|---|---|
| 1 | MCU module | **ESP32-C3-MINI-1-N4** | 1 | $3 | `RF_Module:ESP32-C3-MINI-1` |
| 2 | Buck-boost | **TPS63020DSJR** | 1 | $3 | **VSON-14 (DSJ), 3 × 4 mm** — not the 10-pin one! |
| 3 | Charge controller | **MCP73831T-2ACI/OT** | 1 | $1 | SOT-23-5 (`-2` = 4.20 V) |
| 4 | ESD protection | **USBLC6-2SC6** | 1 | $0.4 | SOT-23-6 |
| 5 | Inductor | **1.5 µH**, ≥2 A saturation, 4×4 mm | 1 | $0.5 | Datasheet Table 4: `XFL4020-152ML` |
| 6 | USB-C receptacle | TYPE-C-31-M-12 (16 pin) | 1 | $1 | HRO |
| 7 | FPC connector | **Hirose FH12-24S-0.5SH** (or Molex 5034802400) | 1 | $1 | 24P, 0.5 mm, bottom contact |
| 8 | Slide switch | MSK-12C02 | 1 | $0.5 | SPDT |
| 9 | Tactile button | PTS645 or equivalent | 3 | $1 | SMD |
| 10 | LED | Green 0603 | 1 | $0.1 | Charge indicator |
| 11 | Panel capacitors | 1 µF / **25 V** × 8, 4.7 µF / 25 V × 2 | 10 | $1 | `VCI/VDDIO/VDD/VSH1/VSH2/VSL/VGL/VCOM` + input |
| 12 | Panel boost | 47 µH/500 mA, MBR0530 × 3, Si1308EDL, 4.7 µF, 1 µF, 1 MΩ, 2.2 Ω | 9 | $2 | Datasheet Section 12 — **not needed** if you use an adapter board |
| 13 | Resistor | 0603 / 0805, 1% | ~20 | $2 | Values are in `connections.csv` |
| 14 | Capacitor | 0603 / 0805 X5R/X7R | ~12 | $2 | |
| 15 | Capacitor | 100 µF, 1206, low ESR | 1 | $0.5 | Panel buffer |
| 16 | PCB | 2 layer, 1.6 mm, ENIG | 5 | $2+shipping | 58 × 28 mm (JLCPCB, 5 pcs) |
| 17 | Raw panel | **GDEY0213B74** | 1 | $12 | GoodDisplay or AliExpress |
| 18 | Li-Po battery | 1S 500 mAh protected | 1 | $5 | Inside the case 35 × 20 mm |
| 19 | Case | 3D printed, ~4 g filament | 1 | $1 | `hardware/enclosure/case.scad` |
| 20 | Screw | M1.6 × 4 mm | 4 | $0.5 | For the lid |
| | | | | **~$36** | |

### Resistor and capacitor values

The full list, together with which net each is connected to:
[`hardware/schematic/connections.csv`](../hardware/schematic/connections.csv)

Summary of the critical values:

| Part | Value | Why this value |
|---|---|---|
| `R1`, `R2` | 5.1 kΩ | USB-C UFP identification. The USB-C specification makes it mandatory |
| `R3` | 2 kΩ | `I_charge = 1000 / R3` = 500 mA (MCP73831 formula) |
| `R5` / `R6` | **1 MΩ / 180 kΩ** | `Vout = 0.5 V × (1 + 1M/180k)` = 3.28 V — datasheet Table 3, the 3.3 V row |
| `R7`, `R8` | 100 kΩ / 10 kΩ | EN pull-ups |
| `R9`, `R10` | 100 kΩ | The startup condition of the strapping pins (see `docs/00` §2) |
| `R13`–`R15` | 100 kΩ | Button pull-up |
| `R16`, `R17` | 100 kΩ / 100 kΩ | Battery divider, 1:2. 21 µA at 4.2 V — the dominant draw in sleep |
| `C22` | 100 µF | Buffer for the panel refresh current spike. **If omitted, the panel runs unstably** |
| `C25`–`C27` | 100 nF | Hardware button debounce (for the bounce at the moment of waking) |

---

## C · Common parts (both builds)

| Part | Qty | Note |
|---|---|---|
| Li-Po 1S 500 mAh, protected | 1 | If you buy an unprotected one, `U4`+`Q1` must be added |
| Tactile button | 3 | |
| Slide switch | 1 | |
| M1.6 × 4 mm screw | 4 | |

---

## D · Tools (one-time, ~$60–120)

| Tool | Mandatory? | Note |
|---|---|---|
| Soldering iron (adjustable, 350 °C) | ✅ for the easy build | A fine tip for SMD on the PCB |
| Hot air station or toaster oven | ✅ for the PCB | VSON-10 and SOT-23-5 are hard by hand |
| Digital multimeter | ✅ | Continuity and voltage checking |
| USB-C cable (data-capable!) | ✅ | Some cables are for charging only |
| 3D printer | ➖ | It works without a case too |
| USB-TTL converter | ➖ | The device is programmed over USB-C, not needed |

---

## E · Where to buy

**Turkey**

| Source | Suitable products |
|---|---|
| [Robotistan](https://www.robotistan.com) | XIAO boards, e-paper modules, buttons, Li-Po |
| [Direnc.net](https://www.direnc.net) | e-paper, passive components, connectors |
| [Mouser TR](https://www.mouser.com.tr) | TPS63020, MCP73831, USBLC6, the TPS series |
| [DigiKey TR](https://www.digikey.com.tr) | The same parts, wider stock |

**International**

| Source | Suitable products |
|---|---|
| [Seeed Studio](https://www.seeedstudio.com) | XIAO ESP32-C3 (manufacturer) |
| [Waveshare](https://www.waveshare.com) | e-paper modules (manufacturer) |
| [Good Display](https://www.good-display.com) | Raw panels (manufacturer) |
| [LCSC](https://www.lcsc.com) | All SMD components, combined order with the PCB |
| [JLCPCB](https://jlcpcb.com) | PCB fabrication + LCSC parts in a single order |
| AliExpress | Usually the cheapest for the panel and Li-Po, delivery 3–6 weeks |

> **Tip:** When ordering a PCB at JLCPCB, you can select the TPS63020 and
> MCP73831 through "Parts Library" and take the **assembly service**. That way
> you don't have to solder the two hardest SMD parts yourself. The cost increases
> by ~$15, but the success rate rises a lot.

---

## F · Pre-order checklist

- [ ] Is the panel the **V3** revision and does it have the **SSD1680** controller?
- [ ] Is the panel the **Module** (with breakout board) or the **HAT**? (Module for the easy build)
- [ ] Is the Li-Po **internally protected**? (if not, has `U4`+`Q1` been added to the BOM?)
- [ ] Does the Li-Po's physical size fit the case? (target: ≤ 35 × 20 × 6 mm)
- [ ] Is it the **-2SC6** variant of the USBLC6-2SC6? (there are variants with a different pinout)
- [ ] Is it the **-2ACI/OT** code of the MCP73831? (`-2` = fixed 4.20 V)
- [ ] Is the inductor's saturation current ≥ 1.5 A?
- [ ] Is `hardware/schematic/gen_netlist.py --check` clean?

---

Back: [00 · Overview](00-overview.md) · Next: [02 · Schematic](02-schematic.md)
