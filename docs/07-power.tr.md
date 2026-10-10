> English version: [07-power.md](07-power.md)

# 07 · Güç Yönetimi

Bir e-mürekkep okuyucunun bütün değeri "altı ay sonra açtığımda şarjı bitmemiş
olması"dır. Bu doküman o hedefin nereden geldiğini ve nasıl doğrulanacağını
anlatır.

---

## 1. Gerçekçi pil ömrü modeli

Çoğu proje "sayfa çevirme başına enerji"yi hesaplar ve astronomik sayılar bulur
(*"1.7 milyon sayfa!"*). Bu yanıltıcıdır, çünkü asıl tüketim **ekran yenileme
değil, cihazın uyanık kaldığı süredir**.

Okurken cihaz bir sayfa çevirdikten sonra 60 saniye daha uyanık kalır
(ayarlanabilir uyku süresi). Yani:

```
Baskın kalem = uyanık süre × uyanık akım
             = 25 saat × ~20 mA  (500 mAh pil)
```

| Kullanım | Süre | Açıklama |
|---|---|---|
| **Bekleme (derin uyku)** | **13 ay** (TPS63020) / **26 ay** (TPS63900) | Cihaz kapalı sayılır, sadece butonu bekliyor |
| **Sürekli okuma** | **~25 saat** | Ekran açık, sayfa çeviriyor, 60 s uyku zaman aşımı |
| **Wi-Fi aktarım** | **~5 saat** | Radyo açık, HTTP sunucusu çalışıyor |

Günlük 20 dakika okuyan biri için: **~2,5 ay** (her akşam okuma, arada uyku).

Tek bir sayfa çevirmenin maliyeti merak edilirse: `0.3 s × 35 mA = 0.0029 mAh`.
500 mAh'ın tamamı yalnızca sayfa çevirmeye harcansa ~170.000 sayfa ederdi —
ama gerçekte uyanık kalma süresi bunun ~100 katıdır.

---

## 2. Derin uykudaki döküm

Bekleme süresi bu tablodaki **en büyük üç kalem** tarafından belirlenir:

| Kalem | TPS63020 ile | TPS63900 ile | Nasıl azaltılır |
|---|---|---|---|
| Regülatör boşta akımı | **25 µA** | **0.075 µA** | TPS63900'e geç (PCB yeniden çizilir) |
| Pil bölücü (100k/100k) | 21 µA | 21 µA | 1 MΩ/1 MΩ → 2.1 µA |
| ESP32-C3 derin uyku | ~5 µA | ~5 µA | — |
| Regülatör geri besleme bölücüsü (1M/180k) | 2.8 µA | 0 µA | TPS63900'de bölücü yok |
| Panel derin uyku (SSD1680 Mode 1) | 1 µA | 1 µA | Mode 2 kullanılırsa 0.7 µA |
| Şarj denetleyicisi (MCP73831) | ~0.5 µA | ~0.5 µA | — |
| **Toplam** | **~55 µA** | **~28 µA** | |

```
500 mAh / 55 µA = 9.090 saat = 379 gün ≈ 12 ay
500 mAh / 28 µA = 17.857 saat = 744 gün ≈ 24 ay
```

> **Panel derin uykusu bir sürücü detayına bağlıdır.** SSD1680'in `0x10` komutu
> Mode 1'de (A[1:0] = 01) RAM'i koruyarak **1 µA** çeker; Mode 2'de 0.7 µA
> çeker ama framebuffer içeriği kaybolur. Panel uykuya girmezse (örneğin
> `epdSleep()` çağrılmazsa) tüketim **20 µA**'ya çıkar — bu, toplam bütçenin
> üçte biri demektir. `epdSleep()` çağrısının kodda kaldığını doğrulayın.
>
> Ayrıca panel uykudan **yalnızca donanımsal reset (HWRESET) ile** çıkar;
> yazılımsal reset (`0x12`) uyandırmaz. Firmware'in her uyanmada `epdHwReset()`
> çağırdığından emin olun.

