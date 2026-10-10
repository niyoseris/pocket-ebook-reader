# Twitter/X thread — Pocket Reader

16 posts. Each post is under 280 characters; the exact character count is at the
end of each post as an HTML comment. Total: **3,464 characters** across 16 posts.

> The repository is live at <https://github.com/niyoseris/pocket-ebook-reader>.
> Hashtags are kept to two, at the very end.

---

**1/**

I designed a pocket e-ink reader. Before building it, I put the datasheets up against my own assumptions. They found 12 errors. Wrong package, wrong resistors, a missing high-voltage supply, and a case smaller than its own screen. Thread. <!-- 238 -->

**2/**

ESP32-C3, 2.13"/250x122 e-paper, 500 mAh Li-Po, three buttons. 62x32x13 mm. Deep sleep 28-55 uA → 12-24 months standby. A page turn is ~0.3 s. <!-- 142 -->

**3/**

Error 1. I assumed the buck-boost regulator was a 10-pin VSON. Datasheet: 14-pin. Not a tweak. The footprint, the pinout and the netlist a fab house would import were all wrong, built on a package that doesn't exist. <!-- 216 -->

**4/**

Error 2. A low-power regulator was marked "pin-compatible." It's a different package - 10 pins vs 14, different layout. That board wouldn't be edited, it'd be redrawn. The claim sat in my notes, quietly false, for weeks. <!-- 220 -->

**5/**

Error 3. My 3.3 V feedback divider: 560k / 100k. The datasheet's own 3.3 V row says 1M / 180k. I had a number that produced a plausible voltage and never checked it against the table that exists to give it. <!-- 206 -->

**6/**

Error 4. A strapping pin was documented as "must be HIGH at boot." The real boot table says its value is don't-care for a normal SPI boot. I'd placed a button based on that. The placement survived; the reasoning didn't. Reasoning is what you reuse. <!-- 248 -->

**7/**

Error 5, the worst. The panel needs an external ±15 V boost. It exposes GDR and RESE pins for exactly that. My design had none - just 3.3 V and a capacitor. A bookmark-sized device missing the circuit that makes the ink move. <!-- 225 -->

**8/**

Error 6. The case was 58x30 mm. The panel glass is 59.2x29.2 mm. Not tight - it could not be assembled. The outside is now derived from the glass: glass + 1.4 mm bezel per side = 62x32 mm. <!-- 188 -->

**9/**

Errors 7-8. Mounting holes overlapped four components' courtyards. And three buttons could not fit the 15 mm of edge between two holes. A drawing that looks fine and a drawing that is manufacturable are not the same image. <!-- 222 -->

**10/**

Then two silent software bugs. The EPUB converter deleted every paragraph break. Every book would render as one giant run-on paragraph. Nothing crashed. The file listed fine. Six regression tests now guard it. <!-- 209 -->

**11/**

The font's top offset meant two different things in the two halves of my code. Per-glyph, not a constant shift: a period drifted 13 px up, a capital A dropped 9 below baseline. Two agents wrote two halves, each internally consistent. <!-- 233 -->

**12/**

Lesson: the failures that hurt are the ones that don't crash. A wrong LUT kills a panel slowly. A dropped paragraph break gives you a file that opens. A misread strapping table gives you a device that boots - most of the time. <!-- 226 -->

**13/**

The part I'm proudest of is proud for the wrong reason. 53 pins → 11 GPIOs broken out → 4 that wake from deep sleep. Ten signals into eleven pins, without breaking boot strapping. It worked because one thing lined up: <!-- 217 -->

**14/**

Panel BUSY idles HIGH - the exact level the strapping pin it sits on needs at boot. The busiest signal in the design satisfies a boot requirement by itself, with no extra part. I'll take it. <!-- 190 -->

**15/**

Honesty: never physically built. Firmware never compiled. 66 host tests pass; 13 pin numbers still marked unverified. I'd rather ship a project that documents its own uncertainty than one that performs confidence. <!-- 213 -->

**16/**

Everything is generated from one placement file, so the 3D and 2D drawings can't drift. Repo: schematic, netlist, parametric case, firmware, tools, an interactive 3D page (rotate / explode / cross-section), STL. github.com/niyoseris/pocket-ebook-reader #opensource #ESP32 <!-- 271 -->
