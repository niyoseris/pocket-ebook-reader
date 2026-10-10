#!/usr/bin/env python3
"""Pocket Reader — PCB placement and case assembly drawings (SVG generator).

THREE DRAWINGS, ONE DATA SOURCE
===============================
This script generates three SVG files:

    hardware/pcb/pcb-layout-top.svg       top view (copper pour + silkscreen)
    hardware/pcb/pcb-layout-bottom.svg    bottom view (GND plane, mirrored)
    hardware/diagrams/case-exploded.svg   exploded case assembly drawing

All three read part positions from **hardware/pcb/placement.csv**; pin names,
pin numbers and net classes come from **hardware/schematic/connections.csv**.
Because the positions are held in one place, the drawings cannot drift from the
placement data: change placement.csv and the drawings change too. There is no
second coordinate list to update by hand (the 3D model reads the same file —
see tools/gen_placement.py).

IMPORTANT — these are PLACEMENT PROPOSALS, not a production-ready PCB:
  * Tracks (routing) are NOT drawn; the copper pour shows fill only
  * No thermal or EMC optimisation has been done
  * The antenna keep-out area is marked, but Espressif's 15 mm side-clearance
    rule cannot be met on a 45 x 24 mm board
  * The real placement must be done in KiCad and passed through DRC

Usage:
    python3 gen_pcb_layout.py            # write the three SVGs
    python3 gen_pcb_layout.py --check    # do not write; verify and report

The script runs from anywhere: input paths are resolved relative to the script
file.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

PLACEMENT_CSV = ROOT / "hardware" / "pcb" / "placement.csv"
CONNECTIONS_CSV = ROOT / "hardware" / "schematic" / "connections.csv"
CASE_SCAD = ROOT / "hardware" / "enclosure" / "case.scad"

OUT_TOP = ROOT / "hardware" / "pcb" / "pcb-layout-top.svg"
OUT_BOTTOM = ROOT / "hardware" / "pcb" / "pcb-layout-bottom.svg"
OUT_CASE = ROOT / "hardware" / "diagrams" / "case-exploded.svg"

# --- board and case constants (source: placement.csv header + case.scad) -----
BOARD_W = 45.0          # mm — same as placement.csv
BOARD_H = 24.0          # mm
CORNER_R = 1.5          # mm — board corner radius
EDGE_KEEPOUT = 0.4      # mm — mounting holes/parts from the edge (gen_placement.py)
SHEET_MM = 12.0         # px/mm — 2D drawing scale

# Antenna keep-out area (no copper). Source: placement.csv U5 note + docs/03 §4.
ANT_KEEPOUT = (0.0, 5.0, 7.0, 14.0)      # x, y, w, h  (mm)

SCALE_TOP = "12 px = 1 mm (board 540 x 288 px)"
REV = "Rev 1.0"
DATE = "2026-10-09"
LICENSE = "CERN-OHL-S-2.0"
PROJECT = "Pocket Reader"

# Case dimensions read from case.scad (derived: glass + bezel)
CASE_W, CASE_D, CASE_H = 62.0, 32.0, 13.0
CASE_WALL = 1.6
GLASS_W, GLASS_H, GLASS_T = 59.2, 29.2, 1.05
PANEL_ACTIVE_W, PANEL_ACTIVE_H = 48.55, 23.71
WINDOW_W, WINDOW_H = 49.0, 24.1
BEZEL = 1.4
PCB_T = 1.6
CELL_W, CELL_H, CELL_T = 26.0, 21.0, 4.5
REAR_PARTS = 2.5

# Stack (Z) layers — gives exactly the same total as stack_total in case.scad
STACK_LAYERS: list[tuple[str, float, str]] = [
    ("Front wall (glass lip)", 1.2, "panel frame of the case"),
    ("E-paper glass", GLASS_T, "59.2 x 29.2 mm"),
    ("FPC fold allowance", 0.8, "between glass and PCB"),
    ("PCB", PCB_T, "45 x 24 mm, 2 layers"),
    ("Tallest part", REAR_PARTS, "ESP32-C3-MINI-1 = 2.4 mm"),
    ("Li-Po pouch cell", 4.0, "402025"),
    ("Rear cover", CASE_WALL, "4 x M1.6 screws"),
]

# --- style (same palette as hardware/diagrams and hardware/schematic) --------
INK = "#334155"
INK_DARK = "#0f172a"
INK_SOFT = "#64748b"
INK_MUTE = "#475569"
PART_FILL = "#ffffff"
POUR = "#f8fafc"
ACCENT = "#b45309"
NET_BLUE = "#1d4ed8"
ANALOG = "#0e7490"
WARN_BG = "#fef2f2"
WARN_FG = "#b91c1c"
INFO_BG = "#eff6ff"
FRAME = "#cbd5e1"

FONT = ("ui-sans-serif, -apple-system, 'Segoe UI', Roboto, Helvetica, "
        "Arial, sans-serif")
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"

# Net class -> colour (derived from the connections.csv "Class" column)
CLASS_COLOUR = {"power": ACCENT, "signal": NET_BLUE, "analog": ANALOG}


# =============================================================================
#  1) Small SVG helper layer
# =============================================================================

_ATTRS = {
    "stroke_width": "stroke-width", "font_size": "font-size",
    "font_family": "font-family", "font_weight": "font-weight",
    "text_anchor": "text-anchor", "letter_spacing": "letter-spacing",
    "marker_end": "marker-end", "marker_start": "marker-start",
    "class_": "class", "fill_rule": "fill-rule", "clip_path": "clip-path",
    "stroke_dasharray": "stroke-dasharray", "stroke_linecap": "stroke-linecap",
    "stroke_linejoin": "stroke-linejoin", "paint_order": "paint-order",
    "fill_opacity": "fill-opacity", "stroke_opacity": "stroke-opacity",
    "dominant_baseline": "dominant-baseline", "transform_origin":
        "transform-origin", "shape_rendering": "shape-rendering",
    "vector_effect": "vector-effect",
}


def _n(v: float) -> str:
    """Write a number for SVG in short form (without redundant zeros)."""
    if isinstance(v, int):
        return str(v)
    s = f"{float(v):.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def esc(s: str) -> str:
    """XML text escaping."""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def attrs(**kw: object) -> str:
    """Converts snake_case keys into SVG attributes."""
    out: list[str] = []
    for key, val in kw.items():
        if val is None:
            continue
        name = _ATTRS.get(key, key).replace("_", "-")
        out.append(f'{name}="{val if isinstance(val, str) else _n(val)}"')
    return (" " + " ".join(out)) if out else ""


def rect(x: float, y: float, w: float, h: float, **kw: object) -> str:
    return f"<rect{attrs(x=x, y=y, width=w, height=h, **kw)}/>"


def circle(cx: float, cy: float, r: float, **kw: object) -> str:
    return f"<circle{attrs(cx=cx, cy=cy, r=r, **kw)}/>"


def ellipse(cx: float, cy: float, rx: float, ry: float, **kw: object) -> str:
    return f"<ellipse{attrs(cx=cx, cy=cy, rx=rx, ry=ry, **kw)}/>"


def line(x1: float, y1: float, x2: float, y2: float, **kw: object) -> str:
    return f"<line{attrs(x1=x1, y1=y1, x2=x2, y2=y2, **kw)}/>"


def path(d: str, **kw: object) -> str:
    return f"<path{attrs(d=d, **kw)}/>"


def poly(points: list[tuple[float, float]], **kw: object) -> str:
    pts = " ".join(f"{_n(x)},{_n(y)}" for x, y in points)
    return f"<polygon{attrs(points=pts, **kw)}/>"


def text(x: float, y: float, s: str, **kw: object) -> str:
    return f"<text{attrs(x=x, y=y, **kw)}>{esc(s)}</text>"


def group(body: list[str], **kw: object) -> str:
    return f"<g{attrs(**kw)}>{''.join(body)}</g>"


def halo(_colour: str = INK, w: float = 2.4) -> dict[str, object]:
    """White outline that keeps the text legible over lines/hatching.

    Returns outline attributes only; `fill` comes from the caller.
    """
    return dict(paint_order="stroke", stroke="#ffffff", stroke_width=w)


def shade(hex_colour: str, factor: float) -> str:
    """Darken/lighten a colour (1.0 = unchanged)."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (max(0, min(255, round(r * factor))),
                              max(0, min(255, round(g * factor))),
                              max(0, min(255, round(b * factor))))


def rounded_rect_path(x: float, y: float, w: float, h: float, r: float) -> str:
    """Rounded rectangle whose top-LEFT corner is (x,y); absolute L/A/Z."""
    r = min(r, w / 2, h / 2)
    return (f"M {_n(x + r)} {_n(y)} "
            f"L {_n(x + w - r)} {_n(y)} "
            f"A {_n(r)} {_n(r)} 0 0 1 {_n(x + w)} {_n(y + r)} "
            f"L {_n(x + w)} {_n(y + h - r)} "
            f"A {_n(r)} {_n(r)} 0 0 1 {_n(x + w - r)} {_n(y + h)} "
            f"L {_n(x + r)} {_n(y + h)} "
            f"A {_n(r)} {_n(r)} 0 0 1 {_n(x)} {_n(y + h - r)} "
            f"L {_n(x)} {_n(y + r)} "
            f"A {_n(r)} {_n(r)} 0 0 1 {_n(x + r)} {_n(y)} Z")


def rect_path(x: float, y: float, w: float, h: float) -> str:
    return (f"M {_n(x)} {_n(y)} L {_n(x + w)} {_n(y)} "
            f"L {_n(x + w)} {_n(y + h)} L {_n(x)} {_n(y + h)} Z")


class Frame:
    """mm -> px mapping.  Default: +X right, +Y UP (same as the placement).

    mirror=True: bottom view — X is mirrored (view from below), Y stays the same.
    """

    def __init__(self, ox: float, oy: float, scale: float = SHEET_MM,
                 width_mm: float | None = None, mirror: bool = False) -> None:
        self.ox, self.oy, self.s = ox, oy, scale
        self.width_mm, self.mirror = width_mm, mirror

    def x(self, xm: float) -> float:
        if self.mirror and self.width_mm is not None:
            xm = self.width_mm - xm
        return self.ox + xm * self.s

    def y(self, ym: float) -> float:
        return self.oy - ym * self.s

    def u(self, mm: float) -> float:
        return mm * self.s

    def pt(self, xm: float, ym: float) -> tuple[float, float]:
        return self.x(xm), self.y(ym)

    def rect_mm(self, x0: float, y0: float, w: float, h: float,
                **kw: object) -> str:
        """Rectangle whose bottom-LEFT corner is (x0,y0) mm and size is (w,h) mm."""
        xa, xb = self.x(x0), self.x(x0 + w)
        ya, yb = self.y(y0), self.y(y0 + h)
        return rect(min(xa, xb), min(ya, yb), abs(xb - xa), abs(yb - ya), **kw)

    def crect_mm(self, cx: float, cy: float, w: float, h: float,
                 **kw: object) -> str:
        """Rectangle centred at (cx,cy) mm."""
        return self.rect_mm(cx - w / 2, cy - h / 2, w, h, **kw)


def box_px(fr: Frame, x0: float, y0: float, w: float, h: float
           ) -> tuple[float, float, float, float]:
    """Converts an mm box (including mirroring) to a px box: (x, y, w, h)."""
    xa, xb = fr.x(x0), fr.x(x0 + w)
    ya, yb = fr.y(y0), fr.y(y0 + h)
    return min(xa, xb), min(ya, yb), abs(xb - xa), abs(yb - ya)


# --- dimension lines --------------------------------------------------------