> **Sürpriz:** XIAO ESP32-C3 kartı (regülatör, şarj devresi ve tüm kart
> elektroniği dahil) **44 µA** uyku akımı çeker. Yani kolay yapının bekleme
> süresi, varsayılan PCB yapısıyla **neredeyse aynıdır**. PCB yapısının avantajı
> bekleme süresi değil, **kalınlıktır** (9.5 mm / 15 mm).

### Gerçek sınır: hücrenin kendiliğinden deşarjı

Tablodaki hesap, tüketimi sıfıra indirseniz bile bir tavana çarpar. Li-Po
hücreler ayda ~%2–3 kendiliğinden deşarj olur:

```
500 mAh × %2.5/ay = 12.5 mAh/ay ≈ 17 µA ortalama eşdeğeri
```

Yani **~17 µA'nın altına inmenin pratik faydası yoktur.** TPS63900 + 1 MΩ
bölücü (~7 µA) teorik olarak 8 yıl verir, ama gerçekte 1.5–2 yılda pil
kendiliğinden boşalır. Bu yüzden:

| Hedef | Önerilen |
|---|---|
| Basitlik, tek kaynaktan sipariş | TPS63020 + 100k bölücü → 13 ay |
| Uzun bekleme isteniyorsa | Bölücüyü 1 MΩ/1 MΩ yap → 21 ay |
| Pil ömrü projenin ana hedefiyse | TPS63900 + 1 MΩ bölücü → sınır hücre deşarjı |

---

## 3. Regülatör karşılaştırması

> ⚠️ **Düzeltme:** İlk tasarımda "TPS63900, TPS63020 ile pin uyumludur" diye
> not düşülmüştü. **Bu yanlıştı.** Datasheet'ler doğrulandığında TPS63020'nin
> **14-pin VSON (DSJ), 3 × 4 mm** (SLVS916I Section 3/5), TPS63900'un ise
> **10-pin WSON (DSK), 2.5 × 2.5 mm** (SLVSET3D Table 5-1) olduğu görüldü.
> Pin sayısı, isimleri ve yerleşimi farklıdır — **PCB yerleşimi değişmek
> zorundadır.** Geçiş yapmak istiyorsanız `docs/03`'teki yerleşimi sıfırdan
> çizmeniz gerekir; bu bir "parça değişimi" değil, bir "yeniden tasarım"dır.

| | **TPS63020** (varsayılan) | **TPS63900** (düşük güç seçeneği) |
|---|---|---|
| Boşta akım | 25 µA (max 50 µA) | **75 nA** (max 1 µA) |
| Kapatma akımı | 0.1 µA | 60 nA |
| Paket | **VSON-14 (DSJ), 3 × 4 mm** | **WSON-10 (DSK), 2.5 × 2.5 mm** |
| Giriş aralığı | 1.8–5.5 V | 1.8–5.5 V |
| Çıkış | 3.3 V'ta 2 A | >400 mA (VI ≥ 2.0 V, VO = 3.3 V) |
| Çıkış ayarı | İki dirençli bölücü (`R5`/`R6`) | **CFG1/2/3 dirençleri** ile 32 hazır seviye |
| 3.3 V için ayar | `R5` = 1 MΩ, `R6` = 180 kΩ | **`CFG1` = 36.5 kΩ (%1), `CFG2` = 0 Ω, `CFG3` = 0 Ω, `SEL` = High** |
| Sürekli bölücü akımı | 2.8 µA | **0** (bölücü yok) |
| Mod pini | `PS/SYNC` (GND = tasarruf, VIN = PWM) | **Yok** — tek-mod çalışır, `SEL` pini var |
| Harici bileşenler | 1.5 µH, 2 × 10 µF, 3 × 22 µF, 0.1 µF | 2.2 µH, 10 µF, 22 µF |
| Doğrulama durumu | ✅ pinout doğrulandı | ✅ pinout doğrulandı |

