> English version: [pinouts.md](pinouts.md)

# Pocket E-Ink Reader — Doğrulanmış Pinout ve Uygulama Devresi Verileri

> Bu dosya yalnızca **resmî datasheet'lerden birebir doğrulanmış** verileri içerir.
> Doğrulanamayan her şey açıkça `UNVERIFIED` olarak işaretlenmiştir.
> Hiçbir pin numarası, kondansatör değeri veya register değeri tahmin edilmemiştir.

## Kaynaklar

Bu dosya hazırlanırken **fiilen indirilip okunan** kaynaklar:

- https://www.laskakit.cz/user/related_files/gdey0213b74.pdf — GoodDisplay **GDEY0213B74** 2.13" 250×122 e-paper datasheet (Rev 1.0). PDF `pdftotext` + `pdftoppm` ile çıkarıldı.
- https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf — Espressif **ESP32-C3-MINI-1 & ESP32-C3-MINI-1U Datasheet** v2.2 (yerel kopya: `webfetch-1791567560195-cfrkuc.pdf`).
- https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/esp-hardware-design-guidelines-en-master-esp32c3.pdf — Espressif **ESP32-C3 Hardware Design Guidelines** (antenna keepout figürü için).
- https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf — Microchip **MCP73831/2** datasheet, Rev H (DS20001984H).
- Yerel kopya — TI **TPS63020/TPS63021** datasheet, SLVS916I (Rev October 2019). https://www.ti.com/lit/ds/symlink/tps63020.pdf
- https://www.ti.com/lit/ds/symlink/tps63900.pdf — TI **TPS63900** datasheet, SLVSET3D (Rev October 2020).
- https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf — Solomon Systech **SSD1680** controller datasheet, Rev 0.14 (June 2019).
- https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual — Waveshare 2.13" e-Paper HAT wiki (V3/V4 voltaj ve düzey kaydırıcı bilgisi).
- https://www.content.molex.com/dxdam/44/4456adc5-f3af-4b82-86d4-5ad8260d8178/987651-8371.pdf — Molex Easy-On FBH1 (503480) 0.50 mm FFC/FPC konnektör katalogu.
- https://media.digikey.com/pdf/Data%20Sheets/Hirose%20PDFs/FH12_Rev2018.pdf — Hirose **FH12** serisi 0.5 mm FFC/FPC konnektör katalogu.
- https://www.xfconn.com/uploads/soft/20240925/4-2409251I415K5.pdf — XFCN 16-pin USB Type-C receptacle çizimi (alt-montaj, 0.5 mm).

## Doğrulanmamış bilgiler

- **Waveshare 2.13" V3 HAT'in hangi paneli kullandığı.** `UNVERIFIED`. Waveshare wiki'si siyah/beyaz 2.13" HAT için panel parça numarasını **vermiyor**; ürün sayfaları paneli **HINK-E0213-G01** olarak listeliyor, V3/V4'ün 250×122 olduğunu söylüyor, ancak **GDEY0213B74** veya **SSD1680** adını açıkça yazmıyor. Bu dosyadaki panel verileri, doğrudan GoodDisplay'in **GDEY0213B74** datasheet'inden alınmıştır — panelin kendisi doğrulanmıştır, Waveshare'in bunu hangi revizyonda kullandığı doğrulanmamıştır.
- **Panelin FPC'si üzerinde hâlihazırda hangi kondansatörlerin lehimli olduğu.** `UNVERIFIED`. GDEY0213B74 datasheet'i yalnızca **harici** referans devresini (Section 12) verir; hangi kapasitansın panel/FPC üzerinde gömülü olduğunu belirtmez. Tüm kapasitörler bu dosyada **harici** olarak listelenmiştir.
- **TPS63020'nin paketi.** Koordinatör notu "VSON-10" demişti; ancak datasheet açıkça **14-pin VSON (DSJ)** olduğunu yazar (SLVS916I, Section 3 & Section 5). Bkz. Bölüm 4 ve 6.
- **ESP32-C3-MINI-1 3V3 dekuplaj değerlerinin resmî yazılı öneri olup olmadığı.** `UNVERIFIED` (kısmen). Datasheet metni ayrı bir "recommended decoupling" cümlesi içermiyor; **C1 = 10 µF + C2 = 0.1 µF** değerleri **Peripheral Schematics (Figure 9-1)** üzerinden okunmuştur, yazılı bir öneri değil.
- **2.13" panelin 122 kolonunun SSD1680 RAM'ine birebir byte eşlemesi (16 byte/satır, X window 0–15).** `UNVERIFIED`. Ne GDEY0213B74 ne de SSD1680 datasheet'i bu pencere değerlerini birebir yazmıyor; SSD1680 datasheet'i RAM'in byte-adresli ve 176/8 = 22 byte genişliğinde olduğunu söyler. 16 byte/satır değeri 122/8 → 16'dan türetilmiştir; sürücü kodunda elle doğrulanmalıdır.
- **Kesin USB-C receptacle sipariş kodu.** `UNVERIFIED`. Bulunan **XFCN TPS10-N1F1-2016-A** alt-montaj 16-pin çizimi doğrulanmıştır ama üreticinin resmî "datasheet" niteliği ve stok durumu teyit edilmemiştir. **5.1 kΩ CC pull-down** kuralı USB Type-C UFP/sink standardıdır (aşağıda kaynakla verilmiştir).
- **MCP73831 "AC" opsiyon kodunun tam anlamı.** `UNVERIFIED` (kısmen). Mikroçip arama özeti AC = precondition %10, V_PTH/V_REG = %66.5, I_TERM/I_REG = %7.5, V_RTH/V_REG = %96.5 der; datasheet'in Electrical Characteristics tablosu oranları doğrular (7.5–10–12.5 % / 3.75–5–6.25 %) ama "AC" harf kodunun tam çözümü Product Identification System tablosundan elle teyit edilmelidir.

