> Türkçe sürüm: [06-books-and-fonts.tr.md](06-books-and-fonts.tr.md)

# 06 · Books and Fonts

The device does not read EPUB. Books are converted once on the computer, and the
device only sees plain text. This is a deliberate decision — the rationale is in
`docs/00` §5.

```
book.epub  ──epub2epr.py──>  book.epr  ──send.py / browser──>  device
font.ttf   ──fontgen.py────>  reader.epf ──uploadfs───────────>  device
```

---

## 1 · Setup

```bash
cd tools
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`epub2epr.py`, `send.py` and `make_sample_books.py` **use no external packages**
(only the Python standard library). `fontgen.py` requires Pillow. So even if you
skip the `pip install` step you can convert and upload books — you just can't
generate fonts.

---

## 2 · Generating fonts

### 2.1 Choosing a font

The device's screen is 250 × 122 pixels and with a 14 px font it takes ~7 lines of
text per page. At this size **the typeface determines readability.**

| Font | Licence | Why |
|---|---|---|
| **Atkinson Hyperlegible** | SIL OFL 1.1 | Designed for people with low vision; the distinction between `I/l/1` and `O/0` is very clear. **The best choice on a small screen** |
| **DejaVu Sans** | Bitstream Vera (permissive) | Ready in almost all Linux distributions. Full Turkish coverage |
| **Noto Sans / Noto Serif** | SIL OFL 1.1 | Very wide coverage, downloadable from Google Fonts |
| **Bitter** | SIL OFL 1.1 | A slab serif designed for e-ink |
| **Liberation Sans** | SIL OFL 1.1 | Arial metrics, compatible |

> **Ones to avoid:** Very thin (light/thin) fonts disappear on a 1-bit e-ink
> screen; handwriting and decorative fonts are unreadable at 14 px.

On Linux DejaVu comes ready:

```bash
ls /usr/share/fonts/truetype/dejavu/
# DejaVuSans.ttf  DejaVuSans-Bold.ttf  ...
```

To download Atkinson Hyperlegible:
<https://www.brailleinstitute.org/freefont/>

### 2.2 Generating a font

```bash
python3 fontgen.py DejaVuSans.ttf --size 14 \
        --out ../firmware/data/fonts/reader-14.epf \
        --preview /tmp/onizleme.png
```

| Flag | Meaning |
|---|---|
| `--size N` | Pixel height. On the screen 14 is a good balance, 20 is large text |
| `--out FILE` | The output `.epf` file |
| `--ranges a,b,c` | The character ranges to cover. Ready-made sets: `ascii latin1 latin-ext turkish punct digits currency greek cyrillic all`. Default: `ascii,latin1,latin-ext,turkish,punct` |
| `--line-spacing N` | Extra pixel between lines (default 2) |
| `--extra-codepoints "₺"` | Individual characters not in the sets (e.g. a currency symbol) |
| `--preview PNG` | A preview image containing a sample Turkish paragraph |
| `--preview-width N` | Preview width (default 250 — the same as the screen) |
| `--json P` / `--no-json` | Writes a side file with the metrics (for debugging) |

For the full list: `python3 fontgen.py --help`

Make sure to open the `--preview` file and check that the letters **ç ğ ı İ ö ş ü**
appear correctly. If these characters are missing in a font, the device shows a
blank in their place and the text becomes meaningless.

Generate the three recommended fonts:

```bash
python3 fontgen.py DejaVuSans.ttf --size 12 --out ../firmware/data/fonts/reader-12.epf
python3 fontgen.py DejaVuSans.ttf --size 14 --out ../firmware/data/fonts/reader-14.epf
python3 fontgen.py DejaVuSans.ttf --size 18 --out ../firmware/data/fonts/reader-18.epf
```

The "Font size" setting in the device menu switches between these files.

### 2.3 The `.epf` format (v1)

Little-endian, no padding:

```
header (12 bytes):
  char[4]  magic number = "EPF1"
  uint8    version = 1
  uint8    height          (pixel height of the font box)
  int8     ascent          (from the top of the box to the baseline)
  int8     descent         (stored POSITIVE; height = ascent + descent)
  uint8    line_spacing    (extra pixel between lines)
  uint8    reserved = 0
  uint16   glyph_count