**Neden varsayılan TPS63020?** Çıkış gerilimi iki dirençle ayarlanır, hesabı
şeffaftır ve `PS/SYNC` pini sayesinde ripple/verim dengesini lehim köprüsüyle
seçebilirsiniz. TPS63900'un `CFG1/2/3` dirençleri **%1 tolerans ve
±200 ppm/°C** gerektirir; sıradan %5'lik bir direnç çıkış gerilimini
kaydırabilir ve paneli riske atar.

**Geçiş yapmak isterseniz** kazanç büyüktür: 25 µA → 0.075 µA, yani toplam
uyku akımı ~51 µA'dan ~26 µA'ya iner ve bekleme süresi ikiye katlanır. Ama
`docs/03`'teki PCB'yi yeniden çizmeniz, `EPD` beslemesini yeniden doğrulamanız
ve %1'lik `CFG` dirençlerini tedarik etmeniz gerekir.

---

## 4. Uyanma akışı

```
                    ┌─ 60 s hareketsizlik ─────────────────┐
                    ▼                                      │
  ┌──────────┐   ┌───────────────────┐   ┌─────────────┐    │
  │  AWAKE   │──>│ epdSleep()        │──>│ DEEP SLEEP  │    │
  │ ~20 mA   │   │ RF kapat, panel   │   │ ~51 µA      │    │
  │          │   │ uykuya, RTC'ye    │   │             │    │
  │          │   │ durum yaz         │   │             │    │
  └──────────┘   └───────────────────┘   └──────┬──────┘    │
       ▲                                        │           │
       │                    GPIO2 veya GPIO3 LOW │           │
       └────────────────────────────────────────┘           │
              (ext1, ANY_LOW)                              │
```

Kapanmadan önce sırayla:

1. `epdSleep()` — panele derin uyku komutu (`0x10`). Panelin şarj pompasını
   kapatır; aksi halde panel ~mW mertebesinde çekmeye devam eder.
2. Wi-Fi radyosunu kapat (`WiFi.mode(WIFI_OFF)`) — 100 µA üstü tüketim yapar.
3. Kitaplık konumunu ve sayfa numarasını `RTC_DATA_ATTR` değişkenlere yaz.
   Bu alan derin uykuda korunur; flash'a yazmaya gerek yoktur (flash yazımı
   hem yavaş hem ömür tüketir).
4. `esp_deep_sleep_enable_ext1_wakeup(BIT(GPIO2) | BIT(GPIO3), ANY_LOW)`
5. `esp_deep_sleep_start()`

**Uyanma sonrası kritik UX detayı:** `setup()` içinde `was_deep_sleep` bayrağı
okunur ve cihaz **açılış ekranını atlar**. Hangi butonun basılı olduğu okunur ve
doğrudan ilgili sayfaya gidilir. Kullanıcı butona basar, ~1 saniye içinde
okuduğu sayfanın devamını görür — açılış logosu, kitaplık listesi veya menü
araya girmez. Bir okuyucunun en sık yaptığı eylem bu olduğu için en çok
özen gösterilen kısımdır.

**GPIO20 (menü) uyandıramaz** — RTC alanında değildir. Uyandıktan sonra basılır.

---

## 5. Pil gerilimi ve yüzdesi

`power.cpp` pil gerilimini şu yolla ölçer:

1. `analogReadMilliVolts(VBAT_ADC)` — ESP32-C3'ün dahili kalibrasyonunu kullanır
2. 15 örneğin **medyanı** (uç değerleri atar)
3. 8 örneğin ortalaması (gürültüyü azaltır)
4. `× 2` — bölücü oranı 1:2

Li-Po gerilim→yüzde eşlemesi doğrusal **değildir**; yük altında gerilim düşer.
Kullanılan tablo:

| Gerilim | Yüzde | Not |
|---|---|---|
| 4.20 V | 100% | Dolu |
| 4.05 V | 90% | |
| 3.95 V | 75% | |
| 3.87 V | 60% | |
| 3.80 V | 45% | Nominal |
| 3.72 V | 30% | |
| 3.65 V | 15% | |
| 3.55 V | 5% | |
| 3.40 V | 0% | **Uyarı ekranı gösterilir** |
| 3.30 V | — | Koruma devresi pili keser |

