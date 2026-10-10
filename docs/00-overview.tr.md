> English version: [00-overview.md](00-overview.md)

# 00 · Genel Bakış ve Tasarım Kararları

Bu doküman "ne yaptık" değil, **"neden böyle yaptık"** sorusunu yanıtlar. Bir
parçayı değiştirmek isterseniz önce burayı okuyun; çoğu karar birbirine bağlıdır.

---

## 1. Neden ESP32-C3?

| Aday | Uyku akımı | Boyut | Sonuç |
|---|---|---|---|
| **ESP32-C3** | ~5 µA (çip) | 13.2 × 16.6 mm modül | ✅ seçildi |
| ESP32 (klasik) | ~10 µA ama kart ~1 mA | büyük modül | ❌ kart seviyesinde tüketim yüksek |
| ESP32-S3 | ~8 µA | daha büyük, daha pahalı | ➖ gereğinden güçlü, PSRAM'e ihtiyaç yok |
| Raspberry Pi Zero 2 W | **~120 mA** | 65 × 30 mm | ❌ 500 mAh pil ile ~4 saat |
| ATmega328P | ~0.1 µA | küçük | ➖ Wi-Fi yok, kitap aktarmak için SD kart + fiziksel erişim gerekir |

Belirleyici kısıt **uyku akımı**. Bir e-mürekkep okuyucunun bütün değeri
"açtığımda şarjı bitmemiş olması"dır. Pi Zero W bunu yapısal olarak başaramaz:
Linux'un boştayken çektiği akım, bir e-mürekkep ekranın en büyük avantajını
(statik görüntü = sıfır güç) silip atar.

ESP32-C3'ün ikinci avantajı: **RTC-domain GPIO** ve **RTC belleği**. Cihaz derin
uykudayken butonlardan biriyle uyanıp, hangi kitabın kaçıncı sayfasında
olduğunuzu RAM'den kaybetmeden devam edebilir.

---

## 2. Neden bu pin haritası? (En kritik tasarım kısıtı)

XIAO ESP32-C3, ESP32-C3-MINI-1'in 53 pad'inden yalnızca **11 GPIO'yu** header'a
çıkarır:

```
GPIO2, GPIO3, GPIO4, GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO20, GPIO21
```

İhtiyacımız olan sinyal sayısı: `SCK, MOSI, CS, DC, RST, BUSY, UP, DOWN, MENU, ADC` = **10**.

Yani 11 pinin 10'u kullanılır, GPIO21 boşta kalır. Ama asıl zorluk sayı değil,
**iki ayrı kısıt**:

### Kısıt A: Uykudan uyandırabilen pinler

ESP32-C3'te `ext1` ile derin uykudan uyandırabilen pinler RTC alanındadır:
**GPIO0–GPIO5**. XIAO header'ında bunlardan yalnızca **2, 3, 4, 5** var.

- GPIO4 → SPI saat (vazgeçilmez)
- Kalan: GPIO2, GPIO3, GPIO5

Bunlara üç şeyi sığdırmamız gerekiyor: iki sayfa butonu + pil ölçümü.
ADC1 yalnızca GPIO0–4'te; GPIO0/1 header'da yok, GPIO4 SPI'da. Yani pil ölçümü
**GPIO5 = ADC2_CH0** olmak zorunda. Böylece butonlara GPIO2 ve GPIO3 kalır — ki
ikisi de RTC alanında olduğu için **iki sayfa butonu da cihazı uyandırabilir**.
Kritik olan tam olarak budur.

> ESP32-C3'ün ADC2'si tek kanallıdır ve klasik ESP32'nin aksine Wi-Fi ile
> çakışmaz. Bu yüzden GPIO5'i pil ölçümü için güvenle kullanabiliyoruz.

### Kısıt B: Strapping pinleri

GPIO2, GPIO8 ve GPIO9 strapping pinleridir. Normal (SPI) boot için datasheet
Table 4-3'ün şartı: **GPIO2 = 1, GPIO9 = 1, GPIO8 = serbest**. Açılışta
yanlış seviye = cihaz açılmaz veya indirme moduna girer.

