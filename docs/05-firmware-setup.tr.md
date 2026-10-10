> English version: [05-firmware-setup.md](05-firmware-setup.md)

# 05 · Yazılım Kurulumu

## 1 · Gereksinimler

| Araç | Sürüm | Not |
|---|---|---|
| Python | 3.9+ | PlatformIO ve `tools/` script'leri için |
| PlatformIO | 6.x | VS Code eklentisi veya `pip install platformio` |
| USB-C kablo | **veri destekli** | Bazı kablolar yalnızca şarj içindir — en sık yapılan hata |

PlatformIO kurulumu:

```bash
# Seçenek A: komut satırı
pip install -U platformio

# Seçenek B: VS Code
# Eklenti marketinden "PlatformIO IDE" kurun
```

İlk `pio run` çağrısı, Espressif'in toolchain'ini (~250 MB) indirir. Bir kereye
mahsustur.

---

## 2 · Derleme ve yükleme

```bash
cd firmware

# Kolay yapı (Seeed XIAO ESP32-C3)
pio run -e xiao -t upload

# PCB yapısı (ESP32-C3-MINI-1)
pio run -e esp32-c3-devkitm-1 -t upload

# Sadece derle (yüklemeden)
pio run -e xiao
```

PlatformIO iki ortam tanımlar ve ikisi de **aynı kaynak kodu** derler; fark
yalnızca kart tanımı ve (varsa) `BOARD_XIAO` makrosudur.

### Yükleme başarısız olursa

ESP32-C3, USB-Serial-JTAG kullanır; çoğu zaman otomatik indirme moduna geçer.
Geçmezse:

1. XIAO'da **BOOT** butonunu basılı tutun
2. **RESET**'e basıp bırakın
3. BOOT'u bırakın
4. `pio run -e xiao -t upload` komutunu tekrarlayın

> ⚠️ GPIO9 = `EPD_BUSY` hattı, XIAO'da BOOT butonuyla paraleldir. BOOT'a
> basmak paneli "meşgul" gösterir — firmware bir zaman aşımına düşer, zararsız.
> Ama açılışta basılı tutarsanız cihaz indirme moduna girer (istenen davranış).

---

## 3 · Dosya sistemi (fontlar ve kitaplar)

Font ve kitaplar firmware'in içinde değil, LittleFS bölümündedir. Ayrı bir
yükleme adımı gerekir:

```bash
# 1. Fontu üret (bkz. docs/06)
cd ../tools
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
        --size 14 --out ../firmware/data/fonts/reader-14.epf

# 2. Dosya sistemini cihaza yükle
cd ../firmware
pio run -t uploadfs
```

`data/` klasörünün yapısı:

```
firmware/data/
├── fonts/
│   ├── reader-14.epf        (fontgen.py ile üretilir)
│   └── reader-20.epf        (isteğe bağlı, büyük yazı için)
└── books/
    └── ornek-turkce.epr     (tools/make_sample_books.py ile üretilir)
```