def dim_h(fr: Frame, x0: float, x1: float, ymm: float, label: str, *,
          ext_from: float | None = None, size: float = 9.0,
          colour: str = INK, tick: bool = True) -> str:
    """Horizontal dimension line (in mm), arrows inward, label centred."""
    y = fr.y(ymm)
    a, b = fr.x(x0), fr.x(x1)
    el: list[str] = []
    if ext_from is not None:
        for xv in (a, b):
            el.append(line(xv, fr.y(ext_from), xv, y + (5 if y > fr.y(ext_from)
                                                        else -5),
                           stroke=colour, stroke_width=0.7,
                           stroke_dasharray="3 3"))
    el.append(line(a, y, b, y, stroke=colour, stroke_width=0.9,
                   marker_start="url(#dimArrow)", marker_end="url(#dimArrow)"))
    if tick:
        for xv in (a, b):
            el.append(line(xv, y - 4, xv, y + 4, stroke=colour,
                           stroke_width=1.0))
    el.append(text((a + b) / 2, y - 5, label, font_size=size, fill=colour,
                   text_anchor="middle", font_family=MONO, **halo()))
    return group(el)


def dim_v(fr: Frame, y0: float, y1: float, xmm: float, label: str, *,
          ext_from: float | None = None, size: float = 9.0,
          colour: str = INK) -> str:
    """Vertical dimension line (in mm)."""
    x = fr.x(xmm)
    a, b = fr.y(y0), fr.y(y1)
    el: list[str] = []
    if ext_from is not None:
        for yv in (a, b):
            el.append(line(fr.x(ext_from), yv, x - 6, yv, stroke=colour,
                           stroke_width=0.7, stroke_dasharray="3 3"))
    el.append(line(x, a, x, b, stroke=colour, stroke_width=0.9,
                   marker_start="url(#dimArrow)", marker_end="url(#dimArrow)"))
    for yv in (a, b):
        el.append(line(x - 4, yv, x + 4, yv, stroke=colour, stroke_width=1.0))
    mid = (a + b) / 2
    el.append(text(x - 6, mid, label, font_size=size, fill=colour,
                   text_anchor="middle", font_family=MONO,
                   transform=f"rotate(-90 {_n(x - 6)} {_n(mid)})", **halo()))
    return group(el)


def leader(x0: float, y0: float, x1: float, y1: float, label: str, *,
           anchor: str = "start", colour: str = INK, size: float = 8.5,
           dot: bool = True, elbow: bool = True) -> str:
    """Leader line: from part to label.  Dot at the end, label with white outline."""
    el: list[str] = []
    if elbow:
        el.append(path(f"M {_n(x0)} {_n(y0)} L {_n(x1)} {_n(y0)} "
                       f"L {_n(x1)} {_n(y1)}",
                       stroke=colour, stroke_width=0.7, fill="none"))
    else:
        el.append(path(f"M {_n(x0)} {_n(y0)} L {_n(x1)} {_n(y1)}",
                       stroke=colour, stroke_width=0.7, fill="none"))
    if dot:
        el.append(circle(x0, y0, 1.5, fill=colour, stroke="none"))
    tx = x1 + (3.5 if anchor == "start" else -3.5)
    el.append(text(tx, y1 + size * 0.35, label, font_size=size, fill=colour,
                   text_anchor=anchor, font_family=MONO, **halo()))
    return group(el)


def note(x: float, y: float, lines: list[str], *, size: float = 10.5,
         colour: str = INK_MUTE, mono: bool = False, lead: float = 15.0) -> str:
    return group([text(x, y + i * lead, s, font_size=size, fill=colour,
                       font_family=MONO if mono else None)
                  for i, s in enumerate(lines)])


# =============================================================================
#  2) Data loading — placement.csv and connections.csv
# =============================================================================

@dataclass
class Part:
    """A single part in placement.csv (mm, board origin bottom-left, +Y up)."""
    ref: str
    value: str
    kind: str
    x: float
    y: float
    rot: float
    w: float
    h: float
    height: float
    side: str
    group: str
    note: str

    @property
    def x0(self) -> float:
        return self.x - self.w / 2

    @property
    def x1(self) -> float:
        return self.x + self.w / 2

    @property
    def y0(self) -> float:
        return self.y - self.h / 2

    @property
    def y1(self) -> float:
        return self.y + self.h / 2

    @property
    def inside(self) -> bool:
        """Whether it is inside the board rectangle (touching the edge counts)."""
        return (self.x0 >= -1e-6 and self.x1 <= BOARD_W + 1e-6
                and self.y0 >= -1e-6 and self.y1 <= BOARD_H + 1e-6)


@dataclass
class Conn:
    """A single connection row in connections.csv."""
    net: str
    sinif: str
    ref: str
    pin: str
    aciklama: str

    @property
    def pin_no(self) -> str | None:
        """Pin number in the description: '(pin 13)' or 'pin 5 — ...'."""
        m = re.search(r"pin\s+([0-9]+(?:[,\s]+[0-9]+)*)", self.aciklama,
                      re.IGNORECASE)
        return m.group(1).replace(" ", "") if m else None


# The verified 24-pin FPC table in pinouts.md §1 (panel order).
# Used only for pins that connections.csv does not name.
FPC_NAMES = ["NC", "GDR", "RESE", "NC", "VSH2", "TSCL", "TSDA", "BS1",
             "BUSY", "RES#", "D/C#", "CS#", "SCL", "SDA", "VDDIO", "VCI",
             "VSS", "VDD", "VPP", "VSH1", "VGH", "VSL", "VGL", "VCOM"]
# ones that connections.csv does not number but pinouts.md verifies
FPC_PIN_FALLBACK = {"BS1": "8"}


def load_parts(csv_path: Path) -> list[Part]:
    """placement.csv -> list of Part (the first '# ' line is a comment)."""
    with csv_path.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in fh if not r.lstrip().startswith('"#')]
    reader = csv.DictReader(rows)
    parts: list[Part] = []
    for r in reader:
        parts.append(Part(ref=r["ref"], value=r["value"], kind=r["kind"],
                          x=float(r["x_mm"]), y=float(r["y_mm"]),
                          rot=float(r["rot_deg"]), w=float(r["w_mm"]),
                          h=float(r["h_mm"]), height=float(r["height_mm"]),
                          side=r["side"], group=r["group"], note=r["note"]))
    return parts


def load_connections(csv_path: Path) -> list[Conn]:
    with csv_path.open(encoding="utf-8", newline="") as fh:
        return [Conn(net=r["Net"], sinif=r["Class"], ref=r["RefDes"],
                     pin=r["Pin"], aciklama=r["Description"])
                for r in csv.DictReader(fh)]


def pin_table(conns: list[Conn], ref: str) -> dict[str, Conn]:
    """ref -> {pin_no: Conn}  (only pins whose number is known)."""
    out: dict[str, Conn] = {}
    for c in conns:
        if c.ref != ref:
            continue
        no = c.pin_no
        if no is None and c.pin in FPC_PIN_FALLBACK:
            no = FPC_PIN_FALLBACK[c.pin]
        if no is not None:
            out[no] = c
    return out


def net_colour(c: Conn | None) -> str:
    return CLASS_COLOUR.get(c.sinif, INK) if c is not None else INK_SOFT


# =============================================================================
#  3) Common SVG parts: defs, heading, warning block, title block
# =============================================================================

def svg_defs() -> str:
    """Arrows, hatch pattern, copper plane pattern."""
    return f"""<defs>
  <marker id="dimArrow" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="{INK}"/>
  </marker>
  <marker id="dimArrowA" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="{ACCENT}"/>
  </marker>
  <marker id="leadDot" viewBox="0 0 6 6" refX="3" refY="3"
          markerWidth="5" markerHeight="5">
    <circle cx="3" cy="3" r="2.4" fill="{INK}"/>
  </marker>
  <pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse"
           patternTransform="rotate(45)">
    <rect width="7" height="7" fill="{WARN_BG}"/>
    <line x1="0" y1="0" x2="0" y2="7" stroke="{ACCENT}" stroke-width="1.5"
          stroke-opacity="0.55"/>
  </pattern>
  <pattern id="gnd" width="9" height="9" patternUnits="userSpaceOnUse"
           patternTransform="rotate(45)">
    <rect width="9" height="9" fill="{POUR}"/>
    <line x1="0" y1="0" x2="0" y2="9" stroke="{ACCENT}" stroke-width="1.0"
          stroke-opacity="0.22"/>
  </pattern>
  <linearGradient id="layerTop" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/>
    <stop offset="1" stop-color="#f1f5f9"/>
  </linearGradient>
</defs>"""


def warn_box(x: float, y: float, w: float, h: float,
             heading: str, lines: list[str]) -> str:
    """Red-toned warning block — same style as the other drawings in the project."""
    el = [rect(x, y, w, h, fill=WARN_BG, stroke=WARN_FG, stroke_width=1.4,
               rx=6),
          text(x + 14, y + 22, heading, font_size=12.5, font_weight=700,
               fill=WARN_FG)]
    for i, s in enumerate(lines):
        el.append(text(x + 14, y + 42 + i * 15, s, font_size=10.2,
                       fill=WARN_FG, fill_opacity=0.92))
    return group(el)


def info_box(x: float, y: float, w: float, h: float,
             heading: str, lines: list[str]) -> str:
    el = [rect(x, y, w, h, fill=INFO_BG, stroke=NET_BLUE, stroke_width=1.3,
               rx=6),
          text(x + 12, y + 19, heading, font_size=11, font_weight=700,
               fill=NET_BLUE)]
    for i, s in enumerate(lines):
        el.append(text(x + 12, y + 35 + i * 14, s, font_size=9.6,
                       fill=NET_BLUE))
    return group(el)


def title_block(x: float, y: float, w: float, h: float, sheet_title: str,
                scale_line: str, extra: list[tuple[str, str]] | None = None
                ) -> str:
    """Title block at bottom right (project, sheet, scale, date, licence)."""
    el = [rect(x, y, w, h, fill="#ffffff", stroke=INK, stroke_width=1.2),
          line(x, y + 26, x + w, y + 26, stroke=INK, stroke_width=1.0),
          text(x + 10, y + 18, f"{PROJECT} — {REV}", font_size=12,
               font_weight=700, fill=INK_DARK),
          text(x + 10, y + 42, sheet_title, font_size=9.6, fill=INK,
               font_weight=600)]
    rows = [("Scale", scale_line), ("Date", DATE), ("Licence", LICENSE)]
    rows.extend(extra or [])
    top = y + 48
    for i, (k, v) in enumerate(rows):
        yy = top + i * 15
        el.append(text(x + 10, yy + 11, f"{k}:", font_size=8.6, fill=INK_SOFT))
        el.append(text(x + 62, yy + 11, v, font_size=8.6, fill=INK,
                       font_family=MONO))
        if i:
            el.append(line(x + 6, yy, x + w - 6, yy, stroke=FRAME,
                           stroke_width=0.6))
    return group(el)


def sheet_head(title: str, subtitle: str, w: float) -> list[str]:
    del w
    return [rect(0, 0, 0, 0, fill="none"),
            text(30, 36, title, font_size=20, font_weight=700,
                 fill=INK_DARK),
            text(30, 58, subtitle, font_size=11.5, fill=INK_SOFT)]


# =============================================================================
#  4) Footprint drawing — by part type
# =============================================================================
#  Each function draws the part's courtyard rectangle and the type-appropriate
#  pad/body geometry in mm.  The dimensions are typical SMD footprints;
#  placement.csv gives only the courtyard — the inner geometry is derived from
#  the part value and type.

