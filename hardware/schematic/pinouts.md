# Pocket E-Ink Reader — Verified Pinout and Application Circuit Data

> This file contains only data **verified one-to-one from official datasheets**.
> Everything that could not be verified is clearly marked `UNVERIFIED`.
> No pin number, capacitor value or register value has been guessed.

## Sources

The sources **actually downloaded and read** while this file was being prepared:

- https://www.laskakit.cz/user/related_files/gdey0213b74.pdf — GoodDisplay **GDEY0213B74** 2.13" 250×122 e-paper datasheet (Rev 1.0). The PDF was extracted with `pdftotext` + `pdftoppm`.
- https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf — Espressif **ESP32-C3-MINI-1 & ESP32-C3-MINI-1U Datasheet** v2.2 (local copy: `webfetch-1791567560195-cfrkuc.pdf`).
- https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/esp-hardware-design-guidelines-en-master-esp32c3.pdf — Espressif **ESP32-C3 Hardware Design Guidelines** (for the antenna keep-out figure).
- https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf — Microchip **MCP73831/2** datasheet, Rev H (DS20001984H).
- Local copy — TI **TPS63020/TPS63021** datasheet, SLVS916I (Rev. October 2019). https://www.ti.com/lit/ds/symlink/tps63020.pdf
- https://www.ti.com/lit/ds/symlink/tps63900.pdf — TI **TPS63900** datasheet, SLVSET3D (Rev October 2020).
- https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf — Solomon Systech **SSD1680** controller datasheet, Rev 0.14 (June 2019).
- https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual — Waveshare 2.13" e-Paper HAT wiki (V3/V4 voltage and level-shifter information).
- https://www.content.molex.com/dxdam/44/4456adc5-f3af-4b82-86d4-5ad8260d8178/987651-8371.pdf — Molex Easy-On FBH1 (503480) 0.50 mm FFC/FPC connector catalogue.
- https://media.digikey.com/pdf/Data%20Sheets/Hirose%20PDFs/FH12_Rev2018.pdf — Hirose **FH12** series 0.5 mm FFC/FPC connector catalogue.
- https://www.xfconn.com/uploads/soft/20240925/4-2409251I415K5.pdf — XFCN 16-pin USB Type-C receptacle drawing (bottom-mount, 0.5 mm).
- https://datasheet.octopart.com/USBLC62SC6-STMicroelectronics-datasheet-10412581.pdf — ST Microelectronics **USBLC6-2** (USBLC6-2SC6 / -2P6) datasheet, **Doc ID 11265 Rev 5** (October 2011). This is the ST document itself; `www.st.com` could not be reached from the host that prepared this file and the same PDF (identical ST Doc ID 11265 Rev 5) was read from this distributor mirror. Canonical ST URL: https://www.st.com/content/ccc/resource/technical/document/datasheet/06/1d/48/9c/6c/20/4a/b2/CD00050750.pdf/files/CD00050750.pdf
- https://www.vishay.com/docs/63399/si1308edl.pdf — Vishay Siliconix **Si1308EDL** N-Channel 30 V (D-S) MOSFET datasheet, **Document Number 63399, Rev. C (06-Oct-14)**.
- https://en.krhro.com/Product-Details/726.html — Korean Hroparts (HRO) **TYPE-C-31-M-12** USB Type-C 16-pin receptacle product page, which links the official drawing "USB TYPE C 母座 16Pin R/A 90° SMT", PART NO. TYPE-C-31-M-12, drawing sheet 1 of 4 (the M-12/12A/12B/12C PDF). The drawing PDF read was https://omo-oss-file110.thefastfile.com/portal-saas/pg2026081913505947704/cms/file/type-c-31-m-12&12a&12b&12c(1).pdf (linked from that page).

## Unverified information

- **Which panel the Waveshare 2.13" V3 HAT uses.** `UNVERIFIED`. The Waveshare wiki **does not give** the panel part number for the black/white 2.13" HAT; the product pages list the panel as **HINK-E0213-G01**, say the V3/V4 is 250×122, but do **not** state the name **GDEY0213B74** or **SSD1680** explicitly. The panel data in this file is taken directly from GoodDisplay's **GDEY0213B74** datasheet — the panel itself is verified, but which revision Waveshare uses it in is not verified.
- **Which capacitors are already soldered on the panel's FPC.** `UNVERIFIED`. The GDEY0213B74 datasheet gives only the **external** reference circuit (Section 12); it does not state which capacitance is embedded on the panel/FPC. All capacitors are listed in this file as **external**.
- **The package of the TPS63020.** The coordinator's note said "VSON-10"; however the datasheet clearly states it is a **14-pin VSON (DSJ)** (SLVS916I, Section 3 & Section 5). See Sections 4 and 6.
- **Whether the ESP32-C3-MINI-1 3V3 decoupling values are an official written recommendation.** `UNVERIFIED` (partially). The datasheet text does not contain a separate "recommended decoupling" sentence; the values **C1 = 10 µF + C2 = 0.1 µF** were read from **Peripheral Schematics (Figure 9-1)**, not from a written recommendation.
- **The one-to-one byte mapping of the 2.13" panel's 122 columns to the SSD1680 RAM (16 bytes/row, X window 0–15).** `UNVERIFIED`. Neither the GDEY0213B74 nor the SSD1680 datasheet writes these window values verbatim; the SSD1680 datasheet says the RAM is byte-addressed and 176/8 = 22 bytes wide. The 16 bytes/row value is derived from 122/8 → 16; it must be verified by hand in the driver code.
- **The exact USB-C receptacle ordering code.** `RESOLVED` (pin assignment) / `UNVERIFIED` (procurement). The design uses the **HRO TYPE-C-31-M-12** 16-pin receptacle; its contact assignment is now taken from the manufacturer's own drawing and is recorded in **Section 5.3**. What remains unverified is only **procurement**: this part name is heavily cloned, so pad geometry and the exact ordered variant (M-12 vs 12A/12B/12C) still have to be checked against the vendor drawing at purchase time. The **5.1 kΩ CC pull-down** rule is the USB Type-C UFP/sink standard (given below with its source).
- **The package of Q2 (Si1308EDL) versus the PCB footprint.** `UNVERIFIED` (design decision). The genuine **Vishay Si1308EDL** is **SOT-323 / SC-70 (3 leads)**, not the SOT-23 the design's `Package_TO_SOT_SMD:SOT-23` footprint assumes — see **Section 5.5**. **Fixed:** the footprint is now `Package_TO_SOT_SMD:SOT-323_SC-70`, matching the genuine part. The pin *numbers* were identical either way (1 = G, 2 = S, 3 = D), so the netlist did not change — but a SOT-23 land pattern would not have accepted the real component.
- **The exact meaning of the MCP73831 "AC" option code.** `UNVERIFIED` (partially). The Microchip search summary says AC = precondition 10%, V_PTH/V_REG = 66.5%, I_TERM/I_REG = 7.5%, V_RTH/V_REG = 96.5%; the datasheet's Electrical Characteristics table confirms the ratios (7.5–10–12.5 % / 3.75–5–6.25 %) but the exact decoding of the "AC" letter code must be confirmed by hand from the Product Identification System table.