`firmware/data/fonts/*.epf` **depoya dahil edilmemiştir** (`.gitignore`'da);
her kullanıcı kendi fontunu üretir. Bu bilinçli: font dosyaları lisanslıdır ve
kullanıcının seçimine bağlıdır.

> ⚠️ `uploadfs` **tüm dosya sistemini siler ve yeniden yazar.** Cihaza Wi-Fi
> ile yüklediğiniz kitaplar kaybolur. Kitap yükleme işini Wi-Fi ile yapın;
> `uploadfs`'i yalnızca font güncellerken kullanın.

---

## 4 · Seri port ve hata ayıklama

```bash
pio device monitor -b 115200
```

Konsol **USB-Serial-JTAG** üzerinden çalışır (`ARDUINO_USB_CDC_ON_BOOT=1`).
UART0 (GPIO20/21) bilinçli olarak sessiz bırakılmıştır çünkü o pinler
buton/ekran olarak kullanılıyor.

Göreceğiniz tipik çıktı:

```
Pocket Reader 1.0.0
LittleFS: 3.0 MB toplam, 2.8 MB boş
Font: /fonts/reader-14.epf — 342 glyph, 14 px
Butonlar hazır (GPIO3, GPIO2, GPIO20)
Pil: 3.94 V (%78)
Uyanma: ext1 (GPIO3) — derin uykudan
Kitap: ornek-turkce.epr — sayfa 12/48
```

### Hata ayıklama seviyesi

`platformio.ini` içindeki `CORE_DEBUG_LEVEL`:
`0` = sessiz · `1` = hata · `2` = uyarı (varsayılan) · `3` = bilgi ·
`4` = ayrıntılı · `5` = her şey

SPI iletişimini hata ayıklarken `4` kullanın.

---

## 5 · Ayarları değiştirmek

Neredeyse tüm ayarlar `firmware/include/config.h` içindedir.

### Ekran ters/flip geliyorsa

```c
#define EPD_ROTATION   90      // 0 / 90 / 180 / 270
#define EPD_MIRROR_X   0       // 0 veya 1
#define EPD_MIRROR_Y   0       // 0 veya 1
```

Görüntü yanlış yöndeyse bu üç satırı deneyerek doğru kombinasyonu bulun —
kombinasyon sayısı sınırlıdır (8 ihtimal). Kodun geri kalanına dokunmanız
gerekmez; döndürme tek bir satır içi fonksiyonda yapılır.

### Pin değiştirmek

```c
#define EPD_SCK    4
#define EPD_MOSI   6
// ...
```

> ⚠️ Pin değiştirirken şu kısıtları hatırlayın: butonların uykudan
> uyandırabilmesi için **RTC alanında (GPIO0–5)** olmaları gerekir; strapping
> pinlerinin (GPIO2, GPIO8, GPIO9) açılışta HIGH olması gerekir. Ayrıntı:
> `docs/00` §2.

### Uyku süresi ve yenileme sıklığı

```c
#define DEFAULT_SLEEP_SEC          60   // hareketsizlik sonrası uyku
#define DEFAULT_FULL_REFRESH_EVERY  20   // kaç kısmi yenilemede bir tam yenileme
```

### Türkçe arayüz

İngilizce varsayılandır. Türkçe arayüz için `LANG_TR` derleme bayrağını verin:

```bash
pio run -e xiao -t upload --build-flag="-DLANG_TR=1"
```

---

## 6 · GxEPD2'ye geçmek (isteğe bağlı)

Kendi SSD1680 sürücümüz yerine olgun bir kütüphane kullanmak isterseniz:

1. `platformio.ini` içine ekleyin:
   ```ini
   lib_deps = zinggjm/GxEPD2@^1.6.0
   ```
2. `src/epd.cpp` içinde `Canvas` sınıfının çizim metotlarını GxEPD2'nin
   `GxEPD2_213_GDEY0213B74` sürücüsüne yönlendirin.
3. `epdFullRefresh()` / `epdPartialRefresh()` çağrılarını
   `display.display(false)` / `display.displayWindow(...)` ile değiştirin.

**Bedeli:** ~30 KB flash, kısmi yenileme penceresi üzerindeki kontrolün bir
kısmı ve `epd_lut.h` içindeki şeffaflık. **Kazancı:** panel varyantları
arasında geçiş kolaylığı ve topluluk tarafından test edilmiş kod.

---

## 7 · Sık karşılaşılan derleme hataları

| Hata | Sebep | Çözüm |
|---|---|---|
| `fatal error: epd_lut.h: No such file` | Dosya oluşturulmamış | `src/epd_lut.h` mevcut mu kontrol edin |
| `'EPD_FB_SIZE' undeclared` | `config.h` dahil edilmemiş | `epd.cpp` başında `#include "config.h"` |
| `region 'iram0_0_seg' overflowed` | Flash/RAM bölümü yanlış | `board_build.partitions = default.csv` kontrol edin |
| `A fatal error occurred: Failed to connect` | İndirme moduna geçmiyor | §2'deki BOOT/RESET sırası |
| `LittleFS mount failed` | Dosya sistemi hiç yüklenmemiş | `pio run -t uploadfs` |
| Font bulunamadı ekranı | `.epf` eksik | `tools/fontgen.py` çalıştırıp `uploadfs` yapın |

**Proje bu depo hazırlanırken bir derleyiciden geçirilmedi.** İlk `pio run`
çağrısında yukarıdakilere benzer küçük düzeltmeler gerekebilir; bulduklarınızı
issue olarak açın veya düzeltip PR gönderin.

---

## 8 · Kurulum sonrası doğrulama

```bash
# Cihaz ayakta mı?
cd tools
python3 send.py --status
```

Beklenen çıktı:

```json
{"fw":"1.0.0","heap":245000,"free":2870000,"batt_mv":3940,"batt_pct":78,"uptime":142}
```

Cihaz yanıt vermiyorsa büyük olasılıkla uykudadır — bir sayfa butonuna basın
veya anahtarı kapatıp açın.

---

Geri: [04 · Montaj](04-assembly.tr.md) · Devam: [06 · Kitap ve Font Dönüştürme](06-books-and-fonts.tr.md)