Bu iki kısıtı aynı anda çözen atama:

| Pin | Rol | Neden çalışıyor |
|---|---|---|
| GPIO2 | `BTN_DOWN` | RTC ✓. Strapping: açılışta HIGH olmalı → 100k pull-up sağlar. Buton açılışta basılı tutulmamalı |
| GPIO3 | `BTN_UP` | RTC ✓. Strapping değil, serbest |
| GPIO5 | `VBAT_ADC` | ADC2_CH0 ✓ |
| GPIO8 | `EPD_RST` | Strapping **ama SPI boot için değeri önemsiz** (yalnızca indirme modunda 1 olmalı). ROM mesaj bastırma pinidir |
| GPIO9 | `EPD_BUSY` | Strapping: açılışta HIGH olmalı → **panel BUSY boşta HIGH olduğu için şart kendiliğinden karşılanır** |
| GPIO20 | `BTN_MENU` | U0RXD, yalnızca giriş. RTC değil → uykudan uyandıramaz |

GPIO9'un BUSY'ye verilmesi tasarımın en zarif kısmı: iki kısıt aynı anda,
ekstra parça olmadan çözülüyor.

### Bedeli

- **MENÜ butonu cihazı uykudan uyandıramaz.** Uyandıktan sonra basılır.
  (Uyanmak için sayfa butonlarından biri kullanılır — ki kullanıcı zaten okumaya
  devam etmek ister, menüye dönmek istemez. Pratikte rahatsız etmez.)
- **GPIO6 (MTCK) SPI'da kullanıldığı için klasik JTAG kaybedilir.** USB-Serial-JTAG
  (GPIO18/19, USB-C üzerinden) hata ayıklama için yeterlidir.
- XIAO'da GPIO9 aynı zamanda kartın BOOT butonuna bağlıdır. BOOT'a basmak paneli
  "meşgul" gösterir (zararsız, zaman aşımına düşer) ve açılışta basılı tutulursa
  indirme moduna alır.

---

## 3. Neden güçte buck-boost, LDO değil?

Li-Po 4.2 V'ta dolu, 3.0 V'ta boştur. E-paper paneli ve ESP32-C3 **3.3 V** ister.

- **LDO** (ör. MCP1700): 3.4 V'un altında çıkışı düşmeye başlar. Pilin son
  %20–25'i kullanılamaz. Ayrıca (4.2−3.3) × akım kadar ısı üretir.
- **Sadece boost**: pil 3.3 V'un üstündeyken çalışmaz.
- **Buck-boost (TPS63020)**: 2.5–5.5 V girişte sabit 3.3 V. Pilin **tamamı**
  kullanılır. Panel yenilemesi sırasındaki akım darbelerinde çıkış düşmez —
  e-mürekep panelin içindeki ±15 V şarj pompası düşük giriş gerilimine duyarlıdır.

TPS63020'nin 2 A çıkışı ihtiyaçtan fazladır (ESP32 Wi-Fi TX tepe akımı ~350 mA,
panel yenilemesi ~20 mA). Sebep: sabit 3.3 V veren **lehimlenebilir** bir
buck-boost seçeneği azdır; TPS63020 hem VSON-10 (elle lehimlenebilir) hem de
stok bulunur bir parçadır. Daha ucuz/küçük alternatifler `docs/09`'da.

---

## 4. Neden kendi SSD1680 sürücüsünü yazdık, GxEPD2 kullanmadık?

