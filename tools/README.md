# Pocket Reader — Host Tools

This folder contains the tools that convert EPUB books into the `.epr` format
the device reads, generate `.epf` bitmap fonts for the device, and upload the
produced files to the device over the wireless network.

The device itself **never** runs an EPUB, TrueType or line-wrapping engine.
Everything is prepared here, on the computer, in advance; the device only paints
ready-made bitmaps onto the screen. This is why, on the ESP32-C3, changing a
book, turning a page and battery life are incredibly cheap.

---

## 1. Scripts

| Script | What it does | Dependency |
|---|---|---|
| `epub2epr.py` | EPUB 2/3 → `.epr` book converter. Carries the table of contents too. | **None** (pure Python 3.9+) |
| `fontgen.py` | TTF/OTF → `.epf` bitmap font generator. | `Pillow>=10.0` |
| `send.py` | Upload, list, delete, set Wi-Fi, read status on the device. | **None** |
| `make_sample_books.py` | Generates ready-to-upload sample `.epr` files into `examples/`. | **None** |
| `gen_placement.py` | PCB placement data — the single source all the 2D and 3D drawings are generated from. | **None** |
| `gen_pcb_layout.py` | Generates the 2D technical drawings from `placement.csv`. | **None** |
| `build_site.py` | Fills the `site/template.html` template with the language files and produces the single-file `site/index.html` (EN) and `site/index.tr.html` (TR). | **None** (the first build downloads Three.js) |
| `tests/make_tiny_epub.py` | Writes a tiny, valid EPUB zip for the tests. | **None** |
| `tests/test_epr_roundtrip.py` | Tests for the `.epr` format and the converter. | **None** |

So to convert a book and upload it to the device you **do not need to install any
extra package**; you need Pillow only if you want to generate your own font.

---

## 2. Installation

```bash
cd tools
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

You can also activate it and use it directly:

```bash
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python epub2epr.py --help
```

`epub2epr.py`, `send.py` and `make_sample_books.py` also work without a virtual
environment (with the system Python):

```bash
python3 make_sample_books.py
python3 send.py --list
```

Tests:

```bash
cd tools
python3 -m unittest discover -s tests -v
```

---

## 3. Full workflow on first setup

If you are setting up the device for the first time, do these in order.

### Step 0 — Generate and try the sample books

Have something working in your hands before you generate your own font:

```bash
cd tools
python3 make_sample_books.py
#   ornek-turkce.epr      ... bayt  ... bölüm  ... paragraf  ... TOC kaydı
#   sample-english.epr    ...
#   stress-test.epr       ...
```

These three files are valid; they are checked with `epub2epr.read_epr()` and at
the raw byte level.

### Step 1 — Generate the font (`.epf`)

You cannot read anything if the device has no font. Choose a font with Turkish
support (see the "Which font should I use?" section below):

```bash
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    --size 16 \
    --out ../firmware/data/fonts/reader-16.epf \
    --preview onizleme.png
```

Open `onizleme.png` and look at the rendered text: if the Turkish letters
(ç ğ ı İ ö ş ü) come out broken/empty, the font is unsuitable or there is a
missing range in the `--ranges` list.

### Step 2 — Write the font to the device (filesystem upload)

The whole `firmware/data/` folder goes to the device's LittleFS partition:

```bash
cd ../firmware
pio run --target uploadfs
```

(This step belongs to the firmware side; the details are in
`firmware/README.md`.)

### Step 3 — Convert a book

```bash
cd ../tools
python3 epub2epr.py ~/kitaplar/suç-ve-ceza.epub \
    -o sicve.epr --verify --verbose
```

`--verify` immediately reads the written file back and compares it; if you
briefly see "OK", the file is sound.

### Step 4 — Upload to the device

```bash
python3 send.py sicve.epr
```

If the device is on and on the same Wi-Fi network, the file lands in the
`/books/` folder and appears in the book list on the device's screen.

---

## 4. `epub2epr.py` — Book converter

It preserves the EPUB's `<spine>` order; it reads the table of contents from the
EPUB 3 `nav` document, or from the EPUB 2 `toc.ncx` if it cannot find it. It
cleans the HTML with a small state machine: `<p>`, `<div>`, `<br>`, `<li>`,
`<h1>`–`<h6>`, `<blockquote>`, `<pre>` open a new paragraph; `<h1>`–`<h6>`
additionally start a **new page**; `<script>`, `<style>` and `<head>` content is
discarded; `<img>` → `[resim]`; entities like `&amp;` and `&#351;` are decoded;
soft hyphens and zero-width characters are removed; the text is normalised with
NFC (so `o` + two combining dots becomes a single `ö`).

> **Important:** The converter **does not add newlines** to the text. Line
> wrapping is done on the device; only two control bytes enter the text: `0x0A`
> (paragraph) and `0x0B` (chapter/new page).

