> English version: [09-roadmap.md](09-roadmap.md)

# 09 · Yol Haritası ve Katkı Fikirleri

Her madde **zorluk** ve **etki** ile işaretlenmiştir. Yeni katkı verenler için
en iyi başlangıç: 🟢 kolay + yüksek etkili maddeler.

---

## Şu an çalışan (v1.0)

- ✅ 2.13&quot; SSD1680 sürücüsü: init, tam yenileme, kısmi yenileme, derin uyku
- ✅ Çalışma anında yüklenen `.epf` font sistemi (Türkçe tam kapsama)
- ✅ `.epr` kitap biçimi + sayfalama + sayfa indeksi önbelleği
- ✅ Kitaplık / okuyucu / menü / Wi-Fi / hata ekranları
- ✅ 3 buton, kısa/uzun basma, donanımsal + yazılımsal debounce
- ✅ Derin uyku + ext1 ile uyanma + açılış ekranını atlayan akıllı uyanma
- ✅ ADC pil ölçümü ve Li-Po deşarj eğrisi
- ✅ Wi-Fi aktarım: HTTP sunucu, tarayıcı arayüzü, AP kurulum modu
- ✅ Bilgisayar araçları: EPUB dönüştürücü, font üreteci, yükleme aracı
- ✅ Parametrik 3D baskı kasa
- ✅ Üretilebilir netlist + bağlantı tablosu

---

## Bilinen sınırlamalar

| Sınırlama | Etki | Zorluk |
|---|---|---|
| **13 pin numarası doğrulanmadı** (USB-C, USBLC6, Si1308EDL) | Netlist pcbnew'e doğrudan import edilemez | 🟢 |
| **Panelin harici boost devresi test edilmedi** | Yanlış kurulursa panel hasar görür | 🔴 |
| **BUSY polaritesi tartışmalı** | Yanlışsa cihaz hiç görüntü vermez | 🟢 |
| **Firmware derlenmedi** | İlk derlemede küçük düzeltmeler gerekir | 🟡 |
| Gerçek donanımda test edilmedi | Bazı davranışlar sürpriz olabilir | 🔴 |
| Türkçe heceleme ile kelime bölme yok | Uzun kelimeler satır sonunda bölünür | 🟡 |
| MENÜ butonu uykudan uyandıramaz | Araya bir adım girer | 🔴 (donanım kısıtı) |
| Ön ışık yok | Karanlıkta okunamaz | 🔴 (bu boyutta panel yok) |
| Tek font ailesi | — | 🟢 |

---

## Yol haritası

### v1.1 — Doğrulama ve sağlamlaştırma

| # | Madde | Etki | Zorluk |
|---|---|---|---|
| 1 | ~~`pinouts.md` pinout'larını datasheet'ten tamamla~~ — **kısmen yapıldı:** FPC 24-pin, ESP32-C3-MINI-1 (53 pin), MCP73831, TPS63020 (14-pin), TPS63900, SSD1680 doğrulandı ve `gen_netlist.py`'ye işlendi. **Kalan 13 pin:** USB-C receptacle, USBLC6-2SC6, Si1308EDL | 🔴🔴🔴 | 🟢 |
| 2 | Firmware'i gerçek donanımda derle, derleme hatalarını düzelt | 🔴🔴🔴 | 🟡 |
| 3 | İlk fiziksel prototipi kur, ölçümleri `docs/07` §6 tablosuna işle | 🔴🔴🔴 | 🟡 |
| 4 | Kolay yapı için adım adım fotoğraflı montaj rehberi | 🔴🔴 | 🟢 |
| 5 | Gerber üret ve `hardware/pcb/gerbers/` altına koy | 🔴🔴 | 🟡 |
| 6 | GitHub Actions ile firmware derleme kontrolü | 🔴 | 🟢 |

> **Kalan 13 pin en yüksek etkili katkıdır.** Üç datasheet (USB-C receptacle,
> USBLC6-2SC6, Si1308EDL) okumak yeterli ve ardından netlist doğrudan pcbnew'e
> import edilebilir hale gelir. `python3 gen_netlist.py --check` hangilerinin
> kaldığını listeler.

| 1b | **BUSY polaritesini ölçerek doğrula** (30 saniyelik iş, `firmware/README.md`) ve `config.h` içindeki `EPD_BUSY_ACTIVE_HIGH` değerini sabitle | 🔴🔴🔴 | 🟢 |
| 1c | **Panelin harici boost devresini breadboard'da kur ve doğrula** — ya da adaptör kartıyla çalıştığını göster | 🔴🔴🔴 | 🟡 |

### v1.2 — Okuma deneyimi