---

## 1. 2.13" E-Paper Panel — GoodDisplay GDEY0213B74 (SSD1680 controller)

Panel: 2.13", 250×122 (H×V), active area 23.7046 × 48.55 mm, driver IC **SSD1680Z**.
Source: GDEY0213B74 datasheet Rev 1.0 — https://www.laskakit.cz/user/related_files/gdey0213b74.pdf

> ⚠️ **This 24-pin FPC table is the most critical part of the PCB design.** The pin numbers are identical to the panel's own datasheet (Section 5, p.8). The FPC is **0.5 mm pitch, 24 pin** (in the reference circuit `FPC24PIN(0.5mm)`). Pin 11 = D/C#, pin 12 = CS#, pin 13 = SCL, pin 14 = SDA, pin 9 = BUSY, pin 10 = RES#. BS1 (pin 8) = L → 4-wire SPI (the mode we use).

### FPC interface pin table (1..24)

| Pin | Name | I/O | Description |
|----:|----|-----|----------|
| 1 | NC | — | Do not connect to the other NC pins — leave open |
| 2 | GDR | O | N-Channel MOSFET Gate Drive Control |
| 3 | RESE | I | Control-loop current-sense input |
| 4 | NC | — | Leave open |
| 5 | VSH2 | C | Positive Source drive voltage (Red) |
| 6 | TSCL | O | Digital temperature sensor I2C Clock |
| 7 | TSDA | I/O | Digital temperature sensor I2C Data |
| 8 | BS1 | I | Bus Interface selection (L = 4-wire SPI, H = 3-wire SPI) |
| 9 | BUSY | O | Busy status output |
| 10 | RES# | I | Reset input, active **low** |
| 11 | D/C# | I | Data/Command control (HIGH = data, LOW = command) |
| 12 | CS# | I | Chip select input |
| 13 | SCL | I | SPI serial clock |
| 14 | SDA | I/O | SPI serial data |
| 15 | VDDIO | P | Interface logic supply — **must be tied to VCI** |
| 16 | VCI | P | The chip's power supply |
| 17 | VSS | P | Ground |
| 18 | VDD | C | Core logic power (regulated from VCI); capacitor between VDD and VSS |
| 19 | VPP | P | **For test only (FOR TEST)** |
| 20 | VSH1 | C | Positive Source drive voltage |
| 21 | VGH | C | Positive Gate drive voltage and VSH1 |
| 22 | VSL | C | Negative Source drive voltage |
| 23 | VGL | C | Negative Gate drive voltage |
| 24 | VCOM | C | VCOM drive voltage |

Source (table): https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 5, p.8)

### Application circuit (external) — Section 12 "Reference Circuit", p.29

> ⚠️ All the capacitors below are **external**; the datasheet does not say any of them is embedded on the panel (see `Unverified information`). All are rated **25 V**.

- **VCI (pin 16):** C7 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 12, p.29)
- **VDDIO (pin 15):** C6 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VDD (pin 18):** C8 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VSH2 (pin 5):** C2 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VSH1 (pin 20):** C9 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VSL (pin 22):** C10 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VGL (pin 23):** C11 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VCOM (pin 24):** C12 = **1 µF / 25 V**, to GND — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **3.3 V input buffer:** C4 = **4.7 µF / 25 V** — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **External boost (VGH/VGL generation):** L1 = **47 µH / 500 mA**, D1 = D2 = D3 = **MBR0530** (Schottky), Q1 = **Si1308EDL** N-MOSFET, C3 = **4.7 µF / 25 V**, C5 = **1 µF / 25 V**, R1 = **1 MΩ**, R2 = **2.2 Ω**; GDR (pin 2) and RESE (pin 3) go to this circuit — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 12, p.29)
- **BS1 (pin 8):** pulled to GND in the reference circuit → **4-wire SPI** — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf

### Logic supply and interface timing