| Flag | Description |
|---|---|
| `input` | Source `.epub` file (required). With `--dump` it may also be a `.epr`. |
| `-o`, `--output` | Output `.epr` path. Default: the input name with a `.epr` extension. |
| `--title` | Overrides the book title (EPUB metadata is ignored). |
| `--author` | Overrides the author name. |
| `--lang` | Overrides the language code (e.g. `tr`). |
| `--no-toc` | Does not generate the table of contents; the file gets a little smaller. |
| `--strip-diacritics` | Drops the accents: `İ→I`, `ı→i`, `ş→s`, `ğ→g`, `ç→c`, `ö→o`, `ü→u`. Needed **only** when you are forced to use a font with no Turkish glyphs; the `ş`/`s` and `ı`/`i` distinction is lost, and search and hyphenation behaviour breaks. |
| `--verify` | After writing, reads the file back with `read_epr()` and validates it. |
| `--dump` | Does not convert; prints the header, the table of contents and the first 500 characters of the text of an existing `.epr` file. |
| `-v`, `--verbose` | Prints paragraph/chapter/byte statistics. |

Examples:

```bash
# Simple conversion
python3 epub2epr.py kitap.epub

# Correct the title and verify
python3 epub2epr.py kitap.epub --title "Kürk Mantolu Madonna" --author "Sabahattin Ali" --verify

# Inspect a broken file
python3 epub2epr.py kitap.epr --dump
```

### `.epr` format (summary)

```
0  : "EPR1"            4-byte magic number
4  : uint16 version = 1
6  : uint16 flags      bit0 = table of contents present
8  : uint32 text_offset   start of the text block
12 : uint32 text_length   length of the text block
16 : uint32 toc_offset    table-of-contents block (0 if the flag is off)
20 : uint32 toc_count
24 : uint8 title_len  + title  (UTF-8)
     uint8 author_len + author (UTF-8)
     uint8 lang_len   + language (ASCII, e.g. "tr")
     uint8 encoding   (0 = UTF-8)
     ... zero padding up to text_offset

text block : 0x0A = end of paragraph, 0x0B = start of chapter (new page)
contents   : toc_count × { uint32 text_pos; uint8 len; char title[len] }
```

### Two contracts (important for firmware authors)

1. **The TOC position points at the FIRST BYTE of the text.** The chapter-start
   byte (`0x0B`) stands immediately before it; that is, except for offset 0,
   `text[text_pos - 1] == 0x0B`. The position is a **byte** offset — do not index
   the decoded text as a `str`, it will slip because of multi-byte characters.
2. **If the book's first block is a chapter start, `0x0B` is not written.** Offset
   0 is already the start of the first page; an extra byte could open a blank
   page. Therefore:

   ```
   chapter count = toc_count = number of 0x0B + 1
   ```

   This is why `--dump` and `make_sample_books.py` write the two separately
   ("3 chapters / 2 end-of-chapter (0x0B)").

---

## 5. `fontgen.py` — Bitmap font generator

| Flag | Description |
|---|---|
| `font` | Source `.ttf` / `.otf` file (required). |
| `--size` | Font size in pixels (default `14`). |
| `--out` | The `.epf` file to write (**required**). |
| `--ranges` | Comma-separated range names to include. Default: `ascii,latin1,latin-ext,turkish,punct`. |
| `--line-spacing` | Extra line spacing (px). Line step = `height + line_spacing` (default `2`). |
| `--extra-codepoints` | Extra characters to add to the list, e.g. `--extra-codepoints "₺≥×"`. |
| `--preview` | Draws a sample Turkish paragraph to this PNG file. |
| `--preview-width` | Preview width, px (default `250` = device screen width). |
| `--json` | Path of the auxiliary metrics JSON (default: `<out>.json`). |
| `--no-json` | Does not write the auxiliary JSON file. |
| `-v`, `--verbose` | Prints a metrics table of the first glyphs. |

### Range names

| Name | Coverage |
|---|---|
| `ascii` | U+0020–U+007E (basic Latin + digits + punctuation) |
| `latin1` | U+00A0–U+00FF (Latin-1 Supplement) |
| `latin-ext` | U+0100–U+017F (Latin Extended-A) |
| `turkish` | Ğ ğ İ ı Ş ş (U+011E/011F, U+0130/0131, U+015E/015F) |
| `punct` | Quotes, dash variants, `…`, `•`, `™`, `−`, currency signs |
| `digits` | Digits 0–9 only |
| `currency` | ¢ £ ¤ ¥ € ₺ ₨ |
| `greek` | U+0384–U+03CE |
| `cyrillic` | U+0400–U+045F |
| `all` | All of the above |

