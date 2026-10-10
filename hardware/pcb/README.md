# hardware/pcb

PCB files go in this folder. It is currently **empty** — deliberately.

## Why is it empty?

There are no ready-made Gerbers in the repository, because
`hardware/schematic/gen_netlist.py` still contains **13 unverified pin numbers**
(USB-C receptacle, USBLC6-2SC6, Si1308EDL) and the panel's external ±15 V boost
circuit has not been physically tested. Publishing production files before those
two conditions are met would mean sending a board that does not work to whoever
downloads it.

```bash
cd ../schematic
python3 gen_netlist.py --check     # lists the remaining pins
```

## Making your own PCB

Full guide: [`docs/03-pcb.md`](../../docs/03-pcb.md)

Outline of the flow:

```bash
cd ../schematic
python3 gen_netlist.py             # generates pocket-reader.net

# KiCad
pcbnew
#   File → Import → Netlist → pocket-reader.net
#   Place the parts (placement plan: docs/03 §1)
#   Route the traces, fill the GND plane
#   File → Fabrication Outputs → Gerbers
```

## Board summary

| Feature | Value |
|---|---|
| Size | 45 × 24 mm |
| Layers | 2 |
| Thickness | 1.6 mm |
| Finish | ENIG |
| Component count | 64 (`connections.csv`) |
| Net count | 39 |

## After you have made the board

Add it to this folder and send a PR:

```
hardware/pcb/
├── pocket-reader.kicad_pcb
├── pocket-reader.kicad_pro
├── gerbers/            (production outputs, not in .gitignore)
└── README.md           (your own notes)
```

If you want to add the Gerbers to `.gitignore`, let's discuss — generated files
bloat the repository, but being able to download and make the board straight away
is valuable too.