---

## 1. 2.13" E-Paper Panel — GoodDisplay GDEY0213B74 (SSD1680 kontrolcü)

Panel: 2.13", 250×122 (H×V), aktif alan 23.7046 × 48.55 mm, sürücü IC **SSD1680Z**.
Kaynak: GDEY0213B74 datasheet Rev 1.0 — https://www.laskakit.cz/user/related_files/gdey0213b74.pdf

> ⚠️ **Bu 24-pin FPC tablosu PCB tasarımının en kritik parçasıdır.** Pin numaraları panelin kendi datasheet'i (Section 5, s.8) ile birebir aynıdır. FPC **0.5 mm pitch, 24 pin**'dir (referans devrede `FPC24PIN(0.5mm)`). Pin 11 = D/C#, pin 12 = CS#, pin 13 = SCL, pin 14 = SDA, pin 9 = BUSY, pin 10 = RES#. BS1 (pin 8) = L → 4-wire SPI (kullanacağımız mod).

### FPC arayüz pin tablosu (1..24)

| Pin | Ad | I/O | Açıklama |
|----:|----|-----|----------|
| 1 | NC | — | Diğer NC pinlerine bağlanmayacak — açık bırak |
| 2 | GDR | O | N-Channel MOSFET Gate Drive Control |
| 3 | RESE | I | Kontrol döngüsü akım-sens girişi |
| 4 | NC | — | Açık bırak |
| 5 | VSH2 | C | Pozitif Source sürme voltajı (Kırmızı) |
| 6 | TSCL | O | Dijital sıcaklık sensörü I2C Clock |
| 7 | TSDA | I/O | Dijital sıcaklık sensörü I2C Data |
| 8 | BS1 | I | Bus Interface seçimi (L = 4-wire SPI, H = 3-wire SPI) |
| 9 | BUSY | O | Busy durum çıkışı |
| 10 | RES# | I | Reset girişi, aktif **low** |
| 11 | D/C# | I | Data/Command kontrol (HIGH = data, LOW = command) |
| 12 | CS# | I | Chip select girişi |
| 13 | SCL | I | SPI seri saat |
| 14 | SDA | I/O | SPI seri veri |
| 15 | VDDIO | P | Arayüz lojik beslemesi — **VCI ile birleştirilmeli** |
| 16 | VCI | P | Çipin güç beslemesi |
| 17 | VSS | P | Toprak |
| 18 | VDD | C | Çekirdek lojik gücü (VCI'den regüle); VDD–VSS arası kondansatör |
| 19 | VPP | P | **Yalnızca test için (FOR TEST)** |
| 20 | VSH1 | C | Pozitif Source sürme voltajı |
| 21 | VGH | C | Pozitif Gate sürme voltajı ve VSH1 |
| 22 | VSL | C | Negatif Source sürme voltajı |
| 23 | VGL | C | Negatif Gate sürme voltajı |
| 24 | VCOM | C | VCOM sürme voltajı |

Kaynak (tablo): https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 5, s.8)

### Uygulama devresi (harici) — Section 12 "Reference Circuit", s.29

> ⚠️ Aşağıdaki tüm kapasitörler **harici**dir; datasheet hiçbirinin panel üzerinde gömülü olduğunu söylemez (bkz. `Doğrulanmamış bilgiler`). Tümü **25 V** anma gerilimlidir.

- **VCI (pin 16):** C7 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 12, s.29)
- **VDDIO (pin 15):** C6 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VDD (pin 18):** C8 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VSH2 (pin 5):** C2 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VSH1 (pin 20):** C9 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VSL (pin 22):** C10 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VGL (pin 23):** C11 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VCOM (pin 24):** C12 = **1 µF / 25 V**, GND'ye — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **3.3 V giriş tamponu:** C4 = **4.7 µF / 25 V** — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **Harici boost (VGH/VGL üretimi):** L1 = **47 µH / 500 mA**, D1 = D2 = D3 = **MBR0530** (Schottky), Q1 = **Si1308EDL** N-MOSFET, C3 = **4.7 µF / 25 V**, C5 = **1 µF / 25 V**, R1 = **1 MΩ**, R2 = **2.2 Ω**; GDR (pin 2) ve RESE (pin 3) bu devreye gider — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 12, s.29)
- **BS1 (pin 8):** referans devrede GND'ye çekilmiştir → **4-wire SPI** — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf

### Lojik besleme ve arayüz zamanlaması

