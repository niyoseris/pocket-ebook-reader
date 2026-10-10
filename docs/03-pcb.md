# 03 · PCB Design

If you chose the easy build, skip this document. For the PCB build:

| Feature | Value |
|---|---|
| Dimensions | **45 × 24 mm** |
| Layers | 2 (top: signal + power · bottom: GND plane) |
| Thickness | 1.6 mm |
| Surface finish | ENIG (HASL will do too; ENIG is safer at fine pitch) |
| Minimum trace width | 0.25 mm |
| Minimum clearance | 0.2 mm |
| Via | 0.3 mm hole / 0.6 mm pad |
| Copper thickness | 1 oz |

> These dimensions are within JLCPCB's standard (cheapest) category — no extra
> charge. 5 pcs ~$2 + shipping.

---

## 1. Placement plan

Lay the board out **horizontally (landscape)**; the device rests flat with the
screen facing forward.

```
┌──────────────────────────────────────────────────────┐
│  [U5 ESP32-C3-MINI-1]        [J2 FPC 24P]            │  ◀ top edge = panel side
│   ▲ antenna feed ┐             ▲                     │
│                  │             │                     │
│   ┌──────────────┴──┐   ┌──────┴─────────┐           │
│   │ ANTENNA         │   │   L1  U3       │           │
│   │ KEEP-OUT AREA   │   │ ┌──┐ TPS63020  │           │
│   │ (NO copper)     │   │ └──┘           │           │
│   │                 │   │                │           │
│   └─────────────────┘   └────────────────┘           │
│                                                      │
│  [U2 MCP73831]   [U1 USBLC6]   [SW1 connector]       │
│                                                      │
│  [J1 USB-C]                    [SW2] [SW3] [SW4]     │  ◀ bottom edge
└──────────────────────────────────────────────────────┘
```

Critical placement rules:

| Rule | Why |
|---|---|
| **The antenna must overhang the module's edge** | Range. The module's antenna must be at the board edge |
| **No copper under or around the antenna** | Same reason — a copper plane detunes the antenna |
| **`C9` (0.1 µF) right at the module's 3V3 pin** | The shorter the bypass capacitor's trace, the more effective it is |
| **The buck-boost's "hot loop" must be minimal** | A separate heading below |
| **The FB trace must stay away from the inductor** | If the inductor's magnetic field couples into FB, the output voltage drifts |
| **J2 (FPC) on the top edge, away from L1** | If the panel cable passes through the inductor's field, noise appears in the image |
| **`C10` (100 µF) right at J2** | The panel's current spike must be met by the shortest path |

---

## 2. Buck-boost placement (the most critical part)

In switching regulators, the PCB layout is more decisive than the schematic. A bad
layout means a board that doesn't work.

**The hot loop** is this path:

```
C2 (+) → U3 VIN → (internal switches) → U3 PGND → C2 (−)
```

**Minimise the area enclosed by this loop** as much as possible. Every mm² of
extra area increases the switching noise radiated around it and lowers efficiency.

In practice:

1. Place the `C2` (10 µF) input capacitor **right next to U3's VIN and PGND pins**;
   the trace length should be < 3 mm.
2. Place `L1` as close to U3 as possible; make the L1–L2 traces short and **thick**
   (0.6 mm).
3. Place the `C4`/`C5` output capacitors next to the VOUT pin.
4. Make the bottom layer an **unbroken GND plane**; on the top layer, drop to
   ground with vias under the power traces.
5. Put **ground stitching vias** around the regulator — they let the loop current
   return through the plane.
6. Place the `R5`/`R6` feedback resistors close to U3's FB pin and **do not route
   the FB trace under/next to L1**.

---

## 3. Trace widths

| Trace | Width | Current |
|---|---|---|
| `VBUS`, `VBAT`, `VBAT_SW` | 0.6 mm | ~500 mA |
| `3V3` main distribution | 0.5 mm | ~400 mA peak |
| `L1` ↔ U3 (L1/L2 pins) | 0.6 mm | ~1 A peak |
| SPI (`SCK`, `MOSI`) | 0.25 mm | Signal |
| Button, ADC | 0.25 mm | Signal |
| GND | Plane | — |

Impedance control is **not required** for `EPD_SCK`/`EPD_MOSI`: the SPI clock rate
is between 4–10 MHz and the trace length is under 30 mm. A series termination
resistor is not needed either.

---

## 4. Antenna keep-out area

> ⚠️ If this area is violated the Wi-Fi range drops below 10 metres and the cause
> is not electrically visible — you just say "it doesn't reach."

The exact dimensions are in `pinouts.md` §2. The general rule:

The Espressif Hardware Design Guidelines (p.23, Fig. 21) give the exact
dimensions:

- There must be no copper/component/trace **to the left, above and to the right
  of the antenna for at least 15 mm**
- Leave **6 mm** of clear space in the direction facing the module body
- **The copper plane must be cut** underneath this area too (bottom layer) — clear
  the GND plane in this region
- In the case print, do not put even plastic in this region; leave **at least
  15 mm in every direction within the product enclosure**
- Placing the module at the **centre** of the board and cutting a notch on all
  four sides is **wrong**

