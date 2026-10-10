# The datasheet is the reviewer

I set out to build a pocket e-ink book reader. Before I built anything, I pointed
the official datasheets at my own design and let them argue with it. They found
twelve errors.

Not typos. Wrong packages, wrong resistor values, a missing high-voltage supply,
a case that could not physically contain the screen it was built around. Every
one of them was sitting in a design that looked finished. I want to write down
what happened, because the errors are more interesting than the device.

## What the thing is

A single-hand e-ink reader. An ESP32-C3, a 2.13-inch 250 × 122 panel, a 500 mAh
1S Li-Po, three buttons, USB-C, in a 62 × 32 × 13 mm case. It deep-sleeps at
28–55 µA, which is 12 to 24 months of standby. Wake it and it skips the splash
screen and drops you on the page you left. A page turn is about 0.3 seconds.
No backlight, no touch, no phone.

The engineering rules I set for the repo are boring and strict: the schematic,
the KiCad netlist, the PCB placement drawings and a parametric OpenSCAD case are
all generated from one placement file. The 3D model and the 2D technical drawings
read the same coordinates, so they cannot drift apart. The firmware has no
third-party dependencies — the panel driver, the font loader, the book parser
and the HTTP server are all in the tree. A wrong panel waveform damages hardware
slowly, so the one vendor table I could not derive myself is copied verbatim,
with its source URL in the file header.

That is the tidy version. Here is the untidy one.

## The errors that don't crash

The one that stopped me was small. I had assumed the buck-boost regulator was a
10-pin VSON. The datasheet says 14-pin. That is not a value I could nudge — the
footprint, the pinout, and every net attached to it were wrong. The netlist that
a fab house would import was built on a package that does not exist.

Right behind it: I had described a lower-power regulator as "pin-compatible," a
drop-in alternative. It is a different package entirely. Ten pins, not fourteen,
different names, different layout. The board would not have been edited; it would
have been redrawn. That claim sat in my notes, quietly false, for weeks.

The feedback divider for the 3.3 V rail was 560 kΩ and 100 kΩ. The datasheet's own
3.3 V row says 1 MΩ and 180 kΩ. I had a number that produced a plausible voltage
and never checked it against the table that exists precisely to give it to you.

A strapping pin was documented in my design as "must be HIGH at boot." The real
boot table says its value is *don't care* for a normal SPI boot. I had placed a
button based on that requirement. The placement survived; the reasoning behind it
was wrong, which is worse, because the reasoning is what you reuse.

Then the one I keep coming back to. The panel needs an external ±15 V boost
converter. It is not optional and it is not hidden — the panel exposes two pins,
`GDR` and `RESE`, for exactly this purpose, and the datasheet's reference circuit
builds the charge pump out of an inductor, three Schottky diodes and a MOSFET. My
design had none of it. Just 3.3 V and a capacitor. The device was the size of a
bookmark, and it was missing the circuit that makes the ink move.

## The case was smaller than the glass

The enclosure was 58 × 30 mm. The panel's glass outline is 59.2 × 29.2 mm. The
glass did not fit in the case. Not "tight" — it could not be assembled, in either
dimension, by more than a millimetre. The outside dimensions are now *derived*
from the glass: glass plus a 1.4 mm bezel on each side, giving 62 × 32 mm. The
script prints the arithmetic on every run and warns if the panel no longer fits.

The thickness was wrong the same way. I had sketched 9.5 mm. The actual stack —
front wall, glass, FPC fold, PCB, the tallest rear component, the battery pouch,
the lid — totals 12.75 mm. 9.5 mm was not a case; it was a wish. It is 13.0 mm now,
and the script computes the stack rather than trusting me to.

Two more, from the same afternoon. The mounting holes overlapped the courtyards
of four components. And three buttons could not fit in the 15 mm of board edge
left between two mounting holes. Both are geometry problems with a single
correct answer, and both had been wrong in a drawing that looked fine, because a
drawing that looks fine and a drawing that is manufacturable are not the same
image.

## Two silent software bugs

The hardware errors were sharp. The software ones were worse, because nothing
about them announced itself.

The EPUB converter silently deleted every paragraph break. Every book would have
rendered as one enormous run-on paragraph. Nothing crashed. The file listed
correctly. The chapter markers were still there, so it looked structured. The
cause was an unconditional call to trim trailing breaks that was meant to run
only at a chapter start, and it ran everywhere. Six regression tests now guard it.