- **VCI lojik besleme aralığı:** min **2.2 V**, tip **3.0 V**, max **3.7 V** (Absolute max −0.5 to +4.0 V) — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 6.2, s.10)
- **VDD çekirdek lojik voltajı:** min **1.7 V**, tip **1.8 V**, max **1.9 V** (VCI'den regüle; harici beslenmez) — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf
- **VDDIO = VCI** olmalıdır (pin açıklaması: "should be connected with VCI") — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 5)
- **Arayüz modu:** hem 3-wire hem 4-wire SPI; BS1 = L → **8-bit 4-wire SPI** (kullanılacak mod) — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Note 5-5)
- **Maks. SCLK (Write mode):** **20 MHz**; **maks. SCLK (Read mode):** **2.5 MHz** — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 6.3.4, s.13)
- **SPI modu:** GoodDisplay/Waveshare arayüz tarifi CPOL = 0, CPHA = 0 → **SPI Mode 0** — kaynak: https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual
- **Tipik güç:** 10.5 mW (VCI = 3.0 V, 25 °C); **tip çekilen akım:** 3.5 mA (VCI = 3.0 V) — kaynak: https://www.laskakit.cz/user/related_files/gdey0213b74.pdf (Section 6.2)

### Waveshare 2.13" HAT — 3.3 V mi 5 V mi?

- **Çıplak panel 3.3 V'luk bir cihazdır.** VCI 2.2–3.7 V'tur (yukarıda). Panel doğrudan 5 V lojik kabul etmez.
- **Waveshare HAT kartı** "3.3 V / 5 V" yazar ve wiki'de: *"The working voltage of the e-Paper display is 3.3V"*; V2.1 revizyonundan sonra karta **level-shifting (seviye dönüştürücü)** devresi eklenmiştir, bu yüzden kart 3.3 V **veya** 5 V lojik/besleme kabul eder. Yani "3.3V/5V (5V is required for power supply and signal)" ifadesi **HAT kartının** girişine dairdir; panelin kendisi 3.3 V'ta çalışır — kaynak: https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual
- **Bizim tasarımımızda** ESP32-C3 zaten 3.3 V lojik olduğundan düzey kaydırıcıya **gerek yoktur**; panel doğrudan 3.3 V VCI ile sürülür.

---

## 2. ESP32-C3-MINI-1 / ESP32-C3-MINI-1U (Espressif)

Kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (v2.2)

> ⚠️ **Aşağıdaki pin tablosu 53 pinlidir ve resmî Table 3-1 ile birebir aynıdır.** En sık hataya yol açan pin: **EN = pin 8** ve **3V3 = pin 3**. EPAD/GND pinlerini toprağa bağlamak zorunlu değildir ama termal performansı iyileştirir.

### Pin tanımları (Table 3-1, s.11)

| Pin(ler) | Ad | Tip | Fonksiyon |
|----------|----|-----|-----------|
| 1, 2, 11, 14, 36–53 | GND | P | Toprak |
| 3 | 3V3 | P | Besleme (VDD33) |
| 4, 7, 9, 10, 15, 17, 24, 25, 28, 29, 32–35 | NC | — | Bağlanmaz |
| 5 | IO2 | I/O/T | GPIO2, ADC1_CH2, FSPIQ |
| 6 | IO3 | I/O/T | GPIO3, ADC1_CH3 |
| 8 | EN | I | High = çip açık, Low = kapalı. **Açık bırakılmamalı** |
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

Tip anahtarı: P = besleme, I = giriş, O = çıkış, T = yüksek empedans.
Kaynak (tablo): https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 3-1, s.11)

### Mekanik ölçüler ve anten keep-out

> ⚠️ **Anten keep-out alanına hiçbir katmanda bakır, bileşen veya iz konmayacaktır.** Modülü kartın **merkezine** yerleştirip dört yandan oyuk açmak yasaktır; anten kart kenarından **dışarı** taşmalı ve besleme noktası kenara yakın olmalıdır.

- **Modül ölçüleri:** ESP32-C3-MINI-1 = **13.2 × 16.6 × 2.4 mm**; ESP32-C3-MINI-1U = **13.2 × 12.5 × 2.4 mm** (±0.15 mm) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 10.1)
- **Anten keep-out (Figure 21, "Keepout Zone for ESP32-C3 Module's Antenna"):** antenin **solunda, üstünde ve sağında minimum 15 mm**, modül gövdesine bakan yönde **6 mm** clear (bakır/bileşen/iz yok) — kaynak: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/esp-hardware-design-guidelines-en-master-esp32c3.pdf (s.23, Fig. 21)
- **Ürün muhafazası içinde:** her yönde **en az 15 mm** boşluk önerilir — kaynak: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html
- **ESP32-C3-MINI-1U** harici anten konnektörü kullanır; **anten keep-out alanı yoktur** — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (s.11)

### Besleme, dekuplaj ve EN RC

> ⚠️ **EN pininin RC gecikme devresi: R = 10 kΩ, C = 1 µF.** EN açık bırakılırsa çip rastgele boot eder.

