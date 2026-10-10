> Türkçe sürüm: [09-roadmap.tr.md](09-roadmap.tr.md)

# 09 · Roadmap and Contribution Ideas

Each item is marked with **difficulty** and **impact**. The best starting point for
new contributors: 🟢 easy + high-impact items.

---

## Currently working (v1.0)

- ✅ 2.13" SSD1680 driver: init, full refresh, partial refresh, deep sleep
- ✅ `.epf` font system loaded at runtime (full Turkish coverage)
- ✅ `.epr` book format + pagination + page index cache
- ✅ Library / reader / menu / Wi-Fi / error screens
- ✅ 3 buttons, short/long press, hardware + software debounce
- ✅ Deep sleep + wake via ext1 + smart wake that skips the splash screen
- ✅ ADC battery measurement and Li-Po discharge curve
- ✅ Wi-Fi transfer: HTTP server, browser interface, AP setup mode
- ✅ Desktop tools: EPUB converter, font generator, upload tool
- ✅ Parametric 3D-printed case
- ✅ Generatable netlist + connection table

---

## Known limitations

| Limitation | Impact | Difficulty |
|---|---|---|
| **13 pin numbers not verified** (USB-C, USBLC6, Si1308EDL) | The netlist cannot be imported directly into pcbnew | 🟢 |
| **The panel's external boost circuit has not been tested** | If built wrong the panel is damaged | 🔴 |
| **The BUSY polarity is disputed** | If wrong the device gives no image at all | 🟢 |
| **The firmware has not been compiled** | The first build needs small fixes | 🟡 |
| Not tested on real hardware | Some behaviours may be surprising | 🔴 |
| No word breaking with Turkish hyphenation | Long words are split at the end of the line | 🟡 |
| The MENU button cannot wake from sleep | An extra step gets in the way | 🔴 (hardware constraint) |
| No frontlight | It cannot be read in the dark | 🔴 (no panel at this size) |
| Single font family | — | 🟢 |

---

## Roadmap

### v1.1 — Verification and hardening

| # | Item | Impact | Difficulty |
|---|---|---|---|
| 1 | ~~Complete the pinouts in `pinouts.md` from the datasheet~~ — **partially done:** FPC 24-pin, ESP32-C3-MINI-1 (53 pin), MCP73831, TPS63020 (14-pin), TPS63900, SSD1680 verified and entered into `gen_netlist.py`. **The remaining 13 pins:** USB-C receptacle, USBLC6-2SC6, Si1308EDL | 🔴🔴🔴 | 🟢 |
| 2 | Compile the firmware on real hardware, fix the build errors | 🔴🔴🔴 | 🟡 |
| 3 | Build the first physical prototype, enter the measurements into the table in `docs/07` §6 | 🔴🔴🔴 | 🟡 |
| 4 | A step-by-step photo assembly guide for the easy build | 🔴🔴 | 🟢 |
| 5 | Generate the Gerbers and put them under `hardware/pcb/gerbers/` | 🔴🔴 | 🟡 |
| 6 | Firmware build check with GitHub Actions | 🔴 | 🟢 |

> **The remaining 13 pins are the highest-impact contribution.** Reading three
> datasheets (USB-C receptacle, USBLC6-2SC6, Si1308EDL) is enough, and after that
> the netlist becomes directly importable into pcbnew. `python3 gen_netlist.py
> --check` lists which are left.

| 1b | **Verify the BUSY polarity by measurement** (a 30-second job, `firmware/README.md`) and fix the `EPD_BUSY_ACTIVE_HIGH` value in `config.h` | 🔴🔴🔴 | 🟢 |
| 1c | **Build and verify the panel's external boost circuit on a breadboard** — or show that it works with the adapter board | 🔴🔴🔴 | 🟡 |

### v1.2 — Reading experience