def _pads(fr: Frame, p: Part, count_a: int, count_b: int, *, pad_w: float,
          pad_h: float) -> list[str]:
    """SOT-23-like: count_a pads on one long side, count_b on the opposite."""
    el: list[str] = []
    for i in range(count_a):
        cx = p.x - p.w / 2 + (i + 0.5) * p.w / count_a
        el.append(fr.crect_mm(cx, p.y - p.h / 2 + pad_h / 2, pad_w, pad_h,
                              fill=PART_FILL, stroke=INK, stroke_width=0.7,
                              rx=0.08))
    for i in range(count_b):
        cx = p.x - p.w / 2 + (i + 0.5) * p.w / count_b
        el.append(fr.crect_mm(cx, p.y + p.h / 2 - pad_h / 2, pad_w, pad_h,
                              fill=PART_FILL, stroke=INK, stroke_width=0.7,
                              rx=0.08))
    return el


def draw_chip(fr: Frame, p: Part) -> list[str]:
    """0603/0805 capacitor or resistor: two pads + body line."""
    el: list[str] = []
    pw = min(0.5, p.w * 0.34)
    ph = p.h * 0.92
    for sx in (-1, 1):
        el.append(fr.crect_mm(p.x + sx * (p.w / 2 - pw / 2), p.y, pw, ph,
                              fill=PART_FILL, stroke=INK, stroke_width=0.7,
                              rx=0.06))
    el.append(fr.crect_mm(p.x, p.y, p.w * 0.62, p.h * 0.86, fill=PART_FILL,
                          stroke=INK, stroke_width=0.8))
    return el


def draw_diode(fr: Frame, p: Part) -> list[str]:
    """Two pads + cathode band (double notch on a Schottky)."""
    el: list[str] = []
    pw = 0.42
    for sx in (-1, 1):
        el.append(fr.crect_mm(p.x + sx * (p.w / 2 - pw / 2), p.y, pw,
                              p.h * 0.9, fill=PART_FILL, stroke=INK,
                              stroke_width=0.7))
    el.append(fr.crect_mm(p.x, p.y, p.w * 0.66, p.h * 0.8, fill=PART_FILL,
                          stroke=INK, stroke_width=0.8))
    band_x = p.x + p.w * 0.33
    el.append(fr.rect_mm(band_x - 0.13, p.y - p.h * 0.34, 0.26, p.h * 0.68,
                         fill=INK, stroke="none"))
    return el


def draw_sot(fr: Frame, p: Part, variant: str) -> list[str]:
    """SOT-23-5/6 or VSON-14 body + pads."""
    el: list[str] = []
    body_w, body_h = p.w * 0.66, p.h * 0.72
    if variant == "vson14":
        n = 7
        for side in (-1, 1):
            for i in range(n):
                cx = p.x - p.w / 2 + (i + 0.5) * p.w / n
                cy = p.y + side * (p.h / 2 - 0.19)
                el.append(fr.crect_mm(cx, cy, p.w / n * 0.62, 0.38,
                                      fill=PART_FILL, stroke=INK,
                                      stroke_width=0.6))
        el.append(fr.crect_mm(p.x, p.y, p.w * 0.4, p.h * 0.34,
                              fill=shade(ACCENT, 1.55), stroke=ACCENT,
                              stroke_width=0.7, stroke_dasharray="2 1.6"))
    else:
        a, b = {"sot23_6": (3, 3), "sot23_5": (3, 2),
                "sot23_3": (2, 1)}[variant]
        el.extend(_pads(fr, p, a, b, pad_w=p.w / 3.4, pad_h=0.42))
    el.append(fr.crect_mm(p.x, p.y, body_w, body_h, fill=PART_FILL,
                          stroke=INK, stroke_width=1.0, rx=0.1))
    # pin 1 marker
    el.append(circle(fr.x(p.x - body_w / 2 + 0.3),
                     fr.y(p.y + body_h / 2 - 0.3), fr.u(0.16),
                     fill=INK, stroke="none"))
    return el


def draw_module(fr: Frame, p: Part) -> list[str]:
    """ESP32-C3-MINI-1: rows of castellation pads on the two long sides + antenna end."""
    el: list[str] = []
    el.append(fr.crect_mm(p.x, p.y, p.w, p.h, fill=PART_FILL, stroke=INK,
                          stroke_width=1.2, rx=0.25))
    count = 20                       # two edges x ~10 castellation pads
    for side in (-1, 1):
        for i in range(count):
            cx = p.x - p.w / 2 + (i + 0.5) * p.w / count
            cy = p.y + side * (p.h / 2 - 0.32)
            el.append(fr.crect_mm(cx, cy, p.w / count * 0.55, 0.64,
                                  fill=POUR, stroke=INK, stroke_width=0.6))
    rx0, ry0, rw, rh = ANT_KEEPOUT
    el.append(fr.rect_mm(rx0, ry0, rw, rh, fill="url(#hatch)", stroke=ACCENT,
                         stroke_width=0.9, stroke_dasharray="4 3"))
    ant_x = p.x - p.w / 2
    el.append(path(
        f"M {_n(fr.x(ant_x + 2.4))} {_n(fr.y(p.y - 3.4))} "
        f"L {_n(fr.x(ant_x + 2.4))} {_n(fr.y(p.y + 3.4))}",
        stroke=ACCENT, stroke_width=1.6, fill="none"))
    for i in range(5):
        yy = p.y - 2.8 + i * 1.4
        el.append(path(f"M {_n(fr.x(ant_x + 2.4))} {_n(fr.y(yy))} "
                       f"q 1.0 -0.8 2.0 0 q 1.0 0.8 2.0 0",
                       stroke=ACCENT, stroke_width=0.8, fill="none"))
    el.append(fr.crect_mm(p.x + 1.6, p.y, 4.2, 4.2, fill=shade(POUR, 1.0),
                          stroke=INK_SOFT, stroke_width=0.6,
                          stroke_dasharray="2.5 2"))
    return el


def draw_usbc(fr: Frame, p: Part) -> list[str]:
    """USB-C 16P: shell outline, two rows of signal pads, 2 mounting posts."""
    el: list[str] = []
    el.append(fr.crect_mm(p.x, p.y, p.w, p.h, fill=PART_FILL, stroke=INK,
                          stroke_width=1.3, rx=0.5))
    el.append(fr.crect_mm(p.x, p.y - p.h / 2 + 0.9, p.w - 0.6, 1.8,
                          fill=POUR, stroke=INK_SOFT, stroke_width=0.6,
                          stroke_dasharray="2.5 2"))
    pads = 8
    for row, dy in enumerate((-0.85, 0.85)):
        for i in range(pads):
            cx = p.x - 1.75 + i * 0.5
            el.append(fr.crect_mm(cx, p.y + dy, 0.3, 1.1, fill=PART_FILL,
                                  stroke=INK, stroke_width=0.5))
    for sx in (-1, 1):
        el.append(fr.crect_mm(p.x + sx * (p.w / 2 - 0.55), p.y, 1.1, 1.9,
                              fill=PART_FILL, stroke=INK, stroke_width=0.8,
                              rx=0.3))
    return el


def draw_fpc24(fr: Frame, p: Part) -> list[str]:
    """FPC 24P 0.5 mm: 24 pads + two mounting flanges + ZIF tongue."""
    el: list[str] = []
    el.append(fr.crect_mm(p.x, p.y, p.w, p.h, fill=PART_FILL, stroke=INK,
                          stroke_width=1.1, rx=0.2))
    pitch, span = 0.5, 24 * 0.5
    x_start = p.x - span / 2 + pitch / 2
    for i in range(24):
        el.append(fr.crect_mm(x_start + i * pitch, p.y - p.h / 2 + 0.75,
                              0.3, 1.4, fill=PART_FILL, stroke=INK,
                              stroke_width=0.45))
    for sx in (-1, 1):
        el.append(fr.crect_mm(p.x + sx * (p.w / 2 - 0.7), p.y, 1.4, 1.6,
                              fill=PART_FILL, stroke=INK, stroke_width=0.7,
                              rx=0.2))
    el.append(fr.crect_mm(p.x, p.y + p.h / 2 - 0.85, span + 1.2, 0.9,
                          fill=POUR, stroke=INK, stroke_width=0.7, rx=0.15))
    return el


def draw_button(fr: Frame, p: Part) -> list[str]:
    """Tactile button: 4 pads + round actuator."""
    el: list[str] = []
    el.append(fr.crect_mm(p.x, p.y, p.w * 0.82, p.h * 0.82, fill=PART_FILL,
                          stroke=INK, stroke_width=1.1, rx=0.3))
    for sx in (-1, 1):
        for sy in (-1, 1):
            el.append(fr.crect_mm(p.x + sx * (p.w / 2 - 0.6),
                                  p.y + sy * (p.h / 2 - 0.55), 1.1, 0.9,
                                  fill=PART_FILL, stroke=INK,
                                  stroke_width=0.6, rx=0.15))
    el.append(circle(fr.x(p.x), fr.y(p.y), fr.u(1.3), fill=PART_FILL,
                     stroke=INK, stroke_width=1.0))
    el.append(circle(fr.x(p.x), fr.y(p.y), fr.u(0.72), fill="none",
                     stroke=INK_SOFT, stroke_width=0.6))
    el.append(line(fr.x(p.x - 1.3), fr.y(p.y), fr.x(p.x + 1.3), fr.y(p.y),
                   stroke=INK_SOFT, stroke_width=0.5))
    el.append(line(fr.x(p.x), fr.y(p.y - 1.3), fr.x(p.x), fr.y(p.y + 1.3),
                   stroke=INK_SOFT, stroke_width=0.5))
    return el


def draw_inductor(fr: Frame, p: Part) -> list[str]:
    """Inductor: two large pads + body (winding representation)."""
    el: list[str] = []
    pw = p.w * 0.3
    for sx in (-1, 1):
        el.append(fr.crect_mm(p.x + sx * (p.w / 2 - pw / 2), p.y, pw, p.h,
                              fill=PART_FILL, stroke=INK, stroke_width=0.9))
    el.append(fr.crect_mm(p.x, p.y, p.w * 0.62, p.h * 0.86, fill=PART_FILL,
                          stroke=INK, stroke_width=1.1, rx=0.15))
    for i in range(4):
        cx = p.x - p.w * 0.24 + i * p.w * 0.16
        el.append(path(f"M {_n(fr.x(cx))} {_n(fr.y(p.y + p.h * 0.3))} "
                       f"q {_n(fr.u(p.w * 0.08))} {_n(-fr.u(p.h * 0.6))} 0 0",
                       stroke=INK, stroke_width=0.7, fill="none"))
    return el


def draw_switch(fr: Frame, p: Part) -> list[str]:
    """SPDT slide switch: 3 pads + slider slot."""
    el: list[str] = []
    el.append(fr.crect_mm(p.x, p.y, p.w, p.h, fill=PART_FILL, stroke=INK,
                          stroke_width=1.1, rx=0.25))
    for i in range(3):
        cx = p.x - p.w * 0.3 + i * p.w * 0.3
        el.append(fr.crect_mm(cx, p.y - p.h / 2 + 0.45, 0.55, 0.9,
                              fill=PART_FILL, stroke=INK, stroke_width=0.6))
    el.append(fr.crect_mm(p.x, p.y + 0.15, p.w * 0.6, p.h * 0.34,
                          fill=POUR, stroke=INK, stroke_width=0.7, rx=0.1))
    el.append(fr.crect_mm(p.x - p.w * 0.13, p.y + 0.15, p.w * 0.22,
                          p.h * 0.3, fill=INK_SOFT, stroke="none", rx=0.08))
    return el