- **Besleme gerilimi (VDD33):** min **3.0 V**, tip **3.3 V**, max **3.6 V** (Absolute max −0.3 … +3.6 V) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 6-2)
- **Harici besleme akımı:** en az **0.5 A** verebilmelidir (I_VDD) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 6.2)
- **Pik akımlar:** 802.11b 1 Mbps @20.5 dBm = **350 mA**; Bluetooth LE @20 dBm = **340 mA** — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 6.4, s.~30)
- **3V3 dekuplaj (Peripheral Schematics, Fig. 9-1):** **C1 = 10 µF** + **C2 = 0.1 µF** (VDD33 üzerinde) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 9, s.34) — *(yazılı öneri değil, şema üzerinden; bkz. Doğrulanmamış bilgiler)*
- **EN RC gecikme devresi:** **R = 10 kΩ**, **C = 1 µF** (şemada R9 = 10 kΩ VDD33'e pull-up, C3 = EN kapasitörü) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 9, s.34)
- **EPAD:** toprağa lehimlemek zorunlu değil, ama termal performansı iyileştirir — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 9)

### Strap pinleri (GPIO2, GPIO8, GPIO9)

> ⚠️ **Boot modu seçimi reset anında latch'lenir.** SPI boot için GPIO9 = 1 (dahili weak pull-up) ve GPIO2 = 1 olmalıdır. GPIO2 teknik olarak modu seçmez ama glitch'e karşı **yukarı çekilmesi önerilir**.

- **Varsayılan durumlar (Table 4-1):** GPIO2 = Floating, GPIO8 = Floating, GPIO9 = **Weak pull-up (bit değeri 1)** — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 4-1)

| Boot modu | GPIO2 | GPIO8 | GPIO9 |
|-----------|:-----:|:-----:|:-----:|
| **SPI boot** (normal çalışma) | 1 | Any value | 1 |
| **Joint download boot** (UART/USB flash) | 1 | 1 | 0 |

- Kaynak (tablo): https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 4-3, s.13)
- **Zamanlama:** setup time t_SU min **0 ms**; hold time t_H min **3 ms** (CHIP_EN yükseldikten sonra) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Table 4-2)
- **GPIO8 ayrıca ROM mesaj bastırma içindir** (eFuse EFUSE_UART_PRINT_CONTROL / EFUSE_USB_PRINT_CHANNEL, varsayılan 0 = yakılmamış) — kaynak: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf (Section 4.2)

---

## 3. MCP73831 LiPo Şarj Kontrolcüsü (SOT-23-5)

Kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Rev H)

> ⚠️ **SOT-23-5 pin numaraları DFN'den FARKLIDIR.** SOT-23-5: 1 = STAT, 2 = VSS, 3 = VBAT, 4 = VDD, 5 = PROG. (8-lead DFN'de yerlşim tamamen farklıdır: 1/2 = VDD, 3/4 = VBAT, 5 = STAT, 6 = VSS, 8 = PROG, 9 = EP.) Yanlış paket pinout'u kullanmak şarj devresini bozar.

### SOT-23-5 pinout

| Pin | Ad | Fonksiyon |
|----:|----|-----------|
| 1 | STAT | Şarj durum çıkışı |
| 2 | VSS | 0 V referans (toprak) |
| 3 | VBAT | Batarya şarj kontrol çıkışı |
| 4 | VDD | Besleme girişi |
| 5 | PROG | Akım ayar direnci ve şarj enable |

Kaynak (tablo): https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Table 3-1, s.10)
*(DFN karşılığı: 1/2 = VDD, 3/4 = VBAT, 5 = STAT, 6 = VSS, 7 = NC, 8 = PROG, 9 = EP — aynı tablo.)*

### Şarj akımı formülü ve PROG direnci

- **Formül:** `I_REG = 1000 V / R_PROG` — R_PROG **kΩ**, I_REG **mA** cinsinden — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 5.1.2)
- **~500 mA için R_PROG = 2 kΩ** (1000/2 = 500 mA) — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Figür 6-1 typical application: `2 kΩ`)
- **Geçerli R_PROG aralığı:** **2 kΩ … 67 kΩ** (≈15 mA … 500 mA) — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Electrical Characteristics: R_PROG 2–67 kΩ)
- **PROG açık bırakılırsa** (>200 kΩ / float) şarj devre dışı kalır ve STAT = High-Z olur — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 5.2.2)

### STAT pin durumları ve LED bağlantısı

> ⚠️ MCP73831'in STAT'ı **tri-state**'tir (MCP73832 = open-drain, farklı!). Tri-state sayesinde tek pinle iki LED sürülebilir: biri VDD→STAT, diğeri STAT→GND.

| Şarj durumu | MCP73831 STAT | MCP73832 STAT |
|-------------|:-------------:|:-------------:|
| Shutdown | High-Z | High-Z |
| Batarya yok | High-Z | High-Z |
| Preconditioning | Low | Low |
| Constant-current fast charge | Low | Low |
| Constant voltage | Low | Low |
| Charge complete (standby) | **High** | High-Z |

- Kaynak (tablo): https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Table 5-1, s.16)
- **LED bağlantısı (typical application):** LED, **470 Ω** seri direnç ile **VDD ile STAT arasına**; şarj sürerken (STAT = Low) LED yanar, tam dolumda (STAT = High) söner — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Figür 6-1, s.1)

