# hardware/pcb

PCB dosyaları bu klasöre gelir. Şu an **boştur** — bilinçli olarak.

## Neden boş?

Depoda hazır Gerber yoktur, çünkü `hardware/schematic/gen_netlist.py` içinde
hâlâ **13 doğrulanmamış pin numarası** var (USB-C receptacle, USBLC6-2SC6,
Si1308EDL) ve panelin harici ±15 V boost devresi fiziksel olarak test
edilmemiştir. Bu iki koşul tamamlanmadan üretim dosyası yayınlamak, indiren
kişiye çalışmayan bir kart göndermek demektir.

```bash
cd ../schematic
python3 gen_netlist.py --check     # kalan pinleri listeler
```

## Kendi PCB'nizi üretmek

Tam rehber: [`docs/03-pcb.md`](../../docs/03-pcb.md)

Özet akış:

```bash
cd ../schematic
python3 gen_netlist.py             # pocket-reader.net üretir

# KiCad
pcbnew
#   File → Import → Netlist → pocket-reader.net
#   Parçaları yerleştir (yerleşim planı: docs/03 §1)
#   İzleri çek, GND düzlemini doldur
#   File → Fabrication Outputs → Gerbers
```

## Kart özeti

| Özellik | Değer |
|---|---|
| Ölçü | 45 × 24 mm |
| Katman | 2 |
| Kalınlık | 1.6 mm |
| Yüzey | ENIG |
| Bileşen sayısı | 64 (`connections.csv`) |
| Net sayısı | 39 |

## Kartı ürettikten sonra

Bu klasöre ekleyip PR gönderin:

```
hardware/pcb/
├── pocket-reader.kicad_pcb
├── pocket-reader.kicad_pro
├── gerbers/            (üretim çıktıları, .gitignore'da değil)
└── README.md           (kendi notlarınız)
```

Gerber'ları `.gitignore`'a eklemek isterseniz tartışalım — üretilmiş dosyalar
depoyu şişirir ama indirip hemen üretebilmek de değerlidir.