```bash
# Default Turkish setup
python3 fontgen.py DejaVuSans.ttf --size 16 --out reader-16.epf --preview onizleme.png

# 12 px for more lines on the small screen
python3 fontgen.py DejaVuSans.ttf --size 12 --out reader-12.epf --line-spacing 1

# If you only need digits and punctuation (a very small file)
python3 fontgen.py font.ttf --size 14 --ranges digits,ascii --out mini.epf
```

### Output files

* `reader-16.epf` — the binary file the device reads.
* `reader-16.json` — the metrics of the same font; for manual debugging on the
  firmware side (per glyph `advance`, `left`, `width`, `height`, `top`).

### `.epf` format (summary)

```
header (12 bytes): "EPF1"; uint8 version=1; uint8 height; int8 ascent;
                   int8 descent; uint8 line_spacing; uint8 reserved;
                   uint16 glyph_count
glyph  (10 bytes): uint32 codepoint; int8 advance; int8 left; uint8 width;
                   uint8 height; uint8 top; uint8 reserved
                   + ceil(width*height/8) bytes of bitmap
```

The bitmap is **a continuous MSB-first bit stream with no line padding**: the bit
`N = y*width + x` corresponds to the mask `0x80 >> (N & 7)` of the byte at index
`N >> 3`. `descent` is **positive** and `height == ascent + descent`.

**The `top` rule (the one assumption where the two halves silently diverge —
careful):** `top` is measured from the **top** of the glyph box (the ascender
line), not from the baseline. The baseline is `ascent` pixels below the top of
the cell; that is why the drawing code must find the top edge of the ink with

```
y0 = baseline_y - (ascent - top) * scale
```

— `baseline_y - top` is **wrong**. The error is not a fixed shift: because it
varies per glyph, the text is drawn vertically scattered and the glyphs spill
into neighbouring lines (measurement table:
`tools/tests/test_epf_interop.py::test_top_origin_matches_firmware_renderer`). The
same test keeps this rule under regression protection by reading the source of
`firmware/src/font.cpp`.

---

## 6. `send.py` — Uploader and device manager

The device is looked for at `http://pocketreader.local/` (mDNS). If it cannot be
found, give the IP **shown on the device's screen** with `--ip <address>`.

| Flag | Description |
|---|---|
| `file` | The `.epr` (or `.epub`; converted automatically) to upload. |
| `--host` | Device address (default `pocketreader.local`). |
| `--ip` | The IP on the device's screen; takes the place of `--host`. |
| `--port` | TCP port (default `80`). |
| `--timeout` | Timeout in seconds (default `30`). |
| `--list` | Lists the books on the device as a table. |
| `--rm NAME` | Deletes a book from the device. |
| `--wifi SSID PASSWORD` | Saves the Wi-Fi credentials to NVS. |
| `--status` | Shows the firmware version, battery, free memory and uptime. |
| `--reboot` | Reboots the device. If the firmware does not support this endpoint (404), it gives a clear warning. |
| `--json` | Prints the `--list` / `--status` output as raw JSON (for scripts). |
| `--dir FOLDER` | Converts and uploads **all** `.epub` files in the folder, in order. |
| `--out-dir FOLDER` | The folder where `.epr` files generated in a batch conversion are written. |
| `--keep` | Does not delete the intermediate `.epr` files in a batch conversion. |
| `--watch` | Re-uploads as the file changes on disk (mtime polling). If an `.epub` is being watched, it reconverts on every change. |
| `--watch-interval` | Polling interval, seconds (default `2.0`). |
| `--yes` | Does not ask for delete confirmation. |
| `--force` | Ignores the large-file warning. |
| `--max-upload BYTES` | Warning threshold (default 8 MiB). |
| `-v`, `--verbose` | Verbose output. |

Examples:

```bash
python3 send.py kitap.epr                       # upload
python3 send.py kitap.epr --ip 192.168.1.42     # if mDNS does not work
python3 send.py --list                          # list the books
python3 send.py --status                        # battery / memory / uptime
python3 send.py --status --json | jq .batt_pct  # use in scripts
python3 send.py --rm eski.epr --yes             # delete without confirmation
python3 send.py --wifi EvimAgi sifre123         # save Wi-Fi
python3 send.py --dir ~/kitaplar/ -v            # convert + upload the whole folder
python3 send.py kitap.epub --watch              # auto-upload while editing
```

### Typical errors and what they mean

| Message | What to do |
|---|---|
| `'pocketreader.local' çözümlenemedi` | mDNS is not working. Give the IP on the device's screen with `--ip`. |
| `Bağlantı reddedildi` | The device is asleep. Press the power button and wait until a page appears on the screen. |
| `Zaman aşımı` | The device may be refreshing the screen; try again a few seconds later. |
| `404 — /upload bu yok` | The firmware is old. Try opening the device's web page in a browser. |
| `Dosya cihaz için çok büyük` | There is no room on the device. Delete unneeded books with `--rm`. |