### Giriş/çıkış kondansatörleri ve termal

- **VDD bypass:** en az **4.7 µF** (VSS'e) — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 3.1)
- **VBAT bypass:** en az **4.7 µF** (VSS'e; batarya takılı değilken döngü kararlılığı için) — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 3.2)
- **Termal:** SOT-23-5 θ_JA ≈ **230 °C/W** (4-layer JC51-7); büyük bakır alanla tipik **~130 °C/W**'a iner — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 6, Thermal Package Resistances)
- **Termal regülasyon:** çip güç harcamasını die sıcaklığına göre sınırlar; **150 °C'de şarj durur**, ~10 °C soğuyunca devam eder — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 4.9 / 4.10)
- **EP (Exposed Pad):** VSS'e bağlanmalı; termal için EP altından diğer katmana via konması önerilir — kaynak: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Section 3.6)

### Sabit voltaj varyantları (doğru sipariş kodu)

| Kod | V_REG (tipik) | Min | Max |
|-----|:-------------:|:---:|:---:|
| **-2** | **4.20 V** | 4.168 V | 4.232 V |
| -3 | 4.35 V | 4.317 V | 4.383 V |
| -4 | 4.40 V | 4.367 V | 4.433 V |
| -5 | 4.50 V | 4.466 V | 4.534 V |

- Doğruluk: **±0.75 %.** LiPo için **MCP73831-2** (4.20 V) kullanılır. Sipariş kodu örneği: **MCP73831T-2ACI/OT** (T = tape&reel, -2 = 4.20 V, I = endüstriyel sıcaklık, OT = SOT-23-5).
- Kaynak (tablo): https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf (Electrical Characteristics + Section 4.6)

---

## 4. TPS63020 Buck-Boost (VSON-14 / DSJ)

Kaynak: TI TPS63020/TPS63021 datasheet, SLVS916I — https://www.ti.com/lit/ds/symlink/tps63020.pdf
(Yerel kopya — TI TPS63020/TPS63021 datasheet, SLVS916I (Rev October 2019).)

> ⚠️ **Paket 14-pin VSON (DSJ)'dir, 10-pin değil.** Datasheet: "packaged in a 14-pin VSON package measuring 3 mm × 4 mm (DSJ)" (Section 3/5). Koordinatörün "VSON-10" notu yanlıştır — **TPS63900 ile pin uyumlu DEĞİLDİR** (bkz. Bölüm 6).

### VSON-14 (DSJ) pinout

| Pin | Ad | I/O | Açıklama |
|----:|----|-----|----------|
| 1 | VINA | I | Kontrol katı beslemesi |
| 2 | GND | — | Kontrol/lojik toprak |
| 3 | FB | I | Geri besleme (ayarlanabilir versiyon) — sabit versiyonda VOUT'a bağlanır |
| 4 | VOUT | O | Buck-boost çıkış |
| 5 | VOUT | O | Buck-boost çıkış |
| 6 | L2 | I | Endüktör bağlantısı |
| 7 | L2 | I | Endüktör bağlantısı |
| 8 | L1 | I | Endüktör bağlantısı |
| 9 | L1 | I | Endüktör bağlantısı |
| 10 | VIN | I | Güç katı beslemesi |
| 11 | VIN | I | Güç katı beslemesi |
| 12 | EN | I | Enable (1 = açık, 0 = kapalı); **açık bırakılmamalı** |
| 13 | PS/SYNC | I | Power-save enable/disable; **açık bırakılmamalı** |
| 14 | PG | O | Power-good (open-drain); boşta bırakılabilir |
| — | Thermal Pad | — | **PGND'ye bağlıdır** |

Kaynak (tablo): https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 5, Pin Functions, s.4)

### Geri besleme ve 3.3 V çıkış

- **Gerçek besleme (feedback) voltajı:** **V_FB = 500 mV** (tipik; min 495 mV, max 505 mV, PS/SYNC = VIN) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5, s.6)
- **Bölücü formülü:** `R1 = R2 × (VOUT / V_FB − 1)`; **R2 ≈ 200 kΩ** aralığında tutulmalı — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.3, Equation 3)
- **3.3 V çıkış için: R1 = 1 MΩ, R2 = 180 kΩ** (datasheet Table 3 birebir satırı) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Table 3, s.15)

### Harici bileşenler

