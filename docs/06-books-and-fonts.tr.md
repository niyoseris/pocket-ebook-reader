> English version: [06-books-and-fonts.md](06-books-and-fonts.md)

# 06 · Kitap ve Font Dönüştürme

Cihaz EPUB okumaz. Kitaplar bilgisayarda bir kez dönüştürülür, cihaz yalnızca
düz metin görür. Bu bilinçli bir karardır — gerekçesi `docs/00` §5'te.

```
kitap.epub  ──epub2epr.py──>  kitap.epr  ──send.py / tarayıcı──>  cihaz
font.ttf    ──fontgen.py───>  reader.epf ──uploadfs──────────────>  cihaz
```

---

## 1 · Kurulum

```bash
cd tools
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`epub2epr.py`, `send.py` ve `make_sample_books.py` **hiçbir harici paket
kullanmaz** (yalnızca Python standart kütüphanesi). `fontgen.py` Pillow
gerektirir. Yani `pip install` adımını atlasanız bile kitap dönüştürebilir ve
yükleyebilirsiniz — sadece font üretemezsiniz.

---

## 2 · Font üretmek

### 2.1 Font seçimi

Cihazın ekranı 250 × 122 piksel ve 14 px fontla sayfa başına ~7 satır metin
alır. Bu boyutta **harf biçimi okunabilirliği belirler.**

| Font | Lisans | Neden |
|---|---|---|
| **Atkinson Hyperlegible** | SIL OFL 1.1 | Görme zorluğu çekenler için tasarlandı; `I/l/1` ve `O/0` ayrımı çok net. **Küçük ekranda en iyi seçim** |
| **DejaVu Sans** | Bitstream Vera (izin verici) | Neredeyse tüm Linux dağıtımlarında hazır. Türkçe tam kapsama |
| **Noto Sans / Noto Serif** | SIL OFL 1.1 | Çok geniş kapsama, Google Fonts'tan indirilebilir |
| **Bitter** | SIL OFL 1.1 | E-mürekkep için tasarlanmış bir slab serif |
| **Liberation Sans** | SIL OFL 1.1 | Arial ölçülerinde, uyumlu |

> **Kaçınılacaklar:** Çok ince çizgili (light/thin) fontlar 1-bit e-mürekep
> ekranda kaybolur; el yazısı ve dekoratif fontlar 14 px'te okunmaz.

Linux'ta DejaVu hazır gelir:

```bash
ls /usr/share/fonts/truetype/dejavu/
# DejaVuSans.ttf  DejaVuSans-Bold.ttf  ...
```

Atkinson Hyperlegible'ı indirmek için:
<https://www.brailleinstitute.org/freefont/>

### 2.2 Font üretmek

```bash
python3 fontgen.py DejaVuSans.ttf --size 14 \
        --out ../firmware/data/fonts/reader-14.epf \
        --preview /tmp/onizleme.png
```

| Bayrak | Anlamı |
|---|---|
| `--size N` | Piksel yüksekliği. Ekranda 14 iyi bir denge, 20 büyük yazı |
| `--out DOSYA` | Çıktı `.epf` dosyası |
| `--ranges a,b,c` | Kapsanacak karakter aralıkları. Hazır kümelere: `ascii latin1 latin-ext turkish punct digits currency greek cyrillic all`. Varsayılan: `ascii,latin1,latin-ext,turkish,punct` |
| `--line-spacing N` | Satırlar arası ek piksel (varsayılan 2) |
| `--extra-codepoints "₺"` | Kümelerde olmayan tek tek karakterler (ör. para birimi simgesi) |
| `--preview PNG` | Türkçe örnek paragraf içeren önizleme görüntüsü |
| `--preview-width N` | Önizleme genişliği (varsayılan 250 — ekranla aynı) |
| `--json P` / `--no-json` | Ölçülerle birlikte yan dosya yazar (hata ayıklama için) |

Tam liste için: `python3 fontgen.py --help`

`--preview` dosyasını açıp **ç ğ ı İ ö ş ü** harflerinin doğru göründüğünü
mutlaka kontrol edin. Bir fontta bu karakterler eksikse cihaz onların yerine
boşluk gösterir ve metin anlamsızlaşır.

Önerilen üç font üretin:

```bash
python3 fontgen.py DejaVuSans.ttf --size 12 --out ../firmware/data/fonts/reader-12.epf
python3 fontgen.py DejaVuSans.ttf --size 14 --out ../firmware/data/fonts/reader-14.epf
python3 fontgen.py DejaVuSans.ttf --size 18 --out ../firmware/data/fonts/reader-18.epf
```

Cihaz menüsündeki "Yazı boyutu" ayarı bu dosyalar arasında geçiş yapar.

### 2.3 `.epf` biçimi (v1)

Little-endian, dolgu yok:

```
başlık (12 bayt):
  char[4]  sihirli sayı = "EPF1"
  uint8    sürüm = 1
  uint8    yükseklik        (font kutusunun piksel yüksekliği)
  int8     ascent           (kutu üstünden taban çizgisine)
  int8     descent          (POZİTİF saklanır; yükseklik = ascent + descent)
  uint8    satır_aralığı    (satırlar arası ek piksel)
  uint8    ayrılmış = 0
  uint16   glyph_sayısı

