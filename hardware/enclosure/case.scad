// =============================================================================
//  Pocket Reader — 2.13" e-reader case (OpenSCAD, parametric)
// =============================================================================
//  Target hardware: ESP32-C3-MINI-1 + 2.13" 250x122 SSD1680 e-paper + 402025 LiPo.
//
//  Usage:
//      openscad -o case.stl        case.scad
//      openscad -o body.stl        -D 'PART="body"'       case.scad
//      openscad -o lid.stl         -D 'PART="lid"'        case.scad
//      openscad -o panel_test.stl  -D 'PART="panel_test"' case.scad
//
//  COORDINATE SYSTEM (same as print orientation):
//      X : width      — case_w = 62 mm  (±31)
//      Y : depth      — case_d = 32 mm  (±16), -Y = USB-C edge (bottom)
//      Z : thickness  — 0 = FRONT OUTER FACE (panel side), +Z = toward the rear
//
//      The case body is printed with its front face on the bed (z=0 at the bottom).
//      In this orientation NO support material is needed.
//
// -----------------------------------------------------------------------------
//  WHERE THE OUTER DIMENSIONS (case_w / case_d) COME FROM — THEY ARE NOT FREE CHOICES
// -----------------------------------------------------------------------------
//  case_w and case_d are derived from the panel GLASS, not chosen arbitrarily:
//
//      2.13" panel glass outer outline (Waveshare "Outline (screen only)")
//                                               59.2 x 29.2 mm
//      + bezel remaining around the glass on the front face (bezel_lip)
//                                            2 x 1.4 mm
//      ------------------------------------------------------------------
//      = case_w / case_d                      62.0 x 32.0 mm
//
//      The old 58 x 30 mm values were WRONG: the 59.2 mm glass would not
//      fit into a 58 mm case at all. If you fit a different panel, FIRST
//      update panel_glass_w / panel_glass_h (the glass's actual outer outline)
//      and bezel_lip, THEN re-derive the outer dimensions with
//      case_w = panel_glass_w + 2*bezel_lip and
//      case_d = panel_glass_h + 2*bezel_lip.
//      (case.scad also prints this relationship to the console via `echo`.)
//
//      The glass is placed BEHIND this frame, into a slot opened from the
//      inside: the glass is recessed by lip_depth (1.2 mm) behind the front
//      face, leaving a 1.4 mm bezel on the front face. Do not try to fit the
//      glass from the front, it will not go in.
//
// -----------------------------------------------------------------------------
//  THICKNESS (Z) STACK-UP CALCULATION — case_h is derived from this
// -----------------------------------------------------------------------------
//  This case cannot be 9.5 mm: the parts do not stack up and the lid does not close.
//  The actual stack, front to back:
//
//      layer                                   thickness   z range
//      --------------------------------------  ---------  -------------
//      1. front wall over the panel edge          1.20     0.00 –  1.20
//      2. panel glass (2.13" e-paper)             1.05     1.20 –  2.25
//      3. FPC fold clearance                      0.80     2.25 –  3.05
//      4. PCB                                     1.60     3.05 –  4.65
//      5. tallest part on the back of the board   2.50     4.65 –  7.15
//         (ESP32-C3-MINI-1 module = 2.4 mm)
//      6. Li-Po pouch cell (402025)               4.00     7.15 – 11.15
//      7. rear wall (lid plate)                   1.60    11.15 – 12.75
//      --------------------------------------  ---------
//      TOTAL                                      12.75 mm
//
//      case_h = 13.0 mm  ->  0.25 mm safety margin (for foam/sponge)
//
//  If you change the panel or the battery, do NOT GUESS case_h: the
//  stack_total variable below is computed automatically from the layers,
//  printed with `echo` and compared against case_h.  If you see a red/large
//  difference, update case_h to match stack_total.
//
//  PRINT SETTINGS (recommended):
//      0.2 mm layer, 3 perimeters, 20% infill, PLA or PETG.
//      NO supports needed.  Nozzle 0.4 mm, first layer 0.25 mm.
//
//  On the first print, print ONLY the panel slot first and fit it to the panel:
//      openscad -o panel_test.stl -D 'PART="panel_test"' case.scad
// =============================================================================