| # | Item | Impact | Difficulty |
|---|---|---|---|
| 7 | **Word breaking with Turkish hyphenation** (at the end of the line `kitap-` / `lar`) | 🔴🔴 | 🟡 |
| 8 | A table of contents screen and chapter skipping | 🔴🔴 | 🟡 |
| 9 | Saving the reading position per book (currently a single position) | 🔴🔴 | 🟢 |
| 10 | Placing a bookmark | 🔴 | 🟡 |
| 11 | A reading progress bar (currently only %) | 🔴 | 🟢 |
| 12 | Adapting the sleep time to the user's behaviour | 🔴 | 🟢 |
| 13 | Fast page skipping (10 pages when the button is held) | 🔴🔴 | 🟢 |
| 14 | Changing the typeface (more than one `.epf` from the menu) | 🔴 | 🟡 |
| 15 | Margin and line spacing adjustment | 🔴 | 🟢 |

### v1.3 — Power

| # | Item | Impact | Difficulty |
|---|---|---|---|
| 16 | **Complete the TPS63900 low-power variant** (configuration resistor + pinout check, `docs/07` §3) | 🔴🔴🔴 | 🟡 |
| 17 | Make the divider 1 MΩ/1 MΩ (19 µA gain) | 🔴🔴 | 🟢 |
| 18 | Cut the divider completely with a MOSFET in sleep | 🔴🔴 | 🟡 |
| 19 | Measure and shorten the wake time | 🔴🔴 | 🟡 |
| 20 | A sleep current measurement script / test method standard | 🔴 | 🟢 |

### v1.4 — Content and transfer

| # | Item | Impact | Difficulty |
|---|---|---|---|
| 21 | **Direct import from a Kobo/Kindle library** (Calibre plugin) | 🔴🔴🔴 | 🟡 |
| 22 | A Calibre plugin (`epub2epr` integrated) | 🔴🔴🔴 | 🟡 |
| 23 | Showing a progress bar on the screen during a wireless upload | 🔴 | 🟢 |
| 24 | Downloading a book from the device (backup) | 🔴 | 🟢 |
| 25 | Scheduled automatic upload (watch the library folder) | 🔴 | 🟡 |
| 26 | OPDS catalogue support (direct download from Kavita/Calibre-Web) | 🔴🔴 | 🔴 |

### Errors found and fixed during verification

While this repo was being prepared, **twelve errors** were found in the first
design and fixed. None of them on real hardware. They fall into three groups and
stand here as a record.

**Six came from reading the official datasheets** against assumptions that had
never been checked:

| Finding | First design | Correct |
|---|---|---|
| TPS63020 package | VSON-10 | **VSON-14 (DSJ), 3×4 mm** |
| TPS63900 compatibility | "pin-compatible" | **Not compatible**, the layout changes |
| Feedback resistors | 560k / 100k | **1 MΩ / 180 kΩ** (datasheet Table 3) |
| GPIO8 strapping | Must be HIGH at startup | **Don't care for SPI boot** (Table 4-3) |
| Panel supply | Only 3.3 V + capacitor | **An external ±15 V boost is also mandatory** (GDR/RESE) |
| Panel BUSY polarity | HIGH = idle | **Datasheet: HIGH = busy** — made configurable |

**Four came from validators written around the placement data.** A part that
overlaps a mounting hole, or does not fit inside its own case, is invisible in a
schematic:

| Finding | What it would have caused | Fix |
|---|---|---|
| Body dimension | The case was 58 × 30 mm; the panel **glass is 59.2 × 29.2 mm** and cannot be assembled into it | **62 × 32 mm**, derived from the glass: glass + 2 × 1.4 mm bezel |
| FPC passage on the wrong case edge | The case cut the ribbon channel into −Y while J2 sits on the PCB's +Y edge, so the FPC had to wrap the whole board | Channel moved to +Y. Caught by the drawing generator's geometry check |
| Mounting holes vs courtyards | The four M1.6 holes overlapped the courtyards of `BT1`, `SW4`, `R13` and `R15` | The hole zones are now reserved keep-out regions and the placer refuses to put anything there |
| Buttons did not fit | Three 5 mm buttons cannot fit in the 15 mm of edge left between two holes | Buttons reduced to 4.5 mm and re-spaced |