- **Endüktör:** değer **≥ 1 µH** olmalı; 1.5–2 A çıkış için **1 µH veya 1.5 µH** önerilir; daha düşük yükte 2.2 µH da olur — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2)
- **Endüktör doyum akımı:** hesaplanan tepe akımından **en az %20 yüksek** seçilmelidir; önerilen örnek **XFL4020-152ML** (1.5 µH, I_sat 5.1 A, DCR 15 mΩ) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.2, Table 2)
- **Giriş kondansatörü:** **10 µF** (uygulama devresinde **2 × 10 µF**, X5R/X7R, VIN–PGND'a yakın) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.4, Table 4)
- **Çıkış kondansatörü:** nominal **3 × 22 µF** (X5R, VOUT–PGND'a yakın) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.3, Table 4)
- **VINA bypass:** **0.1 µF** (X5R/X7R); **0.22 µF'ı geçmemeli** — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 8.2.2.5)
- **3.3 V uygulama bileşen listesi (Table 4):** U1 = TPS63020, L1 = 1.5 µH XFL4020-152ML, C1 = 2×10 µF, C2 = 3×22 µF, C3 = 0.1 µF, R1 = 1 MΩ, R2 = 180 kΩ, R3 = 1 MΩ — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Table 4)

### PS/SYNC, EN, PG pinlerinin işlevi

- **PS/SYNC = Low:** power-save modu **etkin** — hafif yükte ortalama endüktör akımı ~100 mA altına inince düşük anahtarlama frekansına geçer, **verim artar** — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.4.4)
- **PS/SYNC = High:** power-save modu **devre dışı** — sabit frekanslı PWM; **çıkış dalgacığı (ripple) daha düşük** — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.4.4)
- **Düşük-ripple isteyen hafif-yük uygulaması için** PS/SYNC'i **High**'a çekip (forced PWM) büyük çıkış kondansatörü kullanmak gerekir; ancak hafif-yükte **en yüksek verim** PS/SYNC = Low'dadır. (Trade-off: verim ↔ ripple.) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.4.4, 8.2.2.3)
- **EN:** High = çalışır, Low = shutdown (yük bataryadan ayrılır); **açık bırakılmamalı** — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.3.3, Pin Functions)
- **PG:** open-drain power-good (1 = iyi, 0 = arıza); istenmezse boşta bırakılabilir; besleme voltajına pull-up bağlanabilir — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 7.3.4)

### Giriş aralığı, çıkış akımı ve akım tüketimi

- **Giriş voltajı aralığı:** **1.8 V … 5.5 V** — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5)
- **Çıkış akımı (VIN > 2.5 V, VOUT = 3.3 V):** **2 A** — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 1, Features)
- **Ortalama anahtar akım limiti:** 3500 / **4000** / 4500 mA (VIN = VINA = 3.6 V, 25 °C) — kaynak: https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5)
- **1S LiPo (3.0–4.2 V) → 3.3 V:** VIN > 2.5 V olduğundan **2 A'a kadar** verebilir; ESP32-C3 Wi-Fi TX piki (~350 mA) + panel rahatça karşılanır. **Ancak aşağıdaki quiescent akım deep-sleep bütçesini yer.**

| Parametre | Sembol | Test koşulu | Min | Tip | Max | Birim |
|-----------|--------|-------------|:---:|:---:|:---:|:-----:|
| Quiescent akım (VIN & VINA) | I_q | IOUT = 0 mA, VEN = VIN = VINA = 3.6 V | — | **25** | **50** | µA |
| Shutdown akımı | I_S | VEN = 0 V, VIN = VINA = 3.6 V | — | **0.1** | **1** | µA |

- Kaynak (tablo, **doğrulandı**): https://www.ti.com/lit/ds/symlink/tps63020.pdf (Section 6.5 Electrical Characteristics, s.6)
- ⚠️ **25 µA quiescent akım**, tipik bir deep-sleep hedefi olan ~50 µA bütçesinin yarısını tek başına yer. Bu yüzden Bölüm 6'daki TPS63900 alternatifi değerlendirilmelidir.

---

## 5. SSD1680 Kontrolcü + FPC Konnektör + USB-C (yardımcı parçalar)

### 5.1 SSD1680 kontrolcü — sürücü kodu için gerekli gerçekler

Kaynak: SSD1680 datasheet Rev 0.14 — https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf

- **RAM boyutu:** İki bank, her biri **176 × 296 bit**. Mono B/W RAM (**komut 0x24**) = 176×296 bit; Mono Red RAM (**komut 0x26**) = 176×296 bit — kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 6.5)
- **Adresleme:** X adresi **byte** tabanlıdır (X = 0…0x15 → 176/8 = **22 byte** tam satır); Y adresi 0…0x127 (295). Kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 8.6)
- **RAM pencere komutları:** X-start/end = **0x44** (POR XSA = 00h, XEA = 15h); Y-start/end = **0x45** (POR YSA = 000h, YEA = 127h); X-counter = **0x4E**, Y-counter = **0x4F** — kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Command Table)
- **Data Entry Mode (0x11):** ID[1:0] adres sayacının otomatik artış/azalış yönünü, AM biti X/Y yönünü seçer. POR değeri A[2:0] = 011. — kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 8.3)
- **2.13" 250×122 panele eşleme:** panel 122 kolon kullanır; byte-adreslemede bu **16 byte/satır**'a denk gelir (16 × 8 = 128 ≥ 122), 250 satır Y = 0…249 ile taranır. **`UNVERIFIED`** — bu değerler ne panel ne kontrolcü datasheet'inde birebir yazılı değildir; sürücü kodunda elle doğrulanmalıdır (SSD1680 datasheet yalnızca 22 byte'lık tam satır genişliğini verir).
- **BUSY polaritesi:** **aktif-HIGH = meşgul.** Datasheet: *"When Busy is High, the operation of the chip should not be interrupted, and command should not be sent."* Komut göndermeden önce BUSY'nin **LOW** olması beklenir. — kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Table 5-2 pin description)
- **Deep sleep (komut 0x10):** A[1:0] = 00 Normal (POR), **01 = Deep Sleep Mode 1**, **11 = Deep Sleep Mode 2**. Komut sonrası BUSY pad **High** kalır. Çıkış **yalnızca donanım reset (HWRESET)** ile olur; SW reset (0x12) uyandırmaz. — kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Command Table, 0x10)
- **Deep sleep akımı:** Mode 1 = **1 µA** tip / 3 µA max (RAM korunur); Mode 2 = **0.7 µA** tip / 3 µA max (RAM korunmaz). Sleep (normal) = 20 µA tip / 35 µA max. — kaynak: https://www.crystalfontz.com/controllers/uploaded/SSD1680.pdf (Section 6.5 DC Characteristics)