her glyph (10 baytlık sabit başlık + bitmap):
  uint32   kod_noktası      (UTF-8 çözülmüş Unicode değeri)
  int8     advance          (kalemin ilerleyeceği piksel)
  int8     left             (çizerken x ofseti)
  uint8    genişlik         (bitmap genişliği, piksel)
  uint8    yükseklik        (bitmap yüksekliği, piksel)
  uint8    top              (satır kutusunun ÜSTÜNDEN bitmap'in y ofseti)
  uint8    ayrılmış = 0
  uint8[]  bitmap           (aşağıdaki kurala göre)
```

> ⚠️ **Bitmap SÜREKLİ bir bit akışıdır — satırlar bayta hizalanmaz.**
> Uzunluk `ceil(genişlik × yükseklik / 8)` bayttır (satır başına dolgu yok).
> Bit `N = y × genişlik + x` → bayt `N >> 3`, maske `0x80 >> (N & 7)`.
>
> Neden önemli: `ceil(genişlik × yükseklik / 8)` ile satır dolgulu okuma
> (`ceil(genişlik/8) × yükseklik`) **8 pikselden geniş her glyph'te** farklı
> sonuç verir. Örneğin 9 × 3 piksellik bir glyph akışta 4 bayt, dolgulu okumada
> 6 bayttır — ve dolgulu okuyan bir sürücü o glyph'i tamamen bozuk çizer.
> Firmware tarafı (`firmware/src/font.cpp`) bu akış kuralını uygular.

**Neden bu tasarım:** `left`/`top` ofsetleri sayesinde glyph'ler kutunun dışına
taşabilir (örneğin `ğ`'nin yumuşak işareti veya `ç`'nin çengeli); glyph'leri
kutuya sığdırmaya çalışmak Türkçe harfleri bozar. `advance` ayrı tutulur, böylece
`ı` ve `İ` gibi harfler doğru aralıkla dizilir.

`fontgen.py` her glyph'in bitmap'ini ürettikten sonra **paketleyip geri açıp
karşılaştırır**; uyuşmazlık varsa dosyayı yazmadan hata verir. Ayrıca
`tools/tests/test_epf_interop.py` iki tarafın aynı kuralı uyguladığını
sınır durumlardaki glyph genişlikleriyle (9, 12, 13, 17 px) doğrular.

---

## 3 · Kitap dönüştürmek

```bash
python3 epub2epr.py ~/kitaplar/suc-ve-ceza.epub \
        -o suc-ve-ceza.epr \
        --title "Suç ve Ceza" --author "Dostoyevski" --lang tr
```

| Bayrak | Anlamı |
|---|---|
| `-o, --output` | Çıktı dosyası |
| `--title` / `--author` / `--lang` | Üst veriyi geçersiz kıl (EPUB'da yanlışsa) |
| `--no-toc` | İçindekiler tablosunu üretme (daha küçük dosya) |
| `--strip-diacritics` | Aksanları kaldırır. **Fontunuzda Türkçe harfler yoksa** kullanın — ama metin bozulur |
| `--dump` | Dönüştürmeden başlığı ve ilk 500 karakteri göster (hata ayıklama) |
| `--verify` | Yazdıktan sonra dosyayı geri okuyup doğrula |
| `--verbose` | Paragraf/bölüm/bayt istatistikleri |

Örnek çıktı:

```
Girdi:    suc-ve-ceza.epub (812 KB)
Başlık:   Suç ve Ceza
Yazar:    Dostoyevski
Dil:      tr
Spine:    42 belge
Bölüm:    18
Paragraf: 3.412
Çıktı:    suc-ve-ceza.epr (398 KB)
```

### 3.1 `.epr` biçimi (v1)

Little-endian:

```
offset 0   : "EPR1" (4 ASCII bayt)
offset 4   : uint16 sürüm = 1
offset 6   : uint16 bayraklar          (bit0 = içindekiler var)
offset 8   : uint32 metin_offset
offset 12  : uint32 metin_uzunluk
offset 16  : uint32 toc_offset         (bayrak kapalıysa 0)
offset 20  : uint32 toc_sayısı
offset 24  : uint8  başlık_uzunluk,  ardından UTF-8 başlık
           : uint8  yazar_uzunluk,   ardından UTF-8 yazar
           : uint8  dil_uzunluk,     ardından ASCII dil etiketi ("tr")
           : uint8  kodlama          (0 = UTF-8)
           : metin_offset'e kadar 0x00 dolgu

metin bloğu (UTF-8):
  0x0A  paragraf sonu   → okuyucu yeni paragrafa geçer, ilk satırı girintiler
  0x0B  bölüm sonu      → okuyucu YENİ SAYFA başlatır ve başlığı ortalar
  diğer baytlar düz metindir; 0x0D (CR) dosyada bulunmaz

içindekiler bloğu: toc_sayısı adet giriş
  { uint32 metin_konumu (metin bloğuna göre bayt ofseti)
    uint8  uzunluk
    char[] başlık (UTF-8, NUL sonlandırıcı YOK) }
```

**Satır sonu neden yok?** Cihaz satırları kendi sarar, çünkü sarma yazı
boyutuna bağlıdır. Dönüştürücü satır sonu koysaydı büyük yazı boyutunda metin
bozuk görünürdü. Dönüştürücünün işi yalnızca **paragraf ve bölüm sınırlarını**
işaretlemektir.

### 3.2 Dönüştürücünün yaptığı temizlik

| İşlem | Neden |
|---|---|
| `<script>`, `<style>`, `<head>` içeriği atılır | Metne karışmamalı |
| HTML varlıkları çözülür (`&amp;` → `&`, `&#287;` → `ğ`) | |
| Yumuşak tire (U+00AD) ve sıfır genişlikli karakterler silinir | Satır sarma bozulur |
| Unicode NFC normalizasyonu | Türkçe birleşik dizileri tek kod noktasına indirir |
| Boşluklar sadeleştirilir (satır içi çoklu boşluk → tek) | E-kitapta girinti sorunları |
| `<h1>`–`<h6>` öncesine bölüm sonu (0x0B) konur | Sayfa kırılması ve başlık |
| `<img>` → `[resim]` | Görseller desteklenmiyor |

---

## 4 · Cihaza yüklemek

### 4.1 Komut satırı

```bash
# Tek kitap
python3 send.py suc-ve-ceza.epr

# Cihazda ne var?
python3 send.py --list

# Kitap sil
python3 send.py --rm suc-ve-ceza.epr

# Wi-Fi şifresini cihaza kaydet
python3 send.py --wifi "EvAgi" "sifre123"

# Cihaz durumu
python3 send.py --status

# Bir klasördeki tüm EPUB'ları dönüştürüp yükle
python3 send.py --dir ~/kitaplar/

# Dosya değiştiğinde otomatik yükle (yazarken test için)
python3 send.py kitap.epr --watch

# IP'yi elle ver (mDNS çalışmıyorsa)
python3 send.py kitap.epr --ip 192.168.1.42
```

### 4.2 Tarayıcıdan

1. Cihazda **MENÜ'ye uzun basın** → Wi-Fi aktarım modu
2. Ekranda SSID ve adres görünür
3. Bilgisayardan `http://pocketreader.local` açın
4. Dosyayı sürükleyip bırakın

Cihaz kendi ağını (`PocketReader-XXXX`, şifre `readbooks`) açtıysa önce o ağa
bağlanın, sonra tarayıcıdan açın ve **ev ağınızın şifresini bir kez** girin.
Bundan sonra cihaz kendi başına ev ağınıza bağlanır.

> **Önemli:** Cihaz `.epr` bekler, `.epub` değil. Tarayıcı arayüzü yüklenen
> dosyanın sihirli sayısını (`EPR1`) kontrol eder ve EPUB yüklerseniz
> "geçersiz biçim" hatası verir. Önce `epub2epr.py` ile dönüştürün.

### 4.3 Cihaz uykuya geçtiyse

Aktarım modu, siz çıkana kadar uykuya girmez. Ama cihaz uykudaysa ağda
görünmez — bir sayfa butonuna basın, sonra MENÜ'ye uzun basın.

---

## 5 · Kitap yükleme senaryoları

### Tek seferlik kurulum

```bash
cd tools
python3 make_sample_books.py            # examples/ içine örnek kitaplar üretir

cd ../firmware
pio run -t uploadfs                     # font + örnek kitaplar birlikte
```

`make_sample_books.py` üç dosya üretir:

| Dosya | İçerik |
|---|---|
| `ornek-turkce.epr` | Türkçe özgün kısa metin, 3 bölüm — **Türkçe harf testi** |
| `sample-english.epr` | İngilizce özgün kısa metin |
| `stress-test.epr` | ~200 KB, 40 bölüm — sayfalama ve sayfa indeksi önbelleği testi |

### Kütüphane oluşturmak

```bash
# EPUB arşivinizi dönüştürüp cihaza aktarın
python3 send.py --dir ~/kitaplar/
```

4 MB flash'ta ~3 MB kullanılabilir alan vardır; bu yaklaşık **15–30 kitap**
demektir (bir roman `.epr` olarak 200–500 KB tutar).

---

## 6 · Sorun giderme

| Belirti | Sebep | Çözüm |
|---|---|---|
| Cihazda harfler kutu/boşluk | Fontta o karakter yok | `fontgen.py --ranges` ile Türkçe aralığı ekleyin |
| Metin okunamayacak kadar küçük | 12 px font yüklü | `--size 14` ile yeniden üretin |
| Sayfa sonlarında kelimeler bölünüyor | Normal davranış | Türkçe hece bölme henüz yok — `docs/09` |
| Kitap açılmıyor, "geçersiz biçim" | `.epub` yüklenmiş | `epub2epr.py` ile dönüştürün |
| Başlık/yazar boş görünüyor | EPUB üst verisi eksik | `--title`/`--author` ile geçersiz kılın |
| Kitap açılırken çok yavaş | İlk sayfalama (önbellek yok) | Normaldir; ikinci açılış hızlıdır |
| `pocketreader.local` çözülmüyor | mDNS desteklenmiyor (bazı Windows/Android) | Ekrandaki IP'yi `--ip` ile verin |
| Tarayıcı sayfası açılmıyor | Cihaz uykuda | Butona basın, MENÜ'ye uzun basın |

---

## 7 · Biçim sürümleme

Her iki biçim de sihirli sayı + sürüm numarası taşır (`EPR1`, `EPF1`). Gelecekte
uyumsuz bir değişiklik gerekirse sürüm numarası artırılır ve cihaz eski
dosyaları reddederken **anlaşılır bir mesaj** gösterir — sessizce bozuk metin
göstermez. Yeni alanlar mevcut sürümde `ayrılmış` baytlara eklenir.

---

Geri: [05 · Yazılım Kurulumu](05-firmware-setup.tr.md) · Devam: [07 · Güç Yönetimi](07-power.tr.md)
