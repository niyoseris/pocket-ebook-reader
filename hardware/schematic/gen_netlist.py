#!/usr/bin/env python3
"""
Pocket Reader — netlist generator.

Produces two outputs from a single source of truth:

    connections.csv        human-readable connection table (for docs and review)
    pocket-reader.net      KiCad netlist (importable into pcbnew)

Why a script: a hand-written 200-line connection list inevitably drifts out of
sync. Every change to the schematic is made in one place here, and both outputs
are updated together.

Usage:
    python3 gen_netlist.py            # produce both files
    python3 gen_netlist.py --check    # don't write; only verify consistency

SOURCE OF THE PIN NUMBERS
    The verified pin numbers are taken from `pinouts.md`, and each one is based
    on an official datasheet page. Entries whose source has not been verified
    are left as None; --check lists these as "UNVERIFIED". A wrong netlist is
    never produced silently.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# UNVERIFIED is the "not verified" marker: it means "not verified" and is kept
# in Turkish on purpose, because pinouts.md, the docs and the two `description`
# fields emitted by gen_netlist.py into pocket-reader.net all match on this exact
# literal. Renaming it (e.g. to UNVERIFIED) would have to touch every one of
# those files at once, so it must not be renamed or translated unilaterally.
UNVERIFIED = "UNVERIFIED"

# --------------------------------------------------------------------------
# 1) COMPONENTS
#    ref: (value, KiCad footprint, description)
# --------------------------------------------------------------------------

COMPONENTS: dict[str, tuple[str, str, str]] = {
    # --- USB-C input and ESD ---
    "J1": ("USB-C 16P", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
           f"USB-C female socket, sink only (UFP). Pin numbers {UNVERIFIED}"),
    "R1": ("5.1k", "Resistor_SMD:R_0805_2012Metric",
           "5.1k for CC1. Each CC pin needs its OWN resistor (UFP definition)"),
    "R2": ("5.1k", "Resistor_SMD:R_0805_2012Metric", "5.1k for CC2"),
    "U1": ("USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
           f"USB D+/D- ESD protection. Pinout {UNVERIFIED}"),

    # --- Charging ---
    "U2": ("MCP73831T-2ACI/OT", "Package_TO_SOT_SMD:SOT-23-5",
           "Li-Po charge controller. -2 = fixed 4.20V. SOT-23-5"),
    "C1": ("4.7uF", "Capacitor_SMD:C_0805_2012Metric", "VDD bypass (min 4.7uF)"),
    "C2": ("4.7uF", "Capacitor_SMD:C_0805_2012Metric",
           "VBAT bypass (min 4.7uF) — for loop stability when no battery is connected"),
    "R3": ("2k", "Resistor_SMD:R_0805_2012Metric",
           "PROG: I_REG = 1000/R3 -> 500mA. Valid range 2k..67k"),
    "R4": ("470R", "Resistor_SMD:R_0805_2012Metric",
           "Charge LED current limit. Datasheet Figure 6-1: 470 ohm"),
    "D1": ("green 0603", "LED_SMD:LED_0603_1608Metric",
           "Charge status LED: VDD -> R4 -> LED -> STAT"),

    # --- Battery ---
    "BT1": ("Li-Po 1S 500mAh", "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
            "502030 or 402025, internally protected"),
    # NOTE: the DW01A + FS8205A protection block is deliberately ABSENT from the
    # BOM. The default build uses an internally PROTECTED Li-Po cell. If you use
    # an unprotected cell, add this block as in docs/02-schematic.md Section C and
    # record it here.
    "SW1": ("SPDT slide", "Button_Switch_SMD:SW_SPDT_PCM12", "On/off, MSK-12C02"),

    # --- Power: TPS63020 ---
    "U3": ("TPS63020DSJR", "Package_SON:VSON-14-1EP_3x4mm_P0.5mm",
           "3.3V buck-boost, 2A. 14-PIN VSON (DSJ) 3x4mm. Verify the footprint name "
           "in your KiCad library"),
    "L1": ("1.5uH", "Inductor_SMD:L_Bourns-SRN3015",
           "Buck-boost inductor. Datasheet Table 4: XFL4020-152ML (1.5uH, Isat 5.1A). "
           "2.2uH is also acceptable (light load)"),
    "C3": ("10uF", "Capacitor_SMD:C_0805_2012Metric", "VIN capacitor 1/2 (datasheet: 2x10uF)"),
    "C4": ("10uF", "Capacitor_SMD:C_0805_2012Metric", "VIN capacitor 2/2"),
    "C5": ("0.1uF", "Capacitor_SMD:C_0603_1608Metric",
           "VINA bypass. Must NOT exceed 0.22uF (datasheet Section 8.2.2.5)"),
    "C6": ("22uF", "Capacitor_SMD:C_0805_2012Metric", "VOUT capacitor 1/3 (datasheet: 3x22uF)"),
    "C7": ("22uF", "Capacitor_SMD:C_0805_2012Metric", "VOUT capacitor 2/3"),
    "C8": ("22uF", "Capacitor_SMD:C_0805_2012Metric", "VOUT capacitor 3/3"),
    "C9": ("0.1uF", "Capacitor_SMD:C_0603_1608Metric", "3V3 high-frequency bypass"),
    "R5": ("1M", "Resistor_SMD:R_0603_1608Metric",
           "FB top resistor. Datasheet Table 3 (3.3V output), the exact row"),
    "R6": ("180k", "Resistor_SMD:R_0603_1608Metric",
           "FB bottom resistor. V_FB=500mV -> 0.5*(1+1M/180k)=3.28V"),
    "R7": ("100k", "Resistor_SMD:R_0603_1608Metric",
           "EN pull-up (EN must not be left floating)"),
    "JP1": ("0R bridge", "Jumper:SolderJumper_2_Open",
            "PS/SYNC: GND=power-save mode (high efficiency), VINA=forced PWM (low ripple)"),

    # --- MCU ---
    "U5": ("ESP32-C3-MINI-1-N4", "RF_Module:ESP32-C3-MINI-1",
           "RISC-V 160MHz, 4MB flash, Wi-Fi/BLE. 13.2x16.6x2.4mm"),
    "R8": ("10k", "Resistor_SMD:R_0603_1608Metric", "EN pull-up (datasheet: R=10k)"),
    "C10": ("1uF", "Capacitor_SMD:C_0603_1608Metric", "EN RC delay (datasheet: C=1uF)"),
    "C11": ("10uF", "Capacitor_SMD:C_0805_2012Metric",
            "Module 3V3 decoupling 1/2 (datasheet Fig 9-1)"),
    "C12": ("0.1uF", "Capacitor_SMD:C_0603_1608Metric",
            "Module 3V3 decoupling 2/2 — right at the module's base"),

    # --- Panel: connector and interface ---
    "J2": ("FPC 24P 0.5mm", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal",
           "E-paper FPC connector, BOTTOM-CONTACT, ZIF. Molex 5034802400 alternative"),
    "R9": ("100k", "Resistor_SMD:R_0603_1608Metric", "EPD_RST pull-up"),
    "R10": ("100k", "Resistor_SMD:R_0603_1608Metric", "EPD_BUSY pull-up"),

    # --- Panel: external capacitor network (datasheet Section 12) ---
    # It was not verified that ANY of these is embedded on the panel; all are
    # assumed external.
    "C13": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VCI (pin 16) — datasheet Section 12"),
    "C14": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VDDIO (pin 15)"),
    "C15": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VDD core (pin 18)"),
    "C16": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VSH2 (pin 5)"),
    "C17": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VSH1 (pin 20)"),
    "C18": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VSL (pin 22)"),
    "C19": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VGL (pin 23)"),
    "C20": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "VCOM (pin 24)"),
    "C21": ("4.7uF/25V", "Capacitor_SMD:C_0805_2012Metric", "3.3V input buffer (datasheet Section 12)"),
    "C22": ("100uF", "Capacitor_SMD:C_1206_3216Metric",
            "Panel refresh current buffer, low ESR. If omitted, the display refreshes partially"),

    # --- Panel: external VGH/VGL boost (datasheet Section 12 — GDR/RESE pins) ---
    "L2": ("47uH/500mA", "Inductor_SMD:L_Bourns-SRN4018", "Panel boost inductor"),
    "D2": ("MBR0530", "Diode_SMD:D_SOD-123", "Panel boost Schottky"),
    "D3": ("MBR0530", "Diode_SMD:D_SOD-123", "Panel boost Schottky"),
    "D4": ("MBR0530", "Diode_SMD:D_SOD-123", "Panel boost Schottky"),
    "Q2": ("Si1308EDL", "Package_TO_SOT_SMD:SOT-23", "Panel boost N-MOSFET (drives the GDR pin)"),
    "C23": ("4.7uF/25V", "Capacitor_SMD:C_0805_2012Metric", "Panel boost capacitor 1/2"),
    "C24": ("1uF/25V", "Capacitor_SMD:C_0805_2012Metric", "Panel boost capacitor 2/2"),
    "R18": ("1M", "Resistor_SMD:R_0603_1608Metric", "Panel boost resistor 1/2"),
    "R19": ("2.2R", "Resistor_SMD:R_0805_2012Metric", "Panel boost current-sense resistor (RESE)"),

    # --- Buttons ---
    "SW2": ("tactile", "Button_Switch_SMD:SW_SPST_PTS645", "Page back (GPIO3)"),
    "SW3": ("tactile", "Button_Switch_SMD:SW_SPST_PTS645", "Page forward (GPIO2)"),
    "SW4": ("tactile", "Button_Switch_SMD:SW_SPST_PTS645", "Menu / library (GPIO20)"),
    "R13": ("100k", "Resistor_SMD:R_0603_1608Metric", "SW2 pull-up"),
    "R14": ("100k", "Resistor_SMD:R_0603_1608Metric", "SW3 pull-up"),
    "R15": ("100k", "Resistor_SMD:R_0603_1608Metric", "SW4 pull-up"),
    "C25": ("100nF", "Capacitor_SMD:C_0603_1608Metric", "SW2 hardware debounce (for the wake-up instant)"),
    "C26": ("100nF", "Capacitor_SMD:C_0603_1608Metric", "SW3 hardware debounce"),
    "C27": ("100nF", "Capacitor_SMD:C_0603_1608Metric", "SW4 hardware debounce"),

    # --- Battery detection ---
    "R16": ("100k", "Resistor_SMD:R_0603_1608Metric", "Divider top (1:2 ratio)"),
    "R17": ("100k", "Resistor_SMD:R_0603_1608Metric", "Divider bottom. If made 1M/1M, 19uA saving"),
    "C28": ("100nF", "Capacitor_SMD:C_0603_1608Metric", "ADC filter"),
}

# --------------------------------------------------------------------------
# 2) PIN NUMBERS  (source: pinouts.md — each one is based on a datasheet page)
#    A value may contain several pins ("1,2,11,14,53") — the netlist writes all.
#    None = UNVERIFIED, must be completed before importing into pcbnew.
# --------------------------------------------------------------------------

PINMAP: dict[str, dict[str, str | None]] = {
    # --- Passives: 1/2 (non-polarised) ---
    **{r: {"1": "1", "2": "2"} for r in
       ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10",
        "R13", "R14", "R15", "R16", "R17", "R18", "R19",
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
        "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19",
        "C20", "C21", "C22", "C23", "C24", "C25", "C26", "C27", "C28"]},
    "L1": {"1": "1", "2": "2"},
    "L2": {"1": "1", "2": "2"},
    "JP1": {"1": "1", "2": "2"},
    "D1": {"A": "2", "K": "1"},            # LED: 1 = cathode, 2 = anode
    "D2": {"A": "2", "K": "1"},            # MBR0530 SOD-123: 1 = cathode, 2 = anode
    "D3": {"A": "2", "K": "1"},
    "D4": {"A": "2", "K": "1"},
    "SW2": {"A": "1", "B": "2"}, "SW3": {"A": "1", "B": "2"}, "SW4": {"A": "1", "B": "2"},
    "SW1": {"COM": "2", "NO": "1"},
    "BT1": {"+": "1", "-": "2"},

    # --- U2 MCP73831 SOT-23-5 — VERIFIED (DS20001984H Table 3-1) ---
    "U2": {"STAT": "1", "VSS": "2", "VBAT": "3", "VDD": "4", "PROG": "5"},

    # --- U3 TPS63020 VSON-14 (DSJ) — VERIFIED (SLVS916I Section 5) ---
    "U3": {"VINA": "1", "GND": "2", "FB": "3", "VOUT": "4,5", "L2": "6,7",
           "L1": "8,9", "VIN": "10,11", "EN": "12", "PS/SYNC": "13", "PG": "14"},

    # --- U5 ESP32-C3-MINI-1 — VERIFIED (Table 3-1) ---
    "U5": {"GND": "1,2,11,14,53", "3V3": "3", "GPIO2": "5", "GPIO3": "6",
           "EN": "8", "GPIO10": "16", "GPIO4": "18", "GPIO5": "19",
           "GPIO6": "20", "GPIO7": "21", "GPIO8": "22", "GPIO9": "23",
           "GPIO18": "26", "GPIO19": "27", "GPIO20": "30"},

    # --- J2 GDEY0213B74 FPC 24P — VERIFIED (datasheet Section 5) ---
    "J2": {"VSH2": "5", "GDR": "2", "RESE": "3", "BS1": "8", "BUSY": "9",
           "RST": "10", "DC": "11", "CS": "12", "SCK": "13", "MOSI": "14",
           "VDDIO": "15", "VCI": "16", "GND": "17", "VDD": "18",
           "VSH1": "20", "VGH": "21", "VSL": "22", "VGL": "23", "VCOM": "24",
           "NC1": "1", "NC4": "4", "TSCL": "6", "TSDA": "7", "VPP": "19"},

    # --- UNVERIFIED — those that still need to be completed ---
    "J1": {"VBUS": None, "GND": None, "CC1": None, "CC2": None, "D+": None, "D-": None},
    "U1": {"I/O1": None, "I/O2": None, "GND": None, "VBUS": None},
    "Q2": {"G": None, "S": None, "D": None},   # Si1308EDL SOT-23
}

# --------------------------------------------------------------------------
# 3) NET LIST
#    (net_name, class, [(ref, pin_name, note), ...])
#    class: "power" | "signal" | "analog"
# --------------------------------------------------------------------------

NETS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("3V3", "power", [
        ("U3", "VOUT", "regulator output"),
        ("C6", "1", "VOUT capacitor"), ("C7", "1", ""), ("C8", "1", ""),
        ("C9", "1", "HF bypass"),
        ("U5", "3V3", "module supply (pin 3)"),
        ("C11", "1", "module decoupling"), ("C12", "1", "module base"),
        ("J2", "VCI", "panel logic supply (pin 16)"),
        ("J2", "VDDIO", "must be TIED TO VCI (pin 15)"),
        ("C13", "1", "VCI capacitor"), ("C14", "1", "VDDIO capacitor"),
        ("C21", "1", "3.3V input buffer"),
        ("C22", "1", "panel refresh buffer"),
        ("R9", "1", "RST pull-up"), ("R10", "1", "BUSY pull-up"),
        ("R13", "1", ""), ("R14", "1", ""), ("R15", "1", ""),
    ]),
    ("GND", "power", [
        ("J1", "GND", "USB-C ground and chassis"),
        ("U1", "GND", "ESD diode ground"),
        ("R1", "2", "CC1 5.1k -> GND"),
        ("R2", "2", "CC2 5.1k -> GND"),
        ("C1", "2", ""), ("C2", "2", ""),
        ("U2", "VSS", ""), ("R3", "2", "PROG bottom terminal"),
        ("BT1", "-", "battery negative"),
        ("SW1", "COM", "switch common terminal"),
        ("U3", "GND", "control/logic ground"),
        ("JP1", "1", "PS/SYNC power-save mode"),
        ("C3", "2", ""), ("C4", "2", ""), ("C5", "2", ""),
        ("C6", "2", ""), ("C7", "2", ""), ("C8", "2", ""), ("C9", "2", ""),
        ("R6", "2", "FB bottom terminal"),
        ("U5", "GND", "module ground (GND + EPAD)"),
        ("C10", "2", ""), ("C11", "2", ""), ("C12", "2", ""),
        ("J2", "GND", "panel ground (pin 17)"),
        ("C13", "2", ""), ("C14", "2", ""), ("C15", "2", ""), ("C16", "2", ""),
        ("C17", "2", ""), ("C18", "2", ""), ("C19", "2", ""), ("C20", "2", ""),
        ("C21", "2", ""), ("C22", "2", ""),
        ("J2", "BS1", "L = 4-wire SPI (datasheet reference circuit)"),
        ("Q2", "S", "boost MOSFET source"),
        ("C23", "2", ""), ("C24", "2", ""), ("R18", "2", ""),
        ("SW2", "B", ""), ("SW3", "B", ""), ("SW4", "B", ""),
        ("C25", "2", ""), ("C26", "2", ""), ("C27", "2", ""),
        ("R17", "2", "divider bottom terminal"), ("C28", "2", ""),
    ]),
    ("USB_CC1", "signal", [
        ("J1", "CC1", "USB-C CC1 — UFP definition"),
        ("R1", "1", "to GND via 5.1k (SEPARATE resistor required)"),
    ]),
    ("USB_CC2", "signal", [
        ("J1", "CC2", "USB-C CC2 — UFP definition"),
        ("R2", "1", "to GND via 5.1k"),
    ]),
    ("VBUS", "power", [
        ("J1", "VBUS", "USB 5V"),
        ("U1", "VBUS", "ESD diode supply"),
        ("U2", "VDD", "charge input (pin 4)"),
        ("C1", "1", ""),
        ("R4", "1", "LED top terminal"),
    ]),
    ("VBAT", "power", [
        ("U2", "VBAT", "charge output (pin 3)"),
        ("C2", "1", "VBAT bypass (min 4.7uF, required)"),
        ("BT1", "+", "battery positive"),
    ]),
    ("VBAT_K", "power", [
        ("SW1", "NO", "switch input"),
        ("R16", "1", "divider top terminal"),
    ]),
    ("VBAT_SW", "power", [
        ("SW1", "NO", "switch output"),
        ("U3", "VIN", "regulator power input (pin 10,11)"),
        ("U3", "VINA", "regulator control input (pin 1)"),
        ("C3", "1", ""), ("C4", "1", ""), ("C5", "1", ""),
        ("R7", "1", "EN pull-up top terminal"),
    ]),
    ("FB", "analog", [
        ("U3", "FB", "feedback (pin 3)"),
        ("R5", "2", ""), ("R6", "1", ""),
    ]),
    ("LX", "power", [
        ("U3", "L1", "inductor terminal (pin 8,9)"),
        ("L1", "1", ""),
    ]),
    ("LX2", "power", [
        ("U3", "L2", "inductor terminal (pin 6,7)"),
        ("L1", "2", ""),
    ]),
    ("EN_MCU", "signal", [
        ("U5", "EN", "module reset (pin 8)"),
        ("R8", "1", "10k pull-up"), ("C10", "1", "1uF RC delay"),
    ]),
    ("EPD_SCK", "signal", [
        ("U5", "GPIO4", "SPI clock (pin 18)"),
        ("J2", "SCK", "panel SCL (pin 13)"),
    ]),
    ("EPD_MOSI", "signal", [
        ("U5", "GPIO6", "SPI data (pin 20)"),
        ("J2", "MOSI", "panel SDA (pin 14)"),
    ]),
    ("EPD_CS", "signal", [
        ("U5", "GPIO7", "chip select (pin 21)"),
        ("J2", "CS", "panel CS# (pin 12)"),
    ]),
    ("EPD_DC", "signal", [
        ("U5", "GPIO10", "command/data (pin 16)"),
        ("J2", "DC", "panel D/C# (pin 11)"),
    ]),
    ("EPD_RST", "signal", [
        ("U5", "GPIO8", "panel reset (pin 22)"),
        ("J2", "RST", "panel RES# (pin 10)"),
        ("R9", "2", "pull-up"),
    ]),
    ("EPD_BUSY", "signal", [
        ("U5", "GPIO9", "panel busy (pin 23)"),
        ("J2", "BUSY", "panel BUSY (pin 9)"),
        ("R10", "2", "pull-up"),
    ]),
    # --- The panel's external capacitor and boost network (datasheet Section 12) ---
    ("VDD_CORE", "power", [
        ("J2", "VDD", "core logic (pin 18) — regulated from VCI, not supplied externally"),
        ("C15", "1", "1uF/25V"),
    ]),
    ("VSH1", "power", [("J2", "VSH1", "pin 20"), ("C17", "1", "1uF/25V")]),
    ("VSH2", "power", [("J2", "VSH2", "pin 5"), ("C16", "1", "1uF/25V")]),
    ("VSL", "power",  [("J2", "VSL", "pin 22"), ("C18", "1", "1uF/25V")]),
    ("VGL", "power",  [("J2", "VGL", "pin 23"), ("C19", "1", "1uF/25V")]),
    ("VCOM", "power", [("J2", "VCOM", "pin 24"), ("C20", "1", "1uF/25V")]),
    ("VGH", "power", [
        ("J2", "VGH", "pin 21 — external boost output"),
        ("D4", "K", "MBR0530 cathode"),
    ]),
    ("GDR", "signal", [
        ("J2", "GDR", "pin 2 — MOSFET gate drive"),
        ("Q2", "G", "Si1308EDL gate"),
    ]),
    ("RESE", "analog", [
        ("J2", "RESE", "pin 3 — current-sense input"),
        ("R19", "1", "2.2R"),
    ]),
    ("BOOST_LX", "power", [
        ("Q2", "D", "MOSFET drain"),
        ("L2", "1", "47uH"),
        ("D2", "A", "Schottky anode"),
    ]),
    ("VBAT_BOOST", "power", [
        ("L2", "2", "inductor supply terminal"),
        ("R18", "1", "1M"),
        ("C23", "1", "4.7uF/25V"),
        ("D2", "K", "Schottky cathode"),
        ("D3", "A", "second Schottky anode"),
    ]),
    ("BOOST_AUX", "power", [
        ("D3", "K", ""),
        ("C24", "1", "1uF/25V"),
        ("R19", "2", "RESE bottom terminal"),
        ("D4", "A", "VGH diode anode"),
    ]),
    ("BTN_UP", "signal", [
        ("U5", "GPIO3", "page back (pin 6)"),
        ("SW2", "A", "button"),
        ("R13", "2", "pull-up"),
        ("C25", "1", "debounce"),
    ]),
    ("BTN_DOWN", "signal", [
        ("U5", "GPIO2", "page forward (pin 5)"),
        ("SW3", "A", "button"),
        ("R14", "2", "pull-up"),
        ("C26", "1", "debounce"),
    ]),
    ("BTN_MENU", "signal", [
        ("U5", "GPIO20", "menu (pin 30, U0RXD)"),
        ("SW4", "A", "button"),
        ("R15", "2", "pull-up"),
        ("C27", "1", "debounce"),
    ]),
    ("USB_DP", "signal", [
        ("J1", "D+", "USB data +"),
        ("U1", "I/O1", "ESD protection"),
        ("U5", "GPIO19", "USB D+ (pin 27)"),
    ]),
    ("USB_DN", "signal", [
        ("J1", "D-", "USB data -"),
        ("U1", "I/O2", "ESD protection"),
        ("U5", "GPIO18", "USB D- (pin 26)"),
    ]),
    ("VBAT_ADC", "analog", [
        ("R16", "2", "divider midpoint"),
        ("R17", "1", ""),
        ("C28", "1", "filter"),
        ("U5", "GPIO5", "ADC2_CH0 (pin 19)"),
    ]),
    ("PROG", "analog", [
        ("U2", "PROG", "charge current setting (pin 5)"),
        ("R3", "1", "2k -> 500mA"),
    ]),
    ("STAT", "signal", [
        ("U2", "STAT", "tri-state output (pin 1)"),
        ("D1", "K", "LED cathode"),
    ]),
    ("LED_A", "signal", [
        ("D1", "A", "LED anode"),
        ("R4", "2", ""),
    ]),
]

# --------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------


def _pin_numbers(ref: str, pin: str) -> list[str] | None:
    """Return the pin numbers; None if not verified."""
    raw = PINMAP.get(ref, {}).get(pin)
    if raw is None:
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def write_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Net", "Class", "RefDes", "Pin", "Description"])
        for name, cls, nodes in NETS:
            for ref, pin, note in nodes:
                w.writerow([name, cls, ref, pin, note])


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def write_netlist(path: Path) -> None:
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out: list[str] = [
        '(export (version "E")',
        "  (design",
        '    (source "hardware/schematic/pocket-reader-schematic.svg")',
        f'    (date "{stamp}")',
        '    (tool "pocket-eink-reader/gen_netlist.py")',
        "  )",
        "  (components",
    ]
    for ref, (value, footprint, desc) in COMPONENTS.items():
        out += [
            f'    (comp (ref "{ref}")',
            f'      (value "{_esc(value)}")',
            f'      (footprint "{_esc(footprint)}")',
            f'      (description "{_esc(desc)}")',
            "    )",
        ]
    out.append("  )")
    out.append("  (nets")
    for code, (name, _cls, nodes) in enumerate(NETS, start=1):
        out.append(f'    (net (code "{code}") (name "{name}")')
        for ref, pin, _note in nodes:
            numbers = _pin_numbers(ref, pin) or [pin]
            for number in numbers:
                out.append(f'      (node (ref "{ref}") (pin "{number}"))')
        out.append("    )")
    out.append("  )")
    out.append(")")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def check() -> int:
    """Consistency check. Real inconsistencies are errors, missing pins are warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    used_refs: set[str] = set()

    for name, _cls, nodes in NETS:
        if len(nodes) < 2:
            errors.append(f"net '{name}' has a single node")
        for ref, pin, _note in nodes:
            used_refs.add(ref)
            if ref not in COMPONENTS:
                errors.append(f"net '{name}': undefined component '{ref}'")
            elif pin not in PINMAP.get(ref, {}):
                errors.append(f"net '{name}': undefined pin '{pin}' for {ref}")

    for ref in COMPONENTS:
        if ref not in used_refs:
            errors.append(f"'{ref}' is not connected to any net")

    unverified = sorted({f"{ref}.{pin}" for ref, m in PINMAP.items()
                         for pin, num in m.items() if num is None})

    for e in errors:
        print("ERROR -", e)
    if unverified:
        print(f"\n{len(unverified)} pin numbers {UNVERIFIED} "
              "(complete them from pinouts.md and add them to PINMAP):")
        for u in unverified:
            print("  warning -", u)

    if errors:
        print(f"\n{len(errors)} ERROR — the netlist must not be produced before these are fixed.")
        return 1

    total = sum(len(n) for _name, _cls, n in NETS)
    print(f"\nOK — {len(NETS)} nets, {total} connections, {len(COMPONENTS)} components, "
          f"{len(unverified)} unverified pins.")
    if unverified:
        print("Complete the pin numbers above before importing into pcbnew.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Pocket Reader netlist generator")
    ap.add_argument("--check", action="store_true",
                    help="do not write files, only verify consistency")
    ap.add_argument("--outdir", default=str(HERE), help="output directory")
    args = ap.parse_args()

    if args.check:
        return check()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "connections.csv")
    write_netlist(out / "pocket-reader.net")
    print(f"wrote: {out/'connections.csv'}")
    print(f"wrote: {out/'pocket-reader.net'}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