- **VCI logic supply range:** min **2.2 V**, typ **3.0 V**, max **3.7 V** (Absolute max −0.5 to +4.0 V) — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 6.2, p.10)
- **VDD core logic voltage:** min **1.7 V**, typ **1.8 V**, max **1.9 V** (regulated from VCI; not supplied externally) — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VDDIO = VCI** (pin description: "should be connected with VCI") — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 5)
- **Interface mode:** both 3-wire and 4-wire SPI; BS1 = L → **8-bit 4-wire SPI** (the mode to be used) — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Note 5-5)
- **Max. SCLK (Write mode):** **20 MHz**; **max. SCLK (Read mode):** **2.5 MHz** — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 6.3.4, p.13)
- **SPI mode:** the GoodDisplay/Waveshare interface description CPOL = 0, CPHA = 0 → **SPI Mode 0** — source: https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual
- **Typical power:** 10.5 mW (VCI = 3.0 V, 25 °C); **typical current draw:** 3.5 mA (VCI = 3.0 V) — source: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 6.2)

### Waveshare 2.13" HAT — 3.3 V or 5 V?

- **The bare panel is a 3.3 V device.** VCI is 2.2–3.7 V (above). The panel does not accept 5 V logic directly.
- **The Waveshare HAT board** says "3.3 V / 5 V" and in the wiki: *"The working voltage of the e-Paper display is 3.3V"*; after the V2.1 revision a **level-shifting** circuit was added to the board, which is why the board accepts 3.3 V **or** 5 V logic/supply. So the phrase "3.3V/5V (5V is required for power supply and signal)" refers to the input of the **HAT board**; the panel itself runs at 3.3 V — source: https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual
- **In our design**, since the ESP32-C3 is already 3.3 V logic, a level shifter is **not needed**; the panel is driven directly with a 3.3 V VCI.

---

## 2. ESP32-C3-MINI-1 / ESP32-C3-MINI-1U (Espressif)

Source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (v2.2)

> ⚠️ **The pin table below has 53 pins and is identical to the official Table 3-1.** The pins that most often cause a mistake: **EN = pin 8** and **3V3 = pin 3**. Connecting the EPAD/GND pins to ground is not mandatory but improves thermal performance.

### Pin definitions (Table 3-1, p.11)

| Pin(s) | Name | Type | Function |
|----------|----|-----|-----------|
| 1, 2, 11, 14, 36–53 | GND | P | Ground |
| 3 | 3V3 | P | Supply (VDD33) |
| 4, 7, 9, 10, 15, 17, 24, 25, 28, 29, 32–35 | NC | — | Do not connect |
| 5 | IO2 | I/O/T | GPIO2, ADC1_CH2, FSPIQ |
| 6 | IO3 | I/O/T | GPIO3, ADC1_CH3 |
| 8 | EN | I | High = chip on, Low = off. **Must not be left open** |
| 12 | IO0 | I/O/T | GPIO0, ADC1_CH0, XTAL_32K_P |
| 13 | IO1 | I/O/T | GPIO1, ADC1_CH1, XTAL_32K_N |
| 16 | IO10 | I/O/T | GPIO10, FSPICS0 |
| 18 | IO4 | I/O/T | GPIO4, ADC1_CH4, FSPIHD, MTMS |
| 19 | IO5 | I/O/T | GPIO5, ADC2_CH0, FSPIWP, MTDI |
| 20 | IO6 | I/O/T | GPIO6, FSPICLK, MTCK |
| 21 | IO7 | I/O/T | GPIO7, FSPID, MTDO |
| 22 | IO8 | I/O/T | GPIO8 |
| 23 | IO9 | I/O/T | GPIO9 |
| 26 | IO18 | I/O/T | GPIO18, USB_D− |
| 27 | IO19 | I/O/T | GPIO19, USB_D+ |
| 30 | RXD0 | I/O/T | GPIO20, U0RXD |
| 31 | TXD0 | I/O/T | GPIO21, U0TXD |

Type key: P = power, I = input, O = output, T = high impedance.
Source (table): https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 3-1, p.11)

### Mechanical dimensions and antenna keep-out

> ⚠️ **No copper, component or trace may be placed in the antenna keep-out area on any layer.** Placing the module at the **centre** of the board and cutting a notch on all four sides is forbidden; the antenna must overhang **outside** the board edge and the feed point must be close to the edge.

- **Module dimensions:** ESP32-C3-MINI-1 = **13.2 × 16.6 × 2.4 mm**; ESP32-C3-MINI-1U = **13.2 × 12.5 × 2.4 mm** (±0.15 mm) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 10.1)
- **Antenna keep-out (Figure 21, "Keepout Zone for ESP32-C3 Module's Antenna"):** a minimum of **15 mm to the left, above and to the right** of the antenna, and **6 mm** clear in the direction facing the module body (no copper/component/trace) — source: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/esp-hardware-design-guidelines-en-master-esp32c3.pdf (p.23, Fig. 21)
- **Inside a product enclosure:** at least **15 mm** of clearance in every direction is recommended — source: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html
- The **ESP32-C3-MINI-1U** uses an external antenna connector; it has **no antenna keep-out area** — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (p.11)

### Supply, decoupling and EN RC

> ⚠️ **The EN pin's RC delay circuit: R = 10 kΩ, C = 1 µF.** If EN is left open the chip boots randomly.

