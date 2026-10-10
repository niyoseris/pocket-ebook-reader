# Pocket Reader — firmware

ESP32-C3 tabanlı, açık kaynak e-mürekkep kitap okuyucu.
2.13" 250×122 SSD1680 panel, üç tuş, Li-ion pil, WiFi ile kitap aktarımı.

Panelin görüntüsü derin uykuda korunur; cihaz uyandığında **hiç açılış ekranı
göstermeden** doğrudan istenen sayfayı çizer.

---

## 1. Hızlı başlangıç

```bash
cd firmware

# 1) Derle ve yükle (PCB / DevKitM-1)
pio run -e esp32-c3-devkitm-1 -t upload

#    Breadboard (Seeed XIAO ESP32C3) için
pio run -e seeed_xiao_esp32c3 -t upload

#    Kısa yol
pio run -e xiao -t upload

# 2) Dosya sistemini (fontlar, kitaplar) yükle
pio run -e esp32-c3-devkitm-1 -t uploadfs

# 3) Seri portu izle  (UART0 DEĞİL, USB-CDC)
pio device monitor
```

`lib_deps =` **kasıtlı olarak boştur**: SSD1680 sürücüsü, JSON üretimi ve font
motoru bu projede kendimiz yazılmıştır. GxEPD2'ye ihtiyaç yoktur; yine de
istediğinizde onu kullanabilirsiniz (aşağıya bakın).

### Seri konsol hakkında

GPIO20 `BTN_MENU`, GPIO21 ise U0TXD'dir. Bu yüzden **UART0 hiç kullanılmaz**.
`platformio.ini` içinde `-DARDUINO_USB_CDC_ON_BOOT=1` ayarlıdır; tüm `Serial`
çıktısı USB-Serial-JTAG / USB-CDC üzerinden gelir. GPIO6 JTAG (MTCK) olarak
feda edildiği için (EPD_MOSI orada) donanım hata ayıklaması USB-CDC ile yapılır.

---

## 2. Font oluşturma

Okuma ekranı, LittleFS üzerindeki `/fonts/book.epf` dosyasını çalışma anında
yükler. Font yoksa ekranda **"Font bulunamadı / tools/fontgen.py çalıştırıp
yükleyin"** mesajı görünür (bu mesaj için firmware içinde 3×5'lik yedek bir
font gömülüdür; aksi halde yazı çizemeyeceğimiz için hata da görünemezdi).

```bash
# Font ureteci depoda TEK yerde: ../tools/fontgen.py
pip install -r ../tools/requirements.txt
python3 ../tools/fontgen.py DejaVuSans.ttf --size 16 \
        --out data/fonts/reader-16.epf --preview /tmp/onizleme.png
pio run -t uploadfs
```

Varsayılan `--ranges` kümesi ASCII + Latin-1 + Latin Extended-A + Türkçe
(`çÇğĞıİöÖşŞüÜ`) kapsar. Türkçe harfler
fontun içinde ayrı birer kod noktası olarak bulunur.

Dosya biçimi `include/font.h` başlığında tam olarak açıklanmıştır
(12 baytlık başlık + glif başına 10 baytlık sabit kayıt + 1bpp bitmap).
İyi çalışan boyutlar: **14–18**. Büyük yazı ayarı bu dosyayı ×2 ölçekle çizer.

---

## 3. Kitap biçimi ve yükleme

`.epr` v1 biçimi `include/book.h` başlığında tanımlıdır:
`"EPR1"` + sürüm + bayraklar + metin/TOC ofsetleri + başlık/yazar/dil +
metin bloğu (0x0A paragraf, 0x0B bölüm sonu) + isteğe bağlı içindekiler.

Kitaplar iki yolla yüklenir:

* **WiFi ile** (aşağıya bakın).
* Seri porttan dosya sistemi yükleyip `/books/` klasörüne kopyalayarak.

---

## 4. İlk açılış ve WiFi aktarım