---

## 7. `make_sample_books.py` — Sample books

| Flag | Description |
|---|---|
| `--out-dir FOLDER` | Output folder (default: `examples/` at the repository root). |
| `--stress-kb KiB` | Stress-test size (default `200`). |
| `--stress-chapters N` | Stress-test chapter count (default `40`). |
| `--seed N` | Randomness seed; the same seed always produces the same file (default `1337`). |
| `-v`, `--verbose` | Also prints header/text sizes. |

What is generated:

* `ornek-turkce.epr` — an original Turkish text of 3 chapters, containing all
  Turkish letters.
* `sample-english.epr` — an original English text of 2 chapters.
* `stress-test.epr` — ~200 KB, 40 chapters. Ideal for stressing pagination and
  the page-index cache; used to find where the device slows down.

Before each file is written it is read back with `epub2epr.read_epr()` and checked
at the raw byte level (magic number, version, offsets, TOC entries, the `\r`
prohibition).

---

## 8. Which font should I use?

The device must have **all the Turkish letters** (Ç ç Ğ ğ İ ı Ö ö Ş ş Ü ü).
Otherwise either the letters come out empty or you are forced to use
`--strip-diacritics` and break the meaning. Two recommended fonts:

### DejaVu Sans (recommended)

* **Licence:** Bitstream Vera Fonts Copyright + DejaVu changes. Free software;
  commercial use, modification and redistribution are free. Use of the "DejaVu"
  name is restricted in modified versions (details:
  `dejavu-fonts-ttf-2.37/LICENSE`).
* **Why:** Full Turkish coverage, very good readability, pre-installed on almost
  every Linux distribution, gives a crisp pixel result in the 12–18 px range.
* **Download:**
  * Official site: <https://dejavu-fonts.github.io/>
  * Releases: <https://github.com/dejavu-fonts/dejavu-fonts/releases>
  * Debian/Ubuntu: `sudo apt install fonts-dejavu-core`
    → `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
  * Fedora: `sudo dnf install dejavu-sans-fonts`
    → `/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf`
  * macOS: `brew install --cask font-dejavu`

```bash
python3 fontgen.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    --size 16 --out ../firmware/data/fonts/reader-16.epf --preview onizleme.png
```

### Noto Sans

* **Licence:** SIL Open Font License 1.1 (OFL). Can be used, modified and
  embedded freely; the font file cannot be sold on its own and renamed versions
  must be renamed.
* **Why:** Google's comprehensive font family; full Latin coverage including
  Turkish, designed for screens, looks a little thinner/more elegant than DejaVu.
* **Download:**
  * Google Fonts: <https://fonts.google.com/noto/specimen/Noto+Sans>
    (download: <https://fonts.google.com/download?family=Noto%20Sans>)
  * Source repository: <https://github.com/notofonts/latin-greek-cyrillic/releases>
  * Debian/Ubuntu: `sudo apt install fonts-noto-core`
    → `/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf`
  * macOS: `brew install --cask font-noto-sans`

### Choosing a size

The device's screen is 250 × 122 pixels. Roughly:

| `--size` | Line height | Lines fitting the screen | Notes |
|---|---|---|---|
| 12 px | ~14 px | ~8 lines | very small, try `--line-spacing 1` |
| 14 px | ~16 px | ~7 lines | default, balanced |
| 16 px | ~18 px | ~6 lines | **recommended** |
| 18 px | ~21 px | ~5 lines | large letters, little text |

To decide, generate a PNG with `--preview` and look at it; it is exactly the same
as the device's rendering (the preview is drawn from the `.epf` bitmaps).

---

## 9. Troubleshooting

**The file uploaded but it does not show on the device.**
Check with `send.py --list` that the device really sees it. If it does, the file
name may be too long or the device may not be redrawing the list; change the page
and come back.

**Turkish letters come out as boxes/empty.**
The font does not have that code point. Generate with
`python3 fontgen.py ... --ranges all` and try again, or use DejaVu/Noto. You can
open `reader-16.json` and see whether code points such as `U+011E` (Ğ) are in the
list.

**The book opens but the table of contents is empty.**
The EPUB has neither a `nav` document nor a `toc.ncx`. Look at the `toc_count`
field with `--dump`; if that is fine, the device may not be finding the
chapter-start bytes (`0x0B`).

**The text in the `--dump` output looks broken.**
The bytes `0x0A` and `0x0B` are shown as `¶` and `§`; those are not corruption,
they are the paragraph and chapter markers.

**A very large book opens slowly.**
Try removing the table of contents with `--no-toc`, or split the book into pieces
with `epub2epr.py` (each file becomes a separate book).
