# Hardware Licence

The **hardware design files** in this repository are under the following licence:

> **CERN Open Hardware Licence Version 2 — Strongly Reciprocal (CERN-OHL-S-2.0)**

Scope:

```
hardware/schematic/     schematic, netlist, connection table, generator scripts
hardware/pcb/           PCB placement files and production outputs
hardware/enclosure/     3D-printable case design
hardware/diagrams/      block and wiring diagrams
docs/01..04             bill of materials, schematic, PCB and assembly documents
```

---

## Summary (not binding — the actual text governs)

CERN-OHL-S-2.0 is a **strongly reciprocal** licence:

| Permitted | Condition |
|---|---|
| Use, manufacture and sell the design | ✅ |
| Modify it and make a derivative design | ✅ |
| Sell the product commercially | ✅ |
| Keep the design files (the Source) closed | ❌ **Prohibited** |

In short: you may make a product from this design and sell it, but you **must
publish the design files as open source** — including your own changes. This is
so that no one turns the hardware into a closed product and does not give it back
to the community.

The code side (firmware, tools) is licensed **MIT** and contains no commercial
restriction — see [LICENSE](LICENSE). This split is deliberate: hardware wants
reciprocity, software wants freedom.

---

## The actual licence text

> ⚠️ **To do before release:** This file gives the *summary* and the *scope* of
> the licence; the full, legally binding text of CERN-OHL-S-2.0 (~10,000 words)
> has not yet been inserted here. Before publishing a release, download the full
> text and append it to the end of this file:
>
> ```
> curl -O https://ohwr.org/cern_ohl_s_v2.txt
> cat cern_ohl_s_v2.txt >> LICENSE-HARDWARE.md
> ```
>
> Verify the integrity of the text with `sha256sum`. The licence header and
> disclaimer must be taken from the licence text itself.

Official sources:

- Licence text: <https://ohwr.org/cern_ohl_s_v2.txt>
- Explanation and FAQ: <https://ohwr.org/project/cernohl/wikis/Documents/CERN-OHL-version-2>
- Licence selector (which CERN-OHL variant): <https://ohwr.org/project/cernohl/wikis/Documents/CERN-OHL-version-2#which-licence-to-use>

---

## How to attribute the design files

If you manufacture, modify or distribute the design:

1. **Publish the source files** (schematic, PCB, case) as open source, together
   with your changes
2. Keep the following attribution somewhere visible:

```
Pocket Reader — open-source e-ink reader
https://github.com/<user>/pocket-eink-reader
Licence: CERN-OHL-S-2.0
Modified version — derived from the original project.
```

3. If you made changes, add the words **"modified version"**
4. Give the licence text and this notice with the product

---

## Commercial use

Selling the design **is free**. The only condition is that you keep the design
files open. When you make and sell a product:

- Give the full licence text with the product
- State where the design files are (your own repository or this repository)
- If you made changes, say so

You may additionally use the firmware (MIT); MIT asks for no reciprocity in
commercial use, only that you preserve the copyright notice.

---

## When contributing

When you send a hardware design contribution to this repository, you accept that
your contribution is published under CERN-OHL-S-2.0. Details:
[CONTRIBUTING.md](CONTRIBUTING.md)
