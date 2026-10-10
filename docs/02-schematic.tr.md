> English version: [02-schematic.md](02-schematic.md)

# 02 · Devre Şeması — Blok Blok Açıklama

Şema: [`hardware/schematic/pocket-reader-schematic.svg`](../hardware/schematic/pocket-reader-schematic.svg)
Bağlantı tablosu (170 bağlantı / 39 net / 64 parça): [`hardware/schematic/connections.csv`](../hardware/schematic/connections.csv)
Doğrulanmış datasheet verileri: [`hardware/schematic/pinouts.md`](../hardware/schematic/pinouts.md)

> Renk kodu: **turuncu kalın** = güç yolu · ince siyah = sinyal ·
> **mavi etiket** = net adı (aynı ad = bağlı) · **kırmızı kutu** = mutlaka
> doğrulanması gereken bilgi.

---

## A · USB-C girişi ve ESD koruması

| Parça | Değer | Görev |
|---|---|---|
| `J1` | TYPE-C-31-M-12 | 5 V giriş + veri. Yalnızca alıcı (UFP) olarak çalışır |
| `R1`, `R2` | 5.1 kΩ | CC1 ve CC2'yi GND'ye çeker |
| `U1` | USBLC6-2SC6 | D+/D− hatlarında ESD koruması |

**5.1 kΩ dirençler neden zorunlu?** USB-C'de bir cihazın "alıcı" (sink)
olduğunu, CC hattına 5.1 kΩ ile GND arasında direnç koyarak bildirir. Bu
dirençler yoksa tipik bir USB-C şarj aleti **hiç 5 V vermez** — en sık yapılan
USB-C hatası budur ve belirtisi "kablo takılı ama hiçbir şey olmuyor"dur.

**ESD koruması neden gerekli?** USB kablosuna dokunan bir insan, birkaç kV'luk
statik yük taşır ve bu doğrudan ESP32-C3'ün GPIO18/19'una gider. `U1` bunu
sönümler. Atlanabilir ama çipin ölümü sessiz ve geri dönüşsüz olur.

`U1` ayrıca `VBUS`'a bağlanır (içindeki TVS diyotlarının referansı için).

---

## B · Li-Po şarj (MCP73831)

| Parça | Değer | Hesap |
|---|---|---|
| `U2` | MCP73831T-2ACI/OT | `-2` = 4.20 V sabit (Li-Po için doğru varyant) |
| `R3` | **2 kΩ** | `I_şarj = 1000 V / R3` → **500 mA** |
| `C1` | 4.7 µF | `VDD` bypass (datasheet: min 4.7 µF) |
| `C2` | 4.7 µF | `VBAT` bypass (datasheet: min 4.7 µF, **şart**) |
| `R4` + `D1` | 470 Ω + yeşil LED | Şarj göstergesi |
| `STAT` pini | — | **Tri-state**: şarj sırasında LOW, dolunca HIGH |

**SOT-23-5 pinout** (datasheet Table 3-1): `1` = STAT · `2` = VSS · `3` = VBAT ·
`4` = VDD · `5` = PROG. **DFN paketinin pinout'u tamamen farklıdır** (1/2 = VDD,
3/4 = VBAT, 5 = STAT, 6 = VSS, 8 = PROG, 9 = EP) — yanlış paketin numaralarını
kullanmak şarj devresini bozar.

**`R3` seçimi pilinize bağlıdır.** 500 mAh pil için 500 mA ≈ 1C, sağlıklı bir
değerdir. Piliniz 250 mAh ise `R3`'ü **4 kΩ** yapın (250 mA). Geçerli aralık
**2 kΩ … 67 kΩ** (≈500 mA … 15 mA). `PROG` açık bırakılırsa şarj tamamen
devre dışı kalır.

**`STAT` neden tri-state?** Şarj sırasında pini GND'ye çeker, dolumda HIGH'a
çeker. Bu sayede LED, **VDD ile STAT arasına** bağlanır: şarj varken akım
VDD → `R4` → LED → STAT → GND yolunu izler ve LED yanar; dolduğunda iki uç da
~5 V olur ve LED söner. (LED'i GND'ye bağlarsanız hiç yanmaz — klasik hata.)
MCP73832'nin STAT'ı **open-drain**'dir; onunla bu bağlantı çalışmaz.

**`C2` neden şart?** Datasheet, `VBAT` üzerinde en az 4.7 µF ister — pil takılı
değilken (veya koruma devresi kestiğinde) şarj döngüsünün kararlı kalması için.
Atlanırsa şarj, pilsiz durumda kararsız davranır.

