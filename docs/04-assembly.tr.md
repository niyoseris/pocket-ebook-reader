> English version: [04-assembly.md](04-assembly.md)

# 04 · Montaj

Zorluk ve risk sırasına göre iki bölüm. Kolay yapıdaysanız §1'e, PCB'deyseniz §3'e gidin.

---

## 0 · Güvenlik (atlamayın)

> 🔋 **Li-Po piller yangın çıkarabilir.**
> - Kutup ters bağlamayın (`+` ve `−` işaretlerini iki kez kontrol edin)
> - Lehimlerken uçları **aynı anda kısa devre etmeyin** (kısa devre = anında
>   yüksek akım, hücre şişer)
> - Delinmiş, şişmiş veya yıpranmış hücreyi **kullanmayın**
> - İlk denemede USB-C'den besleyin, pili en son bağlayın
> - Şarj ederken gözetimsiz bırakmayın (ilk seferinde)

> 🖥️ **Paneli en son bağlayın.** Besleme gerilimi doğrulanmadan panel takılırsa
> panel kalıcı olarak ölür. Bkz. §4.

---

## 1 · Kolay yapı (XIAO + breakout modül)

Gerekli: havya, lehim, 30 AWG kablo, yan keski, multimetre. Süre ~1 saat.

### 1.1 Parçaları hazırlayın

XIAO ESP32-C3'ün **pinleri takılı gelmez** — 2.54 mm erkek header'ları
lehimleyin veya doğrudan kabloyu pad'e lehimleyin (daha ince olur).

### 1.2 E-paper bağlantısı

Panel modülünün 8-pin header'ında **pin isimleri yazılıdır — sıraya değil
isimlere göre bağlayın.** Farklı revizyonlarda sıra değişebilir.

| XIAO pad | GPIO | Panel modül pini (isim) | Kablo rengi (öneri) |
|---|---|---|---|
| `D2` | 4 | **CLK** (SCK) | sarı |
| `D4` | 6 | **DIN** (SDA/MOSI) | mavi |
| `D5` | 7 | **CS** | yeşil |
| `D10` | 10 | **DC** | turuncu |
| `D8` | 8 | **RST** | mor |
| `D9` | 9 | **BUSY** | beyaz |
| `3V3` | — | **VCC** | kırmızı |
| `GND` | — | **GND** | siyah |

> ⚠️ Panel modülünün `VCC` pini besleme gerilimidir. Waveshare modülleri 3.3 V
> ve 5 V kabul eder, ancak **bu projede lojik seviye 3.3 V olduğu için `VCC`'yi
> XIAO'nun `3V3` çıkışına bağlayın** — `5V` pinine değil.
> `5V`'a bağlarsanız modüldeki seviye çevirici devreye girer ve `BUSY` hattı
> 5 V'a çekilir; bu ESP32-C3'ün girişine zarar verebilir.

### 1.3 Butonlar

Her butonun bir bacağı GPIO'ya, diğeri GND'ye:

| Buton | XIAO pad | GPIO | İşlev |
|---|---|---|---|
| `SW2` | `D1` | 3 | Sayfa geri |
| `SW3` | `D0` | 2 | Sayfa ileri |
| `SW4` | `D7` | 20 | Menü / kütüphane |

Kolay yapıda **harici pull-up ve kondansatör gerekmez** — firmware dahili
pull-up'ları (`INPUT_PULLUP`) açar ve yazılımsal debounce kullanır. PCB yapısında
harici 100 kΩ + 100 nF vardır çünkü orada amaç **uyanma anında** temiz bir hat.

### 1.4 Güç

```
Li-Po (+) ──> [aç/kapa anahtar] ──> XIAO BAT+
Li-Po (−) ─────────────────────> XIAO BAT−
```

XIAO ESP32-C3'ün **kendi şarj devresi vardır** (380 mA hızlı / 40 mA trickle).
USB-C takıldığında pili kendisi şarj eder. **Ayrı bir TP4056 modülü
bağlamayın** — iki şarj devresi paralel çalışırsa pil zarar görür.

Anahtar pili XIAO'dan ayırır; USB-C takılıyken de şarj devam eder (XIAO'nun
şarj girişi anahtardan bağımsızdır).

### 1.5 İlk açılış

