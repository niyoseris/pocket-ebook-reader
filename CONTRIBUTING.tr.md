# Katkı Rehberi

Teşekkürler. Bu proje hem **donanım** hem **yazılım** içeriyor ve ikisinin katkı
kuralları biraz farklı.

---

## Hızlı başlangıç

```bash
git clone <bu-repo> pocket-eink-reader
cd pocket-eink-reader

# Yazılım tarafı
pip install -U platformio
cd firmware && pio run -e xiao && cd ..

# Araçlar tarafı
cd tools && python3 -m unittest discover tests && cd ..

# Donanım tarafı — netlist tutarlılığı
cd hardware/schematic && python3 gen_netlist.py --check
```

---

## Neye ihtiyaç var?

Öncelik sırasına göre güncel liste: [`docs/09-roadmap.md`](docs/09-roadmap.md)

En yüksek etkili üç iş:

1. **Kalan 13 pin numarasını doğrula** — USB-C receptacle, USBLC6-2SC6,
   Si1308EDL. Datasheet okuyup `hardware/schematic/gen_netlist.py` içindeki
   `PINMAP`'e işleyin. 10 dakikalık iş, PCB üretiminin önünü açar.
2. **BUSY polaritesini ölç** — `firmware/README.md`'deki 30 saniyelik test.
3. **Gerçek donanımda derle ve çalıştır** — bulduğunuz her derleme hatası
   değerli.

---

## Donanım katkıları

### Netlist'i elle düzenlemeyin

`connections.csv` ve `pocket-reader.net` **üretilen** dosyalardır. Kaynağı
`hardware/schematic/gen_netlist.py` içindeki `NETS`, `COMPONENTS` ve `PINMAP`
sözlükleridir.

```bash
cd hardware/schematic
# 1. gen_netlist.py'yi düzenle
# 2. Doğrula — gerçek tutarsızlıklar hata verir, eksik pinler uyarı
python3 gen_netlist.py --check
# 3. Çıktıları üret
python3 gen_netlist.py
```

Bir PR'da `gen_netlist.py` değiştiyse ama `connections.csv` değişmediyse CI
uyarır.

### Yeni pin numarası eklerken

```python
"U1": {"I/O1": "1", "I/O2": "3", "GND": "2", "VBUS": "5"},
#      ^^^^^^ pin ADI   ^^^ pin NUMARASI (datasheet'ten)
```

PR açıklamasına **hangi datasheet, hangi tablo, hangi sayfa** olduğunu yazın.
Doğrulanmamış bir numara girmektense `None` bırakmak yeğdir — `--check` onu
uyarı olarak listeler ve kimse yanlışlıkla üretime göndermez.

### Değer değiştirirken

Hesabı gösterin. Örneğin bir direnç değişikliği için:

> `R6`: 180 kΩ → 200 kΩ. `Vout = 0.5 × (1 + 1M/200k) = 3.00 V`.
> Datasheet `R6 ≈ 200 kΩ` önerir ama o değerde çıkış 3.3 V olmaz; hedefimiz
> 3.3 V olduğu için 180 kΩ'da kalıyoruz.

---

## Yazılım katkıları

### Dil kuralları

| Yer | Dil |
|---|---|
| Tanımlayıcılar, kod yorumları, commit mesajları | **İngilizce** |
| Kullanıcıya görünen firmware metinleri | Varsayılan İngilizce, `-DLANG_TR` ile Türkçe; ikisi de `include/i18n.h` üzerinden |
| Dokümanlar (`docs/`, `README`) | **İngilizce** — kanonik, özgün yolda |
| Türkçe çeviriler | Her İngilizce dosyanın yanında `<name>.tr.md` |

Bir dokümanı değiştirdiğinizde iki dili birlikte değiştirin. Yalnızca tek dile
inen bir doküman güncellemesi eksik sayılır — ikisi yan yana okunmak içindir ve
Türkçe dosya tarihsel bir arşiv değildir.

### Bağımlılık politikası

- **Firmware:** harici kütüphane yok. `platformio.ini` içindeki `lib_deps`
  bilinçli olarak boştur. Yeni bir bağımlılık eklemek istiyorsanız önce issue
  açıp gerekçesini tartışalım.
- **Araçlar:** `epub2epr.py`, `send.py`, `make_sample_books.py` yalnızca Python
  standart kütüphanesini kullanır. `fontgen.py` Pillow kullanır. Yeni bağımlılık
  eklemeyin.

### Kod stili

- C++: 2 boşluk girinti, `static` dosya-yerel yardımcılar, modül başına bir
  `.h`/`.cpp` çifti
- Python: 3.9+, `from __future__ import annotations`, tip ipuçları,
  `if __name__ == "__main__":`
- Her modülün başında **neden** var olduğunu anlatan bir yorum bloğu

### Test

```bash
cd tools && python3 -m unittest discover tests -v
```

Yeni bir dönüştürücü özelliği ekliyorsanız `tests/` altına bir test ekleyin.
Donanım testi yoktur; firmware için derleme başarısı tek otomatik kontroldür.

---

## Sayı iddiaları

Bu projede güç tüketimi, süre ve boyut gibi sayılar **ya ölçülmüş ya da
hesaplanmış** olarak işaretlenir. Bir sayı yazarken hangisi olduğunu belirtin:

- ✅ `~55 µA (hesaplama — docs/07 §2)`
- ✅ `44 µA (ölçüm, Seeed XIAO ESP32-C3 veri sayfası)`
- ❌ `~50 µA` (kaynağı belirsiz)

Bu depo hazırlanırken birden fazla sayı bu kural sayesinde düzeltildi; kayıt için
[`docs/09`](docs/09-roadmap.md) sonuna bakın.

---

## Commit ve PR

- Commit mesajı: `alan: kısa açıklama` — örn. `docs: TPS63020 paketini düzelt`
- Bir PR tek bir konuyu ele alsın
- PR açıklamasında **ne değişti** ve **nasıl doğruladınız** olsun
- Donanım değişikliğinde `gen_netlist.py` çıktısını da gönderin

---

## Lisans

- `firmware/`, `tools/`, `.github/` → **MIT** ([LICENSE](LICENSE))
- `hardware/`, `docs/01..04` → **CERN-OHL-S-2.0** ([LICENSE-HARDWARE.md](LICENSE-HARDWARE.md))

Katkı gönderdiğinizde, katkınızın ilgili lisans altında yayınlanmasına izin
verdiğinizi kabul etmiş olursunuz.

---

## Davranış kuralları

Kısa: **iyi niyetli olun.** Yeni başlayanların sorularına sabırlı davranın,
"bunu neden yapmadın" yerine "şöyle yapabiliriz" diye yazın. Teknik eleştiri
memnuniyetle karşılanır; kişisel eleştiri değil.

---

## Yardım

Takıldığınızda:

1. [`docs/08-troubleshooting.md`](docs/08-troubleshooting.md) — belirtiye göre arayın
2. Mevcut issue'lara bakın
3. Yeni issue açarken şunları ekleyin: seri port çıktısı, ekran fotoğrafı,
   ölçümler, donanım (kolay yapı mı PCB mi), en son ne değiştirdiğiniz
