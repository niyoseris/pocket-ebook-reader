> English version: [08-troubleshooting.md](08-troubleshooting.md)

# 08 · Sorun Giderme

Belirtiye göre arayın. Her maddede **önce en olası sebep** yazılıdır.

---

## Ekran

### Hiç görüntü yok, ekran tamamen beyaz/siyah

| Olası sebep | Kontrol | Çözüm |
|---|---|---|
| Besleme gerilimi yanlış | `C4` üzerinde 3.3 V var mı? | `R5`/`R6` kontrol, `docs/04` §4 |
| FPC ters takılmış | `BUSY` hattı boşta HIGH mı? | Konektörü çıkar, 180° çevirip tak |
| FPC tam oturmamış | Konektörün kilidi kapalı mı? | Sonuna kadar itip kilitle |
| Firmware yüklenmemiş | Seri portta çıktı var mı? | `pio run -e xiao -t upload` |
| Font dosyası yok | Ekranda "font bulunamadı" yazıyor mu? | `tools/fontgen.py` + `uploadfs` |
| `EPD_RST` sürekli LOW'da | GPIO8'i ölç | 100 kΩ pull-up lehimi |
| `RST` ve `CS` karışmış | Şemayla karşılaştır | Doğru pinlere taşı |

> Ekran **tamamen siyah** oluyorsa bu genellikle iyi haberdir: panel besleniyor
> ve reset oluyor, ama veri gelmiyor demektir. Sorun `MOSI`, `SCK` veya `DC`
> hattındadır — besleme değil.

### Görüntü ters / ayna gibi

`firmware/include/config.h` içinde şu üç satırı deneyin:

```c
#define EPD_ROTATION   90
#define EPD_MIRROR_X   0
#define EPD_MIRROR_Y   0
```

8 olası kombinasyon vardır; sırayla deneyin. Kod değişikliği gerekmez ve her
deneme bir derleme + yükleme demektir (~30 saniye). Doğru kombinasyonu bulduğunuzda
kaydedin.

**Görüntü 90° dönükse** yalnızca `EPD_ROTATION` değerini `0`/`180`/`270`
arasında değiştirin. **Ayna gibiyse** `EPD_MIRROR_X` veya `EPD_MIRROR_Y`'yi
`1` yapın.

### Metin var ama leke/gölge (ghosting)

| Sebep | Çözüm |
|---|---|
| Kısmi yenileme sayacı çok yüksek | `DEFAULT_FULL_REFRESH_EVERY` değerini **20 → 10** düşürün |
| Regülatör ripple'ı yüksek | `JP1` köprüsünü `GND`'den `VINA`'ya taşıyın (zorlanmış PWM) |
| `C10` (100 µF) eksik veya uzak | Panel konektörünün dibine ekleyin |
| Panel yaşlanması | Normaldir; tam yenileme sıklığını artırın |

Leke, e-mürekkep teknolojisinin doğal sonucudur. 20 sayfada bir tam yenileme
bunu yönetir. Rahatsız ediyorsa 10'a indirin — bedeli, her 10 sayfada bir
ekranın 2 saniye yanıp sönmesidir.

### Bazen ekran yarım yenileniyor

Klasik **`C10` sorunu**. Panel yenileme anında şarj pompasını doldurmak için
kısa süreli yüksek akım çeker. Tampon kondansatör yoksa veya izi uzunsa
`3V3` rayı çöker ve panel yarıda kalır.