// --- PARAMETERS --------------------------------------------------------------

// ---- outer dimensions ----
// case_w / case_d are derived from the glass outer outline + bezel (see the note above):
//   case_w = panel_glass_w + 2 * bezel_lip = 59.2 + 2.8 = 62.0
//   case_d = panel_glass_h + 2 * bezel_lip = 29.2 + 2.8 = 32.0
case_w        = 62.0;   // case body width (X)  — glass 59.2 + 2 x 1.4 bezel
case_d        = 32.0;   // case body depth (Y)  — glass 29.2 + 2 x 1.4 bezel
case_h        = 13.0;   // case body total thickness (Z) — see the stack-up calculation
wall          = 1.6;    // wall thickness (sufficient at this size in PETG/PLA)

// ---- panel (2.13" e-paper, SSD1680) ----
panel_active_w = 48.6;  // visible (active) area "measure and update"
panel_active_h = 23.7;
panel_glass_w  = 59.2;  // glass OUTER outline — Waveshare "Outline (screen only)"
panel_glass_h  = 29.2;  //   "measure and update"; case_w/case_d derive from this
panel_t        = 1.05;  // glass thickness  -> stack layer 2
window_w       = 49.0;  // window opening in the front face (active area + margin)
window_h       = 24.1;
bezel_lip      = 1.4;   // width of the frame remaining around the glass on the front face
glass_lip_w    = panel_glass_w + 0.2;   // 59.4  inner slot the glass seats in
glass_lip_h    = panel_glass_h + 0.2;   // 29.4  (glass + 0.2 mm clearance)
lip_depth      = 1.2;   // slot depth from the front face -> stack layer 1
// Note: the glass is placed into this slot FROM THE BACK (inside) and recessed
// 1.2 mm behind the front face; a 1.4 mm bezel frame remains on the front face.
// Since the glass is 59.2 mm, it cannot pass through the 1.4 mm frame from the
// front — the slot is open from the inside.
// If it fits too tightly, increase glass_lip_w/h by 0.2 mm (see README §3).

// ---- FPC fold clearance ----
fpc_clearance = 0.8;    // between glass and PCB -> stack layer 3
fpc_w         = 12.0;   // 24-pin FPC channel "measure and update"
fpc_x         = 0.0;    // X position of the channel; wherever the FPC exits the panel

// ---- PCB (45 x 24 mm) ----
pcb_w         = 45.0;   // "measure and update"
pcb_h         = 24.0;   // "measure and update"
pcb_t         = 1.6;    // -> stack layer 4
rear_parts    = 2.5;    // tallest part on the back of the board -> layer 5
                        // (ESP32-C3-MINI-1 = 2.4 mm; margin allowed)
pcb_hole_d    = 1.9;    // hole the M1.6 screw passes through
pcb_hole_inset= 2.5;    // inset of the holes from the board edge
pcb_boss_d    = 4.0;    // boss outer diameter

// ---- battery (402025 LiPo pouch) ----
// The cell lies with its 25 mm edge running along the LONG axis of the case.
cell_w        = 20.0;   // short edge of the 402025 "measure and update"
cell_l        = 25.0;   // long edge
cell_t        = 4.0;    // thickness -> stack layer 6
pocket_clear  = 0.5;    // clearance left on each side of the pocket -> 21 x 26
foam_allow    = 0.5;    // foam/sponge margin (added to thickness) -> 4.5
batt_w        = cell_w + 2 * pocket_clear;   // 21.0  (Y direction)
batt_l        = cell_l + 2 * pocket_clear;   // 26.0  (X direction, long axis)
batt_t        = cell_t + foam_allow;         // 4.5   (Z direction, foam included)
rail_t        = 1.6;    // thickness of the retaining wall surrounding the battery

// ---- USB-C (bottom edge, -Y) ----
usb_w         = 9.0;    // "measure and update"
usb_h         = 3.4;    // "measure and update"
usb_x         = 0.0;    // X position "measure and update"