def draw_led(fr: Frame, p: Part) -> list[str]:
    """LED: two pads + cathode marker + body."""
    el = draw_diode(fr, p)
    el.append(fr.rect_mm(p.x - p.w * 0.12, p.y - p.h * 0.4, p.w * 0.24,
                         p.h * 0.8, fill=ACCENT, stroke="none"))
    return el


def draw_battery(fr: Frame, p: Part) -> list[str]:
    """Li-Po solder pad: two tinned pads + polarity marks (the cell is not on the board)."""
    el: list[str] = []
    el.append(fr.crect_mm(p.x, p.y, p.w, p.h, fill="none", stroke=INK,
                          stroke_width=0.8, stroke_dasharray="3 2.4"))
    for sx, lbl in ((-1, "−"), (1, "+")):
        el.append(fr.crect_mm(p.x + sx * (p.w / 2 - 0.9), p.y, 1.4, p.h * 0.7,
                              fill=PART_FILL, stroke=INK, stroke_width=0.9,
                              rx=0.15))
    return el


KIND_IC_VARIANT = {
    "TPS63020DSJR": "vson14",
    "USBLC6-2SC6": "sot23_6",
    "MCP73831": "sot23_5",
}


def draw_footprint(fr: Frame, p: Part) -> list[str]:
    """Draws the part with type-appropriate pad/body geometry.

    (if/elif instead of match/case for Python 3.9 compatibility.)
    """
    kind = p.kind
    if kind in ("cap", "res", "jumper"):
        return draw_chip(fr, p)
    if kind == "diode":
        return draw_diode(fr, p)
    if kind == "led":
        return draw_led(fr, p)
    if kind == "ic":
        variant = KIND_IC_VARIANT.get(p.value)
        if variant is None:
            variant = "sot23_3" if p.value.startswith("Si") else "sot23_6"
        return draw_sot(fr, p, variant)
    if kind == "module":
        return draw_module(fr, p)
    if kind == "conn":
        return draw_usbc(fr, p) if p.ref == "J1" else draw_fpc24(fr, p)
    if kind == "button":
        return draw_button(fr, p)
    if kind == "inductor":
        return draw_inductor(fr, p)
    if kind == "switch":
        return draw_switch(fr, p)
    if kind == "battery":
        return draw_battery(fr, p)
    return [fr.crect_mm(p.x, p.y, p.w, p.h, fill=PART_FILL, stroke=INK,
                        stroke_width=0.8)]


# =============================================================================
#  5) Silkscreen placement and helpers
# =============================================================================

class LabelPlacer:
    """Non-overlapping label placement (prevents silkscreen overflow)."""

    def __init__(self) -> None:
        self.boxes: list[tuple[float, float, float, float]] = []

    def free(self, box: tuple[float, float, float, float],
             pad: float = 0.8) -> bool:
        x, y, w, h = box
        for ox, oy, ow, oh in self.boxes:
            if (x < ox + ow + pad and ox < x + w + pad
                    and y < oy + oh + pad and oy < y + h + pad):
                return False
        return True

    def take(self, box: tuple[float, float, float, float]) -> None:
        self.boxes.append(box)


def text_w(s: str, size: float) -> float:
    """Monospace text width estimate (px)."""
    return len(s) * size * 0.62


def place_label(fr: Frame, p: Part, s: str, placer: LabelPlacer,
                size: float, colour: str, *, leader_to: bool = True
                ) -> tuple[list[str], bool]:
    """Places the label around the part in the first free non-overlapping spot.

    If no spot is found a farther ring is tried and a leader line is added.
    Returns: (elements, whether a leader was used)
    """
    w = text_w(s, size)
    h = size * 1.05
    rings = [
        [(0, p.h / 2 + 1.0), (0, -(p.h / 2 + 1.0)),
         (p.w / 2 + 0.7 + w / fr.u(1) / 2, 0),
         (-(p.w / 2 + 0.7) - w / fr.u(1) / 2, 0),
         (p.w / 2 + 1.0, p.h / 2 + 0.8), (-(p.w / 2 + 1.0), p.h / 2 + 0.8),
         (p.w / 2 + 1.0, -(p.h / 2 + 0.8)), (-(p.w / 2 + 1.0),
                                            -(p.h / 2 + 0.8))],
        [(0, p.h / 2 + 2.6), (0, -(p.h / 2 + 2.6)),
         (p.w / 2 + 2.6 + w / fr.u(1) / 2, 0),
         (-(p.w / 2 + 2.6) - w / fr.u(1) / 2, 0),
         (0, p.h / 2 + 4.2), (0, -(p.h / 2 + 4.2))],
    ]
    for ring, far in zip(rings, (False, True)):
        for dx, dy in ring:
            px, py = fr.pt(p.x + dx, p.y + dy)
            box = (px - w / 2, py - h / 2, w, h)
            inside = (30 <= box[0] and box[0] + box[2] <= 690
                      and fr.y(BOARD_H) - 6 <= box[1]
                      and box[1] + box[3] <= fr.y(0) + 6)
            if placer.free(box) and (inside or far):
                placer.take(box)
                el = [text(px, py + size * 0.35, s, font_size=size,
                           fill=colour, text_anchor="middle", font_family=MONO,
                           **halo())]
                if far and leader_to:
                    ex, ey = fr.pt(
                        p.x + (dx / abs(dx) * p.w / 2 if dx else 0),
                        p.y + (dy / abs(dy) * p.h / 2 if dy else 0))
                    el.insert(0, line(ex, ey, px, py + size * 0.3,
                                      stroke=colour, stroke_width=0.5))
                return el, far
    return [text(fr.x(p.x), fr.y(p.y + p.h / 2 + 1.0), s, font_size=size,
                 fill=colour, text_anchor="middle", font_family=MONO)], True


def stitch_vias(parts: list[Part], region: tuple[float, float, float, float],
                step: float = 1.0, clear: float = 0.5
                ) -> list[tuple[float, float]]:
    """Stitching vias that fit around the buck-boost and avoid the parts.

    So the loop current can return through the plane (docs/03 §2.5).  Empty
    points on the grid are chosen; none enters a part's courtyard.
    """
    rx, ry, rw, rh = region
    out: list[tuple[float, float]] = []
    nx = int(rw / step)
    ny = int(rh / step)
    for ix in range(nx + 1):
        for iy in range(ny + 1):
            x, y = rx + ix * step, ry + iy * step
            if not (0.8 < x < BOARD_W - 0.8 and 0.8 < y < BOARD_H - 0.8):
                continue
            if (ANT_KEEPOUT[0] - 0.8 < x < ANT_KEEPOUT[0] + ANT_KEEPOUT[2] + 0.8
                    and ANT_KEEPOUT[1] - 0.8 < y
                    < ANT_KEEPOUT[1] + ANT_KEEPOUT[3] + 0.8):
                continue
            if any(abs(x - p.x) < p.w / 2 + clear
                   and abs(y - p.y) < p.h / 2 + clear for p in parts):
                continue
            if any((x - ox) ** 2 + (y - oy) ** 2 < 1.2 ** 2
                   for ox, oy in out):
                continue
            out.append((round(x, 2), round(y, 2)))
    return out


def draw_vias(fr: Frame, vias: list[tuple[float, float]]) -> str:
    el = [circle(fr.x(x), fr.y(y), fr.u(0.3), fill=ACCENT, stroke="none")
          for x, y in vias]
    el += [circle(fr.x(x), fr.y(y), fr.u(0.15), fill="#ffffff", stroke="none")
           for x, y in vias]
    return group(el)


def ant_label(fr: Frame, colour: str, lines: list[str]) -> str:
    """Antenna keep-out area label — two rotated lines that fit inside the area
    (the area is 7 x 14 mm; a single long line overflows)."""
    kx, ky, kw, kh = ANT_KEEPOUT
    yc = fr.y(ky + kh / 2)
    el: list[str] = []
    for i, s in enumerate(lines):
        px = fr.x(kx + 0.95 + i * 1.95)
        el.append(text(px, yc, s, font_size=6.4, fill=colour,
                       font_weight=700, text_anchor="middle",
                       font_family=MONO,
                       transform=f"rotate(-90 {_n(px)} {_n(yc)})",
                       **halo(colour, 2.0)))
    return group(el)


def draw_mount_holes(fr: Frame, positions: list[tuple[float, float]]) -> str:
    """4 x M1.6: 1.6 mm hole + 3.2 mm pad."""
    el: list[str] = []
    for x, y in positions:
        el.append(circle(fr.x(x), fr.y(y), fr.u(1.6), fill=PART_FILL,
                         stroke=INK, stroke_width=0.8))
        el.append(circle(fr.x(x), fr.y(y), fr.u(0.8), fill="#ffffff",
                         stroke=INK, stroke_width=0.8))
        el.append(line(fr.x(x - 0.9), fr.y(y), fr.x(x + 0.9), fr.y(y),
                       stroke=INK_SOFT, stroke_width=0.4))
    return group(el)


def table_box(x: float, y: float, w: float, title: str,
              rows: list[tuple[str, str, str, str]],
              *, note_lines: list[str] | None = None, row_h: float = 14.0,
              two_col: bool = False) -> tuple[str, float]:
    """Pin list table.  rows: (pin, name, net, class).  Returns the height."""
    per_col = (len(rows) + 1) // 2 if two_col else len(rows)
    note_h = 8 + 12 * len(note_lines or [])
    height = 34 + (per_col + 1) * row_h + note_h
    el = [rect(x, y, w, height, fill="#ffffff", stroke=INK, stroke_width=1.1),
          rect(x, y, w, 24, fill=POUR, stroke=INK, stroke_width=1.1),
          text(x + 10, y + 17, title, font_size=11, font_weight=700,
               fill=INK_DARK)]
    blocks = 2 if two_col else 1
    bw = (w - 6) / 2 - 6 if two_col else w - 20
    cols = (0.0, 30.0, 74.0) if two_col else (0.0, 46.0, 128.0)
    for b in range(blocks):
        bx = x + 10 + b * (bw + 12)
        hy = y + 34
        for cx, hdr in ((cols[0], "Pin"), (cols[1], "Name"), (cols[2], "Net")):
            el.append(text(bx + cx, hy - 3, hdr, font_size=7.4,
                           fill=INK_SOFT, font_weight=600))
        el.append(line(bx - 4, hy - 1, bx + bw, hy - 1, stroke=FRAME,
                       stroke_width=0.7))
        for i in range(per_col):
            idx = b * per_col + i
            if idx >= len(rows):
                break
            pin, name, net, sinif = rows[idx]
            ry = hy + i * row_h
            if i % 2 == 0:
                el.append(rect(bx - 4, ry, bw, row_h, fill=POUR, stroke="none",
                               fill_opacity=0.85))
            colour = CLASS_COLOUR.get(sinif, INK_SOFT)
            el.append(text(bx + cols[0], ry + row_h - 4.5, pin, font_size=7.6,
                           fill=INK_SOFT, font_family=MONO))
            el.append(text(bx + cols[1], ry + row_h - 4.5, name, font_size=7.6,
                           fill=INK, font_family=MONO))
            el.append(text(bx + cols[2], ry + row_h - 4.5, net or "—",
                           font_size=7.6,
                           fill=colour if net else INK_SOFT,
                           font_family=MONO,
                           font_weight=600 if net else 400))
    if note_lines:
        ny = y + 34 + (per_col + 1) * row_h + 6
        for i, s in enumerate(note_lines):
            el.append(text(x + 10, ny + i * 12, s, font_size=7.4,
                           fill=INK_SOFT))
    return group(el), height


def wrap(w: float, h: float, title: str, desc: str, body: list[str]) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(w)} '
            f'{_n(h)}" width="{_n(w)}" height="{_n(h)}" '
            f'font-family="{FONT}">\n'
            f'  <title>{esc(title)}</title>\n'
            f'  <desc>{esc(desc)}</desc>\n  {svg_defs()}\n'
            f'  <rect x="0" y="0" width="{_n(w)}" height="{_n(h)}" '
            f'fill="#ffffff"/>\n  ' + "\n  ".join(body) + "\n</svg>\n")