> MCP73831 termal olarak korumalıdır. 500 mA'da, 5 V giriş ve 3.0 V pil
> geriliminde ~1 W harcar. Küçük SOT-23-5 paketi bunu **kısa süreli** kaldırır;
> plastik kasada havalandırma bırakın veya şarj akımını düşürün.

---

## C · Batarya ve koruma

| Parça | Görev |
|---|---|
| `BT1` | 1S Li-Po, 3.0–4.2 V, 500 mAh |
| `U4` + `Q1` | DW01A + FS8205A — **yalnızca korumasız hücre kullanırsanız** |
| `SW1` | SPDT kayar anahtar: pil ile regülatör arasında |

`SW1`'in **pil ile regülatör arasında** olması bilinçlidir. Regülatörün
girişinde olsaydı, cihaz kapalıyken şarj devresi pili şarj edemezdi.
Bu konumda cihaz kapalıyken USB-C takılırsa pil normal şekilde şarj olur.

**Li-Po koruması neden şart?** Korumasız bir Li-Po'yu 3.0 V'un altına
indirirseniz hücre kalıcı olarak bozulur, 4.25 V üstüne çıkarsanız şişer ve
yangın riski doğar. Hazır korumalı hücre almak (önerilen) ya da `U4`+`Q1`
eklemek zorunludur. `U4`+`Q1` bloğu şemada **kesikli çerçeveyle (DNP — takma)**
işaretlidir.

---

## D · 3.3 V buck-boost (TPS63020)

> ⚠️ **Paket 14 pinlidir, 10 değil.** TPS63020 = **VSON-14 (DSJ), 3 × 4 mm**
> (datasheet SLVS916I, Section 3/5). Pinout: 1 = `VINA`, 2 = `GND`,
> 3 = `FB`, 4–5 = `VOUT`, 6–7 = `L2`, 8–9 = `L1`, 10–11 = `VIN`, 12 = `EN`,
> 13 = `PS/SYNC`, 14 = `PG`, alttaki termal pad = `PGND`.

| Parça | Değer | Kaynak / gerekçe |
|---|---|---|
| `U3` | TPS63020DSJR | 1.8–5.5 V giriş → 3.3 V, 2 A (VIN > 2.5 V) |
| `L1` | **1.5 µH**, ≥2 A doyum | Datasheet Table 4: `XFL4020-152ML`. Hafif yükte 2.2 µH de olur |
| `R5` / `R6` | **1 MΩ / 180 kΩ** | Datasheet **Table 3**, 3.3 V çıkış için birebir satır |
| `R7` | 100 kΩ | `EN` pull-up. `EN` **açık bırakılmamalı** |
| `C3`, `C4` | 2 × 10 µF | Giriş kondansatörleri (Table 4) |
| `C5` | 0.1 µF | `VINA` bypass. **0.22 µF'ı geçmemeli** (Section 8.2.2.5) |
| `C6`, `C7`, `C8` | 3 × 22 µF | Çıkış kondansatörleri (Table 4) |
| `C9` | 0.1 µF | Yüksek frekans bypass |
| `JP1` | 0 Ω köprü | `PS/SYNC` seçimi |

### Geri besleme dirençleri

TPS63020'nin geri besleme referansı **V_FB = 500 mV** (min 495, max 505 mV) ve
çıkış iki dirençli bir bölücüyle ayarlanır:

```
R1 = R2 × (Vout / V_FB − 1)
Vout = 0.5 V × (1 + 1M / 180k) = 0.5 × 6.556 = 3.28 V
```

Datasheet Table 3, 3.3 V çıkış için `R5 = 1 MΩ`, `R6 = 180 kΩ` verir — biz de
birebir bu satırı kullanıyoruz. Datasheet `R6`'nın ~200 kΩ civarında
tutulmasını önerir (daha küçüğü bölücü akımını artırır, daha büyüğü gürültüye
açık hale getirir).

Bölücü sürekli akımı `0.5 V / 180 kΩ = 2.8 µA`'dır — uyku bütçesinde hesaba
katılmalıdır (bkz. `docs/07`).

### PS/SYNC köprüsü (`JP1`)

| Bağlantı | Davranış | Ne zaman |
|---|---|---|
| `GND` (varsayılan) | Güç tasarrufu modu. Hafif yükte yüksek verim, çıkış ripple'ı biraz yüksek | Normal kullanım |
| `VINA` | Zorlanmış PWM. Düşük ripple, hafif yükte daha düşük verim | Ekranda hayaletlenme/kararsızlık görürseniz |