1. USB-C'yi takın (pil bağlı değilken)
2. XIAO üzerindeki güç LED'i yanmalı
3. `3V3` pad'inde 3.3 V ölçün
4. Doğruysa paneli takın
5. Firmware'i yükleyin (`docs/05`)

---

## 2 · FPC kablosuna davranış kuralları

Ham panel kullanıyorsanız bu bölüm kurtarıcıdır. FPC kabloları kırılgandır ve
koptuğunda tamir edilemez.

| Yapmayın | Yapın |
|---|---|
| Kabloyu keskin katlayın | En az **3 mm** yarıçapla katlayın |
| Kabloyu çekerek çıkarın | Konektörün kilidini açıp düz çekin |
| Konektöre yarım takın | Uçlarını görünmeyecek kadar sonuna kadar itin |
| Temas yüzeyine parmakla dokunun | Kenarlardan tutun (yağ teması = temassızlık) |
| Lehimlemeden önce bükmeyi deneyin | Önce kuru provasını yapın, sonra lehimleyin |

**Temas yönü:** Konektörün "üst temaslı" (top contact) veya "alt temaslı"
(bottom contact) olması, kablonun mavi/siyah yüzünün hangi tarafa bakacağını
belirler. Yanlış takarsanız panel ters bağlanır ve hiç görüntü vermez.

**Doğrulama:** Panel takılı ama besleme kapalıyken multimetreyle süreklilik
ölçün — panelin `GND` pininden kartın GND'sine kısa devre olmalı, `VDD` ile GND
arasında **olmamalı**. Yanlış yön takıldıysa burada yakalarsınız.

---

## 3 · PCB montajı (SMD)

### 3.1 Sıra

Elle lehimliyorsanız **en zoru en önce** yapın — kart temizken ve çevresinde
yer varken:

| # | Parça | Paket | Not |
|---|---|---|---|
| 1 | `U3` TPS63020 | VSON-10, 0.5 mm pitch | **En zor.** Altındaki termal pad'i lehimlemek gerekir |
| 2 | `U5` ESP32-C3-MINI-1 | modül, 1.27 mm pitch | Kenar pad'leri; modül altına lehim akmamasına dikkat |
| 3 | `U2` MCP73831 | SOT-23-5 | |
| 4 | `U1` USBLC6-2SC6 | SOT-23-6 | |
| 5 | `L1` | 3×3 mm | |
| 6 | 0603 pasifler | 0603 | Dirençler ve küçük kondansatörler |
| 7 | 0805 pasifler | 0805 | `C1`, `C2`, `C4`, `C5`, `C7`, `C10` |
| 8 | `J1` USB-C | 16-pin | Kenar pad'leri, ısı emer — biraz daha uzun süre |
| 9 | `J2` FPC | 24-pin 0.5 mm | Panel en son takılır |
| 10 | `SW1`–`SW4` | | En son |

**Yöntem:** lehim pastası + sıcak hava (veya kontrollü tost fırını) en
güveniliridir. Elle lehimliyorsanız ince uç, 0.5 mm lehim teli ve bol flux
kullanın; VSON-10 ve SOT-23-5 için sıcak hava neredeyse zorunludur.

> **Kolay yol:** JLCPCB'nin montaj hizmetini kullanın ve `U3`, `U2`, `U5`'i
> onlara lehimletin. Geri kalanı elle yapın. Bkz. `docs/03` §6.

### 3.2 Bileşen yerleşiminde sık yapılan hatalar

| Hata | Sonuç |
|---|---|
| `C2` (10 µF) U3'ten uzak | Verim düşer, regülatör kararsız çalışır |
| `C9` (0.1 µF) modülden uzak | Modül rastgele reset olur |
| `C10` (100 µF) J2'den uzak | Ekran bazen yarım yenilenir |
| `R5`/`R6` yanlış değer | Çıkış 3.3 V olmaz → **panel ölür** |
| `U1` yönü ters | USB çalışmaz |
| Direnç 100 kΩ yerine 100 Ω | Butonlar sürekli basılı görünür |

Her lehimlemeden sonra **ilgili nette süreklilik ölçün**; bir sonraki parçaya
geçmeden doğrulayın.

---

## 4 · 🛑 İlk güç verme (panelsiz)