# =============================================================================
#  6) Drawing 1 — PCB top view
# =============================================================================

TOP_W, TOP_H = 1180.0, 780.0
TOP_OX, TOP_OY = 120.0, 470.0
TBL_X, TBL_W = 700.0, 450.0


def build_top(parts: list[Part], conns: list[Conn]) -> str:
    fr = Frame(TOP_OX, TOP_OY)
    j2pins = pin_table(conns, "J2")
    body: list[str] = []
    body += sheet_head(
        "PCB — TOP VIEW (placement + silkscreen)",
        "45.0 x 24.0 mm, 2 layers, 1.6 mm · 64 parts · to scale · "
        "Rev 1.0 · source: placement.csv + connections.csv", TOP_W)

    # --- warning block -------------------------------------------------------
    body.append(warn_box(30, 72, 640, 84, "⚠  EXAMPLE PLACEMENT PROPOSAL — "
                         "NOT PRODUCTION READY", [
        "Tracks (routing) are NOT drawn.  The copper pour shows fill "
        "only; no connection path is drawn.",
        "No thermal or EMC optimisation has been done; the hot-loop area, FB "
        "return path and GND return currents are unverified.",
        "The real placement must be done in KiCad and passed through DRC.  "
        "This file is a technical drawing, not a Gerber.",
    ]))

    # --- copper pour (antenna keep-out cut out) -----------------------------
    kx, ky, kw, kh = ANT_KEEPOUT
    bx, by, bw, bh = box_px(fr, 0, 0, BOARD_W, BOARD_H)
    pour_d = (rounded_rect_path(bx, by, bw, bh, fr.u(CORNER_R)) + " " +
              rect_path(*box_px(fr, kx, ky, kw, kh)))
    body.append(path(pour_d, fill=POUR, fill_rule="evenodd", stroke="none"))
    body.append(rect(*box_px(fr, kx, ky, kw, kh), fill="url(#hatch)",
                     fill_opacity=0.5, stroke="none"))
    body.append(rect(*box_px(fr, kx, ky, kw, kh), fill="none",
                     stroke=ACCENT, stroke_width=1.0,
                     stroke_dasharray="5 3"))
    body.append(ant_label(fr, ACCENT, [
        "ANTENNA KEEP-OUT", "NO COPPER (7.0 x 14.0)"]))

    # --- board outline ------------------------------------------------------
    body.append(path(rounded_rect_path(bx, by, bw, bh, fr.u(CORNER_R)),
                     fill="none", stroke=INK, stroke_width=1.6))

    # --- mounting holes + stitching vias ------------------------------------
    holes = [(2.5, 2.5), (BOARD_W - 2.5, 2.5), (2.5, BOARD_H - 2.5),
             (BOARD_W - 2.5, BOARD_H - 2.5)]
    vias = stitch_vias(parts, (25.0, 3.5, 14.0, 13.0))
    body.append(draw_vias(fr, vias))
    body.append(draw_mount_holes(fr, holes))

    # --- parts --------------------------------------------------------------
    for p in sorted(parts, key=lambda q: -(q.w * q.h)):
        body.append(group(draw_footprint(fr, p), class_="part"))

    # --- silkscreen: ref (all), value on large parts ------------------------
    placer = LabelPlacer()
    short = {"module", "conn", "ic", "inductor", "button", "switch",
             "battery", "diode"}
    for p in parts:
        el, _ = place_label(fr, p, p.ref, placer, 7.2, ACCENT)
        body.append(group(el))
    for p in parts:
        if p.kind in short:
            v = p.value if len(p.value) <= 11 else p.value[:10] + "…"
            el, _ = place_label(fr, p, v, placer, 6.6, INK_MUTE)
            body.append(group(el))

    # --- board edge silkscreen ---------------------------------------------
    for x_mm, s in ((7.6, "POCKET READER"), (29.7, "Rev 1.0"),
                    (37.4, "BOARD: 45 x 24 mm")):
        body.append(text(fr.x(x_mm), fr.y(0.45), s, font_size=6.6, fill=INK,
                         font_family=MONO, **halo()))

    # --- J1 net labels (from connections.csv) ------------------------------
    j1_by_pin = {c.pin: c for c in conns if c.ref == "J1"}
    j1_labels = [("GND", "GND", 23.4, 2.9), ("VBUS", "VBUS", 23.6, 4.6),
                 ("CC1 (A5)", "CC1", 24.5, 4.6), ("D+", "D+", 25.4, 4.6),
                 ("CC2 (B5)", "CC2", 25.4, 2.9), ("D-", "D-", 26.0, 2.9)]
    lx = 205.0
    for name, pin, px_mm, py_mm in j1_labels:
        col = net_colour(j1_by_pin.get(pin))
        body.append(leader(fr.x(px_mm), fr.y(py_mm), lx, 492, name,
                           anchor="middle", colour=col, size=8.4,
                           elbow=False))
        lx += 76
    body.append(text(180, 507, "J1 USB-C: net names from the connections.csv "
                     "RefDes=J1 rows; CC1=A5/CC2=B5 pinouts.md §5.3",
                     font_size=7.4, fill=INK_SOFT))

    # --- J2 pad numbers (rotated) + three callout examples -----------------
    j2 = next(p for p in parts if p.ref == "J2")
    pitch, span = 0.5, 24 * 0.5
    x_start = j2.x - span / 2 + pitch / 2
    num_px = fr.y(19.85)
    for i in range(24):
        px = fr.x(x_start + i * pitch)
        body.append(text(px + 2.2, num_px, str(i + 1), font_size=6.0,
                         fill=INK_MUTE, text_anchor="middle", font_family=MONO,
                         transform=f"rotate(-90 {_n(px + 2.2)} {_n(num_px)})"))
    callouts = [("9", "BUSY", "EPD_BUSY"), ("13", "SCL", "EPD_SCK"),
                ("14", "SDA", "EPD_MOSI")]
    for i, (pin, pname, netname) in enumerate(callouts):
        cx = fr.x(x_start + (int(pin) - 1) * pitch)
        c = j2pins.get(pin)
        col = net_colour(c)
        body.append(leader(cx, fr.y(17.6), cx + 6, 174 + i * 12,
                           f"{pin} {pname}", anchor="start", colour=col,
                           size=8.2, elbow=True))

    # --- U5 pin labels (rotated single row, above the module) -------------
    u5 = next(p for p in parts if p.ref == "U5")
    u5pins = pin_table(conns, "U5")
    order = sorted(u5pins.items(), key=lambda kv: int(kv[0]))
    top_edge = u5.y + u5.h / 2 - 0.32
    for i, (pin, c) in enumerate(order):
        px = fr.x(0.75 + (i + 0.5) * (15.9 / len(order)))
        col = net_colour(c)
        body.append(line(px, fr.y(top_edge), px, fr.y(20.05),
                         stroke=col, stroke_width=0.5))
        body.append(text(px + 2.2, fr.y(20.2), f"{pin} {c.pin}",
                         font_size=6.2, fill=col, text_anchor="start",
                         font_family=MONO,
                         transform=f"rotate(-90 {_n(px + 2.2)} "
                                   f"{_n(fr.y(20.2))})", **halo(col, 2.0)))

    # --- dimension lines ----------------------------------------------------
    body.append(dim_v(fr, 0.0, BOARD_H, -4.3, "24.00", ext_from=0.0))
    body.append(dim_h(fr, 0.0, BOARD_W, -4.5, "45.00 mm", ext_from=0.0))

    # --- tables + title block ----------------------------------------------
    u5_rows = [(p, c.pin, c.net, c.sinif) for p, c in order]
    u5_rows.append(("GND/EPAD", "GND", "GND", "power"))
    t1, h1 = table_box(TBL_X, 76, TBL_W, "U5 — ESP32-C3-MINI-1 pins "
                       "(connections.csv)", u5_rows, row_h=12.0,
                       note_lines=["Pin numbers are read from the "
                                   "connections.csv '(pin N)' field.",
                                   "GND/EPAD is collected into a single row.",
                                   "The castellation pad ORDER has NOT been "
                                   "verified against the module datasheet."])
    body.append(t1)
    j2rows = []
    for i, nm in enumerate(FPC_NAMES, start=1):
        c = j2pins.get(str(i))
        j2rows.append((str(i), nm, c.net if c else "", c.sinif if c else ""))
    t2, h2 = table_box(TBL_X, 76 + h1 + 14, TBL_W, "J2 — 24P FPC 0.5 mm pin "
                       "list (pinouts.md §1 + connections.csv)", j2rows,
                       two_col=True, row_h=13.0,
                       note_lines=["Names from the verified table in "
                                   "pinouts.md §1; nets from connections.csv."])
    body.append(t2)
    body.append(title_block(TBL_X, 592, TBL_W, 150,
                            "PCB PLACEMENT PROPOSAL (not production ready)",
                            SCALE_TOP,
                            [("Board", "45.0 x 24.0 mm · 2 layers · 1.6 mm"),
                             ("Parts", "64 (placement.csv) · 39 nets"),
                             ("Finish", "ENIG · 1 oz copper · min 0.25 mm track"),
                             ("Source", "placement.csv + connections.csv")]))

    # --- footer + colour legend --------------------------------------------
    conflicts = sorted({p.ref for p in parts if not p.ref == "J1"
                        and any(abs(hx - p.x) < p.w / 2 + 1.6
                                and abs(hy - p.y) < p.h / 2 + 1.6
                                for hx, hy in holes)})
    body.append(text(30, 560, "Copper pour #f8fafc; the antenna keep-out area is "
                     "hatched and has no copper.  Pin labels are coloured by "
                     "net CLASS.", font_size=9.5, fill=INK_SOFT))
    leg = [text(30, 604, "NET CLASS COLOURS (connections.csv 'Class')",
                font_size=9.5, font_weight=700, fill=INK),
           line(30, 612, 660, 612, stroke=FRAME, stroke_width=0.8)]
    for i, (cls, col, n) in enumerate((("power", ACCENT, "power / ground"),
                                       ("signal", NET_BLUE, "digital signal"),
                                       ("analog", ANALOG, "analog"))):
        xx = 40 + i * 200
        leg.append(rect(xx, 622, 26, 8, fill=col, stroke="none"))
        leg.append(text(xx + 34, 630, f"{cls} — {n}", font_size=9,
                        fill=INK_MUTE))
    body.append(group(leg))
    body.append(text(30, 660, "Stitching vias (0.3/0.6 mm) were placed around "
                     "the buck-boost by grid scan, avoiding the parts "
                     f"— {len(vias)} of them.", font_size=9.5,
                     fill=INK_SOFT))
    body.append(text(30, 678, "The mounting holes use the same pattern as the "
                     "PCB bosses in case.scad (2.5 mm from the edge).",
                     font_size=9.5, fill=INK_SOFT))
    body.append(text(30, 696,
                     ("WARNING: courtyards overlapping a mounting hole — "
                      + ", ".join(conflicts) + "  (placement.csv should be reviewed)")
                     if conflicts else
                     "No courtyard overlaps a mounting hole — 64 parts clean.",
                     font_size=9.5, fill=WARN_FG if conflicts else INK_MUTE,
                     font_weight=700 if conflicts else 400))

    return wrap(TOP_W, TOP_H,
                "Pocket Reader — PCB top view (placement proposal)",
                "Top view of the 45 x 24 mm board: footprints of the 64 parts, "
                "silkscreen, antenna keep-out area, dimensions and pin lists. "
                "Generated from placement.csv and connections.csv.",
                body)