Ripple'ın e-paper'ı neden ilgilendirdiği: panelin içindeki şarj pompası
`VDD`'den ±15 V üretir. Girişte büyük ripple olursa pompa kararsızlaşır ve
görüntüde leke/hayalet oluşur. Varsayılan tasarım `GND`'dir; sorun görürseniz
köprüyü `VINA`'ya taşıyın.

### Neden buck-boost?

Pil 4.2 V → 3.0 V arasında gezer. Sabit 3.3 V gerektiği için:

- Pil 3.3 V'un **üstünde** → gerilim düşürülmeli (buck)
- Pil 3.3 V'un **altında** → gerilim yükseltilmeli (boost)

LDO kullanılsaydı pilin son %20–25'i kullanılamazdı. Ayrıca ısı olarak
`(Vpil − 3.3) × I` harcanırdı.

---

## E · ESP32-C3-MINI-1

| Parça | Değer | Görev |
|---|---|---|
| `U5` | ESP32-C3-MINI-1-N4 | RISC-V 160 MHz, 4 MB flash, Wi-Fi/BLE, 13.2 × 16.6 × 2.4 mm |
| `R8` | 10 kΩ | `EN` pull-up (datasheet: R = 10 kΩ) |
| `C10` | 1 µF | `EN` RC gecikmesi (datasheet: C = 1 µF) |
| `C11` | 10 µF | Modül 3V3 tamponu (datasheet Fig. 9-1) |
| `C12` | 0.1 µF | Yüksek frekans bypass, **modülün dibine** konur |

`R8`+`C10` kombinasyonu (10 kΩ / 1 µF = 10 ms zaman sabiti) besleme yükselirken
çipin kararsız bir gerilimde açılmasını engeller. Bu RC olmadan, bazı güç
kaynaklarında çip rastgele yeniden başlar. Espressif'in datasheet'i de tam
olarak bu değerleri verir.

### Pin atamasının mantığı

Tam gerekçe `docs/00-overview.tr.md` §2'de. Özet:

- **Strapping pinleri (datasheet Table 4-3).** SPI boot (normal çalışma) için
  **GPIO2 = 1** ve **GPIO9 = 1** olmalıdır; **GPIO8'in değeri önemsizdir** —
  GPIO8 yalnızca *joint download boot* modunda 1 olmak zorundadır ve ayrıca ROM
  mesaj bastırma için kullanılır.
  - `GPIO2` → `BTN_DOWN`: 100 kΩ pull-up açılış şartını sağlar
  - `GPIO9` → `EPD_BUSY`: **panel `BUSY` boşta HIGH olduğu için şart
    kendiliğinden karşılanır** (`R10` garanti için eklenmiştir)
  - `GPIO8` → `EPD_RST`: pull-up'a ihtiyaç duymaz ama `R9` panel reset hattını
    tanımlı tutmak için eklenmiştir
- **GPIO3 ve GPIO2** RTC alanında → sayfa butonları cihazı uykudan uyandırır
- **GPIO5** = `ADC2_CH0` → pil ölçümü (ADC1 pinlerinin hepsi kullanımda)
- **GPIO20** = `U0RXD`, yalnızca giriş → menü butonu (uyandıramaz)

> ⚠️ **BUSY polaritesi bu panel ailesinde tartışmalıdır.** SSD1680 datasheet'i
> (Rev 0.14, Table 5-2) `BUSY`'yi aktif-HIGH tanımlar (HIGH = meşgul), ancak
> bazı satıcı sürücüleri tersini varsayar. Firmware bunu `config.h` içindeki
> `EPD_BUSY_ACTIVE_HIGH` ile yapılandırılabilir yapar ve **zaman aşımına
> düşerse polaritenin yanlış olabileceğini ekrana yazar** — donanım hiçbir
> koşulda sonsuz döngüde kilitlenmez. Doğrulama yöntemi:
> [`docs/05`](05-firmware-setup.tr.md) ve `firmware/README.md`.

### Anten koruma alanı

Modülün anteni PCB kenarına taşmalı ve altında/çevresinde **hiç bakır ve hiç
parça olmamalıdır**. Bu alan ihlal edilirse menzil ciddi şekilde düşer.
Kesin ölçüler `pinouts.md` §2'de; tipik olarak anten ucundan 15 mm ileri ve
anten genişliği boyunca yanlarda 5–10 mm serbest alan gerekir.

---

## F · E-paper arayüzü (24-pin FPC)