each glyph (10-byte fixed header + bitmap):
  uint32   codepoint       (UTF-8 decoded Unicode value)
  int8     advance         (the pixel the pen advances)
  int8     left            (x offset when drawing)
  uint8    width           (bitmap width, pixels)
  uint8    height          (bitmap height, pixels)
  uint8    top             (y offset of the bitmap FROM THE TOP of the line box)
  uint8    reserved = 0
  uint8[]  bitmap          (according to the rule below)
```

> ⚠️ **The bitmap is a CONTINUOUS bit stream — rows are not byte-aligned.**
> The length is `ceil(width × height / 8)` bytes (no padding per row).
> Bit `N = y × width + x` → byte `N >> 3`, mask `0x80 >> (N & 7)`.
>
> Why it matters: `ceil(width × height / 8)` and a row-padded read
> (`ceil(width/8) × height`) give a different result **for every glyph wider than
> 8 pixels**. For example a 9 × 3 pixel glyph is 4 bytes in the stream and 6 bytes
> with padding — and a driver that reads with padding draws that glyph completely
> broken. The firmware side (`firmware/src/font.cpp`) applies this stream rule.

**Why this design:** thanks to the `left`/`top` offsets, glyphs can extend outside
the box (for example the soft sign of `ğ` or the hook of `ç`); trying to fit glyphs
into the box breaks Turkish letters. `advance` is kept separate, so that letters
like `ı` and `İ` are spaced correctly.

After generating each glyph's bitmap, `fontgen.py` **packs it, unpacks it again and
compares**; if there is a mismatch it errors out without writing the file. In
addition `tools/tests/test_epf_interop.py` verifies that the two sides apply the
same rule, with edge-case glyph widths (9, 12, 13, 17 px).

---

## 3 · Converting books

```bash
python3 epub2epr.py ~/kitaplar/suc-ve-ceza.epub \
        -o suc-ve-ceza.epr \
        --title "Suç ve Ceza" --author "Dostoyevski" --lang tr
```

| Flag | Meaning |
|---|---|
| `-o, --output` | The output file |
| `--title` / `--author` / `--lang` | Override the metadata (if it is wrong in the EPUB) |
| `--no-toc` | Do not generate the table of contents (smaller file) |
| `--strip-diacritics` | Removes the accents. Use it **if your font has no Turkish letters** — but the text is corrupted |
| `--dump` | Show the title and the first 500 characters without converting (debugging) |
| `--verify` | After writing, read the file back and verify |
| `--verbose` | Paragraph/chapter/byte statistics |

Example output:

```
Input:      suc-ve-ceza.epub (812 KB)
Title:      Suç ve Ceza
Author:     Dostoyevski
Language:   tr
Spine:      42 documents
Chapters:   18
Paragraphs: 3.412
Output:     suc-ve-ceza.epr (398 KB)
```

### 3.1 The `.epr` format (v1)

Little-endian:

```
offset 0   : "EPR1" (4 ASCII bytes)
offset 4   : uint16 version = 1
offset 6   : uint16 flags             (bit0 = table of contents present)
offset 8   : uint32 text_offset
offset 12  : uint32 text_length
offset 16  : uint32 toc_offset         (0 if the flag is off)
offset 20  : uint32 toc_count
offset 24  : uint8  title_length,  followed by UTF-8 title
           : uint8  author_length,  followed by UTF-8 author
           : uint8  lang_length,    followed by ASCII language tag ("tr")
           : uint8  encoding         (0 = UTF-8)
           : 0x00 padding up to text_offset

text block (UTF-8):
  0x0A  end of paragraph   → the reader moves to a new paragraph and indents its first line
  0x0B  end of chapter     → the reader starts a NEW PAGE and centres the heading
  the other bytes are plain text; 0x0D (CR) does not appear in the file

table of contents block: toc_count entries
  { uint32 text_position (byte offset relative to the text block)
    uint8  length
    char[] title (UTF-8, NO NUL terminator) }
