<div align="center">

# Pocket Reader

**Cebinizde taşıyabileceğiniz, açık kaynak bir e-mürekkep kitap okuyucu.**

62 × 32 × 13 mm · 2.13&quot; e-paper (250×122) · ESP32-C3 · 1S Li-Po · USB-C
Bir sayfa çevirme ~0.3 s · Derin uykuda 28–55 µA · 500 mAh ile **12–24 ay** bekleme

[Donanım](#-donanım) · [Yazılım](#-yazılım) · [Hızlı başlangıç](#-hızlı-başlangıç) · [Dokümanlar](#-dokümanlar) · [English](README.md)

</div>

---

## Nedir?

Pocket Reader, tek elle tutulabilecek kadar küçük bir e-mürekkep okuyucudur. Amacı
telefonunuzu cebinizden çıkarmadan birkaç sayfa okumak: göz yormayan, arkadan
aydınlatmasız, şarjı haftalarca dayanan bir ekran.

İki seviyede kurulabilir:

| | **Kolay yapı** | **PCB yapısı** |
|---|---|---|
| Süre | ~1 saat | ~1 hafta (PCB siparişi dahil) |
| Araç | havya, 4 kablo | SMD lehimleme (fırın/hot air), 3D yazıcı |
| Kart | Seeed XIAO ESP32-C3 | ESP32-C3-MINI-1 + TPS63020 + MCP73831 |
| Panel | Hazır e-paper breakout modülü | Ham panel (24-pin FPC) |
| Kalınlık | ~18 mm (breakout modül) | ~13 mm |
| Uyku akımı | ~44 µA (XIAO kartı) | ~55 µA (TPS63020) / ~28 µA (TPS63900) |
| Firmware | **aynı** | **aynı** |

Firmware iki donanımda da **birebir aynı** çalışır — pin haritası XIAO'nun
çıkardığı 11 GPIO'ya sığacak şekilde tasarlandı.

---

## Özellikler

**Okuma**
- 2.13&quot; e-mürekkep, 250 × 122 piksel, 1-bit (siyah/beyaz)
- Türkçe dahil tam Latin-1 + Latin Extended-A glyph desteği (font dosyası üretilir)
- Kelime kaydırmalı satır sarma, paragraf girintisi, bölüm başlarında sayfa kırma
- Sayfa başına ~7 satır × ~40 karakter (14 px font), 2× büyütme seçeneği
- Kısmi yenileme ile hızlı sayfa çevirme; 20 sayfada bir otomatik tam yenileme
  (e-mürekkep hayaletlenmesini temizler)

**Kullanım**
- 3 buton: geri / ileri / menü — hiç dokunmatik yok, hiç arka ışık yok
- Menü: yazı boyutu, yenileme sıklığı, uyku süresi, Wi-Fi aktarım, kitap sil
- 60 saniye hareketsizlikte derin uyku; sayfa butonuyla **doğrudan okuduğunuz
  yere** dönüş (açılış ekranı yok)
- RTC belleği sayesinde uykuda hangi kitabın kaçıncı sayfasında olduğunuzu korur

**Kitap aktarma**
- Wi-Fi üzerinden HTTP: `http://pocketreader.local`
- Tarayıcıdan sürükle-bırak yükleme; ayrıca `tools/send.py` komut satırı aracı
- İlk kurulumda cihaz kendi Wi-Fi ağını açar (`PocketReader-XXXX`), tarayıcıdan
  ev ağınızın şifresini girersiniz — firmware'in yeniden derlenmesi gerekmez
- EPUB → `.epr` dönüştürücü, tamamen standart kütüphane ile (harici bağımlılık yok)

**Güç**
- 3.0–4.2 V Li-Po, USB-C ile 500 mA şarj (MCP73831)
- TPS63020 buck-boost → gerçek 3.3 V (pil 3.0 V'a inse bile ekran beslenir)
- Aktarım modu dışında RF tamamen kapalı

---

## Donanım

```
USB-C ──> MCP73831 ──> Li-Po 1S ──> [aç/kapa] ──> TPS63020 ──> 3V3 rayı
                                                                  │
                                          ┌───────────────────────┴────────┐
                                          ▼                                ▼
                                   ESP32-C3-MINI-1  ──SPI──>  E-Paper 2.13"
                                          ▲   ▲
                          3 buton ────────┘   └──── pil bölücü (100k/100k)
```

### 🖼️ [**Tüm çizimler ve 3B interaktif model → `site/index.tr.html`**](site/index.tr.html) · [English](site/index.html)

Tarayıcıda açılır; cihazı döndürebilir, katmanları patlatabilir, **kesit
alabilir**, parçalara tıklayabilirsiniz. Otomatik oynayan bir tanıtım
animasyonu da var.

Sayfa **tek dosyadır** — Three.js ve dört SVG dahil her şey base64 olarak
gömülüdür, yani internet bağlantısı ve yanındaki dosyalar olmadan da çalışır.
Mail ile gönderilebilir. (~1.1 MB; `tools/build_site.py` ile üretilir.)

> 📝 **Projenin hikâyesi:** [Twitter makalesi](site/twitter-article.en.md) ·
> [hazır thread](site/twitter-thread.en.md) (16 gönderi, hepsi 280 karakterin
> altında) — bu projede hiçbir şey üretilmeden önce nasıl on iki hata
> bulunduğunu anlatıyor.

- Blok diyagram: [`hardware/diagrams/blok-diyagram.svg`](hardware/diagrams/blok-diyagram.svg)
- **Tam devre şeması:** [`hardware/schematic/pocket-reader-schematic.svg`](hardware/schematic/pocket-reader-schematic.svg)
- **PCB yerleşimi (üst / alt):** [`hardware/pcb/pcb-layout-top.svg`](hardware/pcb/pcb-layout-top.svg) · [`-bottom.svg`](hardware/pcb/pcb-layout-bottom.svg)
- **Patlatılmış montaj:** [`hardware/diagrams/case-exploded.svg`](hardware/diagrams/case-exploded.svg)
- Breadboard kablolama: [`hardware/diagrams/breadboard-wiring.svg`](hardware/diagrams/breadboard-wiring.svg)
- Bağlantı tablosu (170 bağlantı, 39 net, 64 parça): [`hardware/schematic/connections.csv`](hardware/schematic/connections.csv)
- Pinout kaynakları ve doğrulanmış datasheet verileri: [`hardware/schematic/pinouts.md`](hardware/schematic/pinouts.md)
- **3D baskı kasa — hazır STL:** [`govde.stl`](hardware/enclosure/stl/govde.stl) · [`kapak.stl`](hardware/enclosure/stl/kapak.stl) · [`panel-test.stl`](hardware/enclosure/stl/panel-test.stl)
- Kasa kaynağı (parametrik): [`hardware/enclosure/case.scad`](hardware/enclosure/case.scad)

> Tüm 2B ve 3B çizimler `hardware/pcb/placement.csv` dosyasından **üretilir**.
> Elle tutulan ikinci bir koordinat listesi yoktur; iki taraf yapısal olarak
> ayrışamaz.

### Pin haritası

Tek harita, iki donanım. GPIO numaraları hem ESP32-C3-MINI-1 hem XIAO ESP32-C3
için geçerlidir.

| Sinyal | GPIO | XIAO | Yön | Not |
|---|---|---|---|---|
| `EPD_SCK` | 4 | D2 | çıkış | SPI mod 0 |
| `EPD_MOSI` | 6 | D4 | çıkış | JTAG'i kullanımdan düşürür |
| `EPD_CS` | 7 | D5 | çıkış | aktif düşük |
| `EPD_DC` | 10 | D10 | çıkış | 0 = komut, 1 = veri |
| `EPD_RST` | 8 | D8 | çıkış | strapping pini — 100k pull-up şart |
| `EPD_BUSY` | 9 | D9 | giriş | boşta HIGH; strapping şartını kendiliğinden sağlar |
| `BTN_UP` | 3 | D1 | giriş | RTC alanı → uykudan uyandırır |
| `BTN_DOWN` | 2 | D0 | giriş | RTC alanı → uykudan uyandırır |
| `BTN_MENU` | 20 | D7 | giriş | U0RXD — uykudan **uyandıramaz** |
| `VBAT_ADC` | 5 | D3 | analog | ADC2_CH0, 100k/100k bölücü |
| USB D− / D+ | 18 / 19 | — | — | USB-Serial-JTAG |

> **Neden bu kadar kısıtlı?** XIAO ESP32-C3 header'ı yalnızca 11 GPIO çıkarır ve
> bunlardan sadece GPIO2/3/4/5 RTC alanındadır. Tüm buton/ekran/pil sinyalleri
> bu 11 pinin içine, strapping pinlerinin açılış şartlarını bozmadan
> yerleştirilmiştir. Detay: [`docs/02-schematic.md`](docs/02-schematic.md)

---

## Yazılım

```
firmware/                ESP32-C3 gömülü yazılımı (Arduino C++ / PlatformIO)
  include/config.h         pin haritası, ekran döndürme, tüm ayarlar
  src/epd.cpp              SSD1680 sürücüsü: init, tam/kısmi yenileme, Canvas
  src/epd_lut.h            satıcının referans LUT tabloları (kaynak gösterilmiş)
  src/font.cpp             .epf ikili font yükleyici + UTF-8 çözücü
  src/book.cpp             .epr okuyucu + sayfalama + sayfa indeksi önbelleği
  src/ui.cpp               ekranlar: kitaplık, okuyucu, menü, Wi-Fi, hata
  src/buttons.cpp          debounce + kısa/uzun basma
  src/power.cpp            ADC pil ölçümü, derin uyku (ext1), RTC durumu
  src/storage.cpp          LittleFS + NVS ayarlar
  src/wifi_xfer.cpp        HTTP sunucu, yükleme sayfası, AP kurulumu

tools/                   Bilgisayar tarafı araçlar (Python)
  epub2epr.py              EPUB → .epr dönüştürücü (yalnızca stdlib)
  fontgen.py               TTF/OTF → .epf font üreteci (Pillow)
  send.py                  cihaza yükleme, kitap listeleme/silme, Wi-Fi ayarı
  make_sample_books.py     örnek kitaplar üretir
  gen_placement.py         PCB yerleşim verisi (tüm çizimlerin kaynağı)
  gen_pcb_layout.py        2B teknik resimleri üretir (placement.csv'den)

site/                    Tarayıcıda açılan tanıtım sayfası
  index.html               3B interaktif model + tüm çizimler (tek dosya)

hardware/                Şema, netlist, PCB çizimleri, kasa
  schematic/               devre şeması, netlist üreteci, pinout kaynakları
  pcb/                     yerleşim verisi, 2B teknik resimler
  diagrams/                blok, kablolama, patlatılmış montaj
  enclosure/               parametrik OpenSCAD kasa
```

### Kitap biçimi `.epr`

Kendi kapsayıcı biçimimiz var; sebebi basit: cihazda 400 KB RAM ve 4 MB flash
var, EPUB'ı cihazda ayrıştırmak ne mümkün ne de gerekli. Dönüştürme bilgisayarda
bir kez yapılır, cihaz sadece düz metin + iki kontrol baytı görür.

```
"EPR1" | sürüm | bayraklar | metin_offset | metin_uzunluk | toc_offset | toc_sayısı
başlık | yazar | dil | kodlama | dolgu
metin bloğu:  0x0A = paragraf sonu,  0x0B = bölüm sonu (yeni sayfa)
içindekiler bloğu: her giriş { uint32 metin_konumu, uint8 uzunluk, başlık }
```

Tam belirtim: [`docs/06-books-and-fonts.md`](docs/06-books-and-fonts.md)

### Font biçimi `.epf`

Cihazda derlenmiş font yok; font LittleFS'ten çalışma anında yüklenir. Böylece
firmware'e dokunmadan yazı tipini ve boyutunu değiştirebilirsiniz.

```
"EPF1" | sürüm | yükseklik | ascent | descent | satır aralığı | glyph sayısı
her glyph: uint32 kod noktası | advance | left | genişlik | yükseklik | top |
           ceil(genişlik*yükseklik/8) bayt, satır satır, MSB önce
```

---

## Hızlı başlangıç

### 1. Donanım (kolay yapı, ~1 saat)

Malzeme listesi ve sipariş linkleri: [`docs/01-bill-of-materials.md`](docs/01-bill-of-materials.md)

Kablolama şeması: [`hardware/diagrams/breadboard-wiring.svg`](hardware/diagrams/breadboard-wiring.svg)

### 2. Yazılım ortamı

```bash
# PlatformIO (VS Code eklentisi veya komut satırı)
pip install platformio

git clone <bu-repo> pocket-eink-reader
cd pocket-eink-reader/firmware
pio run -e xiao -t upload        # kolay yapı
# pio run -e esp32-c3-devkitm-1 -t upload   # PCB yapısı
```

### 3. Font üret ve yükle

```bash
cd ../tools
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Türkçe kapsayan bir TTF ile font üret
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
        --size 14 --out ../firmware/data/fonts/reader-14.epf

mkdir -p ../firmware/data/fonts && cp reader-14.epf ../firmware/data/fonts/
cd ../firmware && pio run -t uploadfs
```

### 4. İlk açılış

1. Cihaz açılır, font yoksa uyarı ekranı çıkar → 3. adımı yapın.
2. Uzun MENÜ basışı → Wi-Fi aktarım modu. Ekranda SSID ve IP görünür.
3. Telefon/bilgisayardan `http://pocketreader.local` adresini açın.
4. Wi-Fi şifrenizi bir kez girin; bir daha sormaz.
5. EPUB'ınızı sürükleyip bırakın — cihaz dönüştürme yapmaz, `.epr` bekler.

```bash
# EPUB'ı dönüştürüp doğrudan yükle
cd tools
python3 epub2epr.py ~/kitap.epub -o /tmp/kitap.epr --title "Kitap" --author "Yazar"
python3 send.py /tmp/kitap.epr
```

---

## Güç tüketimi

Uykudaki tüketim **regülatör ve pil bölücü** tarafından belirlenir, MCU tarafından değil.
Aşağıdaki dökümle bunu görünür kıldık:

| Kalem | TPS63020 ile | TPS63900 ile |
|---|---|---|
| Regülatör boşta akımı | **25 µA** | **0.075 µA** |
| Pil bölücü (100k/100k) | 21 µA | 21 µA |
| ESP32-C3 derin uyku | ~5 µA | ~5 µA |
| Geri besleme bölücüsü (1M/180k) | 2.8 µA | 0 µA |
| Panel derin uyku | 1 µA | 1 µA |
| **Toplam** | **~55 µA** | **~28 µA** |
| 500 mAh ile bekleme | ~12 ay | ~24 ay |
| Bölücü 1M/1M yapılırsa | ~36 µA → ~19 ay | ~9 µA → **hücre kendiliğinden deşarjı baskın** |

Çalışma sırasında belirleyici olan, ekran yenilemesi değil **uyanık kalma
süresidir**. Cihaz bir sayfa çevirdikten sonra 60 saniye daha uyanık kalır:

| Kullanım | Süre (500 mAh pil) | Açıklama |
|---|---|---|
| **Sürekli okuma** | **~25 saat** | Ekran açık, ~20 mA |
| Wi-Fi aktarım | ~5 saat | Radyo açık |
| Tek sayfa çevirme | ~170.000 kez | 0.3 s × 35 mA — ama uyanık süre bunun ~100 katı |

Günlük 20 dakika okuyan biri için pratikte **~2,5 ay**; bekleme modunda
**12 ay** (TPS63020) veya **24 ay** (TPS63900).

> **Neden iki regülatör?** Varsayılan BOM TPS63020 kullanır: geri beslemesi iki
> dirençle ayarlanır, stok bulunur ve pinout'u doğrulanmıştır. Ancak boşta 25 µA
> çeker ve bu, uykudaki toplam tüketimin yarısıdır. TPS63900 aynı 2.5 × 2.5 mm
> WSON-10 paket ailesindedir ve **330 kat daha az** boşta akım çeker; karşılığında
> çıkış gerilimi datasheet'teki bir yapılandırma direnci tablosundan seçilir.
> Ayrıntılı karşılaştırma: [`docs/07-power.md`](docs/07-power.md)

---

## Dokümanlar

| # | Dosya | İçerik |
|---|---|---|
| 00 | [Genel bakış](docs/00-overview.md) | Mimari, tasarım kararları, neden bu parçalar |
| 01 | [Malzeme listesi](docs/01-bill-of-materials.md) | Tam BOM, sipariş linkleri, yaklaşık fiyat |
| 02 | [Devre şeması](docs/02-schematic.md) | Blok blok açıklama, net listesi, hesap detayları |
| 03 | [PCB](docs/03-pcb.md) | Yerleşim, katmanlar, üretim ayarları, anten koruma alanı |
| 04 | [Montaj](docs/04-assembly.md) | Lehimleme sırası, FPC bağlama, kasa montajı |
| 05 | [Yazılım kurulumu](docs/05-firmware-setup.md) | PlatformIO, derleme, flash, hata ayıklama |
| 06 | [Kitap ve font dönüştürme](docs/06-books-and-fonts.md) | `.epr` ve `.epf` belirtimi, araç kullanımı |
| 07 | [Güç yönetimi](docs/07-power.md) | Uyku, ölçüm, pil ömrü hesabı, iyileştirmeler |
| 08 | [Sorun giderme](docs/08-troubleshooting.md) | Ekran boş/flip, uyanmıyor, Wi-Fi yok, şarj olmuyor |
| 09 | [Yol haritası](docs/09-roadmap.md) | Yapılacaklar, katkı fikirleri |

---

## Durum ve doğruluk

Bu proje **tasarlanmış ve belgelenmiştir**, ancak fiziksel olarak üretilip test
edilmemiştir. Olduğu gibi kabul edin:

- **Derleme:** firmware, bu depo hazırlanırken bir derleyiciden geçirilmedi.
  İlk `pio run` çağrısında küçük düzeltmeler gerekebilir.
- **Testler:** `cd tools && python3 -m unittest discover -s tests` → **66 test,
  hepsi geçiyor.** Bunların 12'si (`.epf` interop) firmware kaynağını çalışma
  anında ayrıştırıp iki tarafın **aynı** ikili biçim kurallarını uyguladığını
  doğrular — bu denetim iki sessiz hatayı yakaladı (bkz. `CHANGELOG.md`).
- **Doğrulanmış (datasheet'ten birebir):** panel aktif alanı ve **24-pin FPC
  pin sırası**, panelin harici kondansatör ve boost şebekesi, ESP32-C3-MINI-1'in
  53 pinlik tablosu, anten keep-out alanı, strapping şartları, MCP73831 SOT-23-5
  pinout'u ve şarj formülü, TPS63020'nin 14-pin VSON pinout'u ve 3.3 V için
  `R5`/`R6` değerleri, TPS63900'un 10-pin pinout'u ve `CFG` dirençleri,
  SSD1680'in RAM/BUSY/uyku davranışı. Hepsi
  [`hardware/schematic/pinouts.md`](hardware/schematic/pinouts.md) içinde
  kaynak URL'siyle birlikte.
- **Hâlâ doğrulanacak (13 pin):** USB-C receptacle'ın pin numaraları,
  USBLC6-2SC6'nın pinout'u, Si1308EDL'in pinout'u. `python3
gen_netlist.py --check` bunları listeler.
- **Ekran görüntünüz ters gelirse:** `firmware/include/config.h` içindeki
  `EPD_MIRROR_X` / `EPD_MIRROR_Y` / `EPD_ROTATION` seçeneklerinden birini
  değiştirin. Bu ayar bilerek tek satırda erişilebilir yapıldı.
- **Kendi PCB'nizi üretmeden önce** `hardware/schematic/gen_netlist.py --check`
  çalıştırın; eksik pin numaralarını listeler.

---

## Katkı ve lisans

Katkı rehberi: [`CONTRIBUTING.md`](CONTRIBUTING.md)

| Bölüm | Lisans |
|---|---|
| Firmware ve araçlar | [MIT](LICENSE) |
| Donanım tasarımı (şema, PCB, kasa) | [CERN-OHL-S-2.0](LICENSE-HARDWARE.md) |

Kısaca: kodu istediğiniz gibi kullanın; donanımı üretip satabilirsiniz ama
tasarım dosyalarını açık tutmak zorundasınız.

<div align="center">
<sub>Bir kitap, bir çip, üç buton.</sub>
</div>
