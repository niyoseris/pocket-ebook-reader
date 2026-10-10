# Değişiklik Kaydı — Pocket Reader

Bu proje [Semantic Versioning](https://semver.org/) kullanır.

## [1.0.0] — 2026-10-09

İlk sürüm. Donanım üzerinde test edilmemiş, derlenmeye hazır tam firmware.

### Eklenen
- **BUSY polaritesi yapılandırılabilir**: `EPD_BUSY_ACTIVE_HIGH` (varsayılan 1,
  datasheet Rev 0.14 Table 5-2). `epdBusyWait()` sabit bir zaman aşımına sahiptir
  (tam yenileme 5 s, kısmi 2 s); zaman aşımında gözlenen pin seviyesini yazıp
  polaritenin yanlış olabileceğini söyler ve `false` döner — cihaz asla asılı
  kalmaz. README'de "BUSY polaritesini 30 saniyede doğrulama" bölümü vardır.
- **Panel derin uykusu** `0x10 = 0x01` (Mode 1, ~1 µA, RAM korunur). Çıkışın
  yalnızca donanımsal reset ile mümkün olduğu `include/epd.h` ve `README.md`
  içinde açıkça belgelenmiştir; sürücü uykudan sonra ilk yenilemede otomatik
  olarak HWRESET + init dizisini çalıştırır.
- `data/fonts/` klasörü (font üretimi için) ve `tools/fontgen.py`.

- **SSD1680 sürücüsü** (`src/epd.cpp`, `src/epd_lut.h`): 2.13" 250x122 panel için
  kendi SPI sürücümüz. Waveshare referans sürücüsünden alınan gerçek init dizisi
  ve LUT tabloları (MIT). Tam + kısmi yenileme, kirli dikdörtgen takibi.
  Panel tipik çekişi 3.5 mA (VCI = 3.0 V, 10.5 mW) olarak not edilmiştir.
- **Döndürme katmanı**: 4000 baytlık native RAM üzerine 250x122 mantıksal tuval.
  `EPD_ROTATION` / `EPD_MIRROR_X` / `EPD_MIRROR_Y` ile yapılandırılır.
- **Font motoru** (`src/font.cpp`): LittleFS'ten çalışma zamanında yüklenen `.epf`
  ikili font formatı, Türkçe karakter desteği, x1/x2 ölçekleme, satır sarma.
- **`.epr` kitap ayrıştırıcısı** (`src/book.cpp`): başlık okuma, akan metin
  okuyucu, sayfalama ve `/cache/*.idx` sayfa dizini önbelleği (bayat önbellek
  tespiti + yeniden üretim).
- **Butonlar** (`src/buttons.cpp`): 25 ms debounce, 700 ms uzun basma, derin
  uykudan uyanma sonrası basılı tuş tespiti.
- **Güç yönetimi** (`src/power.cpp`): GPIO5 (ADC2_CH0) ile pil ölçümü (medyan +
  ortalama), Li-ion boşalma eğrisi, `ext1` ile GPIO2/GPIO3'ten (YUKARI/AŞAĞI)
  derin uyku, RTC'de kalan durum.
- **Depolama** (`src/storage.cpp`): LittleFS + `Preferences` (NVS) ayarları.
- **WiFi aktarım** (`src/wifi_xfer.cpp`): STA (15 s) → AP `PocketReader-XXXX`
  yedekli WebServer, `GET /`, `POST /upload`, `GET /list`, `POST /delete`,
  `POST /wifi`, `GET /status`. Bağımlılıksız JSON ve multipart.
- **Arayüz** (`src/ui.cpp`): SPLASH, LIBRARY, READER, MENU, WIFI, ERROR, INFO,
  SLEEP ekranları; varsayılan olarak İngilizce metinler (`include/i18n.h`;
  Türkçe için `-DLANG_TR`).
- **Derin uykudan doğrudan eylem**: uyanırken splash gösterilmez; basılı tuşa
  göre doğrudan sonraki/önceki sayfa veya kütüphane çizilir (ana UX detayı).
- `tools/fontgen.py`: TTF → `.epf` dönüştürücü.

### Bilinen eksikler
- Donanımda test edilmedi (bkz. README "Test edilmeyenler").
- MENÜ tuşu (GPIO20) RTC alanında olmadığı için derin uykudan **uyandırmaz**;
  uyandırmak için YUKARI veya AŞAĞI kullanılmalıdır.
- GPIO6 JTAG (MTCK) olarak feda edildi; hata ayıklama UART/USB-CDC üzerinden yapılır.