// ---- power switch (RIGHT edge, +X) ----
sw_w          = 4.0;    // "measure and update"
sw_h          = 1.6;    // "measure and update"
sw_y          = -6.0;   // Y position "measure and update"

// ---- 3 buttons (RIGHT edge, +X) ----
btn_count     = 3;
btn_d         = 3.0;    // outer user hole (actuator) "measure and update"
btn_pusher_d  = 1.5;    // inner pusher hole "measure and update"
btn_cbore     = 0.8;    // countersink depth of the outer hole
btn_pitch     = 5.0;    // spacing between buttons "measure and update"
btn_y0        = -4.0;   // Y position of the first button "measure and update"
btn_dz        = 2.5;    // Z offset of each button "measure and update"

// ---- lid and mounting ----
use_snaps     = false;  // true: snap-fit hooks, false: 4x M1.6 screwed boss
screw_d       = 1.6;    // M1.6 sheet-metal screw pilot hole
screw_depth   = 5.0;    // pilot hole depth
corner_leg    = 5.0;    // edge of the corner screw tower (gusset)
pcb_pilot_z   = 0.6;    // bottom of the PCB pilot hole (from the front face); 0.6 mm wall remains
lid_t         = wall;   // lid plate thickness -> layer 7
lid_lip_h     = 1.0;    // height of the lid's OUTER lip that fits into the case body
lid_lip_t     = 1.0;    // lip thickness (inward from the case body outer surface)
snap_hook     = 1.0;    // snap-fit hook protrusion

eps           = 0.01;   // small offset to prevent z-fighting
$fn           = 64;     // round surface resolution

// --- DERIVED DIMENSIONS (do not change) ---------------------------------------

// Stack calculation — when the panel/battery changes, check case_h from here.
stack_total = lip_depth + panel_t + fpc_clearance + pcb_t + rear_parts
            + cell_t + lid_t;                     // = 12.75 mm
stack_slack = case_h - stack_total;               // = 0.25 mm

// Layer boundaries in the Z plane (measured from the front outer face).
z_glass_seat = lip_depth;                          // 1.20  face the glass seats on
z_glass_top  = z_glass_seat + panel_t;             // 2.25  back face of the glass
z_pcb_front  = z_glass_top + fpc_clearance;        // 3.05  PCB front face
z_pcb_back   = z_pcb_front + pcb_t;                // 4.65  PCB back face
z_cell_front = z_pcb_back + rear_parts;            // 7.15  battery front face
z_cell_back  = z_cell_front + cell_t;              // 11.15 battery back face
z_lid_inner  = case_h - lid_t;                     // 11.40 lid inner face
tray_depth   = case_h - lid_t;                     // 11.40 case body (lidless) height

// Section positions — all "measure and update"; the exact height of the
// connector depends on the size of the connector/switch on the board.
usb_z        = z_pcb_front + pcb_t / 2 + 0.1;      // 3.95  USB-C center
sw_z         = z_pcb_front + pcb_t / 2;            // 3.85  switch center
btn_z        = z_pcb_front + pcb_t / 2 - btn_dz;   // 1.35  first button center

inner_w = case_w - 2 * wall;                       // 58.8
inner_d = case_d - 2 * wall;                       // 28.8

// Screw centers: the middle of the corner gussets.  The body and lid use the
// SAME array, so the holes always align.
screw_x = inner_w / 2 - corner_leg / 2;            // 24.9
screw_y = inner_d / 2 - corner_leg / 2;            // 10.9

// Stack check: prints to the OpenSCAD console.
echo(str("STACK: layers = ", stack_total, " mm, case_h = ", case_h,
         " mm, safety margin = ", stack_slack, " mm"));
echo(str("STACK: glass top = ", z_glass_top, ", PCB = ", z_pcb_front, "..",
         z_pcb_back, ", battery = ", z_cell_front, "..", z_cell_back,
         ", lid inner = ", z_lid_inner));
// Remind on every run that the outer dimensions derive from the glass.
echo(str("CASE: glass outer outline = ", panel_glass_w, " x ", panel_glass_h,
         " mm, bezel = ", bezel_lip, " mm -> case_w x case_d = ",
         case_w, " x ", case_d, " mm (expected ",
         panel_glass_w + 2 * bezel_lip, " x ", panel_glass_h + 2 * bezel_lip,
         ")"));