Bu bölümü atlamayın. Yanlış gerilim paneli saniyeler içinde öldürür.

| Adım | İşlem | Beklenen |
|---|---|---|
| 1 | USB-C takılı, **pil bağlı değil**, **panel bağlı değil** | — |
| 2 | `C4` üzerinde gerilim ölç | **3.25 – 3.35 V** |
| 3 | Yanlışsa `R5`/`R6` ve lehimlerini kontrol et | Durdurun, panele dokunmayın |
| 4 | `U5` 3V3 pininde ölç | Aynı gerilim |
| 5 | USB'yi çıkar, pili bağla, anahtarı aç | Aynı ölçüm |
| 6 | USB'yi tak, şarj LED'i (`D1`) yanıyor mu? | Pil doluysa yanmaz — normal |
| 7 | **Şimdi** paneli tak | — |
| 8 | Firmware'i yükle (`docs/05`) | Ekran birkaç saniye içinde görüntü verir |

**Ekran hiç görüntü vermiyorsa:** önce `RST` ve `BUSY` hatlarını osiloskopla
veya multimetreyle kontrol edin. `BUSY` boşta HIGH olmalıdır. LOW'da kalıyorsa
panel meşgul sanıyor demektir — büyük olasılıkla FPC ters takılmıştır.

---

## 5 · Kasa montajı

```bash
# Kasa dosyasını düzenle (ölçüleri kendi parçalarınıza göre)
open hardware/enclosure/case.scad

# STL üret
openscad -o case_body.stl -D 'PART="body"' hardware/enclosure/case.scad
openscad -o case_lid.stl  -D 'PART="lid"'  hardware/enclosure/case.scad
```

**Baskı ayarları:** 0.2 mm katman, 3 perimetre, %20 dolgu, PLA veya PETG,
destek gerekmez.

**Sıra:**

1. **Önce sadece panel yatağını basın** (`PART="panel_test"` benzeri bir
   seçenek varsa) — panele uyup uymadığını 40 dakikalık baskıyı bitirmeden
   görün. Uymuyorsa parametreleri düzeltin.
2. Tam gövdeyi basın.
3. Paneli yatağa oturtun, FPC'yi arkadan geçirin.
4. PCB'yi yükselticilere vidalayın (4× M1.6 × 4 mm).
5. Pili cebe yerleştirin (ince çift taraflı bant ile sabitleyin).
6. Butonların kasa delikleriyle hizalandığını kontrol edin.
7. Kapağı kapatın, vidalayın.
8. USB-C kablosunu takıp şarjın çalıştığını doğrulayın.

**Kalınlık bütçesi** (kasa neden 13 mm?):

| Katman | mm |
|---|---|
| Ön duvar (panel kenarı üstünde) | 1.2 |
| Panel camı | 1.05 |
| FPC katlanma boşluğu | 0.8 |
| PCB | 1.6 |
| PCB arka yüzü en yüksek parça (modül) | 2.5 |
| Li-Po hücre (402025) | 4.0 |
| Arka duvar | 1.6 |
| **Toplam** | **~12.8 → 13.0** |

Panel veya pil değiştirirseniz bu tabloyu yeniden hesaplayın; `case.scad`
içindeki `case_h` parametresi bu toplamdan türetilir.

---

## 6 · Montaj sonrası kontrol listesi

- [ ] Ekran görüntü veriyor, metin okunabilir
- [ ] Görüntü ters değil (ters ise `config.h` → `EPD_MIRROR_X`/`Y`)
- [ ] Üç buton da doğru işlevi yapıyor
- [ ] Sayfa çevirme kısmi yenileme kullanıyor (tam ekran yanıp sönmüyor)
- [ ] 60 saniye dokunmayınca uykuya geçiyor
- [ ] Sayfa butonuyla uyanıyor ve **açılış ekranı atlanıyor**
- [ ] Wi-Fi aktarım modu açılıyor, ekranda IP görünüyor
- [ ] Tarayıcıdan `http://pocketreader.local` açılıyor
- [ ] Şarj çalışıyor (USB takılınca LED yanıyor)
- [ ] Pil yüzdesi ekranda makul bir değer gösteriyor

---

Geri: [03 · PCB](03-pcb.tr.md) · Devam: [05 · Yazılım Kurulumu](05-firmware-setup.tr.md)