- **Supply voltage (VDD33):** min **3.0 V**, typ **3.3 V**, max **3.6 V** (Absolute max −0.3 … +3.6 V) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 6-2)
- **External supply current:** must be able to provide at least **0.5 A** (I_VDD) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 6.2)
- **Peak currents:** 802.11b 1 Mbps @20.5 dBm = **350 mA**; Bluetooth LE @20 dBm = **340 mA** — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 6.4, p.~30)
- **3V3 decoupling (Peripheral Schematics, Fig. 9-1):** **C1 = 10 µF** + **C2 = 0.1 µF** (on VDD33) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 9, p.34) — *(not a written recommendation, read from the schematic; see Unverified information)*
- **EN RC delay circuit:** **R = 10 kΩ**, **C = 1 µF** (in the schematic R9 = 10 kΩ pull-up to VDD33, C3 = EN capacitor) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 9, p.34)
- **EPAD:** soldering it to ground is not mandatory, but it improves thermal performance — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 9)

### Strap pins (GPIO2, GPIO8, GPIO9)

> ⚠️ **The boot mode selection is latched at the reset instant.** For SPI boot GPIO9 = 1 (internal weak pull-up) and GPIO2 = 1 must hold. GPIO2 technically does not select the mode, but it is **recommended to pull it up** against glitches.

- **Default states (Table 4-1):** GPIO2 = Floating, GPIO8 = Floating, GPIO9 = **Weak pull-up (bit value 1)** — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 4-1)

| Boot mode | GPIO2 | GPIO8 | GPIO9 |
|-----------|:-----:|:-----:|:-----:|
| **SPI boot** (normal operation) | 1 | Any value | 1 |
| **Joint download boot** (UART/USB flash) | 1 | 1 | 0 |

- Source (table): https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 4-3, p.13)
- **Timing:** setup time t_SU min **0 ms**; hold time t_H min **3 ms** (after CHIP_EN rises) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 4-2)
- **GPIO8 is also for ROM message suppression** (eFuse EFUSE_UART_PRINT_CONTROL / EFUSE_USB_PRINT_CHANNEL, default 0 = not burned) — source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 4.2)

---

## 3. MCP73831 LiPo Charge Controller (SOT-23-5)

Source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Rev H)

> ⚠️ **The SOT-23-5 pin numbers are DIFFERENT from the DFN.** SOT-23-5: 1 = STAT, 2 = VSS, 3 = VBAT, 4 = VDD, 5 = PROG. (In the 8-lead DFN the arrangement is completely different: 1/2 = VDD, 3/4 = VBAT, 5 = STAT, 6 = VSS, 8 = PROG, 9 = EP.) Using the wrong package pinout breaks the charging circuit.

### SOT-23-5 pinout

| Pin | Name | Function |
|----:|----|-----------|
| 1 | STAT | Charge status output |
| 2 | VSS | 0 V reference (ground) |
| 3 | VBAT | Battery charge control output |
| 4 | VDD | Supply input |
| 5 | PROG | Current-setting resistor and charge enable |

Source (table): https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Table 3-1, p.10)
*(DFN equivalent: 1/2 = VDD, 3/4 = VBAT, 5 = STAT, 6 = VSS, 7 = NC, 8 = PROG, 9 = EP — the same table.)*

### Charge current formula and PROG resistor

- **Formula:** `I_REG = 1000 V / R_PROG` — with R_PROG in **kΩ** and I_REG in **mA** — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 5.1.2)
- **For ~500 mA, R_PROG = 2 kΩ** (1000/2 = 500 mA) — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Figure 6-1 typical application: `2 kΩ`)
- **Valid R_PROG range:** **2 kΩ … 67 kΩ** (≈15 mA … 500 mA) — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Electrical Characteristics: R_PROG 2–67 kΩ)
- **If PROG is left open** (>200 kΩ / float) charging is disabled and STAT = High-Z — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 5.2.2)

### STAT pin states and LED connection

> ⚠️ The MCP73831's STAT is **tri-state** (the MCP73832 = open-drain, different!). Thanks to tri-state, two LEDs can be driven from a single pin: one from VDD→STAT, the other from STAT→GND.

| Charge state | MCP73831 STAT | MCP73832 STAT |
|-------------|:-------------:|:-------------:|
| Shutdown | High-Z | High-Z |
| No battery | High-Z | High-Z |
| Preconditioning | Low | Low |
| Constant-current fast charge | Low | Low |
| Constant voltage | Low | Low |
| Charge complete (standby) | **High** | High-Z |

- Source (table): https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Table 5-1, p.16)
- **LED connection (typical application):** the LED goes **between VDD and STAT** with a **470 Ω** series resistor; while charging (STAT = Low) the LED is lit, at full charge (STAT = High) it goes out — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Figure 6-1, p.1)

### Input/output capacitors and thermal

- **VDD bypass:** at least **4.7 µF** (to VSS) — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 3.1)
- **VBAT bypass:** at least **4.7 µF** (to VSS; for loop stability when the battery is not installed) — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 3.2)
- **Thermal:** SOT-23-5 θ_JA ≈ **230 °C/W** (4-layer JC51-7); with a large copper area it typically drops to **~130 °C/W** — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 6, Thermal Package Resistances)
- **Thermal regulation:** the chip limits its power dissipation according to the die temperature; **charging stops at 150 °C** and resumes after it cools by ~10 °C — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 4.9 / 4.10)
- **EP (Exposed Pad):** must be connected to VSS; for thermal reasons it is recommended to place vias from under the EP to the other layer — source: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 3.6)

### Fixed-voltage variants (the correct ordering code)

| Code | V_REG (typical) | Min | Max |
|-----|:-------------:|:---:|:---:|
| **-2** | **4.20 V** | 4.168 V | 4.232 V |
| -3 | 4.35 V | 4.317 V | 4.383 V |
| -4 | 4.40 V | 4.367 V | 4.433 V |
| -5 | 4.50 V | 4.466 V | 4.534 V |

