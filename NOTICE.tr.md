# Üçüncü Taraf Bileşenler ve Lisansları

Bu proje aşağıdaki açık kaynak çalışmalardan yararlanır. Her birinin lisansı
kendi koşullarına tabidir.

---

## Derleme zamanı bağımlılıkları

| Bileşen | Lisans | Kullanım | Not |
|---|---|---|---|
| **ESP32 Arduino Core** (espressif/arduino-esp32) | LGPL-2.1 | Firmware'in çalıştığı çerçeve | PlatformIO tarafından indirilir, depoda kopyası yoktur |
| **ESP-IDF** | Apache-2.0 | Arduino core'un alt katmanı | İkili olarak bağlanır |
| **PlatformIO** | Apache-2.0 | Derleme sistemi | |

> Bu bileşenler depoda **kopyalanmamıştır**; `platformio.ini` üzerinden
> indirilir. Bu yüzden lisans metinlerini yeniden dağıtmamız gerekmez.

## Python bağımlılıkları

| Bileşen | Lisans | Kullanım |
|---|---|---|
| **Pillow** | MIT-CMU (HPND) | Yalnızca `tools/fontgen.py` |

`tools/epub2epr.py`, `tools/send.py` ve `tools/make_sample_books.py` **hiçbir
üçüncü taraf paket kullanmaz** — yalnızca Python standart kütüphanesi.

---

## Kaynak koda dahil edilmiş üçüncü taraf materyali

| Dosya | Kaynak | Lisans | Ne alındı |
|---|---|---|---|
| `firmware/src/epd_lut.h` | **Waveshare e-Paper** referans sürücüsü<br>`github.com/waveshare/e-Paper` | **MIT** | SSD1680 init register dizisi ve kısmi yenileme LUT tabloları — **birebir**, kaynak URL'si dosya başında belirtilmiştir |

Bu tablolar uydurulmadı: kısmi yenileme, panele özgü bir dalga formu gerektirir
ve yanlış bir tablo paneli kademeli olarak bozar. Kaynağı ve lisansı dosya
başında durur.

---

## Veri kaynakları (kod içermez, yalnızca doğrulama)

`hardware/schematic/pinouts.md` içindeki tüm pin numaraları ve bileşen değerleri
şu **resmî datasheet'lerden** okunmuştur. Datasheet metinleri depoda
kopyalanmamıştır; yalnızca alıntılanan tek tek değerler ve kaynak URL'leri
bulunur.

| Üretici | Doküman |
|---|---|
| GoodDisplay | GDEY0213B74 2.13&quot; e-paper datasheet Rev 1.0 |
| Espressif | ESP32-C3-MINI-1 & MINI-1U Datasheet v2.2 |
| Espressif | ESP32-C3 Hardware Design Guidelines |
| Microchip | MCP73831/2 Family Datasheet DS20001984H |
| Texas Instruments | TPS6302x Datasheet SLVS916I |
| Texas Instruments | TPS63900 Datasheet SLVSET3D |
| Solomon Systech | SSD1680 Controller Datasheet Rev 0.14 |
| Seeed Studio | XIAO ESP32-C3 wiki |
| Waveshare | 2.13inch e-Paper HAT wiki |
| Hirose / Molex | FH12 / 503480 FPC konnektör katalogları |

---

## Önerilen fontlar (depoda yoktur)

`tools/README.md` içinde önerilen fontlar ve lisansları:

| Font | Lisans |
|---|---|
| DejaVu Sans | Bitstream Vera Fonts Copyright (izin verici) |
| Noto Sans / Noto Serif | SIL Open Font License 1.1 |
| Atkinson Hyperlegible | SIL Open Font License 1.1 |
| Bitter | SIL Open Font License 1.1 |
| Liberation Sans | SIL Open Font License 1.1 |

Font dosyaları **bilinçli olarak depoya konmamıştır** — `.epf` dosyaları
kullanıcı tarafından üretilir ve `.gitignore`'dadır.

---

## Tasarım esinlenmesi

| Proje | Etki |
|---|---|
| **Adafruit GFX** | `Canvas` çizim API'sinin tasarımı (drawPixel, fillRect, clip rect) |
| **GxEPD2** (zinggjm) | Kısmi yenileme penceresi ve hayaletlenme yönetimi yaklaşımı |

Hiçbirinden kod kopyalanmamıştır; yalnızca arayüz ve yaklaşım esinlenmesi vardır.

---

## Kendi lisanslarımız

| Bölüm | Lisans |
|---|---|
| `firmware/`, `tools/`, `.github/` | [MIT](LICENSE) |
| `hardware/`, `docs/01..04` | [CERN-OHL-S-2.0](LICENSE-HARDWARE.md) |

Bir lisans uyumsuzluğu fark ettiyseniz lütfen issue açın — düzeltelim.