# =============================================================================
#  7) Drawing 2 — PCB bottom view (mirrored GND plane)
# =============================================================================

BOT_W, BOT_H = 980.0, 700.0
BOT_OX, BOT_OY = 110.0, 490.0


def build_bottom(parts: list[Part], conns: list[Conn]) -> str:
    del conns
    fr = Frame(BOT_OX, BOT_OY, mirror=True, width_mm=BOARD_W)
    body: list[str] = []
    body += sheet_head(
        "PCB — BOTTOM VIEW (mirrored, GND plane)",
        "45.0 x 24.0 mm · bottom layer a continuous ground plane · all 64 "
        "parts are on the TOP side · view from below", BOT_W)
    body.append(info_box(30, 72, 620, 92, "WHAT THIS SIDE SHOWS", [
        "All 64 parts are on the top side. The bottom layer is a continuous "
        "GND plane, except the antenna keep-out area (docs/03 §2.4).",
        "The drawn part outlines are only the COURTYARD contour — there is "
        "no copper or silkscreen on this side.",
        "The view is FROM BELOW: X is mirrored.  Text is not mirrored so it "
        "stays readable (it is mirrored in a production drawing).",
    ]))

    # --- GND plane (cut out under the antenna) ------------------------------
    kx, ky, kw, kh = ANT_KEEPOUT
    bx, by, bw, bh = box_px(fr, 0, 0, BOARD_W, BOARD_H)
    kb = box_px(fr, kx, ky, kw, kh)
    pour_d = rounded_rect_path(bx, by, bw, bh, fr.u(CORNER_R)) + " " \
        + rect_path(*kb)
    body.append(path(pour_d, fill="url(#gnd)", fill_rule="evenodd",
                     stroke="none"))
    body.append(path(pour_d, fill="none", fill_rule="evenodd", stroke=ACCENT,
                     stroke_width=0.8, stroke_opacity=0.55))
    body.append(rect(*kb, fill="url(#hatch)", fill_opacity=0.6,
                     stroke=ACCENT, stroke_width=1.0,
                     stroke_dasharray="5 3"))
    body.append(ant_label(fr, WARN_FG, [
        "ANTENNA KEEP-OUT", "NO COPPER ON BOTTOM EITHER"]))
    body.append(text(fr.x(BOARD_W / 2 + 2), fr.y(BOARD_H / 2),
                     "CONTINUOUS GND PLANE · 1 oz COPPER",
                     font_size=13, fill=ACCENT, fill_opacity=0.35,
                     font_weight=700, text_anchor="middle",
                     letter_spacing="3"))

    # --- board outline ------------------------------------------------------
    body.append(path(rounded_rect_path(bx, by, bw, bh, fr.u(CORNER_R)),
                     fill="none", stroke=INK, stroke_width=1.6))
    body.append(path(rounded_rect_path(bx - 3, by - 3, bw + 6, bh + 6,
                                       fr.u(CORNER_R + 0.25)),
                     fill="none", stroke=INK_SOFT, stroke_width=0.5,
                     stroke_dasharray="4 3"))

    # --- part courtyards (mirrored, outline only) --------------------------
    holes = [(2.5, 2.5), (BOARD_W - 2.5, 2.5), (2.5, BOARD_H - 2.5),
             (BOARD_W - 2.5, BOARD_H - 2.5)]
    vias = stitch_vias(parts, (25.0, 3.5, 14.0, 13.0))
    for p in parts:
        col = ACCENT if p.group == "active" else INK_SOFT
        body.append(fr.crect_mm(p.x, p.y, p.w, p.h, fill="none", stroke=col,
                                stroke_width=0.7 if p.group == "active"
                                else 0.5,
                                stroke_dasharray="3 2", fill_opacity=0.0))
        body.append(text(fr.x(p.x), fr.y(p.y) + 2.2, p.ref, font_size=5.6,
                         fill=INK_SOFT, text_anchor="middle", font_family=MONO,
                         fill_opacity=0.8))
    body.append(draw_vias(fr, vias))
    body.append(draw_mount_holes(fr, holes))

    # --- dimensions ---------------------------------------------------------
    # In the mirrored view X is mirrored, so xmm = BOARD_W + 4.3 is used to
    # put the dimension line on the "visual left" side.
    body.append(dim_v(fr, 0.0, BOARD_H, BOARD_W + 4.3, "24.00", ext_from=0.0))
    body.append(dim_h(fr, 0.0, BOARD_W, -4.5, "45.00 mm", ext_from=0.0))

    # --- right column notes -------------------------------------------------
    body.append(text(660, 96, "BOTTOM LAYER RULES (docs/03 §7)", font_size=11,
                     font_weight=700, fill=INK_DARK))
    body.append(line(660, 104, 950, 104, stroke=FRAME, stroke_width=0.8))
    notes = [
        "[x] Bottom layer is a continuous GND plane",
        "    (except the antenna area)",
        "[x] No copper in the antenna keep-out area",
        "    (both top and bottom layer)",
        "[ ] Stitching vias: buck-boost loop",
        f"    {len(vias)} count, 0.3/0.6 mm",
        "[ ] GND return currents unverified",
        "[ ] Thermal via area not calculated",
        "",
        "There are NO TRACKS on this side: the",
        "plane pour is illustrative; the real",
        "pour must be done in KiCad.",
        "",
        "Mounting holes (4 x M1.6) are at the",
        "same positions on both layers.",
    ]
    for i, s in enumerate(notes):
        col = WARN_FG if s.startswith("[ ]") else INK_MUTE
        if s.startswith("[x]"):
            col = ANALOG
        body.append(text(662, 126 + i * 15, s, font_size=9.2, fill=col,
                         font_family=MONO if s.startswith("[") else None))
    body.append(info_box(660, 372, 290, 66, "ABOUT THE MIRROR", [
        "X is mirrored: someone looking from",
        "below sees the board this way.  Text",
        "is not mirrored so it stays readable.",
    ]))

    body.append(title_block(660, 480, 290, 150,
                            "PCB BOTTOM VIEW (not production ready)",
                            SCALE_TOP,
                            [("Board", "45.0 x 24.0 mm · 2 layers"),
                             ("Parts", "64 — all on the top side"),
                             ("Plane", "bottom layer, 1 oz"),
                             ("Source", "placement.csv")]))

    return wrap(BOT_W, BOT_H,
                "Pocket Reader — PCB bottom view (GND plane)",
                "Bottom view of the 45 x 24 mm board: continuous GND plane, "
                "antenna keep-out area, stitching vias, mounting holes and "
                "mirrored part courtyards.", body)


# =============================================================================
#  8) Drawing 3 — exploded case assembly view (2:1 dimetric)
# =============================================================================

ISO_U = 4.6                 # px/mm
ISO_OX, ISO_OY = 430.0, 810.0
EXPLODE_GAP = 26.0          # spacing between layers (mm, artificial)
THICK_GAIN = 2.0            # plate thickness visibility multiplier
CASE_W2, CASE_H2 = 1090.0, 1090.0

TINT = {"module": "#e2e8f0", "ic": "#e2e8f0", "conn": "#fde68a",
        "button": "#cffafe", "switch": "#dbeafe", "battery": "#e2e8f0",
        "inductor": "#e2e8f0"}


class Iso:
    """2:1 dimetric projection:  sx = (x-y)*u,  sy = (x+y)*u/2 - z*u."""

    def __init__(self, ox: float = ISO_OX, oy: float = ISO_OY,
                 u: float = ISO_U) -> None:
        self.ox, self.oy, self.u = ox, oy, u

    def p(self, x: float, y: float, z: float) -> tuple[float, float]:
        return (self.ox + (x - y) * self.u,
                self.oy + (x + y) * self.u * 0.5 - z * self.u)


def plate(iso: Iso, x0: float, y0: float, x1: float, y1: float,
          zb: float, zt: float, *, fill: str = "#f1f5f9",
          stroke: str = INK, sw: float = 1.0) -> list[str]:
    """Plate: the two visible side faces (+x, +y) and the top face."""
    A = iso.p(x0, y0, zt)
    B = iso.p(x1, y0, zt)
    C = iso.p(x1, y1, zt)
    D = iso.p(x0, y1, zt)
    A0, B0, C0, D0 = (iso.p(x0, y0, zb), iso.p(x1, y0, zb),
                      iso.p(x1, y1, zb), iso.p(x0, y1, zb))
    return [poly([B, C, C0, B0], fill=shade(fill, 0.84), stroke=stroke,
                 stroke_width=sw),
            poly([A, B, B0, A0], fill=shade(fill, 0.92), stroke=stroke,
                 stroke_width=sw),
            poly([A, B, C, D], fill=fill, stroke=stroke, stroke_width=sw)]


def plate_ring(iso: Iso, x0: float, y0: float, x1: float, y1: float,
               wx0: float, wy0: float, wx1: float, wy1: float,
               zb: float, zt: float, *, fill: str = "#f1f5f9") -> list[str]:
    """Plate with a window cutout (front frame/bezel)."""
    el = plate(iso, x0, y0, x1, y1, zb, zt, fill=fill)
    A, B = iso.p(x0, y0, zt), iso.p(x1, y0, zt)
    C, D = iso.p(x1, y1, zt), iso.p(x0, y1, zt)
    W1, W2 = iso.p(wx0, wy0, zt), iso.p(wx1, wy0, zt)
    W3, W4 = iso.p(wx1, wy1, zt), iso.p(wx0, wy1, zt)
    w1, w2 = iso.p(wx0, wy0, zb), iso.p(wx1, wy0, zb)
    w4 = iso.p(wx0, wy1, zb)
    outer = (f"M {_n(A[0])} {_n(A[1])} L {_n(B[0])} {_n(B[1])} "
             f"L {_n(C[0])} {_n(C[1])} L {_n(D[0])} {_n(D[1])} Z")
    hole = (f"M {_n(W1[0])} {_n(W1[1])} L {_n(W2[0])} {_n(W2[1])} "
            f"L {_n(W3[0])} {_n(W3[1])} L {_n(W4[0])} {_n(W4[1])} Z")
    el[2] = path(outer + " " + hole, fill=fill, fill_rule="evenodd",
                 stroke=INK, stroke_width=1.0)
    el.append(poly([W1, W2, w2, w1], fill=shade(fill, 0.76), stroke=INK,
                   stroke_width=0.9))
    el.append(poly([W1, W4, w4, w1], fill=shade(fill, 0.68), stroke=INK,
                   stroke_width=0.9))
    return el


def band(points: list[tuple[float, float]], width: float, **kw: object) -> str:
    """Ribbon (FPC) polygon from a centre line given in screen space."""
    left: list[tuple[float, float]] = []
    right: list[tuple[float, float]] = []
    n = len(points)
    for i, (x, y) in enumerate(points):
        if i == 0:
            dx, dy = points[1][0] - x, points[1][1] - y
        elif i == n - 1:
            dx, dy = x - points[-2][0], y - points[-2][1]
        else:
            dx = points[i + 1][0] - points[i - 1][0]
            dy = points[i + 1][1] - points[i - 1][1]
        ln = (dx * dx + dy * dy) ** 0.5 or 1.0
        nx, ny = -dy / ln, dx / ln
        left.append((x + nx * width / 2, y + ny * width / 2))
        right.append((x - nx * width / 2, y - ny * width / 2))
    return poly(left + right[::-1], **kw)


