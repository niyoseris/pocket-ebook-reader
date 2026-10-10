# Changelog

Bu proje [Semantic Versioning](https://semver.org/lang/tr/) kullanır.
Biçim [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) temellidir.

---

## [Unreleased]

### Eklenecek
- Gerçek donanımda derleme ve ölçüm sonuçları
- Fotoğraflı montaj rehberi (`docs/04`)
- Üretilmiş Gerber dosyaları (`hardware/pcb/`)

---

## [1.0.0] — 2026-10-09

İlk sürüm. Tasarım ve dokümantasyon tamamlandı; **fiziksel donanımda test
edilmedi.**

### Eklendi

**Donanım**
- Tam devre şeması (SVG): USB-C girişi, MCP73831 şarj, TPS63020 3.3 V
  buck-boost, ESP32-C3-MINI-1, 24-pin e-paper FPC, butonlar, pil algılama
- Blok diyagram ve breadboard kablolama şeması
- `gen_netlist.py`: tek kaynaktan üretilen `connections.csv` (170 bağlantı,
  39 net, 64 parça) ve KiCad netlist
- `pinouts.md`: resmî datasheet'lerden birebir doğrulanmış pin tabloları,
  kaynak URL'leriyle
- Parametrik OpenSCAD kasa (62 × 32 × 13 mm) — dış ölçüler panel camından türetilir
- İki yapı seviyesi: hazır modüllerle breadboard ve özel PCB

**Firmware (ESP32-C3, Arduino C++ / PlatformIO)**
- SSD1680 sürücüsü: init, tam yenileme, kısmi yenileme, derin uyku
- Satıcının referans LUT tabloları, kaynak ve lisans belirtilerek
- Çalışma anında yüklenen `.epf` font sistemi (Türkçe tam kapsama)
- `.epr` kitap biçimi: ayrıştırma, satır sarma, sayfalama, sayfa indeksi
  önbelleği
- Arayüz: kitaplık, okuyucu, menü, Wi-Fi, hata, uyku ekranları
- 3 buton, kısa/uzun basma, donanımsal + yazılımsal debounce
- Derin uyku + ext1 uyanma + **açılış ekranını atlayan akıllı uyanma**
- ADC pil ölçümü ve Li-Po deşarj eğrisi
- Wi-Fi aktarım: HTTP sunucu, tarayıcı arayüzü, AP kurulum modu
- İngilizce/Türkçe arayüz (`i18n.h`; varsayılan İngilizce, Türkçe için
  `-DLANG_TR` bayrağı)

**Araçlar (Python)**
- `epub2epr.py` — EPUB 2/3 → `.epr`, yalnızca standart kütüphane
- `fontgen.py` — TTF/OTF → `.epf`, Pillow ile, Türkçe kapsamalı
- `send.py` — yükleme, listeleme, silme, Wi-Fi ayarı, klasör toplu işleme
- `make_sample_books.py` — örnek ve stres testi kitapları
- `unittest` test takımı (`.epr` gidiş-dönüş, küçük EPUB üreteci)

**Dokümantasyon**
- `docs/00`–`09`: mimari, BOM, devre, PCB, montaj, yazılım, kitap/font,
  güç yönetimi, sorun giderme, yol haritası
- `README.md` (İngilizce) ve `README.tr.md` (Türkçe)

**CI**
- GitHub Actions: iki donanım ortamının derlenmesi, Python testleri,
  netlist tutarlılık denetimi, SVG geçerlilik kontrolü

### Düzeltildi (doğrulama sırasında bulunan hatalar)

Bu sürüm yayınlanmadan önce **on iki hata** bulundu ve düzeltildi — hiçbiri
gerçek donanımda değil, hepsi doküman, aritmetik ve çapraz denetimlerle. Üç
grupta toplanıyorlar.

#### 1. Datasheet ve tasarım hataları (6)

Hiç sorgulanmamış varsayımların karşısına resmî datasheet'ler konarak bulundu:

| # | Bulgu | İlk tasarım | Doğrusu |
|---|---|---|---|
| 1 | TPS63020 paketi | VSON-10 | **VSON-14 (DSJ), 3 × 4 mm** |
| 2 | TPS63900 uyumluluğu | "pin uyumlu" | **Uyumlu değil** — layout yeniden çizilmeli |
| 3 | Geri besleme dirençleri | 560 kΩ / 100 kΩ | **1 MΩ / 180 kΩ** (datasheet Table 3) |
| 4 | GPIO8 strapping | Açılışta HIGH şart | **SPI boot'ta serbest** (Table 4-3) |
| 5 | Panel beslemesi | Yalnızca 3.3 V + kondansatör | **Ayrıca harici ±15 V boost şart** (GDR/RESE pinleri) |
| 6 | Panel BUSY polaritesi | HIGH = boşta | Datasheet **HIGH = meşgul** — yapılandırılabilir yapıldı, zaman aşımı eklendi |

#### 2. Geometri ve mekanik hatalar (4)

Yerleşim verisinin etrafına yazılan doğrulayıcılar buldu — bir parçanın montaj
deliğiyle çakışması ya da kendi kasasına sığmaması şemada görünmez:

| # | Bulgu | Yol açacağı belirti | Düzeltme |
|---|---|---|---|
| 7 | Gövde ölçüsü | Kasa 58 × 30 mm'ydi; panelin **camı 59.2 × 29.2 mm** ve o kasaya monte edilemez | **62 × 32 mm**, camdan türetilir: cam + 2 × 1.4 mm çerçeve |
| 8 | FPC kanalı yanlış kasa kenarında | Kasa şerit kanalını −Y kenarına açmıştı, oysa J2 kartın +Y kenarında; kablo tüm kartı dolanmak zorundaydı | Kanal +Y'ye taşındı. Çizim üretecinin geometri denetimi yakaladı |
| 9 | Montaj delikleri ile mahfazalar | Dört M1.6 montaj deliği `BT1`, `SW4`, `R13` ve `R15` mahfazalarının üstüne biniyordu | Dört delik bölgesi artık `gen_placement.py` içinde koruma alanı; yerleştirici oraya parça koymuyor |
| 10 | Butonlar sığmıyordu | İki montaj deliği arasında kalan 15 mm'ye üç adet 5 mm buton sığmaz | Butonlar 4.5 mm'ye indirildi ve yeniden aralandı |

#### 3. Yazılım ve entegrasyon hataları (2)

Aynı biçimin iki yarısı arasındaki çapraz denetimler buldu. İkisi de **sessiz**
hataydı — cihaz açılır, hiçbir şey çökmez, ama sonuç bozuk olurdu:

| # | Bulgu | Belirti | Düzeltme |
|---|---|---|---|
| 11 | `.epr` dönüştürücü, her paragraf sonunu (`0x0A`) siliyordu | Dönüştürülen **her kitap** tek bir uzun paragraf olarak görünürdü; yalnızca bölüm sonları kalırdı | `TextBuilder.add_block` içindeki koşulsuz `_trim_trailing_breaks()` çağrısı yalnızca bölüm açılışında çalışacak şekilde sınırlandı. 6 yeni regresyon testi eklendi |
| 12 | `.epf` fontunda `top` alanının referans noktası iki tarafta farklıydı | Firmware `top`'u taban çizgisinden ölçülmüş sanıyordu; hata **glyph başına değiştiği için** metin dikey olarak dağılırdı (`.` 13 px yukarı, `A` 9 px aşağı) | `y0 = baseline_y - (ascent - top) * scale`. `font.h` yorumları netleştirildi; `tools/tests/test_epf_interop.py` iki tarafın aynı kuralı uyguladığını sınır genişliklerle (9/12/13/17 px) doğruluyor |

12 numaralı hata, aynı ikili biçimin iki yarısını iki farklı ajanın yazmasından
doğdu — bu yüzden `test_epf_interop.py` artık firmware kaynağını çalışma anında
ayrıştırıp kendi varsayımını değil **karşı tarafın** kuralını test ediyor.

Güç bütçesi hesabı da düzeltildi: ilk tasarımda "sayfa çevirme başına
1.300.000 sayfa" yazıyordu, doğrusu **uyanık kalma süresinin baskın olduğu**
gerçekçi bir model (~25 saat sürekli okuma, 12 ay bekleme).

### Bilinen sınırlamalar

- Fiziksel donanımda test edilmedi
- **13 pin numarası doğrulanmadı**: USB-C receptacle, USBLC6-2SC6, Si1308EDL
- Panelin harici boost devresi test edilmedi
- Firmware bu depo hazırlanırken bir derleyiciden geçirilmedi
- Türkçe heceleme ile kelime bölme yok
- MENÜ butonu cihazı uykudan uyandıramaz (GPIO20 RTC alanında değil)
- Ön ışık yok (bu panel boyutunda mevcut değil)

---

## Sürüm numaralandırma politikası

- **MAJOR** — `.epr` veya `.epf` biçiminde geriye uyumsuz değişiklik, pin
  haritasında değişiklik
- **MINOR** — yeni özellik, yeni donanım varyantı, yeni araç
- **PATCH** — hata düzeltmesi, doküman düzeltmesi, değer düzeltmesi

Donanım revizyonları ayrıca `Rev X.Y` olarak şemada işaretlenir.