echo(str("CASE: glass slot = ", glass_lip_w, " x ", glass_lip_h,
         " mm, window = ", window_w, " x ", window_h, " mm, glass depth = ",
         lip_depth, " mm"));

if (case_w < panel_glass_w + 2 * bezel_lip - eps ||
        case_d < panel_glass_h + 2 * bezel_lip - eps)
    echo("WARNING: the glass does not fit the case! Set case_w/case_d to glass + 2*bezel_lip.");

if (stack_slack < 0)
    echo("WARNING: the parts do not fit! Set case_h to at least stack_total.");

// -----------------------------------------------------------------------------
//  Helpers
// -----------------------------------------------------------------------------

// Rounded-corner profile in the XY plane, centered at the origin.
module rounded_profile(w, d, r) {
    hull() {
        for (sx = [-1, 1]) for (sy = [-1, 1])
            translate([sx * (w / 2 - r), sy * (d / 2 - r)])
                circle(r = r);
    }
}

// Rounded box along the Z axis.
module rounded_box(w, d, h, r) {
    linear_extrude(height = h)
        rounded_profile(w, d, r);
}

// -----------------------------------------------------------------------------
//  Panel slot: window + inner lip the glass seats on
//  (used as volumes to "subtract" in the case body difference operation)
// -----------------------------------------------------------------------------

// Window in the front face: passes through the wall completely.
module panel_window() {
    translate([0, 0, -eps])
        linear_extrude(height = wall + 2 * eps)
            rounded_profile(window_w, window_h, 0.6);
}

// Seat for the glass: recessed inward from the front face by lip_depth.
module panel_lip_recess() {
    translate([0, 0, -eps])
        linear_extrude(height = lip_depth + eps)
            rounded_profile(glass_lip_w, glass_lip_h, 0.8);
}

// Channel where the 24-pin FPC exits the panel and folds onto the board.  Removes
// the 1.2–1.6 mm band in the glass region: the glass does not seat on the lip in
// this 12 mm strip, but since the FPC already exits there the edge is not left
// unsupported.
//
// THE CHANNEL IS ON THE +Y EDGE: the J2 connector is on the +Y edge of the board
// (y = 20.6 / 24 mm) and the panel's FPC also exits from that edge.  It used to be
// on -Y; the FPC had to wrap around the whole board (tools/gen_pcb_layout.py
// --check caught this).  If the panel's FPC exits from another edge, shift fpc_x
// or do not call this module.  "measure and update"
module fpc_passage() {
    translate([
        fpc_x - fpc_w / 2,
        glass_lip_h / 2,
        z_glass_seat - eps
    ])
        cube([
            fpc_w,
            (case_d / 2 - glass_lip_h / 2) + eps,
            wall - z_glass_seat + 0.1
        ]);
}

// -----------------------------------------------------------------------------
//  PCB bosses: 45 x 24 mm board, 4x M1.6, from the front wall up to z_pcb_front
// -----------------------------------------------------------------------------

module pcb_boss_positions() {
    for (sx = [-1, 1]) for (sy = [-1, 1])
        translate([
            sx * (pcb_w / 2 - pcb_hole_inset),
            sy * (pcb_h / 2 - pcb_hole_inset),
            0
        ])
            children();
}

// Corner screw towers: square gusset (supported) resting against both side walls.
module screw_positions() {
    for (sx = [-1, 1]) for (sy = [-1, 1])
        translate([sx * screw_x, sy * screw_y, 0])
            children();
}

module screw_gussets() {
    screw_positions()
        translate([0, 0, tray_depth - screw_depth / 2])
            difference() {
                cube([corner_leg, corner_leg, screw_depth], center = true);
                cylinder(d = screw_d, h = screw_depth + 2 * eps, center = true);
            }
}

