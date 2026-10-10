#!/usr/bin/env python3
"""
Pocket Reader — PCB placement data generator.

Three outputs from a single source:

    hardware/pcb/placement.csv   shared data for the 2D PCB drawing and the 3D
                                 model (read by tools/gen_pcb_layout.py and site/index.html)

WHY: the PCB's 2D technical drawing and the 3D model must show the same parts in
the same places. Two coordinate lists maintained by hand in two separate places
inevitably drift apart. Here they are defined in one place.

IMPORTANT — this is a PLACEMENT PROPOSAL, not a production-ready PCB:
  * Traces (routing) are not drawn
  * No thermal or EMC optimisation has been done
  * The antenna keep-out area is marked but not verified against the board
  * The real placement must be done in KiCad and pass DRC

Usage:
    python3 gen_placement.py            # produce placement.csv
    python3 gen_placement.py --check    # verify (overlap, overhang, coverage)
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "hardware" / "pcb" / "placement.csv"

BOARD_W = 45.0          # mm, +X to the right
BOARD_H = 24.0          # mm, +Y up
EDGE_KEEPOUT = 0.4      # a part must be at least this far inside the edge

# --------------------------------------------------------------------------
# Active parts — placed by hand (mm, centre coordinates)
# ref: (value, kind, x, y, rot, w, h, height, side, note)
#   kind     : class used in the 3D model and on the silkscreen
#   w,h      : footprint X and Y extent (mm)
#   height   : height above the board (mm) — for 3D
#   side     : "top" | "bottom"
# --------------------------------------------------------------------------

ACTIVE: list[tuple] = [
    # --- Module: the antenna overhangs the LEFT edge (the only free direction for keep-out) ---
    ("U5",  "ESP32-C3-MINI-1", "module",   8.30, 12.00, 0, 16.6, 13.2, 2.40, "top",
     "The antenna tip overhangs the left edge; no copper underneath or around it"),

    # --- USB-C: bottom edge, its mouth faces out ---
    ("J1",  "USB-C 16P",       "conn",    24.50,  3.75, 0,  9.0,  7.5, 3.20, "top",
     "Overhangs the edge by 0.5 mm so it seats in the case opening"),

    # --- FPC: top edge, the panel cable folds over onto the board ---
    ("J2",  "FPC 24P 0.5mm",   "conn",    31.00, 20.60, 0, 14.0,  5.5, 2.00, "top",
     "Bottom-contact, ZIF-latched"),

    # --- Power: the buck-boost core ---
    ("U3",  "TPS63020DSJR",    "ic",      29.00, 11.00, 0,  3.0,  4.0, 0.90, "top",
     "Hot loop: the C3/C4 input capacitors at its base"),
    ("L1",  "1.5uH",           "inductor",36.50,  6.00, 0,  4.0,  4.0, 1.80, "top",
     "The FB trace must not run under this part"),

    # --- Charging ---
    ("U2",  "MCP73831",        "ic",      21.50, 20.50, 0,  3.0,  3.0, 1.10, "top",
     "Drives the STAT LED"),
    ("D1",  "green LED",       "led",     27.00, 16.50, 0,  1.6,  0.8, 0.60, "top",
     "Charge indicator"),

    # --- USB ESD ---
    ("U1",  "USBLC6-2SC6",     "ic",      21.50, 16.50, 0,  3.0,  3.0, 1.10, "top",
     "On the D+/D- lines, close to the USB-C"),

    # --- Panel boost (datasheet Section 12) ---
    ("L2",  "47uH",            "inductor",20.00, 11.00, 0,  4.5,  4.5, 2.00, "top",
     "VGH/VGL booster"),
    ("Q2",  "Si1308EDL",       "ic",      32.50, 10.00, 0,  3.0,  3.0, 1.10, "top",
     "Drives the GDR pin"),
    ("D2",  "MBR0530",         "diode",   24.50, 13.00, 0,  2.7,  1.6, 1.00, "top", ""),
    ("D3",  "MBR0530",         "diode",   24.50, 11.00, 0,  2.7,  1.6, 1.00, "top", ""),
    ("D4",  "MBR0530",         "diode",   24.50,  9.00, 0,  2.7,  1.6, 1.00, "top", ""),

    # --- Buttons: vertical stack on the RIGHT edge (aligned with the case openings) ---
    ("SW2", "tactile",         "button",  42.00, 17.20, 0,  4.5,  4.5, 3.50, "top",
     "Page back (GPIO3) — 4.5 x 4.5 mm SMD tactile"),
    ("SW3", "tactile",         "button",  42.00, 12.00, 0,  4.5,  4.5, 3.50, "top",
     "Page forward (GPIO2)"),
    ("SW4", "tactile",         "button",  42.00,  6.80, 0,  4.5,  4.5, 3.50, "top",
     "Menu (GPIO20)"),

    # --- Switch: bottom edge, right ---
    ("SW1", "SPDT slide",      "switch",  34.25,  1.80, 0,  4.5,  2.8, 1.50, "top",
     "Accessible from the case's side face"),

    # --- Battery: bottom edge, left, solder pad ---
    ("BT1", "Li-Po 1S",        "battery", 7.50,  2.30, 0,  5.0,  3.5, 0.00, "top",
     "The battery wire is soldered directly (JST PH alternative)"),
]

# --------------------------------------------------------------------------
# Passives — placed automatically around the related part
# (ref, value, kind, anchor_ref, slot)
#   slot: 0..7 -> the eight positions around the anchor part
# --------------------------------------------------------------------------

PASSIVE_SLOTS = [
    (-3.0,  2.6), (0.0,  3.2), (3.0,  2.6),
    (-3.6,  0.0),               (3.6,  0.0),
    (-3.0, -2.6), (0.0, -3.2), (3.0, -2.6),
]

PASSIVES: list[tuple] = [
    # Buck-boost surroundings (datasheet Table 4)
    ("C3",  "10uF",   "cap",  "U3", 0), ("C4",  "10uF",   "cap",  "U3", 7),
    ("C5",  "0.1uF",  "cap",  "U3", 2), ("C6",  "22uF",   "cap",  "U3", 4),
    ("C7",  "22uF",   "cap",  "U3", 3), ("C8",  "22uF",   "cap",  "U3", 5),
    ("C9",  "0.1uF",  "cap",  "U3", 6), ("R5",  "1M",     "res",  "U3", 1),
    ("R6",  "180k",   "res",  "U3", 6), ("R7",  "100k",   "res",  "L1", 3),
    ("JP1", "0R",     "jumper","L1", 5),
    # Charging surroundings
    ("C1",  "4.7uF",  "cap",  "U2", 0), ("C2",  "4.7uF",  "cap",  "U2", 2),
    ("R3",  "2k",     "res",  "U2", 6), ("R4",  "470R",   "res",  "U2", 7),
    # USB ESD surroundings
    ("R1",  "5.1k",   "res",  "U1", 0), ("R2",  "5.1k",   "res",  "U1", 2),
    # Module surroundings (datasheet Fig 9-1)
    ("C11", "10uF",   "cap",  "U5", 2), ("C12", "0.1uF",  "cap",  "U5", 4),
    ("R8",  "10k",    "res",  "U5", 5), ("C10", "1uF",    "cap",  "U5", 6),
    # Panel interface + panel capacitor network (datasheet Section 12)
    ("R9",  "100k",   "res",  "J2", 0), ("R10", "100k",   "res",  "J2", 2),
    ("C13", "1uF",    "cap",  "J2", 6), ("C14", "1uF",    "cap",  "J2", 7),
    ("C15", "1uF",    "cap",  "L2", 0), ("C16", "1uF",    "cap",  "L2", 2),
    ("C17", "1uF",    "cap",  "L2", 5), ("C18", "1uF",    "cap",  "L2", 6),
    ("C19", "1uF",    "cap",  "Q2", 2), ("C20", "1uF",    "cap",  "Q2", 5),
    ("C21", "4.7uF",  "cap",  "Q2", 6), ("C22", "100uF",  "cap",  "Q2", 7),
    ("C23", "4.7uF",  "cap",  "Q2", 0), ("C24", "1uF",    "cap",  "Q2", 2),
    ("R18", "1M",     "res",  "Q2", 0), ("R19", "2.2R",   "res",  "D2", 3),
    # Button surroundings
    ("R13", "100k",   "res",  "SW2", 0), ("C25", "100nF", "cap",  "SW2", 5),
    ("R14", "100k",   "res",  "SW3", 0), ("C26", "100nF", "cap",  "SW3", 5),
    ("R15", "100k",   "res",  "SW4", 0), ("C27", "100nF", "cap",  "SW4", 5),
    # Battery detection
    ("R16", "100k",   "res",  "BT1", 0), ("R17", "100k",   "res",  "BT1", 2),
    ("C28", "100nF",  "cap",  "BT1", 5),
]

# The passives' 3D height and footprint, by type
PASSIVE_GEOM = {
    "cap":    (1.6, 0.8, 0.9),   # 0603/0805 average
    "res":    (1.6, 0.8, 0.6),
    "diode":  (2.7, 1.6, 1.0),
    "jumper": (2.0, 1.25, 0.6),
}

SIZES = {p[0]: (p[4], p[5], p[6]) for p in ACTIVE}

# Areas where no part may be placed (x, y, w, h) — mm
FORBIDDEN: list[tuple[float, float, float, float]] = [
    # Antenna keep-out: the module's antenna tip and its surroundings. Neither a part nor copper.
    # Espressif HW Design Guidelines Fig. 21: 15 mm is required from the sides; on a
    # 45 mm board this does not fit, so the antenna is made to overhang the edge and
    # its underside is cleared.
    (0.0, 5.0, 7.0, 14.0),
    # M1.6 mounting holes — same position as the PCB standoffs in case.scad.
    # 3.2 mm pad + 0.4 mm allowance; no part may overlap these.
    (0.5, 0.5, 4.0, 4.0),      # bottom left  (centre 2.5, 2.5)
    (40.5, 0.5, 4.0, 4.0),     # bottom right (centre 42.5, 2.5)
    (0.5, 19.5, 4.0, 4.0),     # top left     (centre 2.5, 21.5)
    (40.5, 19.5, 4.0, 4.0),    # top right    (centre 42.5, 21.5)
]

CLEARANCE = 0.35        # minimum clearance between parts (mm)
GRID_STEP = 0.5         # step of the free-space scan (mm)


def _hits(x, y, w, h, occupied, margin=CLEARANCE) -> bool:
    for ox, oy, ow, oh in occupied:
        if (abs(x - ox) < (w + ow) / 2 + margin and
                abs(y - oy) < (h + oh) / 2 + margin):
            return True
    return False


def _inside(x, y, w, h) -> bool:
    if (x - w / 2 <= EDGE_KEEPOUT or x + w / 2 >= BOARD_W - EDGE_KEEPOUT or
            y - h / 2 <= EDGE_KEEPOUT or y + h / 2 >= BOARD_H - EDGE_KEEPOUT):
        return False
    for fx, fy, fw, fh in FORBIDDEN:
        if (x + w / 2 > fx and x - w / 2 < fx + fw and
                y + h / 2 > fy and y - h / 2 < fy + fh):
            return False
    return True


def build() -> list[dict]:
    """Actives by hand, passives with overlap-free greedy placement."""
    rows: list[dict] = []
    occupied: list[tuple[float, float, float, float]] = []

    for ref, value, kind, x, y, rot, w, h, height, side, note in ACTIVE:
        rows.append(dict(ref=ref, value=value, kind=kind, x=x, y=y, rot=rot,
                         w=w, h=h, height=height, side=side, group="active",
                         note=note))
        occupied.append((x, y, w, h))

    # Candidate points for the free-position scan (inside the board, on the grid)
    grid = [(round(gx * GRID_STEP, 2), round(gy * GRID_STEP, 2))
            for gx in range(1, int(BOARD_W / GRID_STEP))
            for gy in range(1, int(BOARD_H / GRID_STEP))]

    for ref, value, kind, anchor, slot in PASSIVES:
        ax, ay = next((p[3], p[4]) for p in ACTIVE if p[0] == anchor)
        w, h, height = PASSIVE_GEOM[kind]

        # 1) Try the eight positions around the anchor in order
        order = [slot] + [i for i in range(8) if i != slot]
        placed = None
        for i in order:
            dx, dy = PASSIVE_SLOTS[i]
            cx, cy = round(ax + dx, 2), round(ay + dy, 2)
            if _inside(cx, cy, w, h) and not _hits(cx, cy, w, h, occupied):
                placed = (cx, cy)
                break

        # 2) Otherwise: pick the free point closest to the anchor
        if placed is None:
            best, best_d = None, None
            for gx, gy in grid:
                if not _inside(gx, gy, w, h) or _hits(gx, gy, w, h, occupied):
                    continue
                d = (gx - ax) ** 2 + (gy - ay) ** 2
                if best_d is None or d < best_d:
                    best, best_d = (gx, gy), d
            placed = best

        if placed is None:
            raise RuntimeError(f"No free space found for {ref}")
        cx, cy = placed
        rows.append(dict(ref=ref, value=value, kind=kind, x=cx, y=cy, rot=0,
                         w=w, h=h, height=height, side="top", group="passive",
                         note=f"around {anchor}"))
        occupied.append((cx, cy, w, h))

    return rows


def overlaps(a: dict, b: dict, margin: float = 0.0) -> bool:
    """Do the two rectangles overlap (AABB)?"""
    return (abs(a["x"] - b["x"]) < (a["w"] + b["w"]) / 2 + margin and
            abs(a["y"] - b["y"]) < (a["h"] + b["h"]) / 2 + margin)


def check(rows: list[dict]) -> int:
    problems: list[str] = []

    for r in rows:
        if (r["x"] - r["w"] / 2 < EDGE_KEEPOUT or
                r["x"] + r["w"] / 2 > BOARD_W - EDGE_KEEPOUT or
                r["y"] - r["h"] / 2 < EDGE_KEEPOUT or
                r["y"] + r["h"] / 2 > BOARD_H - EDGE_KEEPOUT):
            # The U5 antenna and J1 overhang on purpose
            if r["ref"] in ("U5", "J1"):
                continue
            problems.append(
                f"{r['ref']}: extends outside the board "
                f"(x {r['x']-r['w']/2:.1f}..{r['x']+r['w']/2:.1f}, "
                f"y {r['y']-r['h']/2:.1f}..{r['y']+r['h']/2:.1f})")

    for r in rows:
        if r["ref"] in ("U5",):          # the U5 antenna overhangs on purpose
            continue
        for fx, fy, fw, fh in FORBIDDEN:
            if (r["x"] + r["w"] / 2 > fx and r["x"] - r["w"] / 2 < fx + fw and
                    r["y"] + r["h"] / 2 > fy and r["y"] - r["h"] / 2 < fy + fh):
                problems.append(
                    f"{r['ref']}: enters a keep-out area "
                    f"(x {fx}..{fx+fw}, y {fy}..{fy+fh})")

    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if overlaps(a, b):
                problems.append(f"{a['ref']} overlaps {b['ref']}")

    known = {p[0] for p in ACTIVE} | {p[0] for p in PASSIVES}
    try:
        sys.path.insert(0, str(HERE.parent / "hardware" / "schematic"))
        import gen_netlist                                   # noqa: E402
        missing = sorted(set(gen_netlist.COMPONENTS) - known)
        extra = sorted(known - set(gen_netlist.COMPONENTS))
        for m in missing:
            problems.append(f"{m}: in the netlist but not in the placement")
        for e in extra:
            problems.append(f"{e}: in the placement but not in the netlist")
    except Exception as exc:                                 # pragma: no cover
        problems.append(f"could not compare with the netlist: {exc}")

    if problems:
        print(f"{len(problems)} problems:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"OK — {len(rows)} parts, no overlap, all inside the board, "
          f"consistent with the netlist.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="PCB placement data generator")
    ap.add_argument("--check", action="store_true",
                    help="do not write, only verify")
    args = ap.parse_args()

    rows = build()
    if args.check:
        return check(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Pocket Reader PCB placement proposal — "
                    f"{BOARD_W} x {BOARD_H} mm, origin bottom left"])
        w.writerow(["ref", "value", "kind", "x_mm", "y_mm", "rot_deg",
                    "w_mm", "h_mm", "height_mm", "side", "group", "note"])
        for r in rows:
            w.writerow([r["ref"], r["value"], r["kind"], r["x"], r["y"],
                        r["rot"], r["w"], r["h"], r["height"], r["side"],
                        r["group"], r["note"]])
    print(f"wrote: {OUT}  ({len(rows)} parts)")
    return check(rows)


if __name__ == "__main__":
    sys.exit(main())
