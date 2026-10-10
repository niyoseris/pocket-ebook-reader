# Pocket Reader — 3B Basılabilir Kasa

2.13" (250 × 122) e-paper panel, ESP32-C3 ve 402025 LiPo pil için iki parçalı,
parametrik bir kasa. Tamamı `case.scad` içinde tanımlıdır; ölçüler kumpasla
ölçülüp üstteki `// --- PARAMETRE ---` bloğundan güncellenir.

| Ölçü | Değer |
|---|---|
| Dış genişlik (X) | 62.0 mm |
| Dış derinlik (Y) | 32.0 mm |
| **Dış kalınlık (Z)** | **13.0 mm** |
| Et kalınlığı | 1.6 mm |
| Ön yüzdeki bezel (çerçeve) | 1.4 mm |
| Cam dış hattı | 59.2 × 29.2 × 1.05 mm |

> **Önemli — 9.5 mm değil 13.0 mm.**
> İlk taslakta 9.5 mm düşünülmüştü; bu kalınlıkta parçalar üst üste sığmaz ve
> kapak kapanmaz. Gerçek yığın 12.75 mm tutuyor, o yüzden dış kalınlık
> **13.0 mm**'dir. Aşağıdaki tabloya bakın.

---

## 0. Dış ölçüler nereden geliyor (58 × 30 değil, 62 × 32)

`case_w` ve `case_d` **serbest seçilmiş sayılar değildir**; panelin camından
türetilir:

| Katkı | Değer |
|---|---|
| 2.13" panelin cam dış hattı (Waveshare "Outline (screen only)") | 59.2 × 29.2 mm |
| Ön yüzde camın çevresinde kalan bezel çerçevesi (2 kenar) | 2 × 1.4 mm |
| **Toplam → `case_w` × `case_d`** | **62.0 × 32.0 mm** |

**Eski 58 × 30 mm'lik değerler yanlıştı:** 59.2 mm'lik cam 58 mm'lik bir kasaya
hiç girmiyordu — panel takılamıyordu. Doğru kontrol: `62.0 − 59.2 = 2.8`, yani
her yanda **1.4 mm** bezel. Dar ama gerçek bir tam-yüzey (flush bezel) cihazda
beklenen ölçü budur.

Cam bu çerçevenin **arkasına**, içten açılan yuvaya bırakılır: cam ön yüzün
1.2 mm gerisine gömülür (`lip_depth`), ön yüzde 1.4 mm'lik bezel kalır. Camı
önden geçirmeye çalışmayın — 59.2 mm'lik cam 1.4 mm'lik çerçeveden geçmez.

> **Paneli değiştirirseniz:** ÖNCE `panel_glass_w` / `panel_glass_h` değerlerini
> (camın gerçek dış hattı) ve `bezel_lip` değerini güncelleyin, SONRA
> `case_w = panel_glass_w + 2 * bezel_lip` ve
> `case_d = panel_glass_h + 2 * bezel_lip` ile dış ölçüleri yeniden türetin.
> `case.scad` bunu her çalıştırmada konsola yazar ve cam sığmıyorsa uyarır
> (`CASE:` ve `UYARI:` satırları).

---

## 1. Kalınlık bütçesi (Z yığını)

Önden arkaya, tüm katmanlar:

