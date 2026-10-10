# Donanım Lisansı

Bu depodaki **donanım tasarım dosyaları** şu lisans altındadır:

> **CERN Open Hardware Licence Version 2 — Strongly Reciprocal (CERN-OHL-S-2.0)**

Kapsam:

```
hardware/schematic/     devre şeması, netlist, bağlantı tablosu, üretici script'leri
hardware/pcb/           PCB yerleşim dosyaları ve üretim çıktıları
hardware/enclosure/     3D baskı kasa tasarımı
hardware/diagrams/      blok ve kablolama diyagramları
docs/01..04             malzeme listesi, devre, PCB ve montaj dokümanları
```

---

## Özet (bağlayıcı değildir — asıl metin geçerlidir)

CERN-OHL-S-2.0 **güçlü karşılıklı** (strongly reciprocal) bir lisansdır:

| İzin verilir | Koşul |
|---|---|
| Tasarımı kullanmak, üretmek, satmak | ✅ |
| Değiştirmek ve türev tasarım yapmak | ✅ |
| Ürünü ticari olarak satmak | ✅ |
| Tasarım dosyalarını (Kaynak) kapalı tutmak | ❌ **Yasak** |

Kısaca: bu tasarımdan bir ürün yapıp satabilirsiniz, ancak **tasarım
dosyalarını açık kaynak olarak yayınlamak zorundasınız** — kendi
değişiklikleriniz dahil. Bu, donanımın birinin kapalı ürüne dönüştürüp
topluluğa geri vermemesi içindir.

Kod tarafı (firmware, araçlar) **MIT** lisanslıdır ve ticari kısıt içermez —
bkz. [LICENSE](LICENSE). Bu ayrım bilinçlidir: donanım karşılıklılık ister,
yazılım özgürlük ister.

---

## Asıl lisans metni

> ⚠️ **Yayın öncesi yapılacak:** Bu dosya lisansın *özetini* ve *kapsamını*
> verir; CERN-OHL-S-2.0'ın tam ve hukuken bağlayıcı metni (~10.000 kelime)
> buraya henüz yerleştirilmemiştir. Bir sürüm yayınlamadan önce tam metni
> indirip bu dosyanın sonuna ekleyin:
>
> ```
> curl -O https://ohwr.org/cern_ohl_s_v2.txt
> cat cern_ohl_s_v2.txt >> LICENSE-HARDWARE.md
> ```
>
> Metnin bütünlüğünü `sha256sum` ile doğrulayın. Lisans başlığı ve
> feragatname, lisans metninin kendisinden alınmalıdır.

Resmî kaynaklar:

- Lisans metni: <https://ohwr.org/cern_ohl_s_v2.txt>
- Açıklama ve SSS: <https://ohwr.org/project/cernohl/wikis/Documents/CERN-OHL-version-2>
- Lisans seçici (hangi CERN-OHL varyantı): <https://ohwr.org/project/cernohl/wikis/Documents/CERN-OHL-version-2#which-licence-to-use>

---

## Tasarım dosyalarına nasıl atıf verilir

Tasarımı üretir, değiştirir veya dağıtırsanız:

1. **Kaynak dosyaları** (şema, PCB, kasa) değişikliklerinizle birlikte açık
   kaynak olarak yayınlayın
2. Şu atfı görünür bir yerde tutun:

```
Pocket Reader — açık kaynak e-mürekkep okuyucu
https://github.com/<kullanıcı>/pocket-eink-reader
Lisans: CERN-OHL-S-2.0
Değiştirilmiş sürüm — orijinal projeden türetilmiştir.
```

3. Değişiklik yaptıysanız **"değiştirilmiş sürüm"** ibaresini ekleyin
4. Ürünle birlikte lisans metnini ve bu bildirimi verin

---

## Ticari kullanım

Tasarımı satmak **serbesttir**. Tek koşul tasarım dosyalarını açık tutmanızdır.
Bir ürün yapıp satarken:

- Ürünle birlikte tam lisans metnini verin
- Tasarım dosyalarının nerede olduğunu belirtin (kendi deponuz veya bu depo)
- Değişiklik yaptıysanız bunu belirtin

Firmware'i (MIT) ayrıca kullanabilirsiniz; MIT ticari kullanımda hiçbir
karşılıklılık istemez, yalnızca telif bildirimini korumanızı ister.

---

## Katkı verirken

Bu depoya donanım tasarımı katkısı gönderdiğinizde, katkınızın CERN-OHL-S-2.0
altında yayınlanmasına izin verdiğinizi kabul etmiş olursunuz. Ayrıntı:
[CONTRIBUTING.md](CONTRIBUTING.md)
