# examples

Örnek kitaplar buraya gelir. **Depoda hazır `.epr` yoktur** — üretilirler.

```bash
cd ../tools
python3 make_sample_books.py            # bu klasöre yazar
# veya
python3 make_sample_books.py --out-dir ../firmware/data/books
```

Üretilen dosyalar:

| Dosya | Boyut | Ne test eder |
|---|---|---|
| `ornek-turkce.epr` | ~4 KB | **Türkçe harfler** (ç ğ ı İ ö ş ü), 3 bölüm, paragraf girintisi |
| `sample-english.epr` | ~3 KB | Latin-1 kapsaması, düz metin |
| `stress-test.epr` | ~200 KB | 40 bölüm, ~3.000 paragraf — sayfalama ve sayfa indeksi önbelleği |

## Neden depoda hazır dosya yok?

`.gitignore` içinde `firmware/data/books/*.epr` ve `examples/*.epr` hariç
tutuluyor. Sebep: `.epr` **üretilen** bir biçimdir ve üretici script depoda.
Herhangi bir biçim değişikliğinde tüm örnek dosyaların yeniden üretilmesi
gerekir; depoda ikili dosya tutmak bu senkronizasyonu bozar.

Ayrıca kullanıcıların kendi kitaplarını koyacağı yeri örnek dosyalarla
doldurmak istemiyoruz.

## Kendi kitaplarınız

```bash
cd ../tools
python3 epub2epr.py ~/kitap.epub -o /tmp/kitap.epr
python3 send.py /tmp/kitap.epr

# veya bir klasörün tamamını
python3 send.py --dir ~/kitaplar/
```

## Örnek metinlerin lisansı

`make_sample_books.py` içindeki Türkçe ve İngilizce metinler bu proje için
özgün olarak yazılmıştır ve deponun lisansına tabidir (MIT). Kamu malı veya
telifli hiçbir metin içermezler.

`stress-test.epr` içeriği üretilmiş (anlamsız ama dilbilgisel olarak tutarlı)
metindir ve okunacak bir şey değildir — yalnızca sayfalama performansını
ölçmek içindir.