| # | Katman | Kalınlık | z aralığı (mm) |
|---|---|---|---|
| 1 | Panel kenarı üzerindeki ön duvar (cam yuvası derinliği) | 1.20 mm | 0.00 – 1.20 |
| 2 | Panel camı (2.13" e-paper) | 1.05 mm | 1.20 – 2.25 |
| 3 | FPC katlanma payı | 0.80 mm | 2.25 – 3.05 |
| 4 | PCB | 1.60 mm | 3.05 – 4.65 |
| 5 | Kartın arka yüzündeki en yüksek parça (ESP32-C3-MINI-1 = 2.4 mm) | 2.50 mm | 4.65 – 7.15 |
| 6 | Li-Po pouch hücre (402025) | 4.00 mm | 7.15 – 11.15 |
| 7 | Arka duvar (kapak levhası) | 1.60 mm | 11.15 – 12.75 |
|   | **TOPLAM** | **12.75 mm** | |
|   | **`case_h` (dış kalınlık)** | **13.00 mm** | emniyet payı **0.25 mm** |

Bu 0.25 mm, pilin üzerine konan köpük/sünger pulu için ayrılmıştır: 4.5 mm'lik
pil yuvasının 0.5 mm'si köpük payıdır (`foam_allow`) ve kapak kapatıldığında
0.25 mm'ye kadar sıkışır.

### Panel ya da pili değiştirirseniz

`case_h`'ı **tahmin etmeyin**. `case.scad` yığını kendisi hesaplar:

```scad
stack_total = lip_depth + panel_t + fpc_clearance + pcb_t + rear_parts
            + cell_t + lid_t;
stack_slack = case_h - stack_total;
```

OpenSCAD'ı çalıştırdığınızda konsola şu satırlar düşer:

```
STACK: katmanlar = 12.75 mm, case_h = 13 mm, emniyet payı = 0.25 mm
STACK: cam ustu = 2.25, PCB = 3.05..4.65, pil = 7.15..11.15, kapak ici = 11.4
```

Pay negatife düşerse `UYARI: parçalar sığmıyor!` mesajı çıkar; `case_h`'ı
`stack_total`'a çekin. Örneğin 5.5 mm'lik bir pil (602025) kullanırsanız
`stack_total` 14.25 mm olur ve `case_h` en az 14.5 mm olmalıdır.

---

## 2. Baskı

```bash
# Tek dosyada gövde + kapak (yan yana)
openscad -o kasa.stl case.scad

# Ayrı ayrı
openscad -o govde.stl -D 'PART="body"' case.scad
openscad -o kapak.stl -D 'PART="lid"'  case.scad
```

OpenSCAD yoksa: <https://openscad.org/downloads.html>
(`brew install --cask openscad` / `sudo apt install openscad`)

### Dilimleyici ayarları

| Ayar | Değer |
|---|---|
| Katman yüksekliği | 0.2 mm |
| İlk katman | 0.25 mm |
| Perimeter | 3 |
| Dolgu | %20 (gyroid veya grid) |
| Malzeme | PLA **veya** PETG (ikisi de olur) |
| Destek | **YOK** |
| Nozzle | 0.4 mm |

### Yönelim

Gövdeyi **ön yüzü (panel tarafı, z = 0) yatağa gelecek** şekilde basın. Bu
yönelimde:

* Panel penceresi ve cam yuvası doğrudan yatağa bakar — köprü yok.
* Yan duvarlar dikey büyür, destek gerekmez.
* Pil tutucusunun iki duvarı gövde yan duvarlarına dayanır, havada kalmaz.
* Vida gusset'leri köşelerde iki duvara birden yaslanır.
* 1.4 mm'lik bezel çerçevesi ve cam yuvasının 1.3 mm'lik dudak halkası ilk
  katmanlarda oluşur; bu yüzden ilk katmanı 0.25 mm alın ve yatağı iyi
  temizleyin.

Kapak düz bir levhadır; hangi yüzü yatağa gelirse gelsin destek gerekmez.

---

## 3. İlk deneme baskısı (şiddetle önerilir)

Pencere ve cam yuvası ölçüleri panele göre **mutlaka** değişir. Tam kasayı
basmadan önce sadece panel yuvasını basın (~15 dakika):

```bash
openscad -o panel_test.stl -D 'PART="panel_test"' case.scad
```

Sonra:

1. Panel camını yuvaya bırakın. **Hafif boşluk olmalı, zorlanmamalı.**
   (Camı ön yüzden değil, **içten/arkadan** yuvaya bırakın.)
2. Camı yuvaya oturtup ön yüzden bakın: aktif alan (250 × 122 px) tamamen
   görünüyor mu? Pencere kenarları aktif alanı kesiyorsa `window_w` /
   `window_h` değerlerini büyütün.
3. Cam sıkışıyorsa `glass_lip_w` / `glass_lip_h` değerlerini 0.2 mm artırın.
4. Cam yuvada çok oynuyorsa 0.2 mm azaltın.

Baskı toleransı yazıcıdan yazıcıya değişir; 0.2 mm'lik adımlarla denemek
en hızlı yoldur.

---

## 4. Ölçüp güncellenmesi gereken parametreler

Aşağıdakiler `case.scad` içinde **"ölçüp güncelleyin"** diye işaretlidir.
Hepsi kumpasla ölçülmelidir; verilen değerler tipik değerlerdir.

| Parametre | Ne ölçülür | Tipik |
|---|---|---|
| `window_w` / `window_h` | Panelin görünen alanı + 0.2 mm | 49.0 × 24.1 mm |
| `glass_lip_w` / `glass_lip_h` | Camın gerçek ölçüsü + 0.2 mm | 59.4 × 29.4 mm |
| `panel_glass_w` / `panel_glass_h` | Camın gerçek dış hattı (bundan `case_w/d` türer) | 59.2 × 29.2 mm |
| `bezel_lip` | Ön yüzde camın çevresinde kalan çerçeve | 1.4 mm |
| `pcb_w` / `pcb_h` | Kartın dış hattı | 45.0 × 24.0 mm |
| `pcb_hole_inset` | Montaj deliklerinin kart kenarından uzaklığı | 2.5 mm |
| `pcb_hole_d` | M1.6 vidanın geçtiği delik | 1.9 mm |
| `cell_w` / `cell_l` / `cell_t` | Pilin gerçek ölçüsü | 20 × 25 × 4 mm |
| `usb_w` / `usb_h` / `usb_x` | USB-C ağzının ölçüsü ve konumu | 9.0 × 3.4 mm |
| `usb_z` | Konnektörün ön yüzden yüksekliği | 3.95 mm |
| `sw_w` / `sw_h` / `sw_y` | Anahtar dili ve konumu | 4.0 × 1.6 mm |
| `btn_*` | Tuş delikleri, aralık ve yükseklik | 3.0 mm / 5.0 mm |
| `fpc_x` / `fpc_w` | FPC'nin panelden çıktığı yer | ortada / 12 mm |

### Bağlantı yükseklikleri en kritik olanlar

USB-C, anahtar ve tuş delikleri **kart üzerindeki parçaların yüksekliğine**
göre yerleştirilir. `usb_z`, `sw_z` ve `btn_z` yalnızca tahmindir
(`z_pcb_front + pcb_t/2 ...`). Doğru değeri bulmak için:

1. Kartı kulelere vidalayın (ya da geçici olarak yapıştırın).
2. Kumpasın derinlik ucuyla ön yüzden konnektörün merkezine olan mesafeyi ölçün.
3. `usb_z` değerini o sayıya ayarlayın.
4. Aynısını anahtar ve tuşlar için yapın; her tuş ayrı yükseklikte olabilir,
   bu yüzden `btn_dz` ile her tuşa ayrı Z kaydırması verilebilir.

Yanlış yükseklikte açılan delik kullanışsızdır ama kasa kapanmaz değil —
bu yüzden önce kartı yerleştirip ölçmek en güvenli yoldur.

---

## 5. Kapak ve vidalar

Kapak, gövdeye **dıştan** geçen 1.0 mm'lik bir bilezikle oturur:
gövdenin dış yüzeyinde 1.0 mm derinliğinde bir basamak vardır, kapağın
bileziği oraya geçer. Bu sayede kapağın içeri doğru uzanan dudağı **yoktur** —
pil tutucusu ve kartla çakışmaz, kapak her zaman tam kapanır.

### Vida listesi

| Parça | Adet | Not |
|---|---|---|
| M1.6 × 4 mm sac vidası (self-tapping) | **4** | Köşe gusset'lerine girer |
| M1.6 × 4 mm sac vidası (PCB için) | 4 | PCB kulelerine girer (opsiyonel) |

`screw_d = 1.6 mm`, derinlik `screw_depth = 5.0 mm`'dir. PLA'da ilk vidalamayı
elle, hafif bastırarak yapın; PETG'de daha rahat döner.

Vidaları sıkarken **aşırı zorlamayın**: M1.6 dişleri plastiği kolayca sıyırır.

### Snap-fit alternatifi

Vida istemiyorsanız:

```bash
openscad -o kasa.stl -D 'PART="body"' -D 'use_snaps=true' case.scad
```

`use_snaps = true` olduğunda vidalı gusset'ler ve kapak delikleri devre dışı
kalır, yerine üst ve alt kenarda iki kanca gelir. Snap-fit, M1.6 vidadan
daha az güvenilirdir ve sık açılıp kapanınca gevşer — sürekli açmayacaksanız
vidalı sürümü kullanın.

---

## 6. Pil

Pil yuvası **26 × 21 × 4.5 mm**'dir:

* Hücre 20 × 25 × 4.0 mm (402025), 25 mm'lik kenarı kasanın **uzun ekseni**
  boyunca uzanır. 0.5 mm `pocket_clear` payı her kenara eklenir → 26 × 21 mm.
* 0.5 mm `foam_allow` kalınlığa eklenir → 4.5 mm.
* Hücre, köşelerdeki 4 desteğin üzerine oturur; iki uzun duvar (X yönünde,
  gövde yan duvarlarına dayanır) ve iki kısa duvar onu yatayda tutar.
* Taban plakası **kasten yoktur**: PCB'nin arkası ile kapağın içi arasında
  yalnızca 6.75 mm var; 2.5 mm'si arka parçalara, 4.0 mm'si hücreye gider.
  Bu yüzden hücre köşe yastıklarına oturur, ortada ESP32 modülü boşta kalır.

Pili yerleştirmeden önce **kabloları lehimleyin** ve uçlarına ısı büzüşmeli
makaron geçirin. Pil yuvaya sıkışmadan girmeli; zorlarsanız hücre delinir.

> Li-Po piller dikkat ister. Kısa devre, ezilme ve 60 °C üzeri sıcaklık
> yangına yol açar. Lehimlemeyi cihaz kapalıyken ve uçları birbirine
> değdirmeden yapın.

---

## 7. Kesitler

| Kesit | Kenar | Ölçü | Konum |
|---|---|---|---|
| USB-C | alt (−Y) | 9.0 × 3.4 mm, yuvarlatılmış | `usb_x`, `usb_z` |
| Anahtar | sağ (+X) | 4.0 × 1.6 mm | `sw_y`, `sw_z` |
| 3 tuş | sağ (+X) | 3.0 mm dış + 1.5 mm pusher | `btn_y0`, `btn_pitch`, `btn_z`, `btn_dz` |
| FPC kanalı | ön yüz, camın alt kenarı | 12.0 mm genişlik | `fpc_x`, `fpc_w` |

**Tuşlar:** Dış delik 3.0 mm'dir ve 0.8 mm derinliğinde bir havşa oluşturur;
arkasından 1.5 mm'lik pusher deliği geçer. Böylece 1.6 mm'lik yan duvar
tamamen zayıflatılmaz, kullanıcı parmağı 3 mm'lik girintiyi hisseder.

**FPC kanalı:** Panelin şerit kablosu camın alt kenarından çıkıp kartın ön
yüzüne katlanır. Kanal, cam bölgesindeki 1.2–1.6 mm bandını kaldırarak
katlanmaya yer açar. Panelinizin FPC'si başka bir kenardan çıkıyorsa `fpc_x`
değerini kaydırın ya da `fpc_passage()` çağrısını kaldırın.

---

## 8. Montaj sırası

1. Paneli ön yüzün iç tarafından yuvaya bırakın (cam, 1.2 mm'lik dudağa oturur).
2. FPC'yi kanaldan geçirip kartın konnektörüne takın; katlanmayı 0.8 mm'lik
   boşlukta yapın.
3. PCB'yi 4 kulenin üzerine oturtup M1.6 vidalarla sabitleyin.
4. Pili köşe yastıklarına oturtun, kabloları karta lehimleyin.
5. Üzerine ince bir köpük pul koyun (0.25 mm sıkışacak).
6. Kapağı bileziği basamağa gelecek şekilde yerleştirip 4 vidayı sıkın.

---

## 9. Sorun giderme

| Belirti | Çözüm |
|---|---|
| Panel kasaya hiç sığmıyor | `case_w/d` camdan türetilmemiş. `case_w = panel_glass_w + 2*bezel_lip` yapın (bkz. §0); konsoldaki `UYARI:` satırına bakın |
| Panel yuvaya girmiyor | `glass_lip_w/h` +0.2 mm; `panel_test` ile doğrulayın. Cam önden değil içten bırakılır |
| Panel yuvada oynuyor | `glass_lip_w/h` −0.2 mm ya da 0.2 mm'lik bant şerit |
| Pencere aktif alanı kesiyor | `window_w/h` büyütün (aktif alan + 0.4 mm) |
| Kapak kapanmıyor | Konsoldaki `emniyet payı` negatif olabilir; ya da `usb_z`/`sw_z`/`btn_z` yanlış, konnektör duvara dayanıyor |
| USB-C kablosu zor giriyor | `usb_z` yüksekliğini kumpasla ölçüp düzeltin |
| Tuşa basılmıyor | `btn_z` / `btn_dz` yüksekliğini ölçüp düzeltin |
| Pil sığmıyor | `cell_t` gerçek değeri girin, `stack_total`'ı kontrol edin, `case_h`'ı güncelleyin |
| Vida yuvası sıyırdı | Bir üst boy vida (M2) için `screw_d` ve `pcb_hole_d` değerlerini büyütün |
| Ön duvar camın altında çatladı | `lip_depth` değerini 0.8'e düşürün (dudak iki kat kalınlaşır) |

---

## Hazır STL dosyaları

`stl/` klasöründeki dosyalar `case.scad`'den **OpenSCAD ile üretilmiştir** —
OpenSCAD kurmadan dilimleyip basabilirsiniz.

| Dosya | Dış ölçü | Hacim | Ne zaman kullanılır |
|---|---|---|---|
| `govde.stl` | 62.00 × 32.00 × 11.41 mm | 4.65 cm³ | Ana gövde (ön çerçeve + panel yatağı) |
| `kapak.stl` | 62.00 × 32.00 × 2.60 mm | 3.33 cm³ | Arka kapak (geçmeli, 1 mm bindirme) |
| `panel-test.stl` | 62.00 × 32.00 × 3.60 mm | 1.17 cm³ | **Önce bunu basın** — panelin yatağa oturup oturmadığını 3 saatlik baskıyı bitirmeden görün |

Gövde + kapak, 1 mm'lik geçme payıyla toplandığında dış yükseklik **13.0 mm**'dir.

**Mesh durumu:** üç dosya da kapalı (su geçirmez) — hiç açık kenar yok.
`govde.stl`'de 20 kenarda iki kapalı yüzey tam olarak temas ediyor (4 yüzey
paylaşımlı). Bu bir delik **değildir**; dilimleyiciler sorunsuz işler, ama
tam katı olmayan bir ağ denetleyicisi uyarı verebilir.

### Yeniden üretmek

```bash
brew install --cask openscad@snapshot     # normal `openscad` casksı 2026-09-01'de
                                           # Gatekeeper nedeniyle devre dışı bırakıldı
cd hardware/enclosure
OSC=/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
$OSC --export-format binstl -o stl/govde.stl      -D 'PART="body"'       case.scad
$OSC --export-format binstl -o stl/kapak.stl      -D 'PART="lid"'        case.scad
$OSC --export-format binstl -o stl/panel-test.stl -D 'PART="panel_test"' case.scad
```

STL'ler **üretilen** dosyalardır — ölçü değiştirirseniz `case.scad`'i düzenleyip
yukarıdaki üç komutu tekrar çalıştırın. Elle STL düzenlemeyin.