> ✅ **Bu tablo artık doğrulanmıştır.** Pin numaraları doğrudan GoodDisplay
> GDEY0213B74 datasheet'inden (Section 5, s.8) alınmıştır. Kaynak:
> [`pinouts.md`](../hardware/schematic/pinouts.md) §1.

### FPC pin tablosu (1–24)

| Pin | Ad | Yön | Bizim netimiz | Açıklama |
|----:|---|---|---|---|
| 1 | NC | — | — | **Boş bırakılır** |
| 2 | `GDR` | → | `GDR` | N-MOSFET gate sürme (harici boost) |
| 3 | `RESE` | ← | `RESE` | Boost akım-sens girişi |
| 4 | NC | — | — | **Boş bırakılır** |
| 5 | `VSH2` | — | `VSH2` | Pozitif source sürme — 1 µF/25 V |
| 6 | `TSCL` | — | — | Sıcaklık sensörü I²C (kullanılmıyor) |
| 7 | `TSDA` | — | — | Sıcaklık sensörü I²C (kullanılmıyor) |
| 8 | `BS1` | ← | `GND` | **L = 4-wire SPI** (kullanacağımız mod) |
| 9 | `BUSY` | ← | `EPD_BUSY` | Meşgul çıkışı |
| 10 | `RES#` | ← | `EPD_RST` | Reset, aktif **düşük** |
| 11 | `D/C#` | ← | `EPD_DC` | HIGH = veri, LOW = komut |
| 12 | `CS#` | ← | `EPD_CS` | Yonga seçimi, aktif düşük |
| 13 | `SCL` | ← | `EPD_SCK` | SPI saat |
| 14 | `SDA` | ← | `EPD_MOSI` | SPI veri |
| 15 | `VDDIO` | — | `3V3` | **VCI ile birleştirilmeli** |
| 16 | `VCI` | — | `3V3` | Çip beslemesi (2.2–3.7 V, tip 3.0 V) |
| 17 | `VSS` | — | `GND` | Toprak |
| 18 | `VDD` | — | `VDD_CORE` | Çekirdek lojik (VCI'den regüle) — 1 µF/25 V |
| 19 | `VPP` | — | — | **Yalnızca test içindir** |
| 20 | `VSH1` | — | `VSH1` | Pozitif source sürme — 1 µF/25 V |
| 21 | `VGH` | — | `VGH` | Pozitif gate sürme — boost çıkışı |
| 22 | `VSL` | — | `VSL` | Negatif source sürme — 1 µF/25 V |
| 23 | `VGL` | — | `VGL` | Negatif gate sürme — 1 µF/25 V |
| 24 | `VCOM` | — | `VCOM` | VCOM sürme — 1 µF/25 V |

### Harici kondansatör şebekesi — atlanamaz

Datasheet'in referans devresi (Section 12, s.29) **sekiz adet 1 µF / 25 V**
kondansatör ister: `VCI`, `VDDIO`, `VDD`, `VSH1`, `VSH2`, `VSL`, `VGL`, `VCOM`.
Ayrıca giriş için 4.7 µF / 25 V.

**Bunlar panelin içindeki ±15 V şarj pompasının rezervuarlarıdır.** Eksik veya
yanlış değerde olurlarsa görüntü soluk, lekeli veya yarım çıkar. Hepsi 25 V
anma geriliminde olmalıdır — şarj pompası çıkışı ±15 V'a ulaşır ve 6.3 V'luk
kondansatör delinir.

### Harici VGH/VGL boost devresi

Panel, `GDR` (pin 2) ve `RESE` (pin 3) pinlerini tam olarak bu iş için çıkarır:
VGH/VGL üretimi dışarıdan yapılır. Datasheet referans devresi:

| Parça | Değer |
|---|---|
| `L2` | 47 µH / 500 mA |
| `D2`, `D3`, `D4` | MBR0530 Schottky |
| `Q2` | Si1308EDL N-MOSFET (`GDR` pinini sürer) |
| `C23`, `C24` | 4.7 µF / 25 V, 1 µF / 25 V |
| `R18`, `R19` | 1 MΩ, 2.2 Ω (`RESE`) |

> ⚠️ Bu blok, bu projede **en yüksek riskli kısımdır**: değerler datasheet'in
> referans devresinden alınmıştır ve anahtarlamalı bir yükselticidir. İlk
> prototipi kurarken **hazır bir adaptör kartı** kullanmanız şiddetle önerilir
> (aşağıdaki tabloya bakın) ve bu bloğu ancak panel datasheet'inizle birebir
> karşılaştırdıktan sonra kendi PCB'nize koyun.

### Tampon kondansatör

`C22` (100 µF, düşük ESR) panel yenileme anındaki akım darbesini emer. Panel
tipik olarak **3.5 mA** çeker (datasheet: 10.5 mW @ VCI = 3.0 V) ama yenileme
anında tepe akım çok daha yüksektir. `C22` yoksa veya `J2`'den uzaksa
"bazen ekran yarım kalıyor" hatası alırsınız — ve sebebini bulmak çok zordur.

### Ham panel mi, breakout modül mü?

| | Ham panel + kendi devreniz | **Adaptör kartı** (önerilen ilk deneme) |
|---|---|---|
| Kalınlık | ~1.05 mm (sadece cam) | ~5 mm (kart + konektör) |
| Bağlantı | 24-pin 0.5 mm FPC | 8-pin 2.54 mm header |
| Harici boost | **Sizin kurmanız gerekir** | Kartta hazır |
| Harici kapasiteler | **Sizin kurmanız gerekir** | Kartta hazır |
| Zorluk | Yüksek | Düşük — sadece jumper kablo |
| Hedef | PCB yapısı (nihai) | Kolay yapı **ve ilk PCB prototipi** |

> 💡 **Pratik öneri:** PCB'nizde 24-pin FPC konektörünün yanına **8-pin 2.54 mm
> header** için de yer bırakın. Boost devresini kurmakta zorlanırsanız adaptör
> kartını bu header'a takıp devreye alırsınız; sonra boost bloğunu doldurup
> ham panele geçersiniz. Aynı firmware ikisinde de çalışır.

---

## G · Butonlar

| Buton | GPIO | İşlev | Uyandırır? |
|---|---|---|---|
| `SW2` | 3 (`BTN_UP`) | Sayfa geri | ✅ |
| `SW3` | 2 (`BTN_DOWN`) | Sayfa ileri | ✅ |
| `SW4` | 20 (`BTN_MENU`) | Menü / kütüphane | ❌ |

Her buton: 100 kΩ pull-up (3V3'e) + 100 nF (GND'ye).

**100 nF neden var?** Mekanik butonlar kapanırken birkaç yüz mikrosaniye
boyunca sekerek onlarca kenar üretir. Yazılımsal debounce bunu çözer ama
**uyanma anında** işe yaramaz: çip uyanırken hâlâ sıçrayan bir hattı okur ve
yanlış butonu algılar. Kondansatör bu sıçramayı donanımsal olarak yok eder.
Bu yüzden her butonda hem 100 nF hem yazılımsal debounce vardır.

**Uyanma maskesi:** `ext1`, yalnızca GPIO2 ve GPIO3'ü izler
(`ESP_EXT1_WAKEUP_ANY_LOW`). GPIO20 RTC alanında olmadığı için maskeye
konulamaz.

---

## H · Pil algılama

| Parça | Değer | Hesap |
|---|---|---|
| `R16`, `R17` | 100 kΩ / 100 kΩ | Bölücü oranı 1:2 |
| `C11` | 100 nF | ADC giriş filtresi |

```
V_adc = V_pil × R17/(R16+R17) = V_pil / 2
4.20 V → 2.10 V   (ESP32-C3 ADC'sinin ölçüm aralığı içinde)
3.00 V → 1.50 V
```

Yazılım okuduğu değeri 2 ile çarpar. Sürekli akım `4.2 V / 200 kΩ = 21 µA` —
uykudaki ikinci büyük tüketim kalemi.

**Azaltmak için:** 1 MΩ/1 MΩ kullanın (2.1 µA). Ancak ADC'nin örnekleme
kondansatörünü doldurabilmesi için giriş empedansı sınırlıdır; bu durumda
`C11`'i 10 nF'e düşürüp ölçüm öncesi kısa bir bekleme ekleyin. Alternatif:
`MAX17048` I²C yakıt göstergesi (kendi bölücüsü içinde, ~3 µA) —
`docs/09`'da.

---

## Doğrulama

Bağlantı listesini tutarlılık açısından denetleyin:

```bash
cd hardware/schematic
python3 gen_netlist.py --check
```

Bu komut şunları bildirir:
- Tanımsız parça veya pin
- Tek düğümlü (bağlanmamış) net
- Hiçbir nete bağlı olmayan parça
- **Pin numarası henüz doğrulanmamış parçalar** (`UNVERIFIED`)

`connections.csv` ve `pocket-reader.net` dosyalarının ikisi de bu script'ten
üretilir; elle düzenlemeyin.

---

Geri: [01 · Malzeme Listesi](01-bill-of-materials.tr.md) · Devam: [03 · PCB](03-pcb.tr.md)
