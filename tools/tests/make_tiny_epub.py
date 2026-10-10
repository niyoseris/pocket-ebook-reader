#!/usr/bin/env python3
"""Produce a valid, tiny EPUB zip (for the tests).

So that `epub2epr.py` can be exercised end to end, it writes the minimal pieces
a real EPUB must carry.  It uses no external library.

    python3 make_tiny_epub.py /tmp/deneme          # write the file there
    python3 make_tiny_epub.py /tmp/deneme --epub2  # EPUB 2 variant with NCX

The container rules are respected: the `mimetype` entry is written with
`ZipInfo`, **first** and **stored** (ZIP_STORED).

The real entry points for the tests:
    make_tiny_epub(dest_dir)        -> EPUB 3 (nav.xhtml)
    make_tiny_epub2(dest_dir)       -> EPUB 2 (toc.ncx)
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

__all__ = ["make_tiny_epub", "make_tiny_epub2", "TINY_TITLE", "TINY_AUTHOR", "TINY_LANG"]

TINY_TITLE = "Minik Kitap"
TINY_AUTHOR = "Test Yazarı"
TINY_LANG = "tr"

CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

# ch1: emphasis/heading, entity, <img>, <script> (must be dropped), soft hyphen,
# zero-width space and a sequence that must be composed with NFC.
CH1_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="tr">
<head>
  <title>Gizli başlık — atılmalı</title>
  <meta charset="utf-8"/>
  <style>p { color: red; }</style>
  <script>var gizli = "bu metin gorunmemeli";</script>
</head>
<body>
  <h1 id="baslangic">Birinci Bölüm</h1>
  <p>Kıyıda küçük bir <em>fener</em> vardı &amp; her akşam yanardı.</p>
  <p>Yumu&#351;ak tire: ka­lem. Sıfır geni&#351;lik: ke​li.</p>
  <p>Birleşik dizi: göl ve düz Yaz.</p>
  <img src="resim.png" alt="bir resim"/>
  <p>Son paragraf&nbsp;&mdash; burada biter.</p>
  <script>console.log("bu satir da gorunmemeli");</script>
</body>
</html>
"""

CH2_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="tr">
<head><title>İkinci dosya</title></head>
<body>
  <h1 id="ikinci">İkinci Bölüm</h1>
  <p>İkinci dosyanın ilk paragrafı.</p>
  <blockquote>Alıntı bloğu ayrı paragraf olur.</blockquote>
  <h2 id="sahne">Bir Sahne</h2>
  <p>Bölüm içi başlıktan sonra gelen paragraf.</p>
  <ul><li>Birinci madde</li><li>İkinci madde</li></ul>
</body>
</html>
"""

NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>İçindekiler</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>İçindekiler</h1>
    <ol>
      <li><a href="ch1.xhtml">Birinci Bölüm</a></li>
      <li><a href="ch2.xhtml">İkinci Bölüm</a>
        <ol>
          <li><a href="ch2.xhtml#sahne">Bir Sahne</a></li>
        </ol>
      </li>
    </ol>
  </nav>
</body>
</html>
"""

OPF3 = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:00000000-0000-0000-0000-000000000001</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>{lang}</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>
"""

OPF2 = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:00000000-0000-0000-0000-000000000002</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>{lang}</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>
"""

NCX = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:00000000-0000-0000-0000-000000000002"/>
    <meta name="dtb:depth" content="2"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>Birinci Bölüm</text></navLabel>
      <content src="ch1.xhtml"/>
    </navPoint>
    <navPoint id="np2" playOrder="2">
      <navLabel><text>İkinci Bölüm</text></navLabel>
      <content src="ch2.xhtml"/>
      <navPoint id="np3" playOrder="3">
        <navLabel><text>Bir Sahne</text></navLabel>
        <content src="ch2.xhtml#sahne"/>
      </navPoint>
    </navPoint>
  </navMap>
</ncx>
"""


def _write_epub(path: Path, files: list[tuple[str, str]]) -> Path:
    """Write the EPUB zip in a rule-compliant way (mimetype first and stored)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        # EPUB requirement: 'mimetype' is the first entry, ZIP_STORED, no extra field.
        info = zipfile.ZipInfo("mimetype", date_time=(2024, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        zf.writestr(info, "application/epub+zip")
        for name, content in files:
            zf.writestr(name, content)
    return path


def make_tiny_epub(dest_dir: str | Path, name: str = "tiny-epub3.epub") -> Path:
    """Write the tiny EPUB 3 (nav.xhtml) book into `dest_dir`."""
    dest = Path(dest_dir).expanduser()
    opf = OPF3.format(title=TINY_TITLE, author=TINY_AUTHOR, lang=TINY_LANG)
    files = [
        ("META-INF/container.xml", CONTAINER_XML),
        ("OEBPS/content.opf", opf),
        ("OEBPS/nav.xhtml", NAV_XHTML),
        ("OEBPS/ch1.xhtml", CH1_XHTML),
        ("OEBPS/ch2.xhtml", CH2_XHTML),
    ]
    return _write_epub(dest / name, files)


def make_tiny_epub2(dest_dir: str | Path, name: str = "tiny-epub2.epub") -> Path:
    """Write the tiny EPUB 2 (toc.ncx) book into `dest_dir`."""
    dest = Path(dest_dir).expanduser()
    opf = OPF2.format(title=TINY_TITLE, author=TINY_AUTHOR, lang=TINY_LANG)
    files = [
        ("META-INF/container.xml", CONTAINER_XML),
        ("OEBPS/content.opf", opf),
        ("OEBPS/toc.ncx", NCX.format(title=TINY_TITLE)),
        ("OEBPS/ch1.xhtml", CH1_XHTML),
        ("OEBPS/ch2.xhtml", CH2_XHTML),
    ]
    return _write_epub(dest / name, files)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="make_tiny_epub.py",
        description="Produce a tiny but valid EPUB zip for the tests.",
    )
    p.add_argument("dest", nargs="?", default=".", help="output folder (default: .)")
    p.add_argument("--epub2", action="store_true", help="produce the EPUB 2 variant with NCX")
    p.add_argument("--name", help="file name")
    args = p.parse_args(argv)

    if args.epub2:
        path = make_tiny_epub2(args.dest, args.name or "tiny-epub2.epub")
    else:
        path = make_tiny_epub(args.dest, args.name or "tiny-epub3.epub")
    print(f"Wrote: {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