```

**Why are there no line breaks?** The device wraps lines itself, because wrapping
depends on the font size. If the converter inserted line breaks, the text would
look broken at a large font size. The converter's job is only to mark **paragraph
and chapter boundaries**.

### 3.2 The cleanup the converter does

| Operation | Why |
|---|---|
| The contents of `<script>`, `<style>`, `<head>` are discarded | They must not get mixed into the text |
| HTML entities are decoded (`&amp;` → `&`, `&#287;` → `ğ`) | |
| Soft hyphen (U+00AD) and zero-width characters are deleted | Line wrapping is broken |
| Unicode NFC normalisation | Reduces Turkish combining sequences to a single code point |
| Whitespace is simplified (multiple inline spaces → one) | Indentation problems in e-books |
| An end of chapter (0x0B) is placed before `<h1>`–`<h6>` | Page break and heading |
| `<img>` → `[image]` | Images are not supported |

---

## 4 · Uploading to the device

### 4.1 Command line

```bash
# Single book
python3 send.py suc-ve-ceza.epr

# What is on the device?
python3 send.py --list

# Delete a book
python3 send.py --rm suc-ve-ceza.epr

# Save the Wi-Fi password to the device
python3 send.py --wifi "EvAgi" "sifre123"

# Device status
python3 send.py --status

# Convert and upload all the EPUBs in a folder
python3 send.py --dir ~/kitaplar/

# Upload automatically when the file changes (for testing while writing)
python3 send.py kitap.epr --watch

# Give the IP manually (if mDNS doesn't work)
python3 send.py kitap.epr --ip 192.168.1.42
```

### 4.2 From the browser

1. **Long-press MENU** on the device → Wi-Fi transfer mode
2. The SSID and address appear on the screen
3. Open `http://pocketreader.local` from the computer
4. Drag and drop the file

If the device has opened its own network (`PocketReader-XXXX`, password
`readbooks`), first connect to that network, then open it from the browser and
enter **your home network's password once**. After that the device connects to
your home network on its own.

> **Important:** The device expects `.epr`, not `.epub`. The browser interface
> checks the magic number (`EPR1`) of the uploaded file and if you upload an EPUB
> it gives an "invalid format" error. Convert it first with `epub2epr.py`.

### 4.3 If the device has gone to sleep

Transfer mode does not enter sleep until you exit. But if the device is asleep it
does not appear on the network — press a page button, then long-press MENU.

---

## 5 · Book upload scenarios

### One-time setup

```bash
cd tools
python3 make_sample_books.py            # generates sample books into examples/

cd ../firmware
pio run -t uploadfs                     # font + sample books together
```

`make_sample_books.py` generates three files:

| File | Contents |
|---|---|
| `ornek-turkce.epr` | Original short Turkish text, 3 chapters — **Turkish letter test** |
| `sample-english.epr` | Original short English text |
| `stress-test.epr` | ~200 KB, 40 chapters — pagination and page index cache test |

### Building a library

```bash
# Convert your EPUB archive and upload it to the device
python3 send.py --dir ~/kitaplar/
```

On 4 MB of flash there is ~3 MB of usable space; that means roughly **15–30 books**
(a novel takes 200–500 KB as `.epr`).

---

## 6 · Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| On the device the letters are boxes/blanks | The character is not in the font | Add the Turkish range with `fontgen.py --ranges` |
| The text is too small to read | A 12 px font is installed | Regenerate with `--size 14` |
| Words are split at the ends of pages | Normal behaviour | Turkish hyphenation does not exist yet — `docs/09` |
| The book won't open, "invalid format" | An `.epub` was uploaded | Convert it with `epub2epr.py` |
| The title/author appear empty | EPUB metadata missing | Override with `--title`/`--author` |
| The book opens very slowly | First pagination (no cache) | Normal; the second opening is fast |
| `pocketreader.local` doesn't resolve | mDNS not supported (some Windows/Android) | Give the IP from the screen with `--ip` |
| The browser page doesn't open | The device is asleep | Press a button, long-press MENU |

---

## 7 · Format versioning

Both formats carry a magic number + version number (`EPR1`, `EPF1`). If an
incompatible change is needed in the future the version number is incremented and
the device shows an **understandable message** while rejecting old files — it does
not silently show corrupted text. New fields are added to the `reserved` bytes in
the current version.

---

Back: [05 · Firmware Setup](05-firmware-setup.md) · Next: [07 · Power](07-power.md)
