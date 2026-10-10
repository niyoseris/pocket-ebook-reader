# Pocket Reader — 3D-Printable Case

A two-part, parametric case for the 2.13" (250 × 122) e-paper panel, the
ESP32-C3 and a 402025 LiPo cell. Everything is defined in `case.scad`; the
dimensions are measured with callipers and updated from the
`// --- PARAMETRE ---` block at the top.

| Dimension | Value |
|---|---|
| Outer width (X) | 62.0 mm |
| Outer depth (Y) | 32.0 mm |
| **Outer thickness (Z)** | **13.0 mm** |
| Wall thickness | 1.6 mm |
| Bezel on the front face | 1.4 mm |
| Panel glass outline | 59.2 × 29.2 × 1.05 mm |

> **Important — 13.0 mm, not 9.5 mm.**
> The first draft assumed 9.5 mm; at that thickness the parts do not stack up and
> the lid will not close. The real stack comes to 12.75 mm, so the outer thickness
> is **13.0 mm**. See the table below.

---

## 0. Where the outer dimensions come from (62 × 32, not 58 × 30)

`case_w` and `case_d` are **not freely chosen numbers**; they are derived from
the panel glass:

| Contribution | Value |
|---|---|
| 2.13" panel glass outline (Waveshare "Outline (screen only)") | 59.2 × 29.2 mm |
| Bezel frame left around the glass on the front face (2 sides) | 2 × 1.4 mm |
| **Total → `case_w` × `case_d`** | **62.0 × 32.0 mm** |

**The old 58 × 30 mm values were wrong:** 59.2 mm of glass did not fit into a
58 mm case at all — the panel could not be installed. The correct check is
`62.0 − 59.2 = 2.8`, i.e. **1.4 mm** of bezel on each side. Narrow, but that is
the dimension you expect in a real flush-bezel device.

The glass is dropped into a recess cut from the **inside**, behind this frame:
the glass sits 1.2 mm behind the front face (`lip_depth`), leaving a 1.4 mm bezel
on the front face. Do not try to pass the glass in from the front — 59.2 mm of
glass will not fit through a 1.4 mm frame.

> **If you change the panel:** FIRST update the `panel_glass_w` / `panel_glass_h`
> values (the real glass outline) and the `bezel_lip` value, THEN re-derive the
> outer dimensions with `case_w = panel_glass_w + 2 * bezel_lip` and
> `case_d = panel_glass_h + 2 * bezel_lip`. `case.scad` prints this to the console
> on every run and warns if the glass will not fit (the `CASE:` and `UYARI:` lines).

---

## 1. Thickness budget (the Z stack)

From front to back, all the layers:

| # | Layer | Thickness | z range (mm) |
|---|---|---|---|
| 1 | Front wall over the panel edge (glass recess depth) | 1.20 mm | 0.00 – 1.20 |
| 2 | Panel glass (2.13" e-paper) | 1.05 mm | 1.20 – 2.25 |
| 3 | FPC fold allowance | 0.80 mm | 2.25 – 3.05 |
| 4 | PCB | 1.60 mm | 3.05 – 4.65 |
| 5 | Tallest part on the back of the board (ESP32-C3-MINI-1 = 2.4 mm) | 2.50 mm | 4.65 – 7.15 |
| 6 | Li-Po pouch cell (402025) | 4.00 mm | 7.15 – 11.15 |
| 7 | Back wall (lid plate) | 1.60 mm | 11.15 – 12.75 |
|   | **TOTAL** | **12.75 mm** | |
|   | **`case_h` (outer thickness)** | **13.00 mm** | safety margin **0.25 mm** |

This 0.25 mm is reserved for the foam/sponge pad placed on the cell: 0.5 mm of
the 4.5 mm battery recess is foam allowance (`foam_allow`), and it compresses by
up to 0.25 mm when the lid is closed.

### If you change the panel or the cell

Do **not guess** `case_h`. `case.scad` computes the stack itself:

```scad
stack_total = lip_depth + panel_t + fpc_clearance + pcb_t + rear_parts
            + cell_t + lid_t;
stack_slack = case_h - stack_total;
```

When you run OpenSCAD these lines appear in the console:

```
STACK: katmanlar = 12.75 mm, case_h = 13 mm, emniyet payı = 0.25 mm
STACK: cam ustu = 2.25, PCB = 3.05..4.65, pil = 7.15..11.15, kapak ici = 11.4
```

If the margin goes negative you get the message `UYARI: parçalar sığmıyor!`;
pull `case_h` down to `stack_total`. For example, if you use a 5.5 mm cell
(602025), `stack_total` becomes 14.25 mm and `case_h` must be at least 14.5 mm.

---

## 2. Printing

```bash
# Body + lid in one file (side by side)
openscad -o kasa.stl case.scad

# Separately
openscad -o govde.stl -D 'PART="body"' case.scad
openscad -o kapak.stl -D 'PART="lid"'  case.scad
```

No OpenSCAD? <https://openscad.org/downloads.html>
(`brew install --cask openscad` / `sudo apt install openscad`)

### Slicer settings

| Setting | Value |
|---|---|
| Layer height | 0.2 mm |
| First layer | 0.25 mm |
| Perimeter | 3 |
| Infill | 20% (gyroid or grid) |
| Material | PLA **or** PETG (either works) |
| Supports | **NONE** |
| Nozzle | 0.4 mm |

### Orientation

Print the body with its **front face (the panel side, z = 0) flat on the bed**.
In this orientation:

* The panel window and glass recess face the bed directly — no bridging.
* The side walls grow vertically, no supports needed.
* The two walls of the battery holder rest against the case side walls; they do
  not float in mid-air.
* The screw gussets brace against two walls at the corners.
* The 1.4 mm bezel frame and the 1.3 mm lip ring of the glass recess form in the
  first layers; so take the first layer at 0.25 mm and clean the bed well.

The lid is a flat plate; it needs no supports whichever face is on the bed.

---

## 3. First test print (strongly recommended)

The window and glass recess dimensions **always** change with the panel. Before
printing the whole case, print only the panel recess (~15 minutes):

```bash
openscad -o panel_test.stl -D 'PART="panel_test"' case.scad
```

Then:

1. Drop the panel glass into the recess. **It should be a light fit, not
   forced.** (Drop the glass in from the **inside/back**, not the front face.)
2. Seat the glass in the recess and look from the front: is the active area
   (250 × 122 px) fully visible? If the window edges cut into the active area,
   increase `window_w` / `window_h`.
3. If the glass is too tight, increase `glass_lip_w` / `glass_lip_h` by 0.2 mm.
4. If the glass rattles in the recess, decrease them by 0.2 mm.

Print tolerance varies from printer to printer; trying in 0.2 mm steps is the
fastest route.

---

## 4. Parameters that must be measured and updated

The following are marked **"measure and update"** in `case.scad`. All of them
should be measured with callipers; the values given are typical.

| Parameter | What to measure | Typical |
|---|---|---|
| `window_w` / `window_h` | The panel's visible area + 0.2 mm | 49.0 × 24.1 mm |
| `glass_lip_w` / `glass_lip_h` | The real glass dimension + 0.2 mm | 59.4 × 29.4 mm |
| `panel_glass_w` / `panel_glass_h` | The real glass outline (`case_w/d` derives from this) | 59.2 × 29.2 mm |
| `bezel_lip` | The frame left around the glass on the front face | 1.4 mm |
| `pcb_w` / `pcb_h` | The board outline | 45.0 × 24.0 mm |
| `pcb_hole_inset` | Distance of the mounting holes from the board edge | 2.5 mm |
| `pcb_hole_d` | The hole the M1.6 screw passes through | 1.9 mm |
| `cell_w` / `cell_l` / `cell_t` | The real cell dimensions | 20 × 25 × 4 mm |
| `usb_w` / `usb_h` / `usb_x` | USB-C opening size and position | 9.0 × 3.4 mm |
| `usb_z` | Height of the connector above the front face | 3.95 mm |
| `sw_w` / `sw_h` / `sw_y` | Power switch tab and position | 4.0 × 1.6 mm |
| `btn_*` | Button holes, pitch and height | 3.0 mm / 5.0 mm |
| `fpc_x` / `fpc_w` | Where the FPC exits the panel | centre / 12 mm |

### Connector heights are the most critical

The USB-C, switch and button holes are positioned relative to **the height of
the parts on the board**. `usb_z`, `sw_z` and `btn_z` are guesses only
(`z_pcb_front + pcb_t/2 ...`). To find the correct value:

1. Screw the board onto the standoffs (or temporarily glue it in place).
2. With the depth rod of the callipers, measure the distance from the front face
   to the centre of the connector.
3. Set `usb_z` to that number.
4. Do the same for the switch and the buttons; each button may be at a different
   height, so `btn_dz` can give each button its own Z offset.

A hole cut at the wrong height is awkward but the case does not fail to close —
so placing the board and measuring first is the safest route.

---

## 5. Lid and screws

The lid seats with a 1.0 mm ring that passes over the body from the
**outside**: there is a 1.0 mm deep step on the outer surface of the body, and
the lid's ring drops into it. This way the lid has **no** inward-projecting lip —
it does not clash with the battery holder or the board, and the lid always closes
fully.

### Screw list

| Part | Qty | Notes |
|---|---|---|
| M1.6 × 4 mm self-tapping screw | **4** | Go into the corner gussets |
| M1.6 × 4 mm self-tapping screw (for the PCB) | 4 | Go into the PCB standoffs (optional) |

`screw_d = 1.6 mm`, depth `screw_depth = 5.0 mm`. For the first screwing into
PLA, do it by hand with light pressure; in PETG it turns more easily.

When tightening the screws **do not over-force them**: M1.6 threads strip
plastic easily.

### Snap-fit alternative

If you do not want screws:

```bash
openscad -o kasa.stl -D 'PART="body"' -D 'use_snaps=true' case.scad
```

With `use_snaps = true` the screw gussets and lid holes are disabled and two
hooks appear on the top and bottom edges instead. Snap-fit is less reliable than
M1.6 screws and loosens with repeated opening and closing — use the screwed
version unless you will not be opening it often.

---

## 6. Battery

The battery recess is **26 × 21 × 4.5 mm**:

* Cell 20 × 25 × 4.0 mm (402025); the 25 mm side runs along the **long axis** of
  the case. A 0.5 mm `pocket_clear` allowance is added on each side → 26 × 21 mm.
* 0.5 mm `foam_allow` is added to the thickness → 4.5 mm.
* The cell rests on the 4 corner supports; two long walls (in the X direction,
  against the case side walls) and two short walls hold it horizontally.
* There is **deliberately no** base plate: there is only 6.75 mm between the back
  of the PCB and the inside of the lid; 2.5 mm goes to the rear parts and 4.0 mm
  to the cell. So the cell rests on the corner pads while the ESP32 module stays
  clear in the middle.

Before fitting the cell, **solder the wires** and put heat-shrink tubing over the
ends. The cell should go into the recess without being forced; if you force it
you will puncture the cell.

> Li-Po cells demand care. A short circuit, crushing and temperatures above
> 60 °C lead to fire. Do the soldering with the device off and without letting
> the ends touch each other.

---

## 7. Sections

| Cut-out | Edge | Dimension | Position |
|---|---|---|---|
| USB-C | bottom (−Y) | 9.0 × 3.4 mm, rounded | `usb_x`, `usb_z` |
| Power switch | right (+X) | 4.0 × 1.6 mm | `sw_y`, `sw_z` |
| 3 buttons | right (+X) | 3.0 mm outer + 1.5 mm pusher | `btn_y0`, `btn_pitch`, `btn_z`, `btn_dz` |
| FPC channel | front face, lower edge of the glass | 12.0 mm wide | `fpc_x`, `fpc_w` |

**Buttons:** The outer hole is 3.0 mm and forms a 0.8 mm deep countersink; a
1.5 mm pusher hole passes through from behind. This way the 1.6 mm side wall is
not weakened all the way through, and the user's finger feels the 3 mm recess.

**FPC channel:** The panel's ribbon cable exits from the lower edge of the glass
and folds onto the front face of the board. The channel makes room for the fold
by removing the 1.2–1.6 mm band over the glass region. If your panel's FPC exits
from another edge, shift the `fpc_x` value or remove the `fpc_passage()` call.

---

## 8. Assembly order

1. Drop the panel into the recess from the inside of the front face (the glass
   seats on the 1.2 mm lip).
2. Pass the FPC through the channel and plug it into the board connector; make
   the fold in the 0.8 mm gap.
3. Seat the PCB on the 4 standoffs and fix it with M1.6 screws.
4. Seat the cell on the corner pads, solder the wires to the board.
5. Put a thin foam pad on top (it will compress by 0.25 mm).
6. Place the lid with its ring over the step and tighten the 4 screws.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| Panel does not fit the case at all | `case_w/d` was not derived from the glass. Set `case_w = panel_glass_w + 2*bezel_lip` (see §0); check the `UYARI:` line in the console |
| Panel will not go into the recess | `glass_lip_w/h` +0.2 mm; verify with `panel_test`. The glass is dropped in from the inside, not the front |
| Panel rattles in the recess | `glass_lip_w/h` −0.2 mm or a 0.2 mm strip of tape |
| Window cuts into the active area | Increase `window_w/h` (active area + 0.4 mm) |
| Lid will not close | The `emniyet payı` (safety margin) in the console may be negative; or `usb_z`/`sw_z`/`btn_z` is wrong and the connector is against the wall |
| USB-C cable is hard to insert | Measure the `usb_z` height with callipers and correct it |
| Button cannot be pressed | Measure and correct the `btn_z` / `btn_dz` height |
| Battery does not fit | Enter the real `cell_t` value, check `stack_total`, update `case_h` |
| Screw hole stripped | Increase `screw_d` and `pcb_hole_d` for the next size up (M2) |
| Front wall cracked under the glass | Reduce `lip_depth` to 0.8 (the lip becomes two layers thick) |

---

## Ready-made STL files

The files in the `stl/` folder were **generated from `case.scad` with
OpenSCAD** — you can slice and print them without installing OpenSCAD.

| File | Outer dimensions | Volume | When to use it |
|---|---|---|---|
| `govde.stl` | 62.00 × 32.00 × 11.41 mm | 4.65 cm³ | Main body (front frame + panel bed) |
| `kapak.stl` | 62.00 × 32.00 × 2.60 mm | 3.33 cm³ | Back lid (interlocking, 1 mm overlap) |
| `panel-test.stl` | 62.00 × 32.00 × 3.60 mm | 1.17 cm³ | **Print this first** — see whether the panel seats, before finishing a 3-hour print |

Assembled with a 1 mm interlocking allowance, the body + lid have an outer
height of **13.0 mm**.

**Mesh status:** all three files are closed (watertight) — no open edges. In
`govde.stl`, two closed surfaces touch exactly along 20 edges (4 shared faces).
This is **not** a hole; slicers handle it without problems, but a mesh checker
that does not require full solidity may warn.

### Regenerating

```bash
brew install --cask openscad@snapshot     # the normal `openscad` cask was
                                           # disabled on 2026-09-01 due to Gatekeeper
cd hardware/enclosure
OSC=/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
$OSC --export-format binstl -o stl/govde.stl      -D 'PART="body"'       case.scad
$OSC --export-format binstl -o stl/kapak.stl      -D 'PART="lid"'        case.scad
$OSC --export-format binstl -o stl/panel-test.stl -D 'PART="panel_test"' case.scad
```

The STLs are **generated** files — if you change a dimension, edit `case.scad`
and run the three commands above again. Do not hand-edit the STLs.
