# Fabrication Specification

What to order, and the design rules the PCB is checked against. Every number
here is matched to a real service's published capability, not chosen to make the
board look tidy — a DRC that passes against rules nobody can manufacture is
worthless.

Target service: **JLCPCB, 4-layer FR4**, standard process, green solder mask.

---

## Stack-up

| | Layer | Copper | Purpose |
|---|---|---|---|
| L1 | `F.Cu` | 1 oz (35 µm) | Components, signals, GND pour in the gaps |
| — | prepreg 3313 | 0.0994 mm | |
| L2 | `In1.Cu` | 0.5 oz (15 µm) | **Solid ground plane** — unbroken except under the antenna |
| — | core | 1.065 mm | |
| L3 | `In2.Cu` | 0.5 oz (15 µm) | Power: 3V3, VBAT_SW, VBUS |
| — | prepreg 3313 | 0.0994 mm | |
| L4 | `B.Cu` | 1 oz (35 µm) | Signals, GND pour |

Standard JLCPCB 1.6 mm four-layer build (JLC04161H-3313). Total ≈ 1.6 mm.

**Why four layers, when the case is only 13 mm thick and the board is 45 × 24 mm.**
Because a two-layer routing of this board does not close. There are 64 parts on
24 mm of depth, including a TPS63020 buck-boost whose switching loop has to stay
small, and a panel boost converter that generates ±15 V. On two layers every
return current has to find its way through a pour broken by the signals running
through it. Four layers buys a continuous ground plane, which is worth more than
the price difference: the same board is roughly $2 for five pieces in two layers
and roughly $8 in four.

The ground plane is what makes the rest of the design defensible. Once it
exists, return paths, the buck-boost loop and the panel's boost converter all
stop competing for the same copper.

---

## Design rules the DRC enforces

| Rule | Value | JLCPCB capability | Headroom |
|---|---|---|---|
| Minimum track width | **0.20 mm** | 0.09 mm | 2.2× |
| Signal track width | 0.25 mm | 0.09 mm | 2.8× |
| Power track width | 0.50 mm | 0.09 mm | 5.6× |
| Minimum clearance | **0.20 mm** | 0.09 mm | 2.2× |
| Via diameter / drill | **0.70 / 0.30 mm** | 0.25 / 0.15 mm | annular ring 0.20 mm, meets the recommended minimum |
| Minimum annular ring | 0.20 mm | 0.15 mm absolute, 0.20 mm recommended | at spec |
| Minimum hole | 0.30 mm | 0.15 mm | 2× |
| Soldermask expansion | 0 mm (1:1) | 1:1 since the June 2025 LDI upgrade | at spec |
| Soldermask clearance to trace | 0.09 mm | 0.09 mm | at spec |
| Soldermask dam (green) | 0.10 mm | 0.10 mm | at spec |
| Minimum silkscreen width | 0.15 mm | 0.15 mm | at spec |
| Minimum silkscreen text height | 1.0 mm | 1.0 mm | at spec |
| Silkscreen to pad clearance | 0.15 mm | 0.15 mm | at spec |
| Board thickness | 1.6 mm | 0.4–4.5 mm | — |
| Edge clearance (copper to board edge) | 0.30 mm | — | |
| Courtyard overlap | forbidden | — | assembly, not fab |

The rules are deliberately set near **2× the service's minimum** wherever the
board allows it. Manufacturing at the limit is how you discover that "0.09 mm"
comes with a tolerance, on your own boards, after you have paid for them. The
board is not dense enough to need the margin for routing; it needs it so that a
board made on a bad day still works.

---

## The antenna keep-out

The ESP32-C3-MINI-1's antenna sits at the module's left end, flush with the
board edge. **No copper on any of the four layers** under it, and no vias, for a
region of roughly **7 × 14 mm** at x 0–7, y 5–19 mm.

A ground plane is exactly what an antenna must not have underneath it. L2 is an
unbroken plane everywhere *except* here, and that exception is the one place
where the plane's integrity is deliberately broken.

Espressif recommends 15 mm of clearance on three sides inside an enclosure. This
board cannot provide it at 45 mm wide in a 62 mm case, which leaves 8.5 mm to the
plastic wall. That is acceptable for plastic; for a metal or metallised case the
design should move to the `ESP32-C3-MINI-1U` variant with an external U.FL
antenna, which has no keep-out requirement at all. See `docs/03-pcb.md` §4.

---

## Order summary

| Setting | Value |
|---|---|
| Layers | 4 |
| Dimensions | 45 × 24 mm |
| Quantity | 5 |
| Thickness | 1.6 mm |
| Surface finish | ENIG (HASL is acceptable; ENIG is safer at 0.5 mm pitch) |
| Copper | 1 oz outer, 0.5 oz inner (default) |
| Solder mask | Green (dam 0.10 mm), or any colour except black/white which need 0.13 mm |
| Silkscreen | White |
| Impedance control | **Not required** — the only differential pair is USB full-speed, ~20 mm long |
| Assembly | Optional but recommended for `U3` (VSON-14) and `U2` (SOT-23-5) |

---

## What this document does not claim

- **No physical prototype has been built.** Nothing here has been fabricated or
  tested. A DRC pass means the geometry obeys the rules above; it does not mean
  the circuit works.
- **The panel's external boost circuit** (`L2`, `D2`–`D4`, `Q2`, `R18`, `R19`) is
  taken from the panel datasheet's reference circuit and has never been built.
  Its values should be re-checked against the datasheet of the specific panel you
  buy, because the reference circuits differ between revisions.
- **DRC is not a design review.** It checks clearances, not whether the buck-boost
  loop is small enough, whether the ground plane has a slot under a fast signal,
  or whether the charger's thermal path is adequate.

Sources for every capability figure in the table:
<https://jlcpcb.com/capabilities/pcb-capabilities>