1. Cihaz açılır, splash görünür, kitaplık listelenir.
2. **MENÜ tuşuna uzun basın** (700 ms) → menü açılır.
3. *WiFi aktarım* seçin.
4. Cihaz önce kayıtlı ağa bağlanmayı dener (15 s). Başaramazsa kendi erişim
   noktasını açar:

   | | |
   |---|---|
   | Ağ adı | `PocketReader-XXXX` (XXXX = MAC'in son iki baytı) |
   | Şifre | `readbooks` |
   | Adres | `http://192.168.4.1/` |

5. Tarayıcıda adresi açın; sayfa Türkçedir, dosya sürükle-bırak ile yüklenir.
6. Çıkmak için **MENÜ** tuşuna basın. Cihaz WiFi'yi tamamen kapatır.

### Uç noktalar

| Yöntem | Yol | Açıklama |
|---|---|---|
| GET | `/` | Yükleme sayfası (tek dosya, harici varlık yok) |
| POST | `/upload` | multipart dosya, veya `X-Filename` başlıklı ham gövde |
| GET | `/list` | Kitapların JSON listesi |
| POST | `/delete` | `{"name":"kitap.epr"}` (form alanı da kabul edilir) |
| POST | `/wifi` | `{"ssid":"..","pass":".."}` |
| GET | `/status` | Sürüm, boş RAM, boş alan, pil mV/%, çalışma süresi |

**Önemli:** Radyo yalnızca aktarım modunda açıktır ve uyumadan önce tamamen
kapatılır (`WiFi.mode(WIFI_OFF)`). Bekleme akımının ~5 µA seviyesinde kalmasını
sağlayan şey budur; ilişkilendirilmiş ama boşta duran bir WiFi yığını miliamper
çeker ve pili bir günde bitirir.

Yükleme sırasında ilk 4 bayt `EPR1` ile doğrulanır. Geçersizse dosya
`/books/.upload.tmp` içinde çöp olarak kalmaz, silinir. Yükleme önce geçici
dosyaya yazılır, doğrulandıktan sonra asıl adına taşınır — yarım kalan bir
aktarım kitaplığı bozmaz.

Ham gövde yolu (`X-Filename`) gövdeyi RAM'de tuttuğu için **64 KB** ile
sınırlıdır; asıl yol multipart'tır ve akış halinde doğrudan flash'a yazılır.

---

## 5. Derin uyku davranışı

* Hareketsizlik süresi (varsayılan **60 s**, menüden 30/60/120/300/sınırsız)
  dolduğunda panel `0x10 = 0x01` ile **Deep Sleep Mode 1**'e alınır: ~1 µA,
  görüntü RAM'de korunur ve ekranda kalır.
* Uyanma yalnızca **YUKARI (GPIO3)** ve **AŞAĞI (GPIO2)** ile olur; ikisi de RTC
  alanındadır ve `ext1` ile `ANY_LOW` tetikler.
  **MENÜ (GPIO20) uyandıramaz** — U0RXD olduğu için RTC alanında değildir.
  Uyandıktan sonra MENÜ'yü kullanabilirsiniz.
* Uyanışta **splash gösterilmez**: kitap sessizce geri yüklenir (sayfa dizini
  önbelleği sayesinde anında) ve basılı tuşun karşılığı olan tek eylem yapılır:

  | Uyanış | Okuyucu ekranında | Kitaplıkta |
  |---|---|---|
  | AŞAĞI | sonraki sayfa | listede aşağı |
  | YUKARI | önceki sayfa | listede yukarı |

  Ardından cihaz yeniden uykuya döner. Kapak açıp AŞAĞI'ya basmak ~1 saniyede
  sonraki sayfayı verir.

### Pil zayıfsa

Gerilim 3.40 V'un altına düşerse ekranda **"Pil zayıf / Cihazı şarj edin"**
görünür ve cihaz **tuşla uyanmayı tamamen kapatır**; yalnızca saatte bir kez
zamanlayıcıyla uyanıp durumu yeniden ölçer. Böylece çantada kalan bir cihaz
pilini uyanma döngüsüyle bitiremez.

---

## 6. Döndürme ve aynalama ayarı

Arayüz her zaman **mantıksal** bir tuvale çizer (varsayılan 250×122, yatay).
Denetleyicinin gerçek RAM'i 122×250'dir; aradaki dönüşüm **tek bir satır içi
fonksiyondadır**: `epdMapLogicalToNative()` (`include/epd.h`).

```c
#define EPD_ROTATION   90    // 0 / 90 / 180 / 270
#define EPD_MIRROR_X   0     // 1 = görüntüyü yatay aynala
#define EPD_MIRROR_Y   0     // 1 = görüntüyü dikey aynala
```

Görüntü ters ya da dönük çıkarsa **sürücüye dokunmayın**: önce aynaları
çevirin. Aynalama, döndürmeden **önce mantıksal uzayda** uygulanır, yani
`EPD_MIRROR_X` her zaman ekranda gördüğünüz sol/sağ yönünü çevirir.

---

## 7. Pin değiştirme

Tüm pinler `include/config.h` içindedir ve **her iki kart için tek bir harita**
kullanılır (XIAO'da yalnızca 11 GPIO dışarı çıkar).

| Sinyal | GPIO | XIAO | Yön | Not |
|---|---|---|---|---|
| EPD_SCK | 4 | D2 | çıkış | SPI CLK, mod 0 |
| EPD_MOSI | 6 | D4 | çıkış | GPIO6 = MTCK → **JTAG feda edildi** |
| EPD_CS | 7 | D5 | çıkış | aktif LOW |
| EPD_DC | 10 | D10 | çıkış | 0 = komut |
| EPD_RST | 8 | D8 | çıkış | GPIO8 strapping, 100k pull-up |
| EPD_BUSY | 9 | D9 | giriş | GPIO9 strapping/boot; XIAO'da BOOT tuşu |
| BTN_UP | 3 | D1 | giriş | RTC → uyandırır |
| BTN_DOWN | 2 | D0 | giriş | RTC → uyandırır; GPIO2 strapping |
| BTN_MENU | 20 | D7 | giriş | U0RXD; **uyandırmaz** |
| VBAT_ADC | 5 | D3 | giriş | ADC2_CH0, 100k/100k bölücü |

Strapping uyarıları:

* **GPIO8** (EPD_RST) ve **GPIO9** (EPD_BUSY) açılışta HIGH olmalıdır. İkisi de
  doğal olarak HIGH'tır (RST pasif, BUSY boşta) ama 100k pull-up takın.
* **GPIO2** (BTN_DOWN) açılışta HIGH olmalıdır — **açılış sırasında AŞAĞI tuşuna
  basılı tutmayın**, cihaz ROM indirme moduna girer.
* XIAO'da GPIO9 on-board BOOT tuşuna bağlıdır. O tuşa basmak firmware'e "panel
  meşgul" gibi görünür; `epdBusyWait()` zaman aşımına uğrar (zararsız, ~2-5 s)
  ve yenileme iptal edilir.

Tuşlar aktif-LOW'dur; harici 100k pull-up ve 100nF (GND'ye) önerilir. Firmware
ayrıca dahili pull-up'ları da açar ve 25 ms yazılım debounce uygular.

---

## 8. BUSY polaritesini 30 saniyede doğrulama

BUSY polaritesi, yeni bir kartın get-up'ında **en sık yapılan hatadır** ve
satıcı sürücüleri arasında farklılık gösterir. Biz datasheet'i (Rev 0.14,
Table 5-2: BUSY aktif-HIGH) temel alıyoruz ama bu **doğrulanması gereken bir
varsayımdır**:

```c
// include/config.h
#define EPD_BUSY_ACTIVE_HIGH  1   // 1 = HIGH meşgul (datasheet), 0 = LOW meşgul
```

### Ölçümle doğrulama

1. Paneli bağlayın, kartı **hiçbir komut göndermeden** açın.
2. Multimetreyle BUSY pad'ini ölçün. Boştaki bir panel **bırakılmış
   seviyesinde** durur. Datasheet'e göre bu LOW'dur.
3. Firmware'de ekran değiştirip **tam yenileme** tetikleyin (örneğin menüden
   *Tam yenileme*).
4. **Ekran gözle görülür şekilde yenilenirken** ibre hangi seviyede duruyorsa
   BUSY **odur**. Ters çevirirken ibrenin titrediğini görürsünüz; kararlı durduğu
   seviye meşgul seviyesidir.

### Yanlışsa ne olur

* Ters ayarlanmışsa firmware ya hiç beklemez (yenileme senkronsuz kalır,
  görüntü bozuk/yarım çıkar) ya da her seferinde zaman aşımına uğrar.
* Zaman aşımında cihaz **asılı kalmaz**: `epdBusyWait()` gözlenen pin seviyesini
  ve `EPD_BUSY_ACTIVE_HIGH` değerini seri porta yazar ve `false` döner.

```
[epd] BUSY TIMEOUT after 5000ms (pin level=0, EPD_BUSY_ACTIVE_HIGH=1)
[epd] *** BUSY polaritesi yanlis olabilir -- include/config.h icindeki
         EPD_BUSY_ACTIVE_HIGH degerini degistirin ***
```

Bu mesajı görürseniz `EPD_BUSY_ACTIVE_HIGH` değerini 1 ↔ 0 yapıp yeniden
yükleyin. Değeri değiştirdikten sonra hâlâ zaman aşımı alıyorsanız problem
polarite değil, kablolamadır (BUSY hattı kopuk olabilir).