def stack_bar(x: float, y: float, w: float, px_mm: float
              ) -> tuple[str, float]:
    """Bar showing the real 12.75 mm stack to scale + dimension chain."""
    el: list[str] = []
    yy = y
    ticks: list[float] = []
    for _name, t, _note in STACK_LAYERS:
        h = t * px_mm
        el.append(rect(x, yy, w, h, fill=POUR, stroke=INK, stroke_width=0.8))
        el.append(text(x + w / 2, yy + h / 2 + 3.4, f"{t:.2f}",
                       font_size=8.4, fill=INK, text_anchor="middle",
                       font_family=MONO))
        ticks.append(yy)
        yy += h
    ticks.append(yy)
    total = sum(t for _n_, t, _note in STACK_LAYERS)
    for ty in ticks:
        el.append(line(x - 7, ty, x, ty, stroke=INK, stroke_width=0.8))
    el.append(line(x - 14, ticks[0], x - 14, ticks[-1], stroke=INK,
                   stroke_width=0.9, marker_start="url(#dimArrow)",
                   marker_end="url(#dimArrow)"))
    for i, (name, t, note) in enumerate(STACK_LAYERS):
        mid = (ticks[i] + ticks[i + 1]) / 2
        h = ticks[i + 1] - ticks[i]
        el.append(line(x + w, mid, x + w + 9, mid, stroke=FRAME,
                       stroke_width=0.7))
        el.append(text(x + w + 13, mid + 3, f"{name} — {t:.2f} mm",
                       font_size=9.0, fill=INK, font_weight=600))
        if h >= 34:
            el.append(text(x + w + 13, mid + 14, note, font_size=7.6,
                           fill=INK_SOFT))
    el.append(text(x + w / 2, y - 10, "ACTUAL STACK (Z)",
                   font_size=10.5, font_weight=700, fill=INK_DARK,
                   text_anchor="middle"))
    el.append(text(x - 14, ticks[-1] + 20, f"total {total:.2f} mm",
                   font_size=10, fill=ACCENT, font_weight=700,
                   font_family=MONO))
    el.append(text(x - 14, ticks[-1] + 34,
                   f"+ 0.25 mm margin = body {CASE_H:.1f} mm", font_size=9.0,
                   fill=ACCENT, font_family=MONO))
    return group(el), yy


def build_case(parts: list[Part], conns: list[Conn]) -> str:
    del conns
    iso = Iso()
    body: list[str] = []
    body += sheet_head(
        "EXPLODED ASSEMBLY — 6 layers, 13.0 mm body",
        "2:1 dimetric projection · NOT to scale (shows the assembly order and "
        "the thickness budget) · source: case.scad + placement.csv", CASE_W2)
    body.append(warn_box(30, 66, 690, 76,
                         "⚠  NOT TO SCALE — SHOWS THE ASSEMBLY ORDER", [
        "The projection is 2:1 dimetric; plate thicknesses are exaggerated 2x. "
        "Real thicknesses are in the stack bar at left.",
        "Part placement is read from placement.csv and case dimensions from "
        "case.scad.  This is a drawing, not an assembly guide.",
    ]))

    # --- horizontal dimension chain: glass + bezel = outer size --------------
    chx, chy, pxmm = 748.0, 96.0, 4.4
    el: list[str] = [text(chx, chy, "HORIZONTAL DIMENSION CHAIN", font_size=10.5,
                          font_weight=700, fill=INK_DARK),
                     text(chx, chy + 14, "Outer size is derived from the glass:",
                          font_size=8.6, fill=INK_SOFT),
                     text(chx, chy + 25, "case_w = glass + 2 x bezel",
                          font_size=8.6, fill=INK_SOFT, font_family=MONO)]
    xx = chx
    for width, lbl in ((BEZEL, "1.4"), (GLASS_W, "59.2"),
                       (BEZEL, "1.4")):
        wpx = width * pxmm
        el.append(rect(xx, chy + 36, wpx, 20, fill=POUR, stroke=INK,
                       stroke_width=0.9))
        el.append(text(xx + wpx / 2, chy + 50, lbl, font_size=8.4, fill=INK,
                       text_anchor="middle", font_family=MONO))
        xx += wpx
    el.append(line(chx, chy + 68, xx, chy + 68, stroke=INK, stroke_width=1.0,
                   marker_start="url(#dimArrow)", marker_end="url(#dimArrow)"))
    el.append(text((chx + xx) / 2, chy + 82, f"{CASE_W:.1f} x "
                   f"{CASE_D:.1f} mm", font_size=9.4, fill=ACCENT,
                   font_weight=700, text_anchor="middle", font_family=MONO))
    el.append(text(chx, chy + 98, f"62.0 − 59.2 = 2.8 → {BEZEL} mm bezel "
                   f"on each side", font_size=8.0, fill=INK_SOFT,
                   font_family=MONO))
    body.append(group(el))

    # --- layer z bases ------------------------------------------------------
    z = [i * EXPLODE_GAP for i in range(6)]
    t_draw = [max(2.0, t * THICK_GAIN) for t in
              (1.2, GLASS_T, 0.8, PCB_T, 4.0, CASE_WALL)]

    # 1) front frame (bezel) + window
    wx0 = (CASE_W - WINDOW_W) / 2
    wy0 = (CASE_D - WINDOW_H) / 2
    body += plate_ring(iso, 0, 0, CASE_W, CASE_D, wx0, wy0,
                       wx0 + WINDOW_W, wy0 + WINDOW_H, z[0], z[0] + t_draw[0],
                       fill="#e8edf3")

    # 2) e-paper glass + active area
    gx0, gy0 = (CASE_W - GLASS_W) / 2, (CASE_D - GLASS_H) / 2
    gx1, gy1 = gx0 + GLASS_W, gy0 + GLASS_H
    body += plate(iso, gx0, gy0, gx1, gy1, z[1], z[1] + t_draw[1],
                  fill="#ffffff")
    ax0 = gx0 + (GLASS_W - PANEL_ACTIVE_W) / 2
    ay0 = gy0 + (GLASS_H - PANEL_ACTIVE_H) / 2
    zt2 = z[1] + t_draw[1]
    body.append(poly([iso.p(ax0, ay0, zt2),
                      iso.p(ax0 + PANEL_ACTIVE_W, ay0, zt2),
                      iso.p(ax0 + PANEL_ACTIVE_W, ay0 + PANEL_ACTIVE_H, zt2),
                      iso.p(ax0, ay0 + PANEL_ACTIVE_H, zt2)],
                     fill="#f1f5f9", stroke=INK, stroke_width=0.8,
                     stroke_dasharray="4 3"))

    # 3) FPC ribbon — from the glass bottom edge to J2
    j2 = next(p for p in parts if p.ref == "J2")
    pcb_x0, pcb_y0 = (CASE_W - BOARD_W) / 2, (CASE_D - BOARD_H) / 2
    j2c = (pcb_x0 + j2.x, pcb_y0 + j2.y)
    z_pcb_top = z[3] + t_draw[3]
    ctr = [iso.p(31.0, 1.6, zt2 - 0.4),
           iso.p(31.2, 0.4, zt2 + 3.0),
           iso.p(31.8, 2.0, zt2 + 9.0),
           iso.p(33.0, 5.5, zt2 + 15.0),
           iso.p(35.0, 10.0, zt2 + 22.0),
           iso.p(37.0, 15.5, zt2 + 29.0),
           iso.p(38.8, 20.5, zt2 + 35.0),
           iso.p(39.5, 23.6, zt2 + 38.0),
           iso.p(39.5, 24.6, z_pcb_top + 0.5)]
    body.append(band(ctr, 9.0 * ISO_U, fill="#fde68a", stroke=ACCENT,
                     stroke_width=0.9, fill_opacity=0.95))

    # 4) PCB + parts
    body += plate(iso, pcb_x0, pcb_y0, pcb_x0 + BOARD_W, pcb_y0 + BOARD_H,
                  z[3], z_pcb_top, fill="#f8fafc")
    for p in sorted(parts, key=lambda q: q.height):
        cx, cy = pcb_x0 + p.x, pcb_y0 + p.y
        ht = 0.35 if p.height <= 0.01 else max(1.0, p.height)
        body.append(fr_block(iso, cx - p.w / 2, cy - p.h / 2,
                             cx + p.w / 2, cy + p.h / 2, z_pcb_top,
                             z_pcb_top + ht,
                             fill=TINT.get(p.kind, "#f1f5f9")))
        if p.height >= 1.4:
            lx, ly = iso.p(cx, cy, z_pcb_top + ht + 0.8)
            body.append(text(lx, ly, p.ref, font_size=7.0, fill=INK_DARK,
                             text_anchor="middle", font_family=MONO,
                             font_weight=700, **halo()))
    # 5) battery cell
    cx0, cy0 = (CASE_W - CELL_W) / 2, (CASE_D - CELL_H) / 2
    body += plate(iso, cx0, cy0, cx0 + CELL_W, cy0 + CELL_H, z[4],
                  z[4] + t_draw[4], fill="#e2e8f0")
    # 6) rear cover
    body += plate(iso, 0, 0, CASE_W, CASE_D, z[5], z[5] + t_draw[5],
                  fill="#e8edf3")

    # --- layer labels (right, evenly spaced) --------------------------------
    labels = [
        ("1", "Body front frame (bezel)",
         f"outer {CASE_W:.1f} x {CASE_D:.1f} · window {WINDOW_W:.1f} x "
         f"{WINDOW_H:.1f} · bezel {BEZEL}", 0),
        ("2", "E-paper glass",
         f"{GLASS_W} x {GLASS_H} x {GLASS_T} mm · active area "
         f"{PANEL_ACTIVE_W} x {PANEL_ACTIVE_H}", 1),
        ("3", "FPC ribbon cable",
         "24P 0.5 mm · fold allowance 0.8 mm", 2),
        ("4", f"PCB ({BOARD_W:.1f} x {BOARD_H:.1f} x {PCB_T} mm)",
         f"{len(parts)} parts — placement from placement.csv", 3),
        ("5", "Li-Po pouch cell",
         f"pocket {CELL_W:.0f} x {CELL_H:.0f} x {CELL_T} mm (402025)", 4),
        ("6", "Rear cover", f"{CASE_WALL} mm plate · 4 x M1.6 screws", 5),
    ]
    for num, name, sub, li in labels:
        px, py = iso.p(CASE_W, 0.0, z[li] + t_draw[li] / 2)
        body.append(group([
            line(px, py, px + 24, py, stroke=INK, stroke_width=0.7),
            circle(px, py, 1.8, fill=INK, stroke="none"),
            circle(px + 46, py, 11.0, fill=ACCENT, stroke="none"),
            text(px + 46, py + 3.8, num, font_size=10, fill="#ffffff",
                 text_anchor="middle", font_weight=700),
            text(px + 63, py - 2, name, font_size=10.2, fill=INK_DARK,
                 font_weight=700),
            text(px + 63, py + 10, sub, font_size=8.4, fill=INK_SOFT),
        ]))

    # --- USB-C / button / switch callouts (bottom left) ---------------------
    zc = z[0] + t_draw[0] / 2
    ux, uy = iso.p(CASE_W / 2, 0.0, zc)
    body.append(leader(ux, uy, 250, 800, "USB-C 9.0 x 3.4 mm cutout "
                       "(bottom edge)", anchor="end", colour=ACCENT, size=9.0,
                       elbow=False))
    bx, by = iso.p(CASE_W, CASE_D / 2 - 3.0, zc)
    body.append(leader(bx, by, 250, 842, "3 x 3.0 mm button hole "
                       "(right edge)", anchor="end", colour=ACCENT, size=9.0,
                       elbow=False))
    sx, sy = iso.p(CASE_W, CASE_D / 2 - 8.0, zc)
    body.append(leader(sx, sy, 250, 878, "SPDT slide switch slot "
                       "4.0 x 1.6", anchor="end", colour=ACCENT, size=9.0,
                       elbow=False))
    body.append(text(30, 752, "The cutouts are opened only in the FRONT FRAME "
                     "(layer 1); they align with the connector height on the "
                     "board.", font_size=8.6, fill=INK_SOFT))
    body.append(text(30, 768, "usb_z / sw_z / btn_z are approximate in "
                     "case.scad — the board must be fitted and measured with "
                     "calipers.", font_size=8.6, fill=INK_SOFT))

    # --- stack bar (top left) ----------------------------------------------
    bar, bottom = stack_bar(40, 190, 52, 40.0)
    body.append(bar)

    body.append(text(30, 1050, "Assembly order: 1 body → 2 glass → 3 FPC → "
                     "4 PCB → 5 battery → 6 cover.  The glass is inserted from "
                     "inside, BEHIND the front frame.", font_size=9.4,
                     fill=INK_SOFT))
    body.append(text(30, 1066, "All dimensions are read from the case.scad "
                     "parameter block; part positions come from placement.csv.  "
                     "Not to scale.", font_size=9.4, fill=INK_SOFT))

    return wrap(CASE_W2, CASE_H2,
                "Pocket Reader — exploded case assembly view",
                "2:1 dimetric exploded view of the six-layer case: front "
                "frame, e-paper glass, FPC ribbon, PCB, Li-Po cell and rear "
                "cover; a 13 mm stack chain on the side.", body)