module pcb_bosses() {
    // The bosses rise from the inner face of the front wall (z = wall) up to the
    // PCB front face (z_pcb_front); the board rests on them.  The pilot hole stops
    // at pcb_pilot_z so it does not pierce the front face.
    pcb_boss_positions()
        difference() {
            translate([0, 0, wall])
                cylinder(d = pcb_boss_d, h = z_pcb_front - wall + eps);
            translate([0, 0, pcb_pilot_z])
                cylinder(d = screw_d, h = z_pcb_front - pcb_pilot_z + eps);
        }
}

// -----------------------------------------------------------------------------
//  Battery holder: 26 x 21 x 4.5 mm pocket, behind the PCB
// -----------------------------------------------------------------------------
//  A continuous base plate does NOT FIT: there is 6.75 mm between the PCB back
//  and the lid inner face, of which 2.5 mm goes to the rear parts and 4.0 mm to
//  the cell.  So the cell rests on 4 small supports at the corners (the central
//  region left beneath the module stays empty) and is held horizontally by a
//  4-walled frame.  Since the frame's two walls in the X direction rest against
//  the case side walls, it is not left floating — no support needed.
// -----------------------------------------------------------------------------

module battery_pocket() {
    pad = 3.0;   // support pad edge

    // 1) Corner support pads — the underside is left empty (module clearance).
    //    They do not line up under the module (ESP32-C3-MINI-1, ~16.6 x 13.2 mm,
    //    centered).  Pad positions "measure and update".
    for (sx = [-1, 1]) for (sy = [-1, 1])
        translate([
            sx * (batt_l / 2 - pad / 2),
            sy * (batt_w / 2 - pad / 2),
            z_cell_front - 0.4
        ])
            cube([pad, pad, 0.8 + eps], center = true);

    // 2) The two walls in the Y direction: extend up to the case side walls (supported).
    for (sy = [-1, 1])
        translate([
            -inner_w / 2,
            sy * (batt_w / 2 + rail_t / 2) - rail_t / 2,
            z_cell_front
        ])
            cube([
                inner_w,
                rail_t,
                tray_depth - z_cell_front + eps
            ]);

    // 3) The two walls in the X direction: connect to the Y walls.
    for (sx = [-1, 1])
        translate([
            sx * (batt_l / 2 + rail_t / 2) - rail_t / 2,
            -(batt_w / 2 + rail_t),
            z_cell_front
        ])
            cube([
                rail_t,
                2 * (batt_w / 2 + rail_t),
                tray_depth - z_cell_front + eps
            ]);
}

// -----------------------------------------------------------------------------
//  Case body
// -----------------------------------------------------------------------------

module case_body() {
    // NOTE: the outer shell, inner cavity and all sections are cut in a single
    // difference operation.  The battery holder, PCB bosses and screw gussets stay
    // INSIDE the cavity, so they are added AFTER this difference operation;
    // otherwise the cavity would erase them too.
    difference() {
        // 1) outer shell (z = 0 .. tray_depth)
        rounded_box(case_w, case_d, tray_depth, 3.0);

        // 2) inner cavity — the front wall and side walls remain
        translate([0, 0, wall])
            rounded_box(inner_w, inner_d, tray_depth - wall + 2 * eps, 2.2);

        // 3) front face: window, glass slot, FPC channel
        panel_window();
        panel_lip_recess();
        fpc_passage();

        // 4) USB-C, bottom edge (-Y)
        //    Given by X and Z measurement so the connector opening is flush with the front face.
        translate([usb_x, -case_d / 2 + wall / 2, usb_z])
            rotate([90, 0, 0])
                linear_extrude(height = wall + 2 * eps, center = true)
                    rounded_profile(usb_w, usb_h, 1.2);

        // 5) power switch, right edge (+X)
        translate([case_w / 2 - wall / 2, sw_y, sw_z])
            rotate([0, 90, 90])
                linear_extrude(height = wall + 2 * eps, center = true)
                    rounded_profile(sw_h, sw_w, 0.5);

        // 6) 3 buttons, right edge (+X): outer countersink + inner pusher hole
        for (i = [0 : btn_count - 1]) {
            y = btn_y0 - i * btn_pitch;
            z = btn_z + i * btn_dz;
            // Outer hole (the actuator is visible through it)
            translate([case_w / 2 - wall - 2 * eps, y, z])
                rotate([90, 0, 0])
                    cylinder(d = btn_d, h = 2 * btn_cbore + 2 * eps);
            // Inner pusher hole
            translate([case_w / 2 - wall - eps, y, z])
                rotate([90, 0, 0])
                    cylinder(d = btn_pusher_d, h = wall + 2 * eps);
        }

        // 7) step for the lid's outer lip (cut from the outside of the case body)
        translate([0, 0, tray_depth - lid_lip_h])
            difference() {
                rounded_box(case_w + 1, case_d + 1, lid_lip_h + eps, 3.0);
                rounded_box(
                    case_w - 2 * lid_lip_t,
                    case_d - 2 * lid_lip_t,
                    lid_lip_h + 2 * eps,
                    2.8
                );
            }

        // 8) snap-fit hook pockets
        if (use_snaps)
            for (sy = [-1, 1])
                translate([
                    -3,
                    sy * (case_d / 2 - wall) - wall / 2,
                    tray_depth - 2 * snap_hook
                ])
                    cube([6, wall + 2 * eps, snap_hook + eps]);
    }

