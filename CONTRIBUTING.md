# Contributing Guide

Thank you. This project contains both **hardware** and **software**, and the two
have somewhat different contribution rules.

---

## Quick start

```bash
git clone <this-repo> pocket-eink-reader
cd pocket-eink-reader

# Software side
pip install -U platformio
cd firmware && pio run -e xiao && cd ..

# Tools side
cd tools && python3 -m unittest discover tests && cd ..

# Hardware side — netlist consistency
cd hardware/schematic && python3 gen_netlist.py --check
```

---

## What is needed?

The up-to-date list, in priority order: [`docs/09-roadmap.md`](docs/09-roadmap.md)

The three highest-impact jobs:

1. **Verify the remaining 13 pin numbers** — USB-C receptacle, USBLC6-2SC6,
   Si1308EDL. Read the datasheet and enter them into `PINMAP` in
   `hardware/schematic/gen_netlist.py`. A 10-minute job that unblocks PCB
   production.
2. **Measure the BUSY polarity** — the 30-second test in `firmware/README.md`.
3. **Build and run on real hardware** — every compilation error you find is
   valuable.

---

## Hardware contributions

### Do not edit the netlist by hand

`connections.csv` and `pocket-reader.net` are **generated** files. Their source is
the `NETS`, `COMPONENTS` and `PINMAP` dictionaries inside
`hardware/schematic/gen_netlist.py`.

```bash
cd hardware/schematic
# 1. Edit gen_netlist.py
# 2. Verify — real inconsistencies error out, missing pins are warnings
python3 gen_netlist.py --check
# 3. Generate the outputs
python3 gen_netlist.py
```

If a PR changes `gen_netlist.py` but not `connections.csv`, CI warns.

### When adding a new pin number

```python
"U1": {"I/O1": "1", "I/O2": "3", "GND": "2", "VBUS": "5"},
#      ^^^^^^ pin NAME   ^^^ pin NUMBER (from the datasheet)
```

State in the PR description **which datasheet, which table, which page**. It is
better to leave a number as `None` than to enter an unverified one — `--check`
lists it as a warning and nobody accidentally sends it to production.

### When changing a value

Show the calculation. For example, for a resistor change:

> `R6`: 180 kΩ → 200 kΩ. `Vout = 0.5 × (1 + 1M/200k) = 3.00 V`.
> The datasheet suggests `R6 ≈ 200 kΩ` but at that value the output would not be
> 3.3 V; since our target is 3.3 V we stay at 180 kΩ.

---

## Software contributions

### Language rules

| Where | Language |
|---|---|
| Identifiers, code comments, commit messages | **English** |
| Documentation (`docs/`, `README`) | **English** |
| User-visible firmware strings | English by default, Turkish with `-DLANG_TR`, both via `include/i18n.h` |

Contributions are written in English.

### Dependency policy

- **Firmware:** no external libraries. `lib_deps` in `platformio.ini` is
  deliberately empty. If you want to add a new dependency, open an issue first
  and let's discuss the reason.
- **Tools:** `epub2epr.py`, `send.py`, `make_sample_books.py` use only the Python
  standard library. `fontgen.py` uses Pillow. Do not add new dependencies.

### Code style

- C++: 2-space indent, `static` file-local helpers, one `.h`/`.cpp` pair per
  module
- Python: 3.9+, `from __future__ import annotations`, type hints,
  `if __name__ == "__main__":`
- A comment block at the top of every module explaining **why** it exists

### Testing

```bash
cd tools && python3 -m unittest discover tests -v
```

If you add a new converter feature, add a test under `tests/`. There are no
hardware tests; a successful build is the only automated check for the firmware.

---

## Numeric claims

In this project, numbers such as power consumption, duration and size are marked
as **either measured or calculated**. When you write a number, state which one it
is:

- ✅ `~55 µA (calculated — docs/07 §2)`
- ✅ `44 µA (measured, Seeed XIAO ESP32-C3 datasheet)`
- ❌ `~50 µA` (source unclear)

Several numbers were corrected thanks to this rule while this repository was
being prepared; for the record see the end of [`docs/09`](docs/09-roadmap.md).

---

## Commit and PR

- Commit message: `area: short description` — e.g. `docs: fix the TPS63020 package`
- A PR should address a single topic
- The PR description should say **what changed** and **how you verified it**
- For a hardware change, also send the `gen_netlist.py` output

---

## Licence

- `firmware/`, `tools/`, `.github/` → **MIT** ([LICENSE](LICENSE))
- `hardware/`, `docs/01..04` → **CERN-OHL-S-2.0** ([LICENSE-HARDWARE.md](LICENSE-HARDWARE.md))

When you send a contribution, you accept that your contribution is published
under the relevant licence.

---

## Code of conduct

In short: **be well-intentioned.** Be patient with beginners' questions; write
"here is how we could do it" rather than "why didn't you do this". Technical
criticism is very welcome; personal criticism is not.

---

## Getting help

When you get stuck:

1. [`docs/08-troubleshooting.md`](docs/08-troubleshooting.md) — search by symptom
2. Look at the existing issues
3. When opening a new issue, include: serial port output, a photo of the screen,
   measurements, the hardware (easy build or PCB), and what you last changed