The second one only existed because two agents wrote two halves of one binary
format. The font's `top` offset was interpreted two different ways — measured
from the baseline in one half, from the cell top in the other. I could write
forever about why that is nasty, but here is the part that matters: the error was
*per-glyph*, not a constant shift. A period drifted 13 pixels up. A capital A
dropped 9 pixels below the baseline. Nothing about the file said "the offset is
wrong." The text simply would have rendered vertically scrambled, with lines
colliding, and the two halves each would have been internally consistent, each
insisting the other was fine.

So the fix was not a constant. It was a rule, written down once, and a test that
reads the firmware source at runtime and asserts that both halves apply the same
rule. Not my assumption of the rule — the other side's actual implementation.

## What the constraint taught me

The pin map is the part I am proudest of, and it is proud for the wrong reason.

The module has 53 pins. The dev board I targeted for the easy build breaks out
only 11 GPIOs. Only 4 of those can wake the chip from deep sleep. I had ten
signals to route — SPI clock and data, chip select, data/command, reset, busy,
three buttons and a battery divider — into eleven available pins, without
breaking the boot strapping requirements, and with two of the buttons still able
to wake it.

It worked out. Not because I am clever, but because one thing lined up: the
panel's `BUSY` line idles HIGH, and the strapping pin it landed on requires HIGH
at boot. The busiest signal in the design satisfies a boot requirement on its
own, with no extra part. I will take it.

The cost is real and documented: the menu button is on a pin that cannot wake the
device. You wake with a page button and press menu afterward. In practice nobody
minds.

One thing I refused to guess: the panel's `BUSY` polarity is genuinely ambiguous
between the datasheet and vendor example code. Rather than pick, the firmware
makes it a compile-time flag with a hard timeout. A wrong guess produces an error
message that names the observed pin level — not a hang.

## Honesty as a feature

Here is the part most project write-ups skip.

**This project has never been physically built. The firmware has never been
compiled.** I am telling you that up front. The 66 host-side tests pass; twelve of
them are the interop check that caught the font bug. The datasheet data is
verified with source URLs. But thirteen pin numbers — the USB-C receptacle, one
ESD diode array, one MOSFET — are still marked unverified, and the panel's boost
circuit has never been soldered. I would rather ship a project that documents its
own uncertainty than one that performs confidence.

## Why I wrote it down

The failures that hurt are the ones that don't crash.

A wrong lookup table damages a panel a little at a time, so you blame the panel.
A dropped paragraph break produces a file that opens, so you blame the reader. A
misread strapping table produces a device that boots — most of the time — so you
blame the flakiness. None of these hand you an error. They hand you a result that
looks like a result.

The datasheet is the only reviewer I have found that does not care what I
intended. It is free, it is already written, and it is frequently right. The
useful move was not to design first and check later. It was to sit the datasheet
down across the table from my own assumptions and let them disagree until one of
them gave up.

Everything is in the repo: the schematic, the generated netlist, the placement
data, the parametric case, the firmware, the host tools, and an interactive 3D
page where you can rotate the device, explode the layers and cut a cross-section
through the stack. The case ships as STL. The errors ship too — in the changelog,
in tables, with what was wrong and what replaced it.

Thirteen of them. I would have shipped every one.

---

## Suggested visuals

Repo-relative paths. Attach these at the matching points of the thread; do not
create new images.

- **Post 1 (hook) / the "what it is" post:** `hardware/diagrams/blok-diyagram.svg`
  — the power and signal block diagram sets the scale in one look.
- **Posts on the regulator, the divider and the ±15 V boost:** 
  `hardware/schematic/pocket-reader-schematic.svg` (full schematic;
  `U3` is the buck-boost, `Q2`/`L2`/`D2`–`D4` are the external boost block) and
  `hardware/pcb/pcb-layout-top.svg` (placement and courtyards).
- **Post on the case, thickness and the missing millimetres:**
  `hardware/diagrams/case-exploded.svg` (the layer stack that adds up to 12.75 mm,
  which is why the case is 13 mm and not 9.5).
- **Posts on the pin map and the buttons:**
  `hardware/diagrams/breadboard-wiring.svg` (the 11-GPIO wiring) and
  `hardware/pcb/pcb-layout-bottom.svg` (ground plane and keep-out).
- **Payoff post (repo, interactive model, STL):** `site/index.html` — the
  self-contained interactive page (rotate, explode, cross-section). Screenshot it
  in a normal browser and attach the still; the STL is generated from
  `hardware/enclosure/case.scad`, so there is no separate render to attach.