**The antenna situation of this design (honest record).** In `placement.csv` the
module (U5) **butts right against** the left edge (x = 0) and does not overhang;
under and around it there is a 7 × 14 mm copper-free keep-out area. The distance to
the case's left wall is `(62 − 45) / 2 = 8.5 mm`. Espressif recommends **15 mm**
within a product enclosure, i.e. this dimension is below the recommendation:

| Situation | Assessment |
|---|---|
| Plastic case (this design) | 8.5 mm is acceptable; RF passes through plastic, no loss expected |
| Metal or carbon-coated case | **Insufficient** — use the `ESP32-C3-MINI-1U` (U.FL) and move the antenna outside |
| Option of rotating the module | The clearance on the board's short edges is 4 mm — worse. Left/right is the best direction |

If you want to improve the dimension: push the board against the left side of the
case (if the board shifts 4 mm to the left the distance becomes 12.5 mm) or
increase the case to 66 mm.

> On a 45 × 24 mm board a 15 mm side clearance **does not fit**. So at this size
> either place the antenna so it overhangs the board edge (one direction is
> enough) or use the **ESP32-C3-MINI-1U** variant (with an external antenna
> connector) and fit a U.FL antenna — that variant has no keep-out area, and if
> you are targeting a metal case that is the right choice.

If you use the `ESP32-C3-MINI-1U` (external antenna connector variant) this
constraint disappears and you can fit a U.FL antenna — if you are targeting a
metal case that is the right choice.

---

## 5. Connecting the panel to the board

The raw panel is connected with a 24-pin, 0.5 mm pitch FPC. Two options:

| Method | Difficulty | Thickness | Note |
|---|---|---|---|
| **FPC connector** (recommended) | Medium | Thin | Hirose FH12-24S-0.5SH, bottom contact, with latch |
| Direct soldering | High | Thinnest | Soldering the FPC to the board is permanent but irreversible |

If you use a connector, place it on the **board's top edge** so the panel folds
over and sits on top of the board. The panel cable's bend radius must be at least
3 mm; a sharp fold breaks the conductors.

**Orientation check:** FPC connectors come in "top contact" and "bottom contact"
variants, and **if you get the wrong one the panel is connected backwards.**
Verify by measuring the `RST` and `BUSY` lines the first time you fit the panel
(see `docs/04` §4).

---

## 6. Fabrication files

There are **no** ready-made Gerbers in the repo — because producing fabrication
files before the pinout verification is complete would not be responsible. Create
your own files like this:

```bash
# 1. Verify the connection list
cd hardware/schematic
python3 gen_netlist.py --check          # shows the missing pin numbers

# 2. From pinouts.md, enter the pin numbers into PINMAP in gen_netlist.py
#    (13 UNVERIFIED entries were left)

# 3. Regenerate the netlist
python3 gen_netlist.py

# 4. In KiCad:
#    pcbnew → File → Import → Netlist → pocket-reader.net
#    Place the parts (according to the placement plan above)
#    Route the traces, fill the GND plane
#    File → Fabrication Outputs → Gerbers
```

### JLCPCB order settings

| Setting | Value |
|---|---|
| Layers | 2 |
| Size | 45 × 24 mm |
| Quantity | 5 |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| "Parts Library" assembly | **Recommended for the TPS63020 + MCP73831 + ESP32-C3-MINI-1** |

If you use the assembly service you won't have to solder the two hardest SMD parts
(VSON-10 and SOT-23-5) yourself; the cost increases by ~$15 and the success rate
rises noticeably.

---

## 7. Pre-fabrication checklist

- [ ] `python3 gen_netlist.py --check` clean (no UNVERIFIED entry)
- [ ] No copper in the antenna keep-out area (both top and bottom layer)
- [ ] Hot-loop area is minimal; `C2` right at U3
- [ ] `C9` right at the module's 3V3 pin
- [ ] `C10` right at J2
- [ ] The FB trace is away from the inductor
- [ ] The bottom layer is an unbroken GND plane (except the antenna region)
- [ ] There are stitching vias around the regulator
- [ ] The board size fits the case (45 × 24 mm, matches the boss positions in
      `case.scad`)
- [ ] The button holes are aligned with the holes in the case wall
- [ ] The USB-C connector overhangs the edge by 0.5–1 mm (as much as the case
      thickness)

---

## 8. First power-up

> 🛑 **Measure the `3V3` rail before connecting the panel.** If the regulator
> gives a wrong voltage instead of 3.3 V (for example 5 V), the panel dies in a
> second and there is no coming back.

Order:

1. **Without panel, without battery** — plug in only USB-C
2. Measure **3.25–3.35 V** at the `U3` output (across C4)
3. If not, check the `R5`/`R6` values and their solder joints — do not touch the
   panel
4. If correct, verify the same voltage at the `U5` 3V3 pin
5. Unplug USB, connect the battery and switch on, repeat the same measurement
6. If all is correct, fit the panel and flash the firmware

Detailed steps: [`docs/04-assembly.md`](04-assembly.md) §4

---

Back: [02 · Schematic](02-schematic.md) · Next: [04 · Assembly](04-assembly.md)
