# Pocket Reader — Host Araçları

Bu klasör, EPUB kitaplarını cihazın okuduğu `.epr` biçimine çeviren, cihaz için
`.epf` bitmap font üreten ve üretilen dosyaları kablosuz ağ üzerinden cihaza
yükleyen araçları içerir.

Cihazın kendisi **hiçbir zaman** EPUB, TrueType ya da satır kaydırma motoru
çalıştırmaz. Her şey burada, bilgisayarda önceden hazırlanır; cihaz yalnızca
hazır bit haritalarını ekrana basar. Bu yüzden ESP32-C3 üzerinde kitap
değiştirmek, sayfa çevirmek ve pil ömrü inanılmaz derecede ucuzdur.

---

## 1. Scriptler

| Script | Ne yapar | Bağımlılık |
|---|---|---|
| `epub2epr.py` | EPUB 2/3 → `.epr` kitap dönüştürücü. İçindekileri de taşır. | **Yok** (saf Python 3.9+) |
| `fontgen.py` | TTF/OTF → `.epf` bitmap font üreteci. | `Pillow>=10.0` |
| `send.py` | Cihaza yükleme, listeleme, silme, Wi-Fi tanımlama, durum okuma. | **Yok** |
| `make_sample_books.py` | `examples/` içine yüklemeye hazır örnek `.epr` dosyaları üretir. | **Yok** |
| `gen_placement.py` | PCB yerleşim verisi — tüm 2B ve 3B çizimlerin üretildiği tek kaynak. | **Yok** |
| `gen_pcb_layout.py` | `placement.csv` dosyasından 2B teknik resimleri üretir. | **Yok** |
| `build_site.py` | `site/template.html` şablonunu dil dosyalarıyla doldurup tek dosyalık `site/index.html` (EN) ve `site/index.tr.html` (TR) üretir. | **Yok** (ilk derleme Three.js'i indirir) |
| `tests/make_tiny_epub.py` | Testler için minik, geçerli bir EPUB zip'i yazar. | **Yok** |
| `tests/test_epr_roundtrip.py` | `.epr` biçiminin ve dönüştürücünün testleri. | **Yok** |

Yani kitap çevirip cihaza yüklemek için **hiçbir ek paket kurmanız gerekmez**;
Pillow'a yalnızca kendi fontunuzu üretmek isterseniz ihtiyaç duyarsınız.

---

## 2. Kurulum

```bash
cd tools
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Aktifleştirip doğrudan da kullanabilirsiniz:

```bash
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python epub2epr.py --help
```

`epub2epr.py`, `send.py` ve `make_sample_books.py` sanal ortam olmadan da
çalışır (sistem Python'u ile):

```bash
python3 make_sample_books.py
python3 send.py --list
```

Testler:

```bash
cd tools
python3 -m unittest discover -s tests -v
```

---

## 3. İlk açılışta tam iş akışı

Cihazı ilk kez kuruyorsanız sırayla şunları yapın.

### Adım 0 — Örnek kitapları üretin ve deneyin

Kendi fontunuzu üretmeden önce elinizde çalışan bir şey olsun:

```bash
cd tools
python3 make_sample_books.py
#   ornek-turkce.epr      ... bayt  ... bölüm  ... paragraf  ... TOC kaydı
#   sample-english.epr    ...
#   stress-test.epr       ...
```

Bu üç dosya geçerlidir; `epub2epr.read_epr()` ile ve ham bayt seviyesinde
denetlenir.

### Adım 1 — Fontu üretin (`.epf`)

Cihazın yazı tipi yoksa hiçbir şey okuyamazsınız. Türkçe destekli bir font seçin
(aşağıdaki "Hangi fontu kullanmalıyım?" bölümüne bakın):

```bash
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    --size 16 \
    --out ../firmware/data/fonts/reader-16.epf \
    --preview onizleme.png
```

`onizleme.png` dosyasını açıp çıkan yazıya bakın: Türkçe harfler (ç ğ ı İ ö ş ü)
bozuk/boş çıkıyorsa font uygun değil ya da `--ranges` listesinde eksik aralık
var demektir.

### Adım 2 — Fontu cihaza yazın (dosya sistemi yüklemesi)

`firmware/data/` klasörünün tamamı cihazın LittleFS bölümüne gider:

```bash
cd ../firmware
pio run --target uploadfs
```

(Bu adım firmware tarafına aittir; ayrıntısı `firmware/README.md` içinde.)

### Adım 3 — Bir kitabı çevirin

```bash
cd ../tools
python3 epub2epr.py ~/kitaplar/suç-ve-ceza.epub \
    -o sicve.epr --verify --verbose
```

`--verify` yazılan dosyayı hemen geri okuyup karşılaştırır; kısaca
"OK" görüyorsanız dosya sağlamdır.

### Adım 4 — Cihaza yükleyin

```bash
python3 send.py sicve.epr
```

Cihaz açık ve aynı Wi-Fi ağındaysa dosya `/books/` klasörüne düşer ve cihaz
ekranındaki kitap listesinde görünür.

---

## 4. `epub2epr.py` — Kitap dönüştürücü

EPUB'ın `<spine>` sırasını korur; içindekiler tablosunu EPUB 3 `nav` belgesinden,
bulamazsa EPUB 2 `toc.ncx`'ten okur. HTML'i küçük bir durum makinesiyle temizler:
`<p>`, `<div>`, `<br>`, `<li>`, `<h1>`–`<h6>`, `<blockquote>`, `<pre>` yeni
paragraf açar; `<h1>`–`<h6>` ayrıca **yeni sayfa** başlatır; `<script>`,
`<style>` ve `<head>` içeriği atılır; `<img>` → `[resim]`; `&amp;` ve `&#351;`
gibi varlıklar çözülür; yumuşak tire ve zero-width karakterler silinir; metin
NFC ile birleştirilir (böylece `o` + birleşen iki nokta tek bir `ö` olur).

> **Önemli:** Dönüştürücü metne **satır sonu eklemez**. Satır kaydırma cihazda
> yapılır; metne yalnızca iki kontrol baytı girer: `0x0A` (paragraf) ve `0x0B`
> (bölüm/yeni sayfa).

| Bayrak | Açıklama |
|---|---|
| `input` | Kaynak `.epub` dosyası (zorunlu). `--dump` ile birlikte bir `.epr` de olabilir. |
| `-o`, `--output` | Çıktı `.epr` yolu. Varsayılan: girdi adı `.epr` uzantısıyla. |
| `--title` | Kitap başlığını geçersiz kılar (EPUB metadata'sı yok sayılır). |
| `--author` | Yazar adını geçersiz kılar. |
| `--lang` | Dil kodunu geçersiz kılar (örn. `tr`). |
| `--no-toc` | İçindekiler tablosunu üretmez; dosya biraz küçülür. |
| `--strip-diacritics` | Aksanları düşürür: `İ→I`, `ı→i`, `ş→s`, `ğ→g`, `ç→c`, `ö→o`, `ü→u`. **Yalnızca** Türkçe glifi olmayan bir font kullanmak zorunda kaldığınızda gerekir; `ş`/`s` ve `ı`/`i` ayrımı kaybolur, arama ve kesme davranışı bozulur. |
| `--verify` | Yazdıktan sonra dosyayı `read_epr()` ile geri okuyup doğrular. |
| `--dump` | Dönüştürmez; var olan bir `.epr` dosyasının header'ını, içindekilerini ve metninin ilk 500 karakterini yazdırır. |
| `-v`, `--verbose` | Paragraf/bölüm/bayt istatistiklerini basar. |

Örnekler:

```bash
# Basit dönüşüm
python3 epub2epr.py kitap.epub

# Başlığı düzeltip doğrula
python3 epub2epr.py kitap.epub --title "Kürk Mantolu Madonna" --author "Sabahattin Ali" --verify

# Bozuk bir dosyayı incele
python3 epub2epr.py kitap.epr --dump
```

### `.epr` biçimi (özet)

```
0  : "EPR1"            4 bayt sihirli sayı
4  : uint16 sürüm = 1
6  : uint16 bayraklar    bit0 = içindekiler var
8  : uint32 text_offset   metin bloğunun başlangıcı
12 : uint32 text_length   metin bloğunun uzunluğu
16 : uint32 toc_offset    içindekiler bloğu (bayrak kapalıysa 0)
20 : uint32 toc_count
24 : uint8 title_len  + başlık  (UTF-8)
     uint8 author_len + yazar   (UTF-8)
     uint8 lang_len   + dil     (ASCII, örn. "tr")
     uint8 encoding   (0 = UTF-8)
     ... text_offset'e kadar sıfır dolgu

metin bloğu : 0x0A = paragraf sonu, 0x0B = bölüm başı (yeni sayfa)
içindekiler : toc_count × { uint32 text_pos; uint8 len; char title[len] }
```

### İki sözleşme (firmware yazanlar için önemli)

1. **TOC konumu metnin İLK BAYTINI gösterir.** Bölüm başı baytı (`0x0B`) hemen
   ondan önce durur; yani ofset 0 hariç `text[text_pos - 1] == 0x0B` olur.
   Konum bir **bayt** ofsetidir — çözülmüş metni `str` olarak indekslemeyin,
   çok baytlı karakterler yüzünden kayar.
2. **Kitabın ilk bloğu bölüm başıysa `0x0B` yazılmaz.** Ofset 0 zaten ilk
   sayfanın başıdır; fazladan bir bayt boş sayfa açtırabilir. Bu yüzden:

   ```
   bölüm sayısı = toc_count = 0x0B sayısı + 1
   ```

   `--dump` ve `make_sample_books.py` bu yüzden ikisini ayrı ayrı yazar
   ("3 bölüm / 2 bölüm sonu (0x0B)").

---

## 5. `fontgen.py` — Bitmap font üreteci

| Bayrak | Açıklama |
|---|---|
| `font` | Kaynak `.ttf` / `.otf` dosyası (zorunlu). |
| `--size` | Piksel cinsinden yazı boyutu (varsayılan `14`). |
| `--out` | Yazılacak `.epf` dosyası (**zorunlu**). |
| `--ranges` | Dahil edilecek kod noktası aralıkları, virgülle ayrılmış adlar. Varsayılan: `ascii,latin1,latin-ext,turkish,punct`. |
| `--line-spacing` | Satır arası ek boşluk (px). Satır adımı = `height + line_spacing` (varsayılan `2`). |
| `--extra-codepoints` | Listeye eklenecek ekstra karakterler, örn. `--extra-codepoints "₺≥×"`. |
| `--preview` | Örnek Türkçe paragrafı bu PNG dosyasına çizer. |
| `--preview-width` | Önizleme genişliği, px (varsayılan `250` = cihaz ekranı genişliği). |
| `--json` | Yardımcı metrik JSON'unun yolu (varsayılan: `<out>.json`). |
| `--no-json` | Yardımcı JSON dosyasını yazmaz. |
| `-v`, `--verbose` | İlk gliflerin metrik tablosunu basar. |

### Aralık adları

| Ad | Kapsam |
|---|---|
| `ascii` | U+0020–U+007E (temel Latin + rakamlar + noktalama) |
| `latin1` | U+00A0–U+00FF (Latin-1 Supplement) |
| `latin-ext` | U+0100–U+017F (Latin Extended-A) |
| `turkish` | Ğ ğ İ ı Ş ş (U+011E/011F, U+0130/0131, U+015E/015F) |
| `punct` | Tırnaklar, tire çeşitleri, `…`, `•`, `™`, `−`, para birimi işaretleri |
| `digits` | Yalnızca 0–9 |
| `currency` | ¢ £ ¤ ¥ € ₺ ₨ |
| `greek` | U+0384–U+03CE |
| `cyrillic` | U+0400–U+045F |
| `all` | Yukarıdakilerin tamamı |

```bash
# Varsayılan Türkçe kurulum
python3 fontgen.py DejaVuSans.ttf --size 16 --out reader-16.epf --preview onizleme.png

# Küçük ekranda daha fazla satır için 12 px
python3 fontgen.py DejaVuSans.ttf --size 12 --out reader-12.epf --line-spacing 1

# Sadece rakam ve noktalama gerekiyorsa (çok küçük dosya)
python3 fontgen.py font.ttf --size 14 --ranges digits,ascii --out mini.epf
```

### Çıkan dosyalar

* `reader-16.epf` — cihazın okuduğu ikili dosya.
* `reader-16.json` — aynı fontun metrikleri; firmware tarafında elle ayıklama
  için (glif başına `advance`, `left`, `width`, `height`, `top`).

### `.epf` biçimi (özet)

```
header (12 bayt): "EPF1"; uint8 sürüm=1; uint8 height; int8 ascent;
                  int8 descent; uint8 line_spacing; uint8 reserved;
                  uint16 glyph_count
glif  (10 bayt) : uint32 codepoint; int8 advance; int8 left; uint8 width;
                  uint8 height; uint8 top; uint8 reserved
                  + ceil(width*height/8) bayt bit haritası
```

Bit haritası **satır dolgusu olmadan, kesintisiz MSB-first bir bit akışıdır**:
`N = y*width + x` biti, `N >> 3` indeksli baytın `0x80 >> (N & 7)` maskesine
karşılık gelir. `descent` **pozitiftir** ve `height == ascent + descent` olur.

**`top` kuralı (iki yarının sessizce ayrıştığı tek varsayım — dikkat):**
`top`, glif kutusunun **tepesinden** (ascender çizgisinden) ölçülür, baseline'dan
değil. Baseline, hücre tepesinin `ascent` piksel altındadır; bu yüzden çizim
kodu mürekkebin üst kenarını

```
y0 = baseline_y - (ascent - top) * scale
```

ile bulmalıdır — `baseline_y - top` **yanlıştır**. Hata sabit bir kayma
değildir: glif başına değiştiği için metin düşey olarak dağınık çizilir ve
glifler komşu satırlara taşar (ölçüm tablosu:
`tools/tests/test_epf_interop.py::test_top_origin_matches_firmware_renderer`).
Aynı test bu kuralı, `firmware/src/font.cpp`'nin kaynağını okuyarak regresyon
koruması altında tutar.

---

## 6. `send.py` — Yükleyici ve cihaz yöneticisi

Cihaz `http://pocketreader.local/` adresinde (mDNS) aranır. Bulunamazsa
`--ip <adres>` ile cihazın **ekranında yazan IP** adresini verin.

| Bayrak | Açıklama |
|---|---|
| `file` | Yüklenecek `.epr` (ya da `.epub`; otomatik çevrilir). |
| `--host` | Cihaz adresi (varsayılan `pocketreader.local`). |
| `--ip` | Cihazın ekranındaki IP; `--host` yerine geçer. |
| `--port` | TCP portu (varsayılan `80`). |
| `--timeout` | Saniye cinsinden zaman aşımı (varsayılan `30`). |
| `--list` | Cihazdaki kitapları tablo hâlinde listeler. |
| `--rm AD` | Cihazdan bir kitabı siler. |
| `--wifi SSID SIFRE` | Wi-Fi bilgilerini NVS'e kaydeder. |
| `--status` | Firmware sürümü, pil, boş bellek ve çalışma süresini gösterir. |
| `--reboot` | Cihazı yeniden başlatır. Firmware bu uç noktayı desteklemiyorsa (404) anlaşılır bir uyarı verir. |
| `--json` | `--list` / `--status` çıktısını ham JSON olarak basar (betikler için). |
| `--dir KLASOR` | Klasördeki **tüm** `.epub` dosyalarını sırayla çevirip yükler. |
| `--out-dir KLASOR` | Toplu çevrimde üretilen `.epr` dosyalarının yazılacağı klasör. |
| `--keep` | Toplu çevrimde ara `.epr` dosyalarını silmez. |
| `--watch` | Dosya diskte değiştikçe yeniden yükler (mtime yoklaması). `.epub` izleniyorsa her değişimde yeniden çevirir. |
| `--watch-interval` | Yoklama aralığı, saniye (varsayılan `2.0`). |
| `--yes` | Silme onayını sormaz. |
| `--force` | Büyük dosya uyarısını yok sayar. |
| `--max-upload BAYT` | Uyarı eşiği (varsayılan 8 MiB). |
| `-v`, `--verbose` | Ayrıntılı çıktı. |

Örnekler:

```bash
python3 send.py kitap.epr                       # yükle
python3 send.py kitap.epr --ip 192.168.1.42     # mDNS çalışmıyorsa
python3 send.py --list                          # kitapları listele
python3 send.py --status                        # pil / bellek / uptime
python3 send.py --status --json | jq .batt_pct  # betiklerde kullanım
python3 send.py --rm eski.epr --yes             # onay sormadan sil
python3 send.py --wifi EvimAgi sifre123         # Wi-Fi kaydet
python3 send.py --dir ~/kitaplar/ -v            # klasörün tamamını çevir+yükle
python3 send.py kitap.epub --watch              # düzenlerken otomatik yükle
```

### Tipik hatalar ve anlamları

| Mesaj | Ne yapmalı |
|---|---|
| `'pocketreader.local' çözümlenemedi` | mDNS çalışmıyor. Cihazın ekranındaki IP'yi `--ip` ile verin. |
| `Bağlantı reddedildi` | Cihaz uyuyor. Güç düğmesine basıp ekranda bir sayfa görene kadar bekleyin. |
| `Zaman aşımı` | Cihaz ekranı yeniliyor olabilir; birkaç saniye sonra tekrar deneyin. |
| `404 — /upload bu yok` | Firmware eski. Cihazın web sayfasını tarayıcıda açıp deneyin. |
| `Dosya cihaz için çok büyük` | Cihazda yer yok. Gereksiz kitapları `--rm` ile silin. |

---

## 7. `make_sample_books.py` — Örnek kitaplar

| Bayrak | Açıklama |
|---|---|
| `--out-dir KLASOR` | Çıktı klasörü (varsayılan: depo kökündeki `examples/`). |
| `--stress-kb KiB` | Stres testi boyutu (varsayılan `200`). |
| `--stress-chapters N` | Stres testi bölüm sayısı (varsayılan `40`). |
| `--seed N` | Rastgelelik tohumu; aynı tohum her zaman aynı dosyayı üretir (varsayılan `1337`). |
| `-v`, `--verbose` | Header/metin boyutlarını da basar. |

Üretilenler:

* `ornek-turkce.epr` — 3 bölümlük özgün Türkçe metin, tüm Türkçe harfleri içerir.
* `sample-english.epr` — 2 bölümlük özgün İngilizce metin.
* `stress-test.epr` — ~200 KB, 40 bölüm. Sayfalama ve sayfa indeksi önbelleğini
  zorlamak için idealdir; cihazın yavaşladığı yeri bulmakta kullanılır.

Her dosya yazılmadan önce `epub2epr.read_epr()` ile geri okunur ve ham bayt
seviyesinde (sihirli sayı, sürüm, offset'ler, TOC kayıtları, `\r` yasağı)
denetlenir.

---

## 8. Hangi fontu kullanmalıyım?

Cihazda **Türkçe harflerin tamamı** (Ç ç Ğ ğ İ ı Ö ö Ş ş Ü ü) bulunmalıdır.
Aksi hâlde ya harfler boş çıkar ya da `--strip-diacritics` kullanıp anlamı
bozmak zorunda kalırsınız. Önerilen iki font:

### DejaVu Sans (önerilen)

* **Lisans:** Bitstream Vera Fonts Copyright + DejaVu değişiklikleri.
  Serbest yazılım; ticari kullanım, değiştirme ve yeniden dağıtım serbesttir.
  Adı değiştirilmiş sürümlerde "DejaVu" adının kullanımı kısıtlanır
  (ayrıntı: `dejavu-fonts-ttf-2.37/LICENSE`).
* **Neden:** Tam Türkçe kapsamı, çok iyi okunabilirlik, hemen her Linux
  dağıtımında kurulu gelir, 12–18 px aralığında net piksel sonucu verir.
* **İndirme:**
  * Resmî site: <https://dejavu-fonts.github.io/>
  * Sürümler: <https://github.com/dejavu-fonts/dejavu-fonts/releases>
  * Debian/Ubuntu: `sudo apt install fonts-dejavu-core`
    → `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
  * Fedora: `sudo dnf install dejavu-sans-fonts`
    → `/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf`
  * macOS: `brew install --cask font-dejavu`

```bash
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    --size 16 --out ../firmware/data/fonts/reader-16.epf --preview onizleme.png
```

### Noto Sans

* **Lisans:** SIL Open Font License 1.1 (OFL). Serbestçe kullanılabilir,
  değiştirilebilir ve gömülebilir; font dosyası tek başına satılamaz ve
  adı değiştirilen sürümler yeniden adlandırılmalıdır.
* **Neden:** Google'ın kapsamlı font ailesi; Türkçe dahil Latin kapsamı tam,
  ekran için tasarlanmış, DejaVu'dan biraz daha ince/kibar görünür.
* **İndirme:**
  * Google Fonts: <https://fonts.google.com/noto/specimen/Noto+Sans>
    (indirme: <https://fonts.google.com/download?family=Noto%20Sans>)
  * Kaynak deposu: <https://github.com/notofonts/latin-greek-cyrillic/releases>
  * Debian/Ubuntu: `sudo apt install fonts-noto-core`
    → `/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf`
  * macOS: `brew install --cask font-noto-sans`

### Boyut seçimi

Cihazın ekranı 250 × 122 pikseldir. Kabaca:

| `--size` | Satır yüksekliği | Ekrana sığan satır | Not |
|---|---|---|---|
| 12 px | ~14 px | ~8 satır | çok küçük, `--line-spacing 1` deneyin |
| 14 px | ~16 px | ~7 satır | varsayılan, dengeli |
| 16 px | ~18 px | ~6 satır | **önerilen** |
| 18 px | ~21 px | ~5 satır | büyük harfler, az metin |

Karar vermek için `--preview` ile PNG üretip gözle bakın; cihazın çizimi ile
birebir aynıdır (önizleme, `.epf` bit haritalarından çizilir).

---

## 9. Sorun giderme

**Dosya yüklendi ama cihazda görünmüyor.**
`send.py --list` ile cihazın gerçekten gördüğünü doğrulayın. Görünüyorsa
dosya adı çok uzun olabilir ya da cihaz listeyi yeniden çizmiyor olabilir;
sayfa değiştirip geri dönün.

**Türkçe harfler kutu/boş çıkıyor.**
Fontta o kod noktası yok. `python3 fontgen.py ... --ranges all` ile üretip
tekrar deneyin, ya da DejaVu/Noto kullanın. `reader-16.json` dosyasını açıp
`U+011E` (Ğ) gibi kod noktalarının listede olup olmadığına bakabilirsiniz.

**Kitap açılıyor ama içindekiler boş.**
EPUB'da ne `nav` belgesi ne `toc.ncx` vardır. `--dump` ile `toc_count` alanına
bakın; sorun yoksa cihaz bölüm başı baytlarını (`0x0B`) bulamıyor olabilir.

**`--dump` çıktısındaki metin bozuk görünüyor.**
`0x0A` ve `0x0B` baytları `¶` ve `§` olarak gösterilir; bunlar bozukluk değil,
paragraf ve bölüm işaretleridir.

**Çok büyük kitap yavaş açılıyor.**
`--no-toc` ile içindekileri kaldırmayı deneyin, ya da kitabı `epub2epr.py` ile
parçalara bölün (her dosya ayrı bir kitap olur).
