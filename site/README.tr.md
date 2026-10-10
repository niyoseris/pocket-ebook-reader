# site/ — Sayfa Üretimi

Bu klasördeki HTML sayfaları **elle yazılmaz; üretilir.** Kaynağı düzenlersiniz,
çıktıya dokunmazsınız.

## Dosyalar

| Dosya | Rolü |
|---|---|
| `template.html` | **Kaynak.** Sayfanın iskeleti; tüm görünür metinler `{{anahtar}}` yer tutucularıyla değiştirilmiştir. Elle düzenlenen tek HTML budur. |
| `strings.tr.json` | Türkçe metinler (düz `{"anahtar": "değer"}` haritası). |
| `strings.en.json` | İngilizce metinler. Anahtar kümesi `tr` ile **birebir aynıdır**. |
| `index.html` | **Üretilen çıktı (İngilizce, kanonik).** README'lerin bağlantı verdiği ve paylaştığınız dosya budur. |
| `index.tr.html` | **Üretilen çıktı (Türkçe).** |
| `build-cache/` | Yalnızca derleme sırasında Three.js'i bir kez indirip saklar (`.gitignore` içinde). Depoya girmez. |

> `index.html` ve `index.tr.html` **üretilen** dosyalardır. Elle düzenlemeyin —
> bir sonraki derlemede üzerine yazılır. Değişiklik için `template.html` ile
> `strings.*.json` dosyalarını düzenleyip yeniden derleyin.

## Derleme

```bash
python3 tools/build_site.py            # ikisini de üretir (en + tr)
python3 tools/build_site.py --lang en  # yalnızca İngilizce
python3 tools/build_site.py --check    # üretmez; anahtarları ve çıktıları doğrular
```

`build_site.py` yalnızca Python 3.9+ standart kütüphanesini kullanır; harici
paket gerekmez. Betik her dizinden çalışır (yollar `__file__` üzerinden
çözülür).

İlk derleme Three.js'i ağdan bir kez indirip `site/build-cache/` içine yazar.
Ağ yoksa ve önbellek de boşsa derleme, ne yapılacağını söyleyen net bir Türkçe
hatayla durur — sessizce CDN bağlantısına düşmez.

`--check`, CI için uygundur: anahtar kümesini doğrular ve diskteki çıktıları
yeniden üretilenlerle karşılaştırır; böylece bayat/elle düzenlenmiş bir çıktıyı
yakalar.

## Anahtar doğrulaması

`build_site.py` her çalıştırmada ve özellikle `--check` altında şunları
reddeder:

- bir dil dosyasında eksik olan anahtar (iki dosyanın anahtar kümesi aynı olmalı);
- `strings.*.json` içinde olup şablonda hiç kullanılmayan anahtar;
- şablonda `{{anahtar}}` olarak geçip hiçbir dil dosyasında değeri bulunmayan anahtar.

Bu üç durumda betik sıfırdan farklı çıkış koduyla ve açıklayıcı bir mesajla durur.

## Yeni dil ekleme

1. `site/strings.xx.json` oluşturun; mevcut bir dosyadan kopyalayıp değerleri
   çevirin. **Anahtar kümesi değişmemelidir.**
2. `tools/build_site.py` içindeki `OUTPUTS` ve `ALL_LANGS` tanımlarına dili ekleyin
   (`OUTPUTS["xx"] = "index.xx.html"`).
3. `python3 tools/build_site.py` çalıştırın.

Sayfa yönelimi için `<html lang="…">` değeri de `strings.xx.json` içindeki
`page.lang` anahtarından gelir; onu da güncelleyin.

## Neden tüm varlıklar base64 gömülü?

Sayfanın iletilmesi gereken biçim **tek bir dosyadır**: birine e-postayla
gönderip açtırabileceğiniz, çevrimdışı da çalışan bir HTML. Bunun için derleme
sırasında:

- Three.js, `<script src="data:text/javascript;base64,…">` olarak,
- dört teknik çizim (SVG), `<img src="data:image/svg+xml;base64,…">` olarak

satır içine gömülür. Böylece çıktıda ne harici URL ne de kardeş dosya referansı
kalır; sayfa `file://` ile doğrudan açıldığında da CDN erişimi ya da CORS
gerekmez. Derleme sonrası bunlar ayrıca doğrulanır.

**Bedeli boyuttur.** Three.js küçültülmüş hâliyle ~590 KB'tır; base64 kodlaması
buna ~%33 ekler ve dört SVG de aynı şekilde gömülür. Sonuçta her çıktı yaklaşık
**1.1 MB** olur. Bu, tek dosya taşınabilirliği için bilinçli olarak ödenen
bedeldir; gömme yerine harici dosya kullanmak sayfayı küçültür ama "tek dosya"
özelliğini ortadan kaldırır.

## Türkçe ve İngilizce

- `index.html` → **İngilizce** (kanonik; paylaştığınız dosya).
- `index.tr.html` → **Türkçe**.

İki sayfa aynı şablondan üretilir; metin ikameleri dışında birebir aynıdır, yani
3B sahne, zaman çizelgesi, kesit görünümü, parça seçme ve etiketler iki dilde de
aynı davranır.