---

## 9. Elektriksel notlar

* **Panel akımı:** GDEY0213B74 için tipik güç 10.5 mW, tipik akım
  **3.5 mA** (VCI = 3.0 V). Yenileme sırasındaki tepe akımlar bunun üzerindedir
  ve panelin pompa devreleri ani çekişler yapar — bu yüzden VCI hattına
  **10 µF + 100 nF** dekuplaj ve besleme yolunda yeterli iz genişliği koyun.
* **Derin uyku:** panel 1 µA (Mod 1, RAM korunur), ESP32-C3 derin uykuda
  ~5 µA. Bölücü dirençleri (100k+100k) sürekli **~21 µA** çeker; bu, kalan
  akımın en büyük kalemidir — kabul edilebilir, ama pili aylarca rafta tutacaksanız
  bölücüyü bir MOSFET ile anahtarlamak gerekir.
* **Şarj:** Li-ion hücre, 3.30 V'ta %0, 4.20 V'ta %100 kabul edilir
  (`src/power.cpp` içindeki tablo).

---

## 10. GxEPD2'ye geçmek (isteğe bağlı)

Kendi sürücümüzü bırakıp GxEPD2 kullanmak isterseniz:
`lib_deps`'e `zinggjm/GxEPD2` ekleyin, `src/epd.cpp` içindeki
`epdInit() / epdFullRefresh() / epdPartialRefresh()` gövdelerini
`GxEPD2_213_GDEY0213B74` çağrılarıyla değiştirin. `src/epd_lut.h` gereksiz
hale gelir çünkü GxEPD2 aynı dalga formlarını kendi içinde taşır. **Üst
katmanlar (Canvas, kitap, arayüz) sürücüden bağımsızdır** — yalnızca
framebuffer'a, `epdDirty()` ve `epdPartialRefresh()`'e dokunurlar.

---

## 11. Test edilmeyenler (dürüst liste)

Bu firmware donanım üzerinde **çalıştırılmadı**; derlenmeye hazır, mantığı
tamamlanmış kod olarak yazıldı. Özellikle şunlar doğrulanmamıştır:

1. **Kısmi yenileme yolu.** Dalga formu ve init dizisi satıcı kaynağından
   birebir alınmıştır, ancak kirli dikdörtgen penceresiyle `0x24`/`0x26`
   çiftini birlikte yazma kararı bize aittir. Hayaletlenme veya yarım
   güncellenen alan görürseniz önce `partial_enabled` ayarını kapatıp tam
   yenilemeyle deneyin, sonra pencereli yazmayı tam ekran yazmaya çevirin.
2. **BUSY polaritesi** — bkz. bölüm 8; ölçülmesi gerekir.
3. **ADC2 (GPIO5) ile pil ölçümü.** ESP32-C3'te ADC2 tek kanallıdır ve klasik
   ESP32'nin aksine WiFi çakışması yoktur; bununla birlikte gerçek doğruluk
   kalibrasyon gerektirebilir. Bölücü takılı değilse okuma 4400 mV'a
   sınırlanır ve yüzde yanıltıcı olur.
4. **Ölçülen uyku akımı.** ~5 µA rakamı ESP32-C3 + panel + bölücü için
   hesaplanmıştır, ölçülmemiştir.
5. **Multipart yükleme akışı** ve WebServer'ın `arg("plain")` davranışı
   çekirdek sürümüne göre değişebilir; JSON yolu bu yüzden form alanlarına da
   düşebilecek şekilde yazılmıştır.
6. **Font üretici** (`../tools/fontgen.py`) Pillow'un `anchor="ls"` özelliğini
   kullanır; çok eski Pillow sürümlerinde desteklenmez.

### Sürüm uyarısı

`platformio.ini` içinde `platform = espressif32@^6.9.0` sabitlendi (istendiği
gibi). Bu platform Arduino çekirdeğinin 2.0.x hattını getirir. Kod hem 2.0.x
hem de 3.x ile derlenecek şekilde yazıldı (örneğin `File::name()` dönüş tipi
sürümler arasında değişir, bu yüzden `String(...)` ile sarmalanır). Arduino
çekirdeği 3.x'in tamamını istiyorsanız `platformio.ini`'de platformu
[pioarduino](https://github.com/pioarduino/platform-espressif32) fork'una
çevirin; `build_flags` aynı kalır.
