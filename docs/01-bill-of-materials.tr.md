> English version: [01-bill-of-materials.md](01-bill-of-materials.md)

# 01 · Malzeme Listesi (BOM)

İki yapı seviyesi için ayrı listeler. Kolay yapıyı seçerseniz PCB listesine hiç
bakmayın; iki liste **ortak parçaları** paylaşır (butonlar, pil, kablo).

> Fiyatlar 2026 itibarıyla tek adetlik **yaklaşık** değerlerdir ve USD'dir.
> Kargo, vergi ve kur dahil değildir. Sipariş öncesi stok kontrolü yapın.

---

## A · Kolay yapı (breadboard / protoboard)

Havya ve ~1 saat yeterli. Hata ayıklaması kolay, taşınabilirliği düşük.

| # | Parça | Önerilen | Adet | ~Fiyat | Not |
|---|---|---|---|---|---|
| 1 | MCU kartı | **Seeed XIAO ESP32-C3** | 1 | $6 | Şarj devresi ve 3.3 V regülatör üzerinde hazır |
| 2 | E-paper modül | **Waveshare 2.13&quot; e-Paper Module (V3)** | 1 | $18 | SSD1680 sürücülü, breakout kartlı. *HAT* değil *Module* alın |
| 3 | Li-Po pil | 1S, 500–1000 mAh, **dahili korumalı** | 1 | $5 | 502030 veya 402025. Korumasız alırsanız DW01A+FS8205A gerekir |
| 4 | Buton | 6×6 mm taktil buton | 3 | $0.5 | Sayfa geri / ileri / menü |
| 5 | Protoboard | 5×7 cm tek taraflı | 1 | $1 | Breadboard da olur ama taşınmaz |
| 6 | Kablo | 30 AWG silikon kaplı, dişi-dişi jumper | 1 | $2 | |
| 7 | Header | 2.54 mm dişi header şeridi | 1 | $0.5 | XIAO ve e-paper modülü için |
| 8 | Anahtar | Küçük SPDT kayar anahtar | 1 | $0.5 | Aç/kapa |
| | | | | **~$34** | |

**Kritik uyarı:** XIAO ESP32-C3'ün kendi şarj devresi vardır (380 mA hızlı /
40 mA trickle). Ayrıca TP4056 modülü **almayın** — gereksiz ve iki şarj devresi
paralel bağlanırsa pile zarar verir.

**Panel seçerken:** Waveshare'ın üç farklı ürünü var ve karıştırılıyor:

| Ürün adı | İçerik | Bizim için |
|---|---|---|
| 2.13inch e-Paper **Module** | Ham panel + breakout kart | ✅ **bunu alın** |
| 2.13inch e-Paper **HAT** | Module + Raspberry Pi 40-pin header | ➖ çalışır, gereksiz büyük |
| 2.13inch e-Paper **HAT (B)** | Kırmızı/siyah/sarı/beyaz 4 renkli panel | ❌ sürücüsü farklı (SSD1680 değil), kısmi yenileme desteklemez |

**V3 revizyonu şart.** V1/V2 farklı denetleyici (UC8151D) kullanır ve
`firmware/src/epd_lut.h` içindeki LUT tabloları uymaz.

---

## B · PCB yapısı (ince, kalıcı cihaz)

| # | Parça | Parça numarası | Adet | ~Fiyat | Footprint |
|---|---|---|---|---|---|
| 1 | MCU modülü | **ESP32-C3-MINI-1-N4** | 1 | $3 | `RF_Module:ESP32-C3-MINI-1` |
| 2 | Buck-boost | **TPS63020DSJR** | 1 | $3 | **VSON-14 (DSJ), 3 × 4 mm** — 10 pinli değil! |
| 3 | Şarj denetleyici | **MCP73831T-2ACI/OT** | 1 | $1 | SOT-23-5 (`-2` = 4.20 V) |
| 4 | ESD koruma | **USBLC6-2SC6** | 1 | $0.4 | SOT-23-6 |
| 5 | İndüktör | **1.5 µH**, ≥2 A doyum, 4×4 mm | 1 | $0.5 | Datasheet Table 4: `XFL4020-152ML` |
| 6 | USB-C soket | TYPE-C-31-M-12 (16 pin) | 1 | $1 | HRO |
| 7 | FPC konektör | **Hirose FH12-24S-0.5SH** (veya Molex 5034802400) | 1 | $1 | 24P, 0.5 mm, alt temaslı |
| 8 | Kayar anahtar | MSK-12C02 | 1 | $0.5 | SPDT |
| 9 | Taktil buton | PTS645 veya eşdeğeri | 3 | $1 | SMD |
| 10 | LED | Yeşil 0603 | 1 | $0.1 | Şarj göstergesi |
| 11 | Panel kondansatörleri | 1 µF / **25 V** × 8, 4.7 µF / 25 V × 2 | 10 | $1 | `VCI/VDDIO/VDD/VSH1/VSH2/VSL/VGL/VCOM` + giriş |
| 12 | Panel boost | 47 µH/500 mA, MBR0530 × 3, Si1308EDL, 4.7 µF, 1 µF, 1 MΩ, 2.2 Ω | 9 | $2 | Datasheet Section 12 — adaptör kartı kullanırsanız **gerekmez** |
| 13 | Direnç | 0603 / 0805, %1 | ~20 | $2 | Değerler `connections.csv`'de |
| 14 | Kondansatör | 0603 / 0805 X5R/X7R | ~12 | $2 | |
| 15 | Kondansatör | 100 µF, 1206, düşük ESR | 1 | $0.5 | Panel tamponu |
| 16 | PCB | 2 katman, 1.6 mm, ENIG | 5 | $2+s/h | 58 × 28 mm (JLCPCB 5 adet) |
| 17 | Ham panel | **GDEY0213B74** | 1 | $12 | GoodDisplay veya AliExpress |
| 18 | Li-Po pil | 1S 500 mAh korumalı | 1 | $5 | Kasa içi 35 × 20 mm |
| 19 | Kasa | 3D baskı, ~4 g filament | 1 | $1 | `hardware/enclosure/case.scad` |
| 20 | Vida | M1.6 × 4 mm | 4 | $0.5 | Kapak için |
| | | | | **~$36** | |