- Accuracy: **±0.75 %.** For LiPo, **MCP73831-2** (4.20 V) is used. Example ordering code: **MCP73831T-2ACI/OT** (T = tape&reel, -2 = 4.20 V, I = industrial temperature, OT = SOT-23-5).
- Source (table): https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Electrical Characteristics + Section 4.6)

---

## 4. TPS63020 Buck-Boost (VSON-14 / DSJ)

Source: TI TPS63020/TPS63021 datasheet, SLVS916I — https://www.ti.com/lit/ds/symlink/tps63020.pdf
(Local copy — TI TPS63020/TPS63021 datasheet, SLVS916I (Rev. October 2019).)

> ⚠️ **The package is 14-pin VSON (DSJ), not 10-pin.** Datasheet: "packaged in a 14-pin VSON package measuring 3 mm × 4 mm (DSJ)" (Section 3/5). The coordinator's "VSON-10" note is wrong — it is **NOT pin-compatible with the TPS63900** (see Section 6).

### VSON-14 (DSJ) pinout

| Pin | Name | I/O | Description |
|----:|----|-----|----------|
| 1 | VINA | I | Control-stage supply |
| 2 | GND | — | Control/logic ground |
| 3 | FB | I | Feedback (adjustable version) — connected to VOUT in the fixed version |
| 4 | VOUT | O | Buck-boost output |
| 5 | VOUT | O | Buck-boost output |
| 6 | L2 | I | Inductor connection |
| 7 | L2 | I | Inductor connection |
| 8 | L1 | I | Inductor connection |
| 9 | L1 | I | Inductor connection |
| 10 | VIN | I | Power-stage supply |
| 11 | VIN | I | Power-stage supply |
| 12 | EN | I | Enable (1 = on, 0 = off); **must not be left open** |
| 13 | PS/SYNC | I | Power-save enable/disable; **must not be left open** |
| 14 | PG | O | Power-good (open-drain); may be left floating |
| — | Thermal Pad | — | **Connected to PGND** |

Source (table): https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 5, Pin Functions, p.4)

### Feedback and 3.3 V output

- **Actual feedback voltage:** **V_FB = 500 mV** (typical; min 495 mV, max 505 mV, PS/SYNC = VIN) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5, p.6)
- **Divider formula:** `R1 = R2 × (VOUT / V_FB − 1)`; R2 should be kept in the region of **~200 kΩ** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.3, Equation 3)
- **For a 3.3 V output: R1 = 1 MΩ, R2 = 180 kΩ** (the exact row of datasheet Table 3) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Table 3, p.15)

### External components

- **Inductor:** the value must be **≥ 1 µH**; for a 1.5–2 A output **1 µH or 1.5 µH** is recommended; 2.2 µH also works at lower load — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2)
- **Inductor saturation current:** should be chosen **at least 20% higher** than the calculated peak current; recommended example **XFL4020-152ML** (1.5 µH, I_sat 5.1 A, DCR 15 mΩ) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.2, Table 2)
- **Input capacitor:** **10 µF** (in the application circuit **2 × 10 µF**, X5R/X7R, close to VIN–PGND) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.4, Table 4)
- **Output capacitor:** nominal **3 × 22 µF** (X5R, close to VOUT–PGND) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.3, Table 4)
- **VINA bypass:** **0.1 µF** (X5R/X7R); **must not exceed 0.22 µF** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.5)
- **3.3 V application bill of materials (Table 4):** U1 = TPS63020, L1 = 1.5 µH XFL4020-152ML, C1 = 2×10 µF, C2 = 3×22 µF, C3 = 0.1 µF, R1 = 1 MΩ, R2 = 180 kΩ, R3 = 1 MΩ — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Table 4)

### The function of the PS/SYNC, EN and PG pins

- **PS/SYNC = Low:** power-save mode **enabled** — when at light load the average inductor current drops below ~100 mA it switches to a low switching frequency and **efficiency rises** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.4.4)
- **PS/SYNC = High:** power-save mode **disabled** — fixed-frequency PWM; **the output ripple is lower** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.4.4)
- **For a light-load application that wants low ripple**, you have to pull PS/SYNC **High** (forced PWM) and use a large output capacitor; however at light load the **highest efficiency** is at PS/SYNC = Low. (Trade-off: efficiency ↔ ripple.) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.4.4, 8.2.2.3)
- **EN:** High = running, Low = shutdown (the load is disconnected from the battery); **must not be left open** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.3.3, Pin Functions)
- **PG:** open-drain power-good (1 = good, 0 = fault); may be left floating if not wanted; it can be pulled up to the supply voltage — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.3.4)

### Input range, output current and current consumption

- **Input voltage range:** **1.8 V … 5.5 V** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5)
- **Output current (VIN > 2.5 V, VOUT = 3.3 V):** **2 A** — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 1, Features)
- **Average switch current limit:** 3500 / **4000** / 4500 mA (VIN = VINA = 3.6 V, 25 °C) — source: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5)
- **1S LiPo (3.0–4.2 V) → 3.3 V:** since VIN > 2.5 V it can deliver **up to 2 A**; the ESP32-C3 Wi-Fi TX peak (~350 mA) + panel are comfortably met. **However, the quiescent current below eats into the deep-sleep budget.**

| Parameter | Symbol | Test condition | Min | Typ | Max | Unit |
|-----------|--------|-------------|:---:|:---:|:---:|:-----:|
| Quiescent current (VIN & VINA) | I_q | IOUT = 0 mA, VEN = VIN = VINA = 3.6 V | — | **25** | **50** | µA |
| Shutdown current | I_S | VEN = 0 V, VIN = VINA = 3.6 V | — | **0.1** | **1** | µA |