**And two came from integration tests** — silent bugs, neither of which stops the
device booting, but both of which corrupt the result:

| Finding | Symptom | Fix |
|---|---|---|
| The `.epr` converter **was deleting every paragraph end** | Every converted book appeared as a single long paragraph | The unconditional trim inside `add_block` was reduced to chapter starts only + 6 regression tests |
| The reference point of the `.epf` `top` field **differed** between the two sides | The firmware assumed `top` was measured from the baseline; because the error varied per glyph, **the text was spread out vertically** | `y0 = baseline_y - (ascent - top) * scale`; `tools/tests/test_epf_interop.py` compares the two halves at edge-case widths |

The second bug arose from **two different agents writing the two halves of the same
binary format.** That is why `test_epf_interop.py` no longer tests its own
assumption, but parses the firmware source at runtime and tests **the other side's**
rule. Searching for other silent mismatches of the same pattern would be a good
contribution — the `.epr` page index cache (`/cache/*.idx`) is the next candidate.

### v2.0 — At the idea stage

| Idea | Note |
|---|---|
| 2.9" 296×128 panel support | The same code, a different panel profile. More readable, ~2× the price, case body 69 × 32 mm |
| Touch | The panel layer is more expensive than the panel; probably not worth it |
| Frontlight | There is no ready solution at this size; a custom light guide is needed |
| An infrared/Bluetooth page-turn remote | Easy with BLE |
| Multilingual interface | `i18n.h` is already in a table structure; a translation PR is enough |
| Greyscale (4 levels) in partial update | The SSD1680 supports it but a LUT is needed; ghosting risk |
| Pairing with an app (Android/iOS) | File transfer over BLE GATT |
| Solar charging | A small panel + BQ25570 |

---

## Contributing

### The easiest starting points

1. **Verify a pin number** — pick a `UNVERIFIED` entry from `pinouts.md`, look it
   up in the datasheet, enter it into `gen_netlist.py`, send a PR. A 5-minute job
   on its own.
2. **Photograph your own build** — add step-by-step photos to `docs/04`.
3. **Test with a typeface** — generate a different font with `fontgen.py` and
   attach the `--preview` output to an issue. Let's decide together which font is
   the most readable at 14 px.
4. **Convert a book** — if `epub2epr.py` fails on an EPUB (rare but it happens) fix
   the converter.
5. **Improve the error messages** — if the error messages are only meaningful to a
   developer, make them meaningful to the user.

### Contribution rules

- Firmware code with **English** identifiers and comments; user-visible strings
  English/Turkish via `i18n.h` (English by default, `-DLANG_TR` for Turkish)
- Documentation is written in **English**; Turkish translations are kept
  alongside as `<name>.tr.md`. Both languages get every change — a doc update
  that only lands in one language is treated as incomplete
- If you make a hardware change, update `gen_netlist.py` and run
  `python3 gen_netlist.py --check` — the outputs (CSV + netlist) are generated from
  this script, not edited by hand
- If you claim a number, either measure it or write that it is a "calculation"

Details: [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## Thanks

This project rests on the following open-source works:

- **Waveshare e-Paper** (MIT) — the SSD1680 init sequence and partial refresh LUT
  tables are taken verbatim from the vendor's reference driver
- **Espressif ESP-IDF / Arduino core** — ESP32-C3 support
- **GoodDisplay** — panel specifications
- **Adafruit GFX** — the design of the Canvas API was inspired by this interface
- **Bitstream Vera / DejaVu** and **SIL OFL** font families — test fonts

---

Back: [08 · Troubleshooting](08-troubleshooting.md) · [Back to top](../README.md)