### Direnç ve kondansatör değerleri

Tam liste, her birinin hangi nete bağlandığıyla birlikte:
[`hardware/schematic/connections.csv`](../hardware/schematic/connections.csv)

Özet kritik değerler:

| Parça | Değer | Neden bu değer |
|---|---|---|
| `R1`, `R2` | 5.1 kΩ | USB-C UFP tanımı. USB-C spesifikasyonu zorunlu kılar |
| `R3` | 2 kΩ | `I_şarj = 1000 / R3` = 500 mA (MCP73831 formülü) |
| `R5` / `R6` | **1 MΩ / 180 kΩ** | `Vout = 0.5 V × (1 + 1M/180k)` = 3.28 V — datasheet Table 3, 3.3 V satırı |
| `R7`, `R8` | 100 kΩ / 10 kΩ | EN pull-up'ları |
| `R9`, `R10` | 100 kΩ | Strapping pinlerinin açılış şartı (bkz. `docs/00` §2) |
| `R13`–`R15` | 100 kΩ | Buton pull-up |
| `R16`, `R17` | 100 kΩ / 100 kΩ | Pil bölücü, 1:2. 4.2 V'ta 21 µA — uykudaki baskın tüketim |
| `C22` | 100 µF | Panel yenileme akım darbesi tamponu. **Atlanırsa panel kararsız çalışır** |
| `C25`–`C27` | 100 nF | Donanımsal buton debounce (uyanma anındaki sıçrama için) |

---

## C · Ortak parçalar (her iki yapı)

| Parça | Adet | Not |
|---|---|---|
| Li-Po 1S 500 mAh, korumalı | 1 | Korumasız alırsanız `U4`+`Q1` eklenmeli |
| Taktil buton | 3 | |
| Kayar anahtar | 1 | |
| M1.6 × 4 mm vida | 4 | |

---

## D · Araçlar (tek seferlik, ~$60–120)

| Araç | Zorunlu mu | Not |
|---|---|---|
| Havya (ayarlanabilir, 350 °C) | Kolay yapıda ✅ | PCB'de SMD için ince uç |
| Sıcak hava istasyonu veya tost fırını | PCB'de ✅ | VSON-10 ve SOT-23-5 elle zor |
| Dijital multimetre | ✅ | Süreklilik ve gerilim kontrolü |
| USB-C kablo (veri destekli!) | ✅ | Bazı kablolar yalnızca şarj içindir |
| 3D yazıcı | ➖ | Kasa olmadan da çalışır |
| USB-TTL dönüştürücü | ➖ | Cihaz USB-C ile programlanır, gerekmez |

---

## E · Nereden alınır

**Türkiye**

| Kaynak | Uygun ürünler |
|---|---|
| [Robotistan](https://www.robotistan.com) | XIAO kartları, e-paper modüller, butonlar, Li-Po |
| [Direnc.net](https://www.direnc.net) | e-paper, pasif bileşenler, konektörler |
| [Mouser TR](https://www.mouser.com.tr) | TPS63020, MCP73831, USBLC6, TPS serisi |
| [DigiKey TR](https://www.digikey.com.tr) | Aynı parçalar, daha geniş stok |

**Uluslararası**

| Kaynak | Uygun ürünler |
|---|---|
| [Seeed Studio](https://www.seeedstudio.com) | XIAO ESP32-C3 (üretici) |
| [Waveshare](https://www.waveshare.com) | e-paper modülleri (üretici) |
| [Good Display](https://www.good-display.com) | Ham paneller (üretici) |
| [LCSC](https://www.lcsc.com) | Tüm SMD bileşenler, PCB ile birleşik sipariş |
| [JLCPCB](https://jlcpcb.com) | PCB üretimi + LCSC parçaları tek siparişte |
| AliExpress | Panel ve Li-Po için genelde en ucuz, teslim 3–6 hafta |

> **İpucu:** JLCPCB'de PCB siparişi verirken "Parts Library" üzerinden
> TPS63020 ve MCP73831'i seçip **montaj hizmeti** alabilirsiniz. Böylece en zor
> iki SMD parçayı kendiniz lehimlemek zorunda kalmazsınız. Maliyet ~$15 artar,
> ama başarı oranı çok yükselir.

---

## F · Sipariş öncesi kontrol listesi

- [ ] Panel **V3** revizyonu ve **SSD1680** denetleyicili mi?
- [ ] Panel **Module** (breakout kartlı) mi, **HAT** mı? (kolay yapıda Module)
- [ ] Li-Po **dahili korumalı** mı? (değilse `U4`+`Q1` BOM'a eklendi mi?)
- [ ] Li-Po fiziksel boyutu kasaya sığıyor mu? (hedef: ≤ 35 × 20 × 6 mm)
- [ ] USBLC6-2SC6'nın **-2SC6** varyantı mı? (farklı pinout'lu varyantlar var)
- [ ] MCP73831'in **-2ACI/OT** kodu mu? (`-2` = 4.20 V sabit)
- [ ] İndüktörün doyum akımı ≥ 1.5 A mı?
- [ ] `hardware/schematic/gen_netlist.py --check` temiz mi?

---

Geri: [00 · Genel Bakış](00-overview.tr.md) · Devam: [02 · Devre Şeması](02-schematic.tr.md)