| # | Madde | Etki | Zorluk |
|---|---|---|---|
| 7 | **Türkçe heceleme ile kelime bölme** (satır sonunda `kitap-` / `lar`) | 🔴🔴 | 🟡 |
| 8 | İçindekiler ekranı ve bölüm atlama | 🔴🔴 | 🟡 |
| 9 | Okuma konumunu kitap başına kaydetme (şu an tek konum) | 🔴🔴 | 🟢 |
| 10 | Ayraç (bookmark) koyma | 🔴 | 🟡 |
| 11 | Okuma ilerlemesi göstergesi çubuğu (şu an sadece %) | 🔴 | 🟢 |
| 12 | Uyku süresini kullanıcı davranışına göre uyarlama | 🔴 | 🟢 |
| 13 | Hızlı sayfa atlama (butonu basılı tutunca 10 sayfa) | 🔴🔴 | 🟢 |
| 14 | Yazı tipi değiştirme (menüden birden fazla `.epf`) | 🔴 | 🟡 |
| 15 | Kenar boşlukları ve satır aralığı ayarı | 🔴 | 🟢 |

### v1.3 — Güç

| # | Madde | Etki | Zorluk |
|---|---|---|---|
| 16 | **TPS63900 düşük güç varyantını tamamla** (yapılandırma direnci + pinout kontrolü, `docs/07` §3) | 🔴🔴🔴 | 🟡 |
| 17 | Bölücüyü 1 MΩ/1 MΩ yap (19 µA kazanç) | 🔴🔴 | 🟢 |
| 18 | Bölücüyü MOSFET ile uykuda tamamen kes | 🔴🔴 | 🟡 |
| 19 | Uyanma süresini ölç ve kısalt | 🔴🔴 | 🟡 |
| 20 | Uyku akımı ölçüm scripti / test yöntemi standardı | 🔴 | 🟢 |

### v1.4 — İçerik ve aktarım