> **Not:** Gerilim ölçümü, cihaz **uyanıkken ve yüksüzken** yapılmalıdır.
> Sayfa yenilemesi sırasında ölçüm yaparsanız panelin çektiği akım gerilimi
> düşürür ve "%5" gibi yanlış bir değer görürsünüz. Firmware ölçümü yenilemeden
> önce yapar.

---

## 6. Ölçüm: gerçekten ne çektiğini nasıl bulursunuz?

Bu dokümandaki sayılar **hesaplama**dır, ölçüm değil. Kendi cihazınızı ölçmek
için:

### Yöntem 1 — USB güç ölçer (en kolay, kaba)

USB-C güç ölçer takın. Cihaz uyanıkken akımı görürsünüz; uykuda ölçer
neredeyse sıfır gösterir (çoğu ölçerin çözünürlüğü µA'ya yetmez).

### Yöntem 2 — multimetre (uyku akımı için şart)

```
USB-C ──> [ölçüm noktası] ──> cihaz
              ▲
         multimetre (mA/µA kademesi)
```

Cihazı USB'den ayırın, pili pile seri bir multimetre bağlayın (µA kademesi).
Güç anahtarı açıkken bekleyin; 60 saniye sonra uykuya geçince akımı okuyun.

> ⚠️ Multimetrenin **burden voltage**'ı (iç direnç gerilim düşümü) uyanma
> anındaki akım darbelerinde cihazı resetleyebilir. Ölçüm sırasında cihaz
> resetleniyorsa multimetrenin yüksek kademesine geçin veya kısa süre
> kısa devre yaparak uyandırın.

### Yöntem 3 — Nordic Power Profiler Kit II (en doğru)

Uyku/uyanma geçişlerini grafikte gösterir. ~$100; bir kez alıp ömür boyu
kullanılır. Uyanma süresini kısaltmak istiyorsanız hangi kodun ne kadar
sürdüğünü bu cihazla görürsünüz.

### Karşılaştırma tablosu

| Ölçüm | Beklenen | Ölçtüğünüz | Muhtemel sebep |
|---|---|---|---|
| Derin uyku, TPS63020 | ~51 µA | >200 µA | Wi-Fi kapanmadı, ya da panel uykuya girmedi |
| Derin uyku, XIAO | ~44 µA | >500 µA | NeoPixel benzeri kart üstü LED'ler, ya da seri port aktif |
| Uyanık, boşta | ~20 mA | >60 mA | Wi-Fi açık kalmış |
| Aktarım modu | ~90 mA | | |

---

## 7. İyileştirme fikirleri

| Fikir | Kazanç | Maliyet |
|---|---|---|
| TPS63900'a geç | 25 µA → 0.075 µA | Yapılandırma direnci tablosu, pinout kontrolü |
| Bölücüyü 1 MΩ/1 MΩ yap | 21 µA → 2.1 µA | `C11` değeri ve ölçüm beklemesi |
| Bölücüyü MOSFET ile kes | 21 µA → ~0 | 1 GPIO (yok) + %1 duty ile ölçüm |
| MAX17048 yakıt göstergesi | Daha doğru % + ~3 µA | I²C pini yok (GPIO8/9 dolu) |
| Uyanma süresini kısalt | Uyanık süre | Karmaşık kod — kısmi yenileme zaten 0.3 s |
| Adaptive uyku süresi | Sayfa çevirirken 60 s yerine 10 s | Kullanıcı ayarı |
| Panel uykusunu doğrula | mW → µW | `epdSleep()` çağrısının kodda kaldığından emin olun |

**En yüksek getirili tek değişiklik**, bölücüyü 1 MΩ/1 MΩ yapmaktır: iki direnç
değişir, 19 µA kazanılır, hiçbir yeni parça gerekmez.

---

Geri: [06 · Kitap ve Font Dönüştürme](06-books-and-fonts.tr.md) · Devam: [08 · Sorun Giderme](08-troubleshooting.tr.md)