- `C10` takılı mı? (100 µF, düşük ESR)
- `C10` panel konektörünün **dibinde** mi? (5 mm'den uzaksa etkisi azalır)
- 0805/1206 yerine daha küçük kasa mı kullandınız? (ESR'si yüksek olabilir)

### Ekran çok yavaş yenileniyor

Tam yenileme ~2 saniyedir — bu panelin doğası. Kısmi yenileme ~0.3 s'dir.
Sürekli tam yenileme yapıyorsa `epdPartialRefresh()` çağrısı devrede değildir;
`config.h` içindeki `partial_enabled` ayarını kontrol edin.

---

## Butonlar ve uyku

### Butonlar yanlış çalışıyor (geri/ileri karışık)

`BTN_UP` ve `BTN_DOWN` pinlerini yer değiştirin (`config.h`) **veya** kabloları
çevirin. Kolay yapıda en sık yapılan hata budur: D0 ve D1'i karıştırmak.

### Cihaz uykudan uyanmıyor

| Sebep | Kontrol |
|---|---|
| MENÜ butonuna basılıyor | GPIO20 RTC alanında **değildir** — uyandıramaz. `BTN_UP` veya `BTN_DOWN` kullanın |
| Butonlar GND'ye bağlı değil | `ANY_LOW` uyanma, pini GND'ye çeken bir yol ister |
| Pil bitmiş | Voltaj ölçün |
| Firmware uykuya girmiyor | Seri portta "sleep" satırı var mı? |

### Uyandıktan sonra açılış ekranı çıkıyor

Firmware `was_deep_sleep` bayrağını okumuyor. Bu bayrak `RTC_DATA_ATTR` ile
tanımlanmalıdır; sıradan bir global değişken derin uykuda **sıfırlanır**.
`power.h` içindeki `RtcState` yapısının `RTC_DATA_ATTR` ile işaretli olduğunu
doğrulayın.

### Cihaz kendi kendine uyanıyor

| Sebep | Çözüm |
|---|---|
| Buton hattında 100 nF yok | Uyanma anındaki sıçrama sahte kenar üretir — kondansatör ekleyin |
| `VBAT_ADC` GPIO5'te, bir butonla karışmış | Şemayla karşılaştırın |
| Buton mekanik olarak sıkışmış | Kasayı kontrol edin |

---

## Güç ve pil

### Şarj olmuyor

| Sebep | Kontrol |
|---|---|
| **USB-C'nin CC dirençleri yok/yanlış** | `R1`, `R2` = 5.1 kΩ mu? (En sık sebep) |
| Kablo yalnızca şarj için | Başka kablo deneyin |
| Şarj LED'i hiç yanmıyor | `R4`/`D1` yönü ve `STAT` bağlantısı |
| LED ters | LED katodu `STAT`'a, anodu `R4` üzerinden `VBUS`'a |
| Pil dolu | LED yanmaz — normal |
| Pil koruma devresi kesti | Pili ayırıp doğrudan ölçün |

### Pil yüzdesi yanlış

| Sebep | Çözüm |
|---|---|
| Ölçüm yenileme sırasında yapılıyor | Firmware ölçümü yenilemeden **önce** yapmalı |
| Bölücü değeri yanlış | 100 kΩ / 100 kΩ olmalı (oran 1:2) |
| ADC zayıflatması eksik | `analogSetPinAttenuation(VBAT_ADC, ADC_11db)` |
| Pil eğrisi uymuyor | Farklı kimyalar farklı eğri ister; `power.cpp`'deki tabloyu ayarlayın |
| ADC2 kullanılmıyor | GPIO5 = **ADC2_CH0**; ADC1 pinleri kullanımda değil |

### Pil 1 günde bitiyor

Beklenen: ~13 ay. Bir günde bitiyorsa:

| Sebep | Kontrol |
|---|---|
| Cihaz uykuya girmiyor | 60 s bekleyip akım ölçün |
| Wi-Fi kapanmıyor | `WiFi.mode(WIFI_OFF)` uykudan önce çağrılıyor mu? |
| Panel uykuya girmiyor | `epdSleep()` çağrılıyor mu? (panel mW mertebesinde çeker) |
| Seri port açık kalıyor | USB takılı değilken seri çıktı akım çekmez ama USB-serial aktifse çeker |
| XIAO üstündeki kullanıcı LED'i | Bazı kartlarda parlaklık LED'i sürekli yanar |

---

## Wi-Fi

### `pocketreader.local` açılmıyor

| Sebep | Çözüm |
|---|---|
| mDNS desteklenmiyor | Ekrandaki IP'yi doğrudan yazın: `http://192.168.1.42` |
| Cihaz uykuda | Butona basın, MENÜ'ye uzun basın |
| Bilgisayar farklı ağda | İkisi de aynı ağda olmalı |
| AP modunda | Önce `PocketReader-XXXX` ağına bağlanın (şifre: `readbooks`) |

### Cihaz ev ağını bulamıyor

Wi-Fi şifresini yeniden girin:

```bash
cd tools
python3 send.py --wifi "EvAgi" "sifre123"
```

AP modunda tarayıcıdan da yapılabilir. **2.4 GHz ağ kullanın** — ESP32-C3
5 GHz desteklemez. En sık sebep budur: modemin 5 GHz SSID'sine bağlanmaya
çalışmak.

### Yükleme yarıda kesiliyor

| Sebep | Çözüm |
|---|---|
| Kitap çok büyük | LittleFS'te boş alan var mı? (`send.py --status`) |
| Cihaz uykuya geçti | Aktarım modunda uyku devre dışı olmalı; firmware'i kontrol edin |
| Zayıf sinyal | Cihazı router'a yaklaştırın |

---

## Derleme ve yazılım

| Hata | Çözüm |
|---|---|
| `epd_lut.h: No such file` | Dosya eksik; `docs/05` §7 |
| `'EPD_FB_SIZE' undeclared` | `config.h` dahil edilmemiş |
| `Failed to connect to ESP32-C3` | BOOT + RESET sırası (`docs/05` §2) |
| `LittleFS mount failed` | `pio run -t uploadfs` |
| `#include <Arduino.h> file not found` | PlatformIO yerine düz derleyici kullanıyorsunuz — `pio run` kullanın |
| Font yüklendi ama ekranda boşluk | `.epf` bozuk; `fontgen.py --preview` ile doğrulayın |

> **Not:** Bu proje bu depo hazırlanırken bir derleyiciden geçirilmedi. İlk
> `pio run` çağrısında küçük düzeltmeler gerekebilir. Bulduğunuz hatayı
> `CONTRIBUTING.md`'deki gibi bildirin.

---

## Kitap ve font

| Belirti | Sebep | Çözüm |
|---|---|---|
| Türkçe harfler boş kare | Font `latin-ext` kapsamıyor | `fontgen.py --ranges` ile ekleyin |
| `ğ` üstteki işaret kesik | Font kutudan taşıyor | `fontgen.py` sürümünüz `top`/`left` ofsetlerini kullanıyor mu? |
| Kitap açılmıyor | `.epub` yüklenmiş | Önce dönüştürün |
| Başlık boş | EPUB üst verisi yok | `--title`/`--author` |
| Sayfa numaraları yanlış | Font değişti, önbellek eski | `/cache/*.idx` silin veya kitabı yeniden yükleyin |

Cihaz, önbelleğin geçerli olup olmadığını kitap boyutu + font metrikleriyle
kontrol eder; uyuşmazlıkta kendisi yeniden sayfalar. Yine de sorun görürseniz
kitabı silip yeniden yükleyin.

---

## Hâlâ çalışmıyor

Sorunu bildirirken şunları ekleyin — çözüm süresi yarıya iner:

1. **Seri port çıktısı** (`pio device monitor`, `CORE_DEBUG_LEVEL=4`)
2. **Ekranın fotoğrafı** (nasıl bozuk olduğu çok şey anlatır)
3. **Ölçümler**: `3V3` gerilimi, pil gerilimi, uyku akımı
4. **Donanım**: kolay yapı mı PCB mi, panel tam modeli
5. **Ne değişti**: en son neyi değiştirdiniz?

Şablon: [`.github/ISSUE_TEMPLATE`](../.github) (varsa) veya doğrudan issue açın.

---

Geri: [07 · Güç Yönetimi](07-power.tr.md) · Devam: [09 · Yol Haritası](09-roadmap.tr.md)