| # | Madde | Etki | Zorluk |
|---|---|---|---|
| 21 | **Kobo/Kindle kitaplığından doğrudan içe aktarma** (Calibre eklentisi) | 🔴🔴🔴 | 🟡 |
| 22 | Calibre eklentisi (`epub2epr` entegre) | 🔴🔴🔴 | 🟡 |
| 23 | Kablosuz yükleme sırasında ilerleme çubuğunu ekranda gösterme | 🔴 | 🟢 |
| 24 | Cihazdan kitap indirme (yedekleme) | 🔴 | 🟢 |
| 25 | Zamanlanmış otomatik yükleme (kitaplık klasörünü izle) | 🔴 | 🟡 |
| 26 | OPDS kataloğu desteği (Kavita/Calibre-Web'den doğrudan indirme) | 🔴🔴 | 🔴 |
### Doğrulama sırasında bulunan ve düzeltilen hatalar

Bu depo hazırlanırken ilk tasarımda **on iki hata** bulundu ve düzeltildi.
Hiçbiri gerçek donanımda değil. Üç grupta toplanıyorlar ve kayıt olarak burada
duruyorlar.

**Altısı, hiç sorgulanmamış varsayımların karşısına resmî datasheet'ler
konarak** bulundu:

| Bulgu | İlk tasarım | Doğrusu |
|---|---|---|
| TPS63020 paketi | VSON-10 | **VSON-14 (DSJ), 3×4 mm** |
| TPS63900 uyumluluğu | "pin uyumlu" | **Uyumlu değil**, layout değişir |
| Geri besleme dirençleri | 560k / 100k | **1 MΩ / 180 kΩ** (datasheet Table 3) |
| GPIO8 strapping | Açılışta HIGH şart | **SPI boot'ta serbest** (Table 4-3) |
| Panel beslemesi | Yalnızca 3.3 V + kondansatör | **Ayrıca harici ±15 V boost şart** (GDR/RESE) |
| Panel BUSY polaritesi | HIGH = boşta | **Datasheet: HIGH = meşgul** — yapılandırılabilir yapıldı |

**Dördü, yerleşim verisinin etrafına yazılan doğrulayıcılardan** çıktı. Bir
parçanın montaj deliğiyle çakışması ya da kendi kasasına sığmaması şemada
görünmez:

| Bulgu | Yol açacağı belirti | Düzeltme |
|---|---|---|
| Gövde ölçüsü | Kasa 58 × 30 mm'ydi; panelin **camı 59.2 × 29.2 mm** ve o kasaya monte edilemez | **62 × 32 mm**, camdan türetilir: cam + 2 × 1.4 mm çerçeve |
| FPC kanalı yanlış kasa kenarında | Kasa şerit kanalını −Y'ye açmıştı, oysa J2 kartın +Y kenarında; kablo tüm kartı dolanmak zorundaydı | Kanal +Y'ye taşındı. Çizim üretecinin geometri denetimi yakaladı |
| Montaj delikleri ile mahfazalar | Dört M1.6 deliği `BT1`, `SW4`, `R13` ve `R15` mahfazalarının üstüne biniyordu | Delik bölgeleri artık koruma alanı; yerleştirici oraya parça koymuyor |
| Butonlar sığmıyordu | İki delik arasında kalan 15 mm'ye üç adet 5 mm buton sığmaz | Butonlar 4.5 mm'ye indirildi ve yeniden aralandı |

**Ve ikisi entegrasyon testlerinden** çıktı — ikisi de sessiz hata: cihazın
açılmasını engellemezler, ama sonucu bozarlar:

| Bulgu | Belirti | Düzeltme |
|---|---|---|
| `.epr` dönüştürücü **her paragraf sonunu siliyordu** | Dönüştürülen her kitap tek bir uzun paragraf olarak görünürdü | `add_block` içindeki koşulsuz kırpma yalnızca bölüm açılışına indirildi + 6 regresyon testi |
| `.epf` `top` alanının referans noktası iki tarafta **farklıydı** | Firmware `top`'u taban çizgisinden sanıyordu; hata glyph başına değiştiği için **metin dikey olarak dağılırdı** | `y0 = baseline_y - (ascent - top) * scale`; `tools/tests/test_epf_interop.py` iki yarıyı sınır genişliklerle karşılaştırıyor |
### v2.0 — Fikir aşamasında

| Fikir | Not |
|---|---|
| 2.9&quot; 296×128 panel desteği | Aynı kod, farklı panel profili. Daha okunur, ~2× fiyat, gövde 69 × 32 mm |
| Dokunmatik | Panel katmanı panelden pahalı; muhtemelen değmez |
| Ön ışık | Bu boyutta hazır çözüm yok; özel ışık kılavuzu gerekir |
| Kızılötesi/Bluetooth sayfa çevirme kumandası | BLE ile kolay |
| Çok dilli arayüz | `i18n.h` zaten tablo yapısında; çeviri PR'ı yeterli |
| Kısmi güncellemede gri tonlama (4 seviye) | SSD1680 destekler ama LUT gerekir; hayaletlenme riski |
| Uygulama (Android/iOS) ile eşleştirme | BLE GATT üzerinden dosya transferi |
| Solar şarj | Küçük panel + BQ25570 |

---

## Katkı vermek

### En kolay başlangıçlar

1. **Bir pin numarasını doğrula** — `pinouts.md`'den bir `UNVERIFIED` maddesi
   seç, datasheet'ten bak, `gen_netlist.py`'ye işle, PR gönder. Tek başına
   5 dakikalık iş.
2. **Kendi montajınızı fotoğrafla** — `docs/04`'e adım adım fotoğraf ekle.
3. **Bir yazı tipiyle test et** — `fontgen.py` ile farklı bir font üretip
   `--preview` çıktısını issue'ya ekle. Hangi font 14 px'te en okunur, birlikte
   karar verelim.
4. **Bir kitap dönüştür** — `epub2epr.py` bir EPUB'da başarısız olursa
   (nadir ama olur) dönüştürücüyü düzelt.
5. **Hata mesajlarını iyileştir** — hata mesajları yalnızca geliştiriciye
   anlamlıysa, kullanıcıya anlamlı hale getir.

### Katkı kuralları

- Firmware kodu **İngilizce** tanımlayıcı ve yorum; kullanıcıya görünen metinler
  `i18n.h` üzerinden Türkçe/İngilizce
- Dokümanlar Türkçe (İngilizce sürümler `*.en.md`)
- Bir donanım değişikliği yaparsanız `gen_netlist.py`'yi güncelleyip
  `python3 gen_netlist.py --check` çalıştırın — çıktılar (CSV + netlist) bu
  script'ten üretilir, elle düzenlenmez
- Bir sayı iddia ediyorsanız ya ölçün ya da "hesaplama" olduğunu yazın

Ayrıntı: [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## Teşekkürler

Bu proje şu açık kaynak çalışmalara dayanır:

- **Waveshare e-Paper** (MIT) — SSD1680 init dizisi ve kısmi yenileme LUT
  tabloları, satıcının referans sürücüsünden aynen alınmıştır
- **Espressif ESP-IDF / Arduino core** — ESP32-C3 desteği
- **GoodDisplay** — panel spesifikasyonları
- **Adafruit GFX** — Canvas API'sinin tasarımı bu arayüzden esinlenmiştir
- **Bitstream Vera / DejaVu** ve **SIL OFL** font aileleri — test fontları

---

Geri: [08 · Sorun Giderme](08-troubleshooting.tr.md) · [Başa dön](../README.md)