- Source (table, **verified**): https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5 Electrical Characteristics, p.6)
- ⚠️ **The 25 µA quiescent current** on its own eats half of the ~50 µA budget that is a typical deep-sleep target. That is why the TPS63900 alternative in Section 6 should be considered.

---

## 5. SSD1680 Controller + FPC Connector + USB-C (supporting parts)

### 5.1 SSD1680 controller — the facts needed for driver code

Source: SSD1680 datasheet Rev 0.14 — https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf

- **RAM size:** Two banks, each **176 × 296 bits**. Mono B/W RAM (**command 0x24**) = 176×296 bits; Mono Red RAM (**command 0x26**) = 176×296 bits — source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 6.5)
- **Addressing:** the X address is **byte**-based (X = 0…0x15 → 176/8 = **22 bytes** full row); the Y address is 0…0x127 (295). Source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 8.6)
- **RAM window commands:** X-start/end = **0x44** (POR XSA = 00h, XEA = 15h); Y-start/end = **0x45** (POR YSA = 000h, YEA = 127h); X-counter = **0x4E**, Y-counter = **0x4F** — source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Command Table)
- **Data Entry Mode (0x11):** ID[1:0] selects the automatic increment/decrement direction of the address counter, the AM bit selects the X/Y direction. The POR value is A[2:0] = 011. — source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 8.3)
- **Mapping to the 2.13" 250×122 panel:** the panel uses 122 columns; in byte addressing this corresponds to **16 bytes/row** (16 × 8 = 128 ≥ 122), and the 250 rows are scanned with Y = 0…249. **`UNVERIFIED`** — these values are not written verbatim in either the panel or the controller datasheet; they must be verified by hand in the driver code (the SSD1680 datasheet gives only the full row width of 22 bytes).
- **BUSY polarity:** **active-HIGH = busy.** Datasheet: *"When Busy is High, the operation of the chip should not be interrupted, and command should not be sent."* Before sending a command, BUSY is expected to be **LOW**. — source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Table 5-2 pin description)
- **Deep sleep (command 0x10):** A[1:0] = 00 Normal (POR), **01 = Deep Sleep Mode 1**, **11 = Deep Sleep Mode 2**. After the command the BUSY pad stays **High**. Exit is **only via hardware reset (HWRESET)**; a SW reset (0x12) does not wake it. — source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Command Table, 0x10)
- **Deep sleep current:** Mode 1 = **1 µA** typ / 3 µA max (RAM preserved); Mode 2 = **0.7 µA** typ / 3 µA max (RAM not preserved). Sleep (normal) = 20 µA typ / 35 µA max. — source: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 6.5 DC Characteristics)

### 5.2 24-pin 0.5 mm FPC connector

> ⚠️ The panel FPC is **24 pin, 0.5 mm pitch** (see Section 1). A **bottom contact** connector must be chosen.

- **Hirose FH12-24S-0.5SH(55)** — 24 positions, **0.5 mm pitch**, **bottom contact**, SMD right-angle, flip-lock ZIF, height above board 2.0 mm, FPC thickness 0.30 mm, 0.5 A/contact, 50 V — source: https://media.digikey.com/pdf/Data%20Sheets/Hirose%20PDFs/FH12_Rev2018.pdf
- **Molex 5034802400** (Easy-On FBH1 series) — 24 circuit, **0.50 mm pitch**, **bottom contact (dual contact)**, right-angle, mated height 1.00 mm, 0.5 A/contact, 50 V, FPC 0.30 mm — source: https://www.content.molex.com/dxdam/44/4456adc5-f3af-4b82-86d4-5ad8260d8178/987651-8371.pdf

### 5.3 USB-C receptacle and CC resistors

> ⚠️ **For a sink (UFP), EACH of the CC1 and CC2 pins must be pulled to GND separately with 5.1 kΩ.** Joining the two CC pins or connecting them with a single resistor causes errors with smart (E-marked) cables.

#### J1 — USB-C 16-pin receptacle, HRO TYPE-C-31-M-12

The board's `J1` footprint is KiCad `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`. The contact
assignment below is the **manufacturer's own pin-assignment table** (drawing "USB TYPE C 母座 16Pin
R/A 90° SMT", PART NO. TYPE-C-31-M-12, sheet 1 of 4):

| Designator | Signal | Notes |
|-----------|--------|-------|
| A1, A12, B1, B12 | GND | Four ground contacts (the two outermost contacts on each side) |
| A4, A9, B4, B9 | VBUS | Four VBUS contacts — **all four must be connected** |
| A5 | CC1 | Needs its **own** 5.1 kΩ Rd to GND |
| B5 | CC2 | Needs its **own** 5.1 kΩ Rd to GND |
| A6, B6 | D+ | DP1 / DP2 — one USB 2.0 line, duplicated for plug reversal; tie A6–B6 |
| A7, B7 | D− | DN1 / DN2 — duplicated for plug reversal; tie A7–B7 |
| A8, B8 | SBU1 / SBU2 | Sideband-use contacts (unused in this design) |
| S1 (four pads) | SHIELD | Shell / board-retention legs |

Source (table): https://omo-oss-file110.thefastfile.com/portal-saas/pg2026081913505947704/cms/file/type-c-31-m-12&12a&12b&12c(1).pdf (pin-assignment table, sheet 1 of 4) — linked from the manufacturer page https://en.krhro.com/Product-Details/726.html