### 5.2 24-pin 0.5 mm FPC konnektör

> ⚠️ Panel FPC'si **24 pin, 0.5 mm pitch**'tir (bkz. Bölüm 1). Konnektörde **alt-kontak (bottom contact)** seçilmelidir.

- **Hirose FH12-24S-0.5SH(55)** — 24 pozisyon, **0.5 mm pitch**, **bottom contact**, SMD right-angle, flip-lock ZIF, kart üstü yükseklik 2.0 mm, FPC kalınlığı 0.30 mm, 0.5 A/kontak, 50 V — kaynak: https://media.digikey.com/pdf/Data%20Sheets/Hirose%20PDFs/FH12_Rev2018.pdf
- **Molex 5034802400** (Easy-On FBH1 serisi) — 24 circuit, **0.50 mm pitch**, **bottom contact (dual contact)**, right-angle, mated height 1.00 mm, 0.5 A/kontak, 50 V, FPC 0.30 mm — kaynak: https://www.content.molex.com/dxdam/44/4456adc5-f3af-4b82-86d4-5ad8260d8178/987651-8371.pdf

### 5.3 USB-C receptacle ve CC dirençleri

> ⚠️ **Sink (UFP) için CC1 ve CC2 pinlerinin HER BİRİ ayrı ayrı 5.1 kΩ ile GND'ye çekilmelidir.** İki CC pinini birleştirmek veya tek dirençle bağlamak akıllı (E-marked) kablolarla hataya yol açar.

- **16-pin, 0.5 mm, alt-montaj örnek:** XFCN **TPS10-N1F1-2016-A** (A5 = CC1, B5 = CC2; toplam 16 pin: GND, VBUS, D+, D−, CC1, CC2, SBU1, SBU2) — kaynak: https://www.xfconn.com/uploads/soft/20240925/4-2409251I415K5.pdf — **`UNVERIFIED`** (resmî datasheet ve stok teyidi yapılmadı)
- **CC1/CC2 pull-down:** UFP/sink için **5.1 kΩ, her CC pinine ayrı ayrı, GND'ye** — kaynak: https://www.hestore.eu/en/prod_10050443.html (USB-C sink referansı)

---

## 6. Güç regülatörü alternatifi: TPS63900

Kaynak: TI TPS63900 datasheet, SLVSET3D — https://www.ti.com/lit/ds/symlink/tps63900.pdf (Rev October 2020)

> ⚠️ **TPS63900, TPS63020 ile pin uyumlu DEĞİLDİR — PCB layoutu değişmelidir.** TPS63020 = **14-pin VSON (DSJ)**, TPS63900 = **10-pin WSON (DSK, 2.5×2.5 mm, 0.5 mm pitch)**. Pin sayısı, isimleri ve yerleşimi farklıdır; yalnızca aynı "küçük WSON/VSON" paket ailesindendir. Koordinatörün "pin-count-compatible" varsayımı geçerli değildir.

### 10-pin WSON (DSK) pinout

| Pin | Ad | I/O | Açıklama |
|----:|----|-----|----------|
| 1 | EN | I | Device enable (High = açık, Low = kapalı); **açık bırakılmamalı** |
| 2 | SEL | I | Çıkış voltajı seçimi: High → VO(2), Low → VO(1); **açık bırakılmamalı** |
| 3 | CFG1 | I | GND'ye direnç ile VO(2) + giriş akım limiti ayarı; açık bırakılmamalı |
| 4 | CFG2 | I | GND'ye direnç ile VO(2) + giriş akım limiti ayarı; açık bırakılmamalı |
| 5 | CFG3 | I | GND'ye direnç ile VO(1) ayarı; açık bırakılmamalı |
| 6 | VOUT | — | Çıkış voltajı |
| 7 | LX2 | — | Boost kademesi anahtarlama düğümü |
| 8 | GND | — | Toprak |
| 9 | LX1 | — | Buck kademesi anahtarlama düğümü |
| 10 | VIN | — | Besleme voltajı |
| — | Thermal Pad | — | Doğru çalışma için GND'ye bağlanmalı |

Kaynak (tablo): https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 5-1, s.3)

### Çıkış voltajı seçimi — 3.3 V için direnç

> ⚠️ Çıkış voltajı **CFG1/CFG2/CFG3 pinlerine GND'ye bağlanan dirençlerle** ayarlanır (harici R2D arayüzü). Dirençler **±1 % veya daha iyi tolerans** ve **±200 ppm/°C veya daha iyi** sıcaklık katsayısında olmalıdır; toplam RMS hata < ±3 %.