GxEPD2 olgun ve iyi bir kütüphanedir; **kullanmak isterseniz geçebilirsiniz**
(`firmware/README.md`'de nasıl yapıldığı yazıyor). Kendi sürücümüzü yazmamızın
gerekçesi:

1. **Kısmi yenileme bizim kontrolümüzde olmalı.** Ghosting yönetimi (20 sayfada
   bir tam yenileme), kirli dikdörtgen takibi ve panel uykusu ana UX'i belirliyor.
2. **Bağımlılık yok.** 4 MB flash'ın ve 400 KB RAM'in olduğu bir yerde 30 KB'lık
   bir kütüphaneyi taşımak gereksiz.
3. **Şeffaflık.** Satıcının init dizisi ve LUT tabloları depoda, kaynak URL'siyle
   birlikte duruyor; ne olduğu görülebiliyor.

**LUT tabloları uydurulmadı.** Kısmi yenileme, panele özgü bir dalga formu (LUT)
gerektirir; yanlış LUT paneli yavaş yavaş bozar. Tablolar, MIT lisanslı satıcı
referans sürücüsünden aynen alındı ve `src/epd_lut.h` başında kaynak URL'si
belirtildi.

---

## 5. Neden `.epr` diye kendi kitap biçimimiz var?

Cihazda EPUB ayrıştırmak için ne RAM ne de CPU var — ve gerekmiyor da.
Dönüştürme bilgisayarda **bir kez** yapılır:

```
EPUB  ──(epub2epr.py, bilgisayarda)──>  .epr  ──(Wi-Fi)──>  cihaz
```

Cihaz tarafında kalan iş: UTF-8 okuma, satır sarma, sayfa bölme, sayfa
konumlarını `uint32` dizisi olarak önbelleğe alma. 200 KB'lık bir kitapta
~4.000 sayfa konumu = 16 KB RAM. ESP32-C3 için sorun değil.

Alternatif `TXT` de kullanılabilirdi ama o zaman başlık, yazar, dil ve
içindekiler bilgisi kaybolurdu; kitaplık ekranı ve bölüm atlama çalışmazdı.

---

## 6. Neden font dosyası LittleFS'te, firmware'de gömülü değil?

Gömülü font, firmware'i yeniden derlemeden yazı tipini değiştiremeyeceğiniz
anlamına gelir. Oysa yazı boyutu/ tipi bir okuyucuda en çok değiştirilen ayardır.

Bunun bedeli: cihaz ilk açılışta font bulamazsa çalışamaz. Bu yüzden firmware
font yoksa **açık bir hata ekranı** gösterir ("`tools/fontgen.py` çalıştırın"),
sessizce boş ekran bırakmaz.

---

## 7. Bilinçli olarak yapılmayanlar

| Yapılmadı | Neden |
|---|---|
| Dokunmatik ekran | 2.13" panelde dokunmatik katman maliyeti panelin kendisinden pahalı; 3 buton yeterli |
| Ön ışık | Bu boyutta ön ışıklı panel yok (en küçükleri 4.2"+) |
| SD kart | 4 MB flash'ta ~3 MB kullanılabilir alan ≈ 15–30 kitap; Wi-Fi aktarımı zaten var. GPIO da yok |
| Harici PSRAM | 250×122×1 bit = 3.9 KB tampon. Gülünç derecede küçük |
| Gerçek zaman saati | Saat göstermiyoruz. İstenirse MAX17048 zaten I²C'de yer ayırıyor |
| Çoklu dil UI | Türkçe + İngilizce derleme bayrağıyla; `i18n.h` genişletilebilir |

---

## 8. Veri akışı

```
┌─ BİLGİSAYAR ──────────────────────────────┐
│  kitap.epub                                │
│      │ epub2epr.py                         │
│      ▼                                     │
│  kitap.epr ──┐                             │
│              │ send.py / tarayıcı          │
└──────────────┼─────────────────────────────┘
               │ HTTP (Wi-Fi, aktarım modu)
┌──────────────▼─────────────────────────────┐
│  CİHAZ                                     │
│  wifi_xfer.cpp  ──> LittleFS /books/       │
│                          │                 │
│  book.cpp  <── aç ───────┘                 │
│      │ header oku, metni akıt              │
│      │ font.cpp ile satır sar              │
│      ▼                                     │
│  sayfa konumları (uint32 dizisi)           │
│      │                                     │
│      ▼                                     │
│  ui.cpp  ──> Canvas (4000 bayt)  ──> epd.cpp ──SPI──> panel
│                    ▲                       │
│  buttons.cpp ──────┘                       │
│  power.cpp (uyku/uyanma, RTC belleği) ─────┘
└────────────────────────────────────────────┘
```

---

Devam: [01 · Malzeme Listesi](01-bill-of-materials.tr.md)