- **16-contact USB 2.0 subset:** power (GND ×4, VBUS ×4), CC1, CC2, D+ ×2, D− ×2, SBU1, SBU2 — **no SuperSpeed pairs**; a USB 3.x SuperSpeed link would require the full 24-pin part — source: https://en.krhro.com/Product-Details/726.html
- **Reversible plug:** D+ and D− each appear on **two** contacts (A6/B6 and A7/B7); tie each pair together with short stubs — source: https://omo-oss-file110.thefastfile.com/portal-saas/pg2026081913505947704/cms/file/type-c-31-m-12&12a&12b&12c(1).pdf (sheet 1 of 4)
- **VBUS and GND are multi-pad groups, not single pads:** the netlist connects **every** member — VBUS = A4, A9, B4, B9; GND = A1, A12, B1, B12 — plus the shell (S1) — source: https://omo-oss-file110.thefastfile.com/portal-saas/pg2026081913505947704/cms/file/type-c-31-m-12&12a&12b&12c(1).pdf (sheet 1 of 4)
- **Equivalent alternative 16-contact, 0.5 mm, bottom-mount part:** XFCN **TPS10-N1F1-2016-A** (A5 = CC1, B5 = CC2; 16 contacts: GND, VBUS, D+, D−, CC1, CC2, SBU1, SBU2) — source: https://www.xfconn.com/uploads/soft/20240925/4-2409251I415K5.pdf
- **CC1/CC2 pull-down:** for a UFP/sink **5.1 kΩ, separately on each CC pin, to GND** — source: https://www.hestore.eu/en/prod_10050443.html (USB-C sink reference)

### 5.4 U1 — USBLC6-2SC6 USB ESD protection (SOT23-6L)

Source: ST Microelectronics USBLC6-2 datasheet, Doc ID 11265 Rev 5 —
https://datasheet.octopart.com/USBLC62SC6-STMicroelectronics-datasheet-10412581.pdf

The part protects **two** data lines plus VBUS. Each protected line is brought out on **two** pins so
that the ESD current splits between them; that is why I/O1 and I/O2 each appear twice.

| Pin | Name | I/O | Description |
|----:|----|-----|----------|
| 1 | I/O1 | I/O | Data line 1 (one half; internally joined to pin 6) |
| 2 | GND | — | Ground |
| 3 | I/O2 | I/O | Data line 2 (one half; internally joined to pin 4) |
| 4 | I/O2 | I/O | Data line 2 (internally joined to pin 3) |
| 5 | VBUS | — | VBUS (supply) protection |
| 6 | I/O1 | I/O | Data line 1 (internally joined to pin 1) |

Source (table): https://datasheet.octopart.com/USBLC62SC6-STMicroelectronics-datasheet-10412581.pdf (Figure 1 "Functional diagram (top view)", p.1)

- **How J1's lines map onto U1:** USB_DP goes through **I/O1 (pins 1 and 6)** and USB_DN goes through **I/O2 (pins 3 and 4)**; GND = pin 2, VBUS = pin 5 — source: https://datasheet.octopart.com/USBLC62SC6-STMicroelectronics-datasheet-10412581.pdf (Figure 1, p.1)
- **Ordering code / marking:** USBLC6-2SC6 = **SOT23-6L**, marking **UL26**, 16.7 mg — source: https://datasheet.octopart.com/USBLC62SC6-STMicroelectronics-datasheet-10412581.pdf (Table 6, Ordering information)
- **Layout note:** place the device as close as possible to the connector and add a **100 nF** capacitor between VBUS and GND near the device — source: https://datasheet.octopart.com/USBLC62SC6-STMicroelectronics-datasheet-10412581.pdf (application information)

### 5.5 Q2 — Si1308EDL N-channel MOSFET (panel boost, drives GDR)

Source: Vishay Siliconix Si1308EDL datasheet, Document Number 63399, Rev. C —
https://www.vishay.com/docs/63399/si1308edl.pdf

| Pin | Name | I/O | Description |
|----:|----|-----|----------|
| 1 | G | I | Gate |
| 2 | S | I/O | Source (also the body-diode anode side) |
| 3 | D | I/O | Drain |

Source (table): https://www.vishay.com/docs/63399/si1308edl.pdf (page-1 pin diagram, "Top View", document 63399 Rev. C, 06-Oct-14)

> ⚠️ **Package discrepancy.** The genuine Vishay **Si1308EDL** is **SOT-323 / SC-70 (3 leads)**, not SOT-23 —
> source: https://www.vishay.com/docs/63399/si1308edl.pdf (page 1, "SOT-323 / SC-70 (3 leads)"; marking **KG**;
> ordering code **Si1308EDL-T1-GE3**). The design's footprint is now `Package_TO_SOT_SMD:SOT-323_SC-70`.
> The pin **numbers** are the same in either package (1 = G, 2 = S, 3 = D), but a genuine Vishay part will
> **not** fit the SOT-23 footprint — switch the footprint to `Package_TO_SOT_SMD:SOT-323_SC-70` (or pick a
> SOT-23 second source deliberately).

---

## 6. Power regulator alternative: TPS63900

Source: TI TPS63900 datasheet, SLVSET3D — https://www.ti.com/lit/ds/symlink/tps63900.pdf (Rev October 2020)

> ⚠️ **The TPS63900 is NOT pin-compatible with the TPS63020 — the PCB layout must change.** TPS63020 = **14-pin VSON (DSJ)**, TPS63900 = **10-pin WSON (DSK, 2.5×2.5 mm, 0.5 mm pitch)**. The pin count, names and layout are different; they are only from the same "small WSON/VSON" package family. The coordinator's "pin-count-compatible" assumption does not hold.