- **Table 7-2, "3.3 V" satırı (birebir):** R_CFG1 = **36.5 kΩ**; R_CFG2 = 0 Ω (UNLIMITED akım limiti), 511 Ω (100 mA), 1.15 kΩ (50 mA), 1.87 kΩ (25 mA), 2.74 kΩ (10 mA), 3.83 kΩ (5 mA), 5.11 kΩ (2.5 mA), 6.49 kΩ (1 mA) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 7-2, s.14)
- **3.3 V + sınırsız (unlimited) giriş akım limiti için:** **CFG1 = 36.5 kΩ (1 %)**, **CFG2 = 0 Ω**, **CFG3 = 0 Ω** (SEL = High) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 8-5, s.21 ve Figure 8-1 typical application `CFG1 36.5 kΩ`)
- Not: CFG3, **SEL = Low** iken geçerli olan VO(1) presetini belirler; tipik devrede CFG3 = 0 Ω'dir (VO(1) = 1.8 V). SEL'i sabit High kullanacaksanız CFG3 yine de boşta bırakılmamalıdır.

### Önerilen harici bileşenler (typical application, VOUT = 3.3 V)

- **Endüktör:** **2.2 µH** (Table 8-1 tek satır: 2.2 µH); örnek parça **DFE252012F-2R2M** (2.2 µH, 3.3 A, 82 mΩ) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 8-5, s.21)
- **Endüktör doyum akımı:** hesaplanan tepe akımın **%20 üstü**; önerilen 2.2 µH parçaların I_sat aralığı **1.7 … 3.5 A** — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 8-2, s.19)
- **Giriş kondansatörü:** **10 µF** (X5R/X7R, VIN–GND'a yakın); örnek **GRM188R60J106ME47** (0603) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 8.2.2.4, Table 8-4)
- **Çıkış kondansatörü:** tek **22 µF** (X5R/X7R, VOUT–GND'a yakın); örnek **GRM187R60J226ME15** (0603) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 8.2.2.3, Table 8-3)

### Çıkış akımı kapasitesi (3.0 V / 3.6 V → 3.3 V)

- **Özellik:** **> 400 mA** çıkış akımı, VI ≥ 2.0 V, VO = 3.3 V koşulunda (tipik **1.45 A pik anahtarlama akım limiti**) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 1, Features)
- **VIN = 3.0 V → VOUT = 3.3 V:** datasheet "Typical Output Current Capability versus Input Voltage" (Figure 8-2) eğrisinde VIN ≥ 2.0 V bölgesi **> 400 mA** verir. Sayısal eğri okuması datasheet metninde verilmez; tasarım için **≥ 400 mA** alınabilir. — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 8.2.3, Figure 8-2, s.21)
- **VIN = 3.6 V → VOUT = 3.3 V:** aynı eğride VIN arttıkça kapasite artar; spec garantisi **> 400 mA**'dır. **ESP32-C3 Wi-Fi TX piki (~350 mA) + panel** tek başına bu sınırın altındadır, ancak pik anahtarlama akım limiti **1.45 A (1.33–1.6 A)** olduğundan kısa süreli pikler rahatça karşılanır. — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5 CURRENT LIMIT, s.5)
- **Anahtar akım limitleri:** Peak current limit (Q1, unlimited) = **1.45 A** tip (1.33–1.6 A, VI = 1.8 V, VO = 3.6 V); startup piki = 0.35–0.83 A — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5, s.5)
- **`UNVERIFIED`:** VIN = 3.0 V ve 3.6 V'taki **kesin** çıkış akımı değeri datasheet'te sayı olarak verilmez (yalnızca "> 400 mA @ VI ≥ 2.0 V" spec'i ve eğri). Eğri elle okunmalıdır.

### EN davranışı, shutdown akımı ve mod

- **EN:** High = açık, Low = kapalı; **açık bırakılmamalı** — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Table 5-1)
- **Shutdown akımı:** **60 nA** (V(EN) = 0 V) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5, s.5, **doğrulandı**)
- **Quiescent akım:** **0.075 µA (75 nA)** tip, **1 µA** max (V(EN) = 3 V, yük yok, anahtarlama yok, unlimited akım limiti) — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 6.5, s.5)
- **Mod:** **Tek-mod (single-mode)** çalışır — buck / buck-boost / boost arası geçiş yoktur, **PS/SYNC benzeri bir mod pini YOKTUR.** Bunun yerine SEL pini (VO(1)/VO(2) preset seçimi) ve CFG pinleri (voltaj + giriş akım limiti) bulunur. — kaynak: https://www.ti.com/lit/ds/symlink/tps63900.pdf (Section 1, Features: "Single-mode operation")
- **Sonuç:** TPS63020'nin 25 µA quiescent'ine karşılık **75 nA** ile TPS63900, deep-sleep bütçesi açısından ~330× daha iyidir; karşılığında PCB layoutunun (10-pin DSK) yeniden çizilmesi ve CFG dirençlerinin (3.3 V için 36.5 kΩ) eklenmesi gerekir.
