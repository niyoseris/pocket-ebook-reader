> English version: [03-pcb.md](03-pcb.md)

# 03 · PCB Tasarımı

Kolay yapıyı seçtiyseniz bu dokümanı atlayın. PCB yapısı için:

| Özellik | Değer |
|---|---|
| Ölçü | **45 × 24 mm** |
| Katman | 2 (üst: sinyal + güç · alt: GND düzlemi) |
| Kalınlık | 1.6 mm |
| Yüzey | ENIG (HASL de olur; ENIG ince pitch'te daha güvenli) |
| En küçük iz genişliği | 0.25 mm |
| En küçük boşluk | 0.2 mm |
| Via | 0.3 mm delik / 0.6 mm ped |
| Bakır kalınlığı | 1 oz |

> Bu ölçüler JLCPCB'nin standart (en ucuz) kategorisindedir — ek ücret çıkmaz.
> 5 adet ~$2 + kargo.

---

## 1. Yerleşim planı

Kartı **yatay (landscape)** yerleştirin; cihaz öne bakan ekranla yatık durur.

```
   ┌──────────────────────────────────────────────────────┐
   │  [U5 ESP32-C3-MINI-1]        [J2 FPC 24P]            │  ◀ üst kenar = panel tarafı
   │   ▲ anten ─┐                  ▲                      │
   │            │                  │                      │
   │  ┌─────────┴──┐   ┌───────────┴────┐                 │
   │  │ ANTEN      │   │                │                 │
   │  │ KORUMA     │   │   L1  U3       │                 │
   │  │ ALANI      │   │   ┌──┐ TPS63020│                 │
   │  │ (bakır YOK)│   │   └──┘         │                 │
   │  └────────────┘   └────────────────┘                 │
   │                                                       │
   │  [U2 MCP73831]   [U1 USBLC6]   [SW1 konektör]        │
   │                                                       │
   │  [J1 USB-C]                     [SW2] [SW3] [SW4]     │  ◀ alt kenar
   └──────────────────────────────────────────────────────┘
```

Kritik yerleşim kuralları:

| Kural | Neden |
|---|---|
| **Anten modülün kenarından taşsın** | Menzil. Modülün anteni kart kenarında olmalı |
| **Anten altında ve çevresinde bakır olmasın** | Aynı sebep — bakır düzlem anteni detune eder |
| **`C9` (0.1 µF) modülün 3V3 pininin dibinde** | Bypass kondansatörünün izi ne kadar kısaysa o kadar etkili |
| **Buck-boost'un "sıcak döngüsü" minimum olsun** | Aşağıda ayrı başlık |
| **FB izi indüktörden uzak dursun** | İndüktörün manyetik alanı FB'ye kaplırsa çıkış gerilimi kayar |
| **J2 (FPC) üst kenarda, L1'den uzak** | Panel kablosu indüktörün alanından geçerse görüntüde gürültü oluşur |
| **`C10` (100 µF) J2'nin dibinde** | Panelin akım darbesi en kısa yoldan karşılanmalı |

---

## 2. Buck-boost yerleşimi (en kritik kısım)

Anahtarlamalı regülatörlerde PCB yerleşimi, şemadan daha belirleyicidir. Kötü
yerleşim çalışmayan bir kart demektir.

**Sıcak döngü (hot loop)** şu yoldur:

```
C2 (+) → U3 VIN → (iç anahtarlar) → U3 PGND → C2 (−)
```

Bu döngünün **çevrelediği alanı olabildiğince küçültün**. Her mm² ek alan,
çevreye yayılan anahtarlama gürültüsünü artırır ve verimi düşürür.

Pratikte:

1. `C2` (10 µF) giriş kondansatörünü **U3'ün VIN ve PGND pinlerinin hemen
   yanına** koyun; iz uzunluğu < 3 mm olsun.
2. `L1`'i U3'e mümkün olduğunca yakın koyun; L1–L2 izleri kısa ve **kalın**
   (0.6 mm) olsun.
3. `C4`/`C5` çıkış kondansatörlerini VOUT pininin yanına koyun.
4. Alt katmanı **kesintisiz GND düzlemi** yapın; üst katmanda güç izlerinin
   altında via ile toprağa inin.
5. Regülatörün çevresine **toprak dikiş via'ları** (stitching vias) koyun —
   döngü akımının düzlemden dönmesini sağlar.
6. `R5`/`R6` geri besleme dirençlerini U3'ün FB pinine yakın koyun ve FB izini
   **L1'in altından/yanından geçirmeyin**.

---

## 3. İz genişlikleri

| İz | Genişlik | Akım |
|---|---|---|
| `VBUS`, `VBAT`, `VBAT_SW` | 0.6 mm | ~500 mA |
| `3V3` ana dağıtım | 0.5 mm | ~400 mA tepe |
| `L1` ↔ U3 (L1/L2 pinleri) | 0.6 mm | ~1 A tepe |
| SPI (`SCK`, `MOSI`) | 0.25 mm | Sinyal |
| Buton, ADC | 0.25 mm | Sinyal |
| GND | Düzlem | — |

`EPD_SCK`/`EPD_MOSI` için empedans kontrolü **gerekmez**: SPI saat hızı
4–10 MHz arasındadır ve iz uzunluğu 30 mm'nin altındadır. Seri sonlandırma
direnci de gerekmez.

---

## 4. Anten koruma alanı

> ⚠️ Bu alan ihlal edilirse Wi-Fi menzili 10 metrenin altına düşer ve sorunun
> sebebi elektriksel olarak görünmez — sadece "çekmiyor" dersiniz.

Kesin ölçüler `pinouts.md` §2'de. Genel kural:

Espressif Hardware Design Guidelines (s.23, Fig. 21) kesin ölçüleri verir:

- Antenin **solunda, üstünde ve sağında en az 15 mm** bakır/bileşen/iz olmasın
- Modül gövdesine bakan yönde **6 mm** serbest alan bırakın
- Bu alanın altında da (alt katman) **bakır düzlem kesilsin** — GND düzlemini
  bu bölgede boşaltın
- Kasa baskısında bu bölgeye plastik bile koymayın; **ürün muhafazası içinde her
  yönde en az 15 mm** boşluk bırakın
- Modülü kartın **merkezine** yerleştirip dört yandan oyuk açmak **yanlıştır**

**Bu tasarımın anten durumu (dürüst kayıt).** `placement.csv`'de modül (U5) sol
kenara **tam dayanır** (x = 0), dışarı taşmaz; altında ve çevresinde 7 × 14 mm'lik
bakırsız bir koruma alanı vardır. Kasanın sol duvarına uzaklık
`(62 − 45) / 2 = 8.5 mm`'dir. Espressif ürün muhafazası içinde **15 mm** önerir,
yani bu ölçü önerinin altındadır:

| Durum | Değerlendirme |
|---|---|
| Plastik kasa (bu tasarım) | 8.5 mm kabul edilebilir; RF plastikten geçer, kayıp beklenmez |
| Metal veya karbon kaplı kasa | **Yetersiz** — `ESP32-C3-MINI-1U` (U.FL) kullanıp anteni dışarı alın |
| Modülü döndürme seçeneği | Kartın kısa kenarlarında boşluk 4 mm — daha kötü. Sol/sağ en iyi yön |

Ölçüyü iyileştirmek isterseniz: kartı kasada sola yaslayın (kart 4 mm sola
kayarsa mesafe 12.5 mm olur) veya kasayı 66 mm'ye çıkarın.

> 45 × 24 mm'lik bir kartta 15 mm'lik yan boşluk **sığmaz**. Bu yüzden bu boyutta
> ya anteni kart kenarından taşıracak şekilde yerleştirin (tek yön yeterli) ya da
> **ESP32-C3-MINI-1U** (harici anten konnektörlü) varyantını kullanıp U.FL
> anten takın — o varyantta keep-out alanı yoktur ve metal kasa hedefliyorsanız
> doğru seçim budur.

`ESP32-C3-MINI-1U` (harici anten konnektörlü varyant) kullanırsanız bu kısıt
ortadan kalkar ve U.FL anten takabilirsiniz — metal kasa hedefliyorsanız doğru
seçim budur.

---

## 5. Panelin karta bağlanması

Ham panel 24-pin, 0.5 mm pitch FPC ile bağlanır. İki seçenek:

| Yöntem | Zorluk | Kalınlık | Not |
|---|---|---|---|
| **FPC konektörü** (önerilen) | Orta | İnce | Hirose FH12-24S-0.5SH, alt temaslı, kilitlemeli |
| Doğrudan lehim | Yüksek | En ince | FPC'yi karta lehimlemek kalıcıdır ama geri dönüşü yok |

Konektör kullanıyorsanız **kartın üst kenarına** yerleştirin ki panel katlanıp
kartın üstüne otursun. Panel kablosunun katlanma yarıçapı en az 3 mm olmalıdır;
keskin katlama iletkenleri kırar.

**Yön kontrolü:** FPC konektörlerinin "üst temaslı" ve "alt temaslı" varyantları
vardır ve **yanlış olanı alırsanız panel ters bağlanır.** Paneli ilk takışta
`RST` ve `BUSY` hatlarını ölçerek doğrulayın (bkz. `docs/04` §4).

---

## 6. Üretim dosyaları

Depoda hazır Gerber **yoktur** — çünkü pinout doğrulaması tamamlanmadan üretim
dosyası üretmek sorumlu olmaz. Kendi dosyanızı şöyle oluşturun:

```bash
# 1. Bağlantı listesini doğrula
cd hardware/schematic
python3 gen_netlist.py --check          # eksik pin numaralarını gösterir

# 2. pinouts.md'den pin numaralarını gen_netlist.py içindeki PINMAP'e işle
#    (13 adet UNVERIFIED girişi kalmıştı)

# 3. Netlist'i yeniden üret
python3 gen_netlist.py

# 4. KiCad'de:
#    pcbnew → File → Import → Netlist → pocket-reader.net
#    Parçaları yerleştir (yukarıdaki yerleşim planına göre)
#    İzleri çek, GND düzlemini doldur
#    File → Fabrication Outputs → Gerbers
```

### JLCPCB sipariş ayarları

| Ayar | Değer |
|---|---|
| Katman | 2 |
| Ölçü | 45 × 24 mm |
| Miktar | 5 |
| Kalınlık | 1.6 mm |
| Yüzey | ENIG |
| "Parts Library" montaj | **TPS63020 + MCP73831 + ESP32-C3-MINI-1 için önerilir** |

Montaj hizmetini kullanırsanız en zor iki SMD parçayı (VSON-10 ve SOT-23-5)
kendiniz lehimlemek zorunda kalmazsınız; maliyet ~$15 artar, başarı oranı
belirgin şekilde yükselir.

---

## 7. Üretim öncesi kontrol listesi

- [ ] `python3 gen_netlist.py --check` temiz (UNVERIFIED girişi yok)
- [ ] Anten koruma alanında bakır yok (hem üst hem alt katman)
- [ ] Sıcak döngü alanı minimum; `C2` U3'ün dibinde
- [ ] `C9` modülün 3V3 pininin dibinde
- [ ] `C10` J2'nin dibinde
- [ ] FB izi indüktörden uzak
- [ ] Alt katman kesintisiz GND düzlemi (anten bölgesi hariç)
- [ ] Regülatör çevresinde dikiş via'ları var
- [ ] Kart ölçüsü kasaya sığıyor (45 × 24 mm, `case.scad` içindeki boss
      konumlarıyla eşleşiyor)
- [ ] Buton delikleri kasa duvarındaki deliklerle hizalı
- [ ] USB-C konektörü kenardan 0.5–1 mm dışarı taşıyor (kasa kalınlığı kadar)

---

## 8. İlk güç verme

> 🛑 **Paneli bağlamadan önce `3V3` rayını ölçün.** Regülatör 3.3 V yerine
> yanlış bir gerilim veriyorsa (örneğin 5 V), panel bir saniyede ölür ve geri
> dönüşü yoktur.

Sıra:

1. **Panelsiz, pilsiz** — yalnızca USB-C takın
2. `U3` çıkışında (C4 üzerinde) **3.25–3.35 V** ölçün
3. Değilse `R5`/`R6` değerlerini ve lehimlerini kontrol edin — panele dokunmayın
4. Doğruysa `U5` 3V3 pininde de aynı gerilimi doğrulayın
5. USB'yi çıkarın, pili bağlayıp anahtarı açın, aynı ölçümü tekrarlayın
6. Hepsi doğruysa paneli takın ve firmware'i yükleyin

Detaylı adımlar: [`docs/04-assembly.tr.md`](04-assembly.tr.md) §4

---

Geri: [02 · Devre Şeması](02-schematic.tr.md) · Devam: [04 · Montaj](04-assembly.tr.md)