### 10-pin WSON (DSK) pinout

| Pin | Name | I/O | Description |
|----:|----|-----|----------|
| 1 | EN | I | Device enable (High = on, Low = off); **must not be left open** |
| 2 | SEL | I | Output voltage selection: High → VO(2), Low → VO(1); **must not be left open** |
| 3 | CFG1 | I | VO(2) + input current limit setting with a resistor to GND; must not be left open |
| 4 | CFG2 | I | VO(2) + input current limit setting with a resistor to GND; must not be left open |
| 5 | CFG3 | I | VO(1) setting with a resistor to GND; must not be left open |
| 6 | VOUT | — | Output voltage |
| 7 | LX2 | — | Boost-stage switching node |
| 8 | GND | — | Ground |
| 9 | LX1 | — | Buck-stage switching node |
| 10 | VIN | — | Supply voltage |
| — | Thermal Pad | — | Must be connected to GND for correct operation |

Source (table): https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 5-1, p.3)

### Output voltage selection — the resistor for 3.3 V

> ⚠️ The output voltage is set **by resistors connected from the CFG1/CFG2/CFG3 pins to GND** (the external R2D interface). The resistors must have a tolerance of **±1 % or better** and a temperature coefficient of **±200 ppm/°C or better**; the total RMS error < ±3 %.

- **Table 7-2, the "3.3 V" row (exact):** R_CFG1 = **36.5 kΩ**; R_CFG2 = 0 Ω (UNLIMITED current limit), 511 Ω (100 mA), 1.15 kΩ (50 mA), 1.87 kΩ (25 mA), 2.74 kΩ (10 mA), 3.83 kΩ (5 mA), 5.11 kΩ (2.5 mA), 6.49 kΩ (1 mA) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 7-2, p.14)
- **For 3.3 V + unlimited input current limit:** **CFG1 = 36.5 kΩ (1 %)**, **CFG2 = 0 Ω**, **CFG3 = 0 Ω** (SEL = High) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 8-5, p.21 and Figure 8-1 typical application `CFG1 36.5 kΩ`)
- Note: CFG3 sets the VO(1) preset that is valid while **SEL = Low**; in the typical circuit CFG3 = 0 Ω (VO(1) = 1.8 V). If you use SEL fixed High, CFG3 must still not be left floating.

### Recommended external components (typical application, VOUT = 3.3 V)

- **Inductor:** **2.2 µH** (Table 8-1, single row: 2.2 µH); example part **DFE252012F-2R2M** (2.2 µH, 3.3 A, 82 mΩ) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 8-5, p.21)
- **Inductor saturation current:** **20% above** the calculated peak current; the I_sat range of the recommended 2.2 µH parts is **1.7 … 3.5 A** — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 8-2, p.19)
- **Input capacitor:** **10 µF** (X5R/X7R, close to VIN–GND); example **GRM188R60J106ME47** (0603) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 8.2.2.4, Table 8-4)
- **Output capacitor:** a single **22 µF** (X5R/X7R, close to VOUT–GND); example **GRM187R60J226ME15** (0603) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 8.2.2.3, Table 8-3)

### Output current capability (3.0 V / 3.6 V → 3.3 V)

- **Feature:** **> 400 mA** output current under the condition VI ≥ 2.0 V, VO = 3.3 V (typical **1.45 A peak switch current limit**) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 1, Features)
- **VIN = 3.0 V → VOUT = 3.3 V:** in the datasheet's "Typical Output Current Capability versus Input Voltage" (Figure 8-2) curve, the VIN ≥ 2.0 V region gives **> 400 mA**. A numerical curve reading is not given in the datasheet text; **≥ 400 mA** may be taken for the design. — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 8.2.3, Figure 8-2, p.21)
- **VIN = 3.6 V → VOUT = 3.3 V:** on the same curve the capability rises as VIN increases; the spec guarantee is **> 400 mA**. The ESP32-C3 Wi-Fi TX peak (~350 mA) + panel is on its own below this limit, but since the peak switch current limit is **1.45 A (1.33–1.6 A)** short peaks are comfortably met. — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5 CURRENT LIMIT, p.5)
- **Switch current limits:** Peak current limit (Q1, unlimited) = **1.45 A** typ (1.33–1.6 A, VI = 1.8 V, VO = 3.6 V); startup peak = 0.35–0.83 A — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5, p.5)
- **`UNVERIFIED`:** the **exact** output current value at VIN = 3.0 V and 3.6 V is not given as a number in the datasheet (only the "> 400 mA @ VI ≥ 2.0 V" spec and the curve). The curve must be read by hand.

### EN behaviour, shutdown current and mode

- **EN:** High = on, Low = off; **must not be left open** — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 5-1)
- **Shutdown current:** **60 nA** (V(EN) = 0 V) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5, p.5, **verified**)
- **Quiescent current:** **0.075 µA (75 nA)** typ, **1 µA** max (V(EN) = 3 V, no load, no switching, unlimited current limit) — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5, p.5)
- **Mode:** it runs **single-mode** — there is no switching between buck / buck-boost / boost, and there is **NO mode pin like PS/SYNC.** Instead there is the SEL pin (VO(1)/VO(2) preset selection) and the CFG pins (voltage + input current limit). — source: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 1, Features: "Single-mode operation")
- **Conclusion:** against the TPS63020's 25 µA quiescent current, with **75 nA** the TPS63900 is ~330× better in terms of the deep-sleep budget; in return, the PCB layout (10-pin DSK) has to be redrawn and the CFG resistors (36.5 kΩ for 3.3 V) added.