    // --- internal structure: added AFTER the cavity is cut ---

    // Battery holder (its walls rest on the two side walls -> supported)
    battery_pocket();

    // PCB bosses
    pcb_bosses();

    // Corner screw gussets
    if (!use_snaps)
        screw_gussets();

    // Snap-fit hooks (rest against the side walls)
    if (use_snaps)
        for (sy = [-1, 1])
            translate([
                -2.5,
                sy * (case_d / 2 - wall / 2) - wall / 2,
                tray_depth - 2 * snap_hook
            ])
                cube([5, wall, snap_hook]);
}

// -----------------------------------------------------------------------------
//  Rear lid
// -----------------------------------------------------------------------------

module case_lid() {
    difference() {
        union() {
            // Lid plate: z = 11.4 .. 13.0
            translate([0, 0, z_lid_inner])
                rounded_box(case_w, case_d, lid_t, 3.0);

            // OUTER lip that fits into the case body: z = 10.4 .. 11.4
            translate([0, 0, z_lid_inner - lid_lip_h])
                difference() {
                    rounded_box(case_w, case_d, lid_lip_h + eps, 3.0);
                    rounded_box(
                        case_w - 2 * lid_lip_t,
                        case_d - 2 * lid_lip_t,
                        lid_lip_h + 2 * eps,
                        2.8
                    );
                }

            // Snap-fit tabs
            if (use_snaps)
                for (sy = [-1, 1])
                    translate([
                        -3,
                        sy * (case_d / 2 - wall) - wall / 2,
                        z_lid_inner - 2 * snap_hook
                    ])
                        cube([5, wall, snap_hook]);
        }

        // Screw holes (M1.6 passes through the lid).
        // The SAME screw_positions() array is used as the case body gussets,
        // so the holes always align.
        if (!use_snaps)
            screw_positions()
                translate([0, 0, z_lid_inner - lid_lip_h - eps])
                    cylinder(
                        d = screw_d + 0.3,
                        h = lid_t + lid_lip_h + 2 * eps
                    );
    }
}

// -----------------------------------------------------------------------------
//  First test print: panel slot only
//  (to seat the glass and verify the dimensions, a ~15 minute print)
// -----------------------------------------------------------------------------

module panel_test() {
    difference() {
        rounded_box(case_w, case_d, wall + 2.0, 3.0);
        panel_window();
        panel_lip_recess();
        translate([0, 0, wall + eps])
            rounded_box(inner_w, inner_d, 3.0, 2.2);
    }
}

// -----------------------------------------------------------------------------
//  Part selector
// -----------------------------------------------------------------------------

PART = "both";   // "both" | "body" | "lid" | "panel_test"

if (PART == "body") {
    case_body();
} else if (PART == "lid") {
    case_lid();
} else if (PART == "panel_test") {
    panel_test();
} else {
    case_body();
    // The lid is placed next to the case body (on the same print bed).
    translate([0, case_d + 8, 0])
        case_lid();
}