def fr_block(iso: Iso, x0: float, y0: float, x1: float, y1: float,
             zb: float, zt: float, **kw: object) -> str:
    return group(plate(iso, x0, y0, x1, y1, zb, zt, **kw))


# =============================================================================
#  9) Verification (--check)
# =============================================================================

SHAPES = {"rect", "circle", "ellipse", "line", "path", "polygon", "polyline",
          "text", "use"}
_TAG = "{http://www.w3.org/2000/svg}"
_CMD = re.compile(r"([MLHVCSQTAZmlhvcsqtaz])([^MLHVCSQTAZmlhvcsqtaz]*)")


def _floats(s: str) -> list[float]:
    return [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e[-+]?\d+)?", s)]


def path_points(d: str) -> list[tuple[float, float]]:
    """All points in the path data (control points included) — a rough bound."""
    pts: list[tuple[float, float]] = []
    cx = cy = 0.0
    for cmd, body in _CMD.findall(d):
        nums = _floats(body)
        up = cmd.upper()
        rel = cmd.islower()
        if up == "M" or up == "L" or up == "T":
            for i in range(0, len(nums) - 1, 2):
                x, y = nums[i], nums[i + 1]
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                pts.append((cx, cy))
        elif up == "H":
            for x in nums:
                cx = cx + x if rel else x
                pts.append((cx, cy))
        elif up == "V":
            for y in nums:
                cy = cy + y if rel else y
                pts.append((cx, cy))
        elif up in ("C", "S", "Q"):
            step = 6 if up == "C" else (4 if up == "Q" else 4)
            for i in range(0, len(nums) - step + 1, step):
                chunk = nums[i:i + step]
                for j in range(0, len(chunk) - 1, 2):
                    x, y = chunk[j], chunk[j + 1]
                    px, py = (cx + x, cy + y) if rel else (x, y)
                    pts.append((px, py))
                ex, ey = chunk[-2], chunk[-1]
                cx, cy = (cx + ex, cy + ey) if rel else (ex, ey)
        elif up == "A":
            for i in range(0, len(nums) - 6, 7):
                ex, ey = nums[i + 5], nums[i + 6]
                cx, cy = (cx + ex, cy + ey) if rel else (ex, ey)
                pts.append((cx, cy))
    return pts


def element_bbox(root: ET.Element) -> tuple[float, float, float, float] | None:
    """Bounding box of all drawn elements of the root (excluding defs)."""
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: ET.Element, inside_defs: bool) -> None:
        nonlocal xs, ys
        tag = node.tag.replace(_TAG, "")
        if tag == "defs":
            return
        try:
            a = node.attrib
            if tag == "rect":
                x, y = float(a.get("x", 0)), float(a.get("y", 0))
                xs += [x, x + float(a["width"])]
                ys += [y, y + float(a["height"])]
            elif tag == "circle":
                x, y, r = (float(a["cx"]), float(a["cy"]), float(a["r"]))
                xs += [x - r, x + r]
                ys += [y - r, y + r]
            elif tag == "ellipse":
                x, y = float(a["cx"]), float(a["cy"])
                rx, ry = float(a["rx"]), float(a["ry"])
                xs += [x - rx, x + rx]
                ys += [y - ry, y + ry]
            elif tag == "line":
                xs += [float(a["x1"]), float(a["x2"])]
                ys += [float(a["y1"]), float(a["y2"])]
            elif tag in ("polygon", "polyline"):
                for pair in a["points"].split():
                    px, py = pair.split(",")
                    xs.append(float(px))
                    ys.append(float(py))
            elif tag == "path":
                for px, py in path_points(a["d"]):
                    xs.append(px)
                    ys.append(py)
            elif tag == "text" or tag == "use":
                xs.append(float(a.get("x", 0)))
                ys.append(float(a.get("y", 0)))
        except (KeyError, ValueError):
            pass
        for child in node:
            walk(child, inside_defs)

    walk(root, False)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def shape_stats(svg_text: str) -> tuple[ET.Element, dict[str, int], list[str]]:
    root = ET.fromstring(svg_text)
    counts: dict[str, int] = {}
    texts: list[str] = []

    def walk(node: ET.Element) -> None:
        tag = node.tag.replace(_TAG, "")
        if tag == "defs":
            return
        if tag in SHAPES and tag != "text":
            counts[tag] = counts.get(tag, 0) + 1
        elif tag == "text":
            counts["text"] = counts.get("text", 0) + 1
            texts.append(node.text or "")
        for child in node:
            walk(child)

    walk(root)
    return root, counts, texts


def check_parts(parts: list[Part]) -> list[str]:
    """Parts overhanging the board rectangle (U5 and J1 are deliberate exceptions)."""
    problems: list[str] = []
    for p in parts:
        if p.inside or p.ref in ("U5", "J1"):
            continue
        problems.append(
            f"{p.ref}: overhangs the board "
            f"(x {p.x0:.2f}..{p.x1:.2f}, y {p.y0:.2f}..{p.y1:.2f})")
    return problems


def check_hole_conflicts(parts: list[Part],
                         holes: list[tuple[float, float]]) -> list[str]:
    """Mounting holes overlapping part courtyards (warning level)."""
    out: list[str] = []
    for hx, hy in holes:
        for p in parts:
            if (abs(hx - p.x) < p.w / 2 + 0.8 and abs(hy - p.y) < p.h / 2 + 0.8
                    and p.ref != "J1"):
                out.append(f"mounting hole ({hx:.1f}, {hy:.1f}) overlaps the "
                           f"{p.ref} courtyard")
    return out


def run_check(docs: dict[Path, str], parts: list[Part], write: bool) -> int:
    print("=" * 72)
    print("gen_pcb_layout.py --check")
    print("=" * 72)
    problems: list[str] = []

    if write:
        for path, svg in docs.items():
            path.write_text(svg, encoding="utf-8")
            print(f"wrote    : {path}")

    refs = {p.ref for p in parts}
    print(f"\nplacement.csv : {len(parts)} parts, {len(refs)} unique refs")
    print(f"connections.csv: {CONN_NETS} nets, {CONN_ROWS} connections")

    for path, svg in docs.items():
        print(f"\n--- {path.name} ---")
        try:
            root, counts, texts = shape_stats(svg)
        except ET.ParseError as exc:                        # pragma: no cover
            problems.append(f"{path.name}: XML could not be parsed: {exc}")
            print(f"  XML  : ERROR — {exc}")
            continue
        if write:
            try:
                ET.parse(path)
            except ET.ParseError as exc:                    # pragma: no cover
                problems.append(f"{path.name}: written file is invalid XML: "
                                f"{exc}")
                print(f"  file : ERROR — {exc}")
                continue
        vb = root.get("viewBox", "")
        total = sum(counts.values())
        print(f"  XML  : valid")
        print(f"  viewBox: {vb}")
        print(f"  items: {total} drawn elements  " +
              "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        bb = element_bbox(root)
        w, h = (float(v) for v in vb.split()[2:])
        if bb:
            print(f"  bounds: x {bb[0]:.1f}..{bb[2]:.1f}, "
                  f"y {bb[1]:.1f}..{bb[3]:.1f}")
            tol = 1.5
            if bb[0] < -tol or bb[1] < -tol or bb[2] > w + tol \
                    or bb[3] > h + tol:
                problems.append(f"{path.name}: drawing overflows the canvas "
                                f"(canvas {_n(w)}x{_n(h)})")
                print("  canvas: OVERFLOW")
            else:
                print(f"  canvas: inside (0 0 {_n(w)} {_n(h)})")
        found = {r for r in refs if r in texts}
        missing = sorted(refs - found)
        if path.name.startswith("pcb-layout-top"):
            print(f"  ref  : {len(found)}/{len(refs)} placement refs "
                  f"drawn (REQUIRED: all)")
            if missing:
                problems.append(f"{path.name}: missing ref: {', '.join(missing)}")
        else:
            print(f"  ref  : {len(found)}/{len(refs)} refs labelled "
                  f"(not all required in this view)")

    print("\n--- board boundary check ---")
    over = check_parts(parts)
    if over:
        problems += over
        for s in over:
            print("  PROBLEM:", s)
    else:
        print("  OK — no part overhangs the board rectangle.")
    edge = sorted(p.ref for p in parts
                  if abs(p.x0) < 1e-6 or abs(p.x1 - BOARD_W) < 1e-6
                  or abs(p.y0) < 1e-6 or abs(p.y1 - BOARD_H) < 1e-6)
    print(f"  touching the edge exactly: {', '.join(edge) or '—'} "
          f"(nothing overhangs; U5 and J1 are still exempt)")

    print("\n--- mounting hole / courtyard overlap ---")
    for s in check_hole_conflicts(parts, [(2.5, 2.5), (42.5, 2.5),
                                          (2.5, 21.5), (42.5, 21.5)]):
        print("  WARNING:", s)

    print("\n" + "=" * 72)
    if problems:
        print(f"{len(problems)} PROBLEMS:")
        for s in problems:
            print("  -", s)
        return 1
    print("OK — 3 files valid XML, all refs drawn, no overflow.")
    return 0


# =============================================================================
# 10) Entry point
# =============================================================================

CONN_NETS = CONN_ROWS = 0


def main(argv: list[str] | None = None) -> int:
    global CONN_NETS, CONN_ROWS
    ap = argparse.ArgumentParser(
        description="Generates the PCB placement and case assembly drawings "
                    "(input: placement.csv + connections.csv)")
    ap.add_argument("--check", action="store_true",
                    help="do not write; verify and report")
    args = ap.parse_args(argv)

    for path in (PLACEMENT_CSV, CONNECTIONS_CSV):
        if not path.exists():
            print(f"ERROR: input not found: {path}", file=sys.stderr)
            return 2

    parts = load_parts(PLACEMENT_CSV)
    conns = load_connections(CONNECTIONS_CSV)
    CONN_ROWS = len(conns)
    CONN_NETS = len({c.net for c in conns})

    docs = {
        OUT_TOP: build_top(parts, conns),
        OUT_BOTTOM: build_bottom(parts, conns),
        OUT_CASE: build_case(parts, conns),
    }
    for path in docs:
        path.parent.mkdir(parents=True, exist_ok=True)
    return run_check(docs, parts, write=not args.check)


if __name__ == "__main__":
    sys.exit(main())
