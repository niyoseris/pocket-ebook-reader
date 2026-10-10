#!/usr/bin/env python3
"""EPUB -> .epr converter (Pocket Reader).

This script turns an EPUB 2/3 file into the `.epr` container that the Pocket
Reader device reads.  **It uses only the Python standard library**; it needs
none of the extra packages such as `ebooklib`, `lxml` or `bs4`.

Usage
-----
    python3 epub2epr.py kitap.epub -o kitap.epr
    python3 epub2epr.py kitap.epub --title "Özel Başlık" --author "Yazar"
    python3 epub2epr.py kitap.epr --dump        # inspect an existing .epr
    python3 epub2epr.py kitap.epub --verify     # read it back after writing

Format notes (English, low level)
----------------------------------------
All integers are little-endian.

    offset 0  : magic "EPR1" (4 ASCII bytes)
    offset 4  : uint16 version = 1
    offset 6  : uint16 flags            // bit0 = has_toc
    offset 8  : uint32 text_offset
    offset 12 : uint32 text_length
    offset 16 : uint32 toc_offset       // 0 when flags bit0 is clear
    offset 20 : uint32 toc_count
    offset 24 : uint8 title_len,  then title_len  UTF-8 bytes  (title)
              : uint8 author_len, then author_len UTF-8 bytes  (author)
              : uint8 lang_len,   then lang_len   ASCII bytes  (e.g. "tr")
              : uint8 encoding (0 = UTF-8)
              : zero-pad up to text_offset

    text block (UTF-8):
      0x0A = paragraph break   -> reader indents the first line
      0x0B = chapter break     -> reader starts a NEW PAGE, heading centred
      every other byte is literal text; "\\r" must never appear

    toc block: toc_count entries, each
      uint32 text_pos  (byte offset into the text block)
      uint8  len
      char   title[len] (UTF-8, NOT NUL terminated)

The line breaking is done by the reader itself, so this converter must never
insert line breaks of its own -- only the two control bytes above.  All text is
NFC-normalised so Turkish decomposed sequences (o + combining diaeresis) fold
into single codepoints such as "ö" before the byte offsets are computed.

Judgement calls made where the spec was silent
----------------------------------------------
* `text_offset` is aligned up to a multiple of 4; the reader must honour the
  field rather than assume the strings end there.
* A chapter break byte is emitted *instead of* the paragraph break that would
  otherwise close the previous paragraph (0x0B implies a paragraph boundary).
* When a TOC target is the very first block of the book there is nothing to
  break away from, so no 0x0B is written and the TOC entry points at offset 0.
* A TOC entry whose href carries a `#fragment` is mapped onto the block that
  owns the matching `id` attribute when that can be found, and onto the start
  of the spine item otherwise.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import struct
import sys
import unicodedata
import zipfile
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote, urlsplit

__all__ = [
    "MAGIC",
    "VERSION",
    "FLAG_HAS_TOC",
    "PARA",
    "CHAPTER",
    "TocEntry",
    "Book",
    "EprError",
    "build_epr",
    "read_epr",
    "read_epr_file",
    "convert_epub",
    "main",
]

# --- format constants -------------------------------------------------------

MAGIC = b"EPR1"
VERSION = 1
FLAG_HAS_TOC = 0x0001

PARA = 0x0A  # paragraph break
CHAPTER = 0x0B  # chapter / section break

ENCODING_UTF8 = 0
HEADER_SIZE = 24  # fixed part of the header, before the string block
MAX_U8 = 0xFF
MAX_U32 = 0xFFFFFFFF
TEXT_ALIGN = 4


class EprError(Exception):
    """Error raised while producing or parsing an `.epr`."""


# --- data model -------------------------------------------------------------


@dataclass
class TocEntry:
    """A single table-of-contents row: byte position in the text block + title."""

    text_pos: int
    title: str


@dataclass
class Book:
    """A parsed / to-be-produced `.epr` book."""

    title: str = ""
    author: str = ""
    lang: str = ""
    text: bytes = b""
    toc: list[TocEntry] = field(default_factory=list)
    version: int = VERSION
    flags: int = 0
    encoding: int = ENCODING_UTF8
    text_offset: int = 0
    toc_offset: int = 0
    # For statistics/diagnostics only; not written to the file.
    source: str = ""

    @property
    def has_toc(self) -> bool:
        return bool(self.flags & FLAG_HAS_TOC)

    @property
    def text_str(self) -> str:
        """Decode the text block as UTF-8 while preserving the control bytes."""
        return self.text.decode("utf-8", "replace")

    def paragraphs(self) -> int:
        return self.text.count(bytes([PARA])) + self.text.count(bytes([CHAPTER]))

    def chapters(self) -> int:
        return self.text.count(bytes([CHAPTER]))


# --- byte helpers -----------------------------------------------------------


def _fit_u8_string(value: str, limit: int = MAX_U8, what: str = "alan") -> bytes:
    """Encode as UTF-8; if it exceeds `limit` bytes, cut at a code point boundary."""
    data = value.encode("utf-8")
    if len(data) <= limit:
        return data
    return data[:limit].decode("utf-8", "ignore").encode("utf-8")


def _require_u8_string(value: str, what: str) -> bytes:
    """Strict version for `build_epr`: it does not silently cut an over-long field, it raises."""
    data = value.encode("utf-8")
    if len(data) > MAX_U8:
        raise EprError(
            f"{what} is too long: {len(data)} bytes (at most {MAX_U8} bytes allowed). "
            f"Shorten it with --title/--author."
        )
    return data


# --- writing ----------------------------------------------------------------


def build_epr(book: Book) -> bytes:
    """Turn a `Book` object into a `.epr` byte string.

    Bounds are checked strictly here: a title/author/language field longer than
    255 bytes, or a text block larger than 4 GiB, raises `EprError` instead of
    being silently corrupted.
    """
    text = bytes(book.text)
    if b"\r" in text:
        raise EprError(
            "The text block contains '\\r' (0x0D); .epr v1 forbids this. "
            "Converter bug."
        )
    if len(text) > MAX_U32:
        raise EprError(f"Text block is too large: {len(text)} bytes (at most 4 GiB).")

    title_b = _require_u8_string(book.title, "Title")
    author_b = _require_u8_string(book.author, "Author")
    lang_b = _require_u8_string(book.lang, "Language")

    toc = list(book.toc)
    if len(toc) > MAX_U32:
        raise EprError("Table of contents is too large.")

    toc_block = bytearray()
    for entry in toc:
        if not (0 <= entry.text_pos <= len(text)):
            raise EprError(
                f"Table-of-contents position is outside the text: {entry.text_pos} "
                f"(text is {len(text)} bytes)."
            )
        title_bytes = _require_u8_string(entry.title, "Table-of-contents title")
        toc_block += struct.pack("<I", entry.text_pos)
        toc_block += struct.pack("<B", len(title_bytes))
        toc_block += title_bytes

    flags = FLAG_HAS_TOC if toc else 0
    encoding = book.encoding if book.encoding == ENCODING_UTF8 else ENCODING_UTF8
    version = book.version if book.version else VERSION

    strings = bytearray()
    for blob in (title_b, author_b, lang_b):
        strings += struct.pack("<B", len(blob))
        strings += blob
    strings += struct.pack("<B", encoding)

    text_offset = HEADER_SIZE + len(strings)
    pad = (-text_offset) % TEXT_ALIGN
    text_offset += pad  # zero padding between the strings and the text block

    toc_offset = text_offset + len(text) if toc else 0

    header = struct.pack(
        "<4sHHIIII",
        MAGIC,
        version,
        flags,
        text_offset,
        len(text),
        toc_offset,
        len(toc),
    )
    out = bytearray(header)
    out += strings
    out += b"\x00" * pad
    out += text
    out += toc_block
    return bytes(out)


# --- reading ----------------------------------------------------------------


def read_epr(data: bytes) -> Book:
    """Parse and validate an `.epr` byte string.

    On a corrupt file it raises `EprError`; it never returns a half-built `Book`.
    """
    if len(data) < HEADER_SIZE:
        raise EprError(
            f"File is too small: {len(data)} bytes (at least {HEADER_SIZE} bytes required)."
        )
    magic, version, flags, text_offset, text_length, toc_offset, toc_count = struct.unpack(
        "<4sHHIIII", data[:HEADER_SIZE]
    )
    if magic != MAGIC:
        raise EprError(
            f"Invalid magic number: {magic!r} (expected 'EPR1'). "
            f"This is not an .epr file."
        )
    if version != VERSION:
        raise EprError(f"Unsupported version: {version} (expected {VERSION}).")

    pos = HEADER_SIZE
    strings: list[str] = []
    for what in ("Title", "Author", "Language"):
        if pos >= len(data):
            raise EprError(f"File ended while reading the {what} field.")
        n = data[pos]
        pos += 1
        if pos + n > len(data):
            raise EprError(f"File ended while reading the {what} field ({n} bytes expected).")
        strings.append(data[pos : pos + n].decode("utf-8", "replace"))
        pos += n
    if pos >= len(data):
        raise EprError("File ended while reading the encoding byte.")
    encoding = data[pos]
    pos += 1

    if encoding != ENCODING_UTF8:
        raise EprError(
            f"Unsupported text encoding: {encoding} (only 0 = UTF-8)."
        )
    if text_offset < HEADER_SIZE or text_offset > len(data):
        raise EprError(f"text_offset out of range: {text_offset} (file is {len(data)} bytes).")
    if text_offset + text_length > len(data):
        raise EprError(
            f"Text block runs past the end of the file: {text_offset}+{text_length} > {len(data)}."
        )

    text = bytes(data[text_offset : text_offset + text_length])
    if b"\r" in text:
        raise EprError("Forbidden 0x0D (\\r) byte found in the text block.")

    has_toc = bool(flags & FLAG_HAS_TOC)
    toc: list[TocEntry] = []
    if has_toc:
        if toc_count == 0:
            raise EprError("flags bit0 is set but toc_count = 0.")
        if toc_offset == 0:
            raise EprError("flags bit0 is set but toc_offset = 0.")
        if toc_offset < text_offset + text_length or toc_offset > len(data):
            raise EprError(f"toc_offset out of range: {toc_offset}.")
        tp = toc_offset
        for i in range(toc_count):
            if tp + 5 > len(data):
                raise EprError(f"File ended while reading table-of-contents entry {i}.")
            text_pos = struct.unpack("<I", data[tp : tp + 4])[0]
            tp += 4
            n = data[tp]
            tp += 1
            if tp + n > len(data):
                raise EprError(f"File ended while reading table-of-contents title {i}.")
            title = data[tp : tp + n].decode("utf-8", "replace")
            tp += n
            if text_pos > text_length:
                raise EprError(
                    f"Table-of-contents entry {i} points outside the text: {text_pos}."
                )
            toc.append(TocEntry(text_pos=text_pos, title=title))
    elif toc_count != 0 or toc_offset != 0:
        raise EprError("flags bit0 is clear but toc_count/toc_offset is not zero.")

    return Book(
        title=strings[0],
        author=strings[1],
        lang=strings[2],
        text=text,
        toc=toc,
        version=version,
        flags=flags,
        encoding=encoding,
        text_offset=text_offset,
        toc_offset=toc_offset,
    )


def read_epr_file(path: str | Path) -> Book:
    """Read an `.epr` file from disk and parse it with `read_epr`."""
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise EprError(f"Could not read file: {p} ({exc.strerror or exc})") from exc
    book = read_epr(data)
    book.source = str(p)
    return book


# --- HTML -> text -----------------------------------------------------------

# Content of these elements is thrown away entirely.
DROP_TAGS = frozenset({"script", "style", "head", "title", "noscript", "svg", "canvas"})

# These start a new paragraph (0x0A).
BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "br",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "pre",
        # Extra structural tags that almost always mark a visual block.  They can
        # only ever add a paragraph break, never remove text.
        "hr",
        "section",
        "article",
        "header",
        "footer",
        "aside",
        "figure",
        "figcaption",
        "ul",
        "ol",
        "dl",
        "dd",
        "dt",
        "table",
        "tr",
        "td",
        "th",
        "caption",
    }
)

# <h1>..<h6> additionally force a chapter break (0x0B).
HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

# Soft hyphen + zero-width characters: silently deleted.
ZERO_WIDTH_CHARS = "­​‌‍﻿"
_ZERO_WIDTH_TABLE = {ord(ch): None for ch in ZERO_WIDTH_CHARS}

# Exotic spaces mapped onto a plain ASCII space so the reader can break lines.
EXOTIC_SPACES = "               　"
_SPACE_TABLE = {ord(ch): " " for ch in EXOTIC_SPACES}

_WS_RE = re.compile(r"[ \t\n\f\v\r]+")


def normalize_text(raw: str, strip_diacritics: bool = False) -> str:
    """Normalise a single run of text into the form the device expects.

    In order: delete soft-hyphen/zero-width characters, simplify exotic spaces,
    collapse whitespace runs into a single space, strip leading/trailing space,
    and compose with NFC.  `strip_diacritics` flattens Turkish accents.
    """
    s = raw.translate(_ZERO_WIDTH_TABLE).translate(_SPACE_TABLE)
    s = _WS_RE.sub(" ", s).strip()
    if not s:
        return ""
    if strip_diacritics:
        s = remove_diacritics(s)
    return unicodedata.normalize("NFC", s)


# Turkish letters that have no NFD decomposition (or that NFD would mangle the
# dotless/dotted distinction on) are handled by an explicit table first.
_TR_TRANSLIT = {
    ord("ı"): "i",
    ord("İ"): "I",
    ord("ğ"): "g",
    ord("Ğ"): "G",
    ord("ş"): "s",
    ord("Ş"): "S",
    ord("ç"): "c",
    ord("Ç"): "C",
    ord("ö"): "o",
    ord("Ö"): "O",
    ord("ü"): "u",
    ord("Ü"): "U",
    ord("â"): "a",
    ord("î"): "i",
    ord("û"): "u",
}


def remove_diacritics(text: str) -> str:
    """Strip diacritics; letters specific to Turkish are mapped by hand.

    Such as `İ` -> `I`, `ı` -> `i`, `ş` -> `s`, `ğ` -> `g`, `ç` -> `c`.  This
    mode is only meaningful when you are forced to use a font that lacks the
    Turkish glyphs: "İstanbul" -> "Istanbul", "şğüöçı" -> "sguoci".
    Distinguishing information is lost, so it is OFF by default.
    """
    text = text.translate(_TR_TRANSLIT)
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


@dataclass
class Block:
    """A single normalised run of text produced from one HTML block."""

    text: str
    chapter: bool = False


class HtmlTextExtractor(HTMLParser):
    """A small state machine: it produces plain text block by block from HTML.

    `blocks` is the result, while `id_marks` says which block each `id="..."`
    attribute falls on (so that intra-book links can be resolved).
    """

    def __init__(self, strip_diacritics: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.id_marks: dict[str, int] = {}
        self.strip_diacritics = strip_diacritics
        self._cur: list[str] = []
        self._pending_chapter = False
        self._drop_depth = 0

    # -- internals ----------------------------------------------------------

    def _flush(self) -> None:
        text = normalize_text("".join(self._cur), self.strip_diacritics)
        self._cur = []
        chapter, self._pending_chapter = self._pending_chapter, False
        if text:
            self.blocks.append(Block(text, chapter))

    def _note_id(self, attrs: Sequence[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key == "id" and value:
                self.id_marks.setdefault(value, len(self.blocks))

    # -- HTMLParser hooks ---------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._drop_depth:
            if tag in DROP_TAGS:
                self._drop_depth += 1
            return
        if tag in DROP_TAGS:
            self._flush()
            self._drop_depth = 1
            return
        if tag == "img":
            self._cur.append("[resim]")
            self._note_id(attrs)
            return
        if tag in BLOCK_TAGS:
            self._flush()
            if tag in HEADING_TAGS:
                self._pending_chapter = True
        self._note_id(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing tags such as <br/>, <img/>, <hr/>.
        if self._drop_depth:
            return
        if tag == "img":
            self._cur.append("[resim]")
            self._note_id(attrs)
            return
        if tag in BLOCK_TAGS:
            self._flush()
        self._note_id(attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._drop_depth:
            if tag in DROP_TAGS:
                self._drop_depth -= 1
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._drop_depth:
            return
        self._cur.append(data)

    def close(self) -> None:
        super().close()
        if not self._drop_depth:
            self._flush()
        self._drop_depth = 0


# --- text builder -----------------------------------------------------------


class TextBuilder:
    """Builds up the text block (with the 0x0A / 0x0B control bytes) in sequence."""

    def __init__(self) -> None:
        self.buf = bytearray()

    def _trim_trailing_breaks(self) -> None:
        # 0x0A and 0x0B are ASCII control bytes; they can never be part of a
        # multi-byte UTF-8 sequence, so trimming from the end is safe.
        while self.buf and self.buf[-1] in (PARA, CHAPTER):
            self.buf.pop()

    def add_block(self, block: Block) -> int:
        """Append the block and return the position of the text's first byte (-1: empty block).

        Each block leaves a 0x0A at its own end; that way there is exactly one
        control byte between blocks.  The trailing byte is trimmed ONLY when a
        chapter break is being added: then the paragraph end gives way to 0x0B.
        (If this trimming were done unconditionally, the previous block's
        paragraph end would be deleted and every 0x0A byte in the text would be
        lost -- the blocks would run together.)
        """
        data = block.text.encode("utf-8")
        if not data or not data.strip():
            # A block that is empty or holds only whitespace does not open a
            # paragraph.  The text normally already arrives trimmed from
            # HtmlTextExtractor; it is checked here too so that the "blocks
            # carry no whitespace" rule holds for every caller.
            return -1
        if block.chapter:
            self._trim_trailing_breaks()
            if self.buf:
                # If the book's first block is a chapter break, no 0x0B is
                # written: offset 0 is already the start of the first page, and
                # an extra byte could open a blank page.
                self.buf.append(CHAPTER)
        start = len(self.buf)
        self.buf.extend(data)
        self.buf.append(PARA)
        return start

    def finish(self) -> bytes:
        self._trim_trailing_breaks()
        return bytes(self.buf)


# --- EPUB reading -----------------------------------------------------------


def _localname(tag: str) -> str:
    """`{namespace}tag` -> `tag` (lowercases it)."""
    if "}" in tag:
        tag = tag.rsplit("}", 1)[1]
    return tag.lower()


def _findall_local(root, name: str):
    name = name.lower()
    return [el for el in root.iter() if _localname(el.tag) == name]


def _text_of(elem) -> str:
    return "".join(elem.itertext()).strip()


@dataclass
class ManifestItem:
    id: str
    href: str  # path resolved against the OPF directory and normalised
    media_type: str = ""
    properties: str = ""


@dataclass
class EpubDoc:
    """Raw data gathered from the EPUB."""

    title: str = ""
    author: str = ""
    lang: str = ""
    opf_dir: str = ""
    manifest: dict[str, ManifestItem] = field(default_factory=dict)
    by_path: dict[str, str] = field(default_factory=dict)  # path -> manifest id
    spine: list[str] = field(default_factory=list)  # list of manifest ids
    nav_path: str = ""
    ncx_path: str = ""

    def spine_paths(self) -> list[str]:
        return [self.manifest[i].href for i in self.spine if i in self.manifest]


@dataclass
class TocSource:
    """A raw row coming from a table-of-contents source (href not yet resolved)."""

    href: str
    title: str


def _resolve_href(base_dir: str, href: str) -> tuple[str, str]:
    """Resolve href into (path, fragment) relative to `base_dir`."""
    parts = urlsplit(href.strip())
    path = unquote(parts.path)
    frag = parts.fragment or ""
    if path:
        joined = posixpath.join(base_dir, path) if base_dir else path
        path = posixpath.normpath(joined)
        if path.startswith("../"):
            path = path.lstrip("./")
    else:
        path = ""
    return path, frag


def _decode_xml_bytes(raw: bytes) -> str:
    """Decode XHTML/XML bytes with the declared encoding (UTF-8 otherwise)."""
    head = raw[:2048]
    enc = None
    m = re.search(rb'<\?xml[^>]*?encoding\s*=\s*["\']([^"\']+)', head, re.I)
    if m:
        enc = m.group(1).decode("ascii", "ignore")
    if not enc:
        m = re.search(rb'<meta[^>]*?charset\s*=\s*["\']?([A-Za-z0-9_\-]+)', raw[:8192], re.I)
        if m:
            enc = m.group(1).decode("ascii", "ignore")
    if enc:
        try:
            return raw.decode(enc, "replace")
        except LookupError:
            pass
    return raw.decode("utf-8", "replace")


def open_epub(path: str | Path) -> tuple[zipfile.ZipFile, EpubDoc]:
    """Open the EPUB zip and gather the OPF/metadata/manifest/spine information."""
    try:
        zf = zipfile.ZipFile(path)
    except FileNotFoundError as exc:
        raise EprError(f"EPUB not found: {path}") from exc
    except zipfile.BadZipFile as exc:
        raise EprError(
            f"'{path}' is not a valid ZIP/EPUB ({exc}). "
            f"The file may be corrupt; try downloading it from another source."
        ) from exc
    except OSError as exc:
        raise EprError(f"Could not open EPUB: {path} ({exc})") from exc

    try:
        doc = _parse_opf(zf)
    except EprError:
        zf.close()
        raise
    return zf, doc


def _parse_opf(zf: zipfile.ZipFile) -> EpubDoc:
    import xml.etree.ElementTree as ET

    try:
        container_raw = zf.read("META-INF/container.xml")
    except KeyError as exc:
        raise EprError(
            "Invalid EPUB: META-INF/container.xml not found. "
            "This is not an EPUB file."
        ) from exc

    try:
        container = ET.fromstring(container_raw)
    except ET.ParseError as exc:
        raise EprError(f"Could not parse container.xml: {exc}") from exc

    opf_path = ""
    for rootfile in _findall_local(container, "rootfile"):
        candidate = rootfile.get("full-path") or ""
        if candidate:
            opf_path = candidate
            break
    if not opf_path:
        raise EprError("No rootfile/full-path inside container.xml.")

    try:
        opf_raw = zf.read(opf_path)
    except KeyError as exc:
        raise EprError(f"OPF file is not inside the package: {opf_path}") from exc

    try:
        opf = ET.fromstring(opf_raw)
    except ET.ParseError as exc:
        raise EprError(f"Could not parse OPF ({opf_path}): {exc}") from exc

    opf_dir = posixpath.dirname(opf_path)
    doc = EpubDoc(opf_dir=opf_dir)

    # --- metadata ---
    for meta in _findall_local(opf, "metadata"):
        for child in meta:
            name = _localname(child.tag)
            value = _text_of(child)
            if not value:
                continue
            if name == "title" and not doc.title:
                doc.title = value
            elif name == "creator" and not doc.author:
                doc.author = value
            elif name == "language" and not doc.lang:
                doc.lang = value.split("-")[0].split("_")[0].strip()

    # --- manifest ---
    for manifest in _findall_local(opf, "manifest"):
        for item in manifest:
            if _localname(item.tag) != "item":
                continue
            item_id = item.get("id") or ""
            href = item.get("href") or ""
            if not item_id or not href:
                continue
            resolved, _frag = _resolve_href(opf_dir, href)
            entry = ManifestItem(
                id=item_id,
                href=resolved,
                media_type=(item.get("media-type") or "").lower(),
                properties=(item.get("properties") or "").lower(),
            )
            doc.manifest[item_id] = entry
            doc.by_path.setdefault(resolved, item_id)

    # --- spine ---
    ncx_id: str | None = None
    for spine in _findall_local(opf, "spine"):
        ncx_id = spine.get("toc") or ncx_id
        for ref in spine:
            if _localname(ref.tag) != "itemref":
                continue
            idref = ref.get("idref") or ""
            if idref and idref in doc.manifest:
                doc.spine.append(idref)
        break

    if not doc.spine:
        raise EprError(
            "The EPUB has no readable sections (empty spine). The file may be corrupt."
        )

    # --- find the nav / ncx sources ---
    for item in doc.manifest.values():
        if "nav" in item.properties.split():
            doc.nav_path = item.href
            break
    if not doc.nav_path:
        # Some producers omit the properties="nav" attribute; we look for an
        # XHTML file named "nav"/"toc", and fall back to the first XHTML if we
        # cannot find one (in which case the table of contents most likely
        # comes from the NCX).
        candidates = [
            item
            for item in doc.manifest.values()
            if item.media_type == "application/xhtml+xml"
        ]
        for item in candidates:
            if re.search(r"(nav|toc|contents|icindekiler)", item.href, re.I):
                doc.nav_path = item.href
                break
        if not doc.nav_path and candidates:
            doc.nav_path = candidates[0].href

    if ncx_id and ncx_id in doc.manifest:
        doc.ncx_path = doc.manifest[ncx_id].href
    if not doc.ncx_path:
        for item in doc.manifest.values():
            if item.media_type == "application/x-dtbncx+xml":
                doc.ncx_path = item.href
                break
    if not doc.ncx_path:
        for item in doc.manifest.values():
            if item.href.lower().endswith(".ncx"):
                doc.ncx_path = item.href
                break

    return doc


def _read_nav(zf: zipfile.ZipFile, nav_path: str) -> list[TocSource]:
    """Read the table of contents from the EPUB3 nav document (empty list if absent)."""
    import xml.etree.ElementTree as ET

    if not nav_path:
        return []
    try:
        raw = zf.read(nav_path)
    except KeyError:
        return []
    try:
        root = ET.fromstring(_decode_xml_bytes(raw).encode("utf-8"))
    except ET.ParseError:
        return []

    nav_elems = [
        el
        for el in _findall_local(root, "nav")
        if "toc" in (el.get("{http://www.idpf.org/2007/ops}type") or el.get("type") or "")
    ]
    if not nav_elems:
        nav_elems = _findall_local(root, "nav")
    if not nav_elems:
        return []

    base_dir = posixpath.dirname(nav_path)
    entries: list[TocSource] = []

    def walk(list_elem) -> None:
        for child in list_elem:
            name = _localname(child.tag)
            if name == "li":
                for sub in child:
                    if _localname(sub.tag) == "a":
                        href = sub.get("href") or ""
                        title = _text_of(sub)
                        if href:
                            entries.append(TocSource(href=href, title=title or href))
                    elif _localname(sub.tag) in ("ol", "ul"):
                        walk(sub)
            elif name in ("ol", "ul"):
                walk(child)

    for nav in nav_elems:
        for child in nav:
            if _localname(child.tag) in ("ol", "ul"):
                walk(child)

    # nav hrefs are relative to the nav document; resolve the paths now.
    out: list[TocSource] = []
    for src in entries:
        path, frag = _resolve_href(base_dir, src.href)
        rebuilt = path + (("#" + frag) if frag else "")
        out.append(TocSource(rebuilt, src.title))
    return out


def _read_ncx(zf: zipfile.ZipFile, ncx_path: str) -> list[TocSource]:
    """Read the table of contents from the EPUB2 toc.ncx file (empty list if absent)."""
    import xml.etree.ElementTree as ET

    if not ncx_path:
        return []
    try:
        raw = zf.read(ncx_path)
    except KeyError:
        return []
    try:
        root = ET.fromstring(_decode_xml_bytes(raw).encode("utf-8"))
    except ET.ParseError:
        return []

    base_dir = posixpath.dirname(ncx_path)
    entries: list[TocSource] = []

    def walk(node) -> None:
        for child in node:
            if _localname(child.tag) != "navpoint":
                continue
            title = ""
            for label in child:
                if _localname(label.tag) == "navlabel":
                    title = _text_of(label)
                    break
            href = ""
            for content in child:
                if _localname(content.tag) == "content":
                    href = content.get("src") or ""
                    break
            if href:
                path, frag = _resolve_href(base_dir, href)
                rebuilt = path + (("#" + frag) if frag else "")
                entries.append(TocSource(rebuilt, title or href))
            walk(child)

    containers = _findall_local(root, "navmap")
    for navmap in containers:
        walk(navmap)
    if not containers:
        for navpoint in _findall_local(root, "navpoint"):
            title = ""
            for label in navpoint:
                if _localname(label.tag) == "navlabel":
                    title = _text_of(label)
                    break
            for content in navpoint:
                if _localname(content.tag) == "content":
                    href = content.get("src") or ""
                    if href:
                        path, frag = _resolve_href(base_dir, href)
                        entries.append(
                            TocSource(path + (("#" + frag) if frag else ""), title or href)
                        )
                    break
            break
    return entries


# --- conversion -------------------------------------------------------------


@dataclass
class SpineInfo:
    """The projection of one spine item into the text block."""

    first_pos: int = -1
    block_positions: list[int] = field(default_factory=list)
    id_marks: dict[str, int] = field(default_factory=dict)


@dataclass
class ConvertStats:
    paragraphs: int = 0
    chapters: int = 0
    spine_items: int = 0
    text_bytes: int = 0
    toc_entries: int = 0
    toc_resolved: int = 0
    toc_unresolved: int = 0

    def lines(self) -> list[str]:
        return [
            f"Spine items      : {self.spine_items}",
            f"Paragraph (0x0A) : {self.paragraphs}",
            f"Chapter (0x0B)   : {self.chapters}",
            f"Text size        : {self.text_bytes} bytes",
            f"Contents         : {self.toc_entries} rows "
            f"({self.toc_resolved} resolved, {self.toc_unresolved} skipped)",
        ]


def convert_epub(
    path: str | Path,
    *,
    title: str | None = None,
    author: str | None = None,
    lang: str | None = None,
    want_toc: bool = True,
    strip_diacritics: bool = False,
    truncate: bool = True,
) -> tuple[Book, ConvertStats]:
    """Read the EPUB file and return `Book` + statistics.

    When `truncate=True`, title/author/table-of-contents rows longer than 255
    bytes are cut at a code point boundary; when `False`, `EprError` is raised.
    """
    zf, doc = open_epub(path)
    try:
        return _convert_open(zf, doc, path, title, author, lang, want_toc,
                             strip_diacritics, truncate)
    finally:
        zf.close()


def _convert_open(
    zf: zipfile.ZipFile,
    doc: EpubDoc,
    path: str | Path,
    title: str | None,
    author: str | None,
    lang: str | None,
    want_toc: bool,
    strip_diacritics: bool,
    truncate: bool,
) -> tuple[Book, ConvertStats]:

    spine_paths = doc.spine_paths()
    toc_sources: list[TocSource] = []
    if want_toc:
        toc_sources = _read_nav(zf, doc.nav_path)
        if not toc_sources:
            toc_sources = _read_ncx(zf, doc.ncx_path)

    # 1) Build the text and produce the position map of each spine item.
    builder = TextBuilder()
    infos: list[SpineInfo] = []
    stats = ConvertStats(spine_items=len(spine_paths))

    toc_targets: set[str] = set()
    for src in toc_sources:
        toc_targets.add(src.href.split("#", 1)[0])

    spine_index_of: dict[str, int] = {}
    for idx, mpath in enumerate(spine_paths):
        spine_index_of.setdefault(mpath, idx)
    spine_index_lower = {k.lower(): v for k, v in spine_index_of.items()}

    def lookup_spine(target: str) -> int | None:
        if target in spine_index_of:
            return spine_index_of[target]
        return spine_index_lower.get(target.lower())

    for idx, mpath in enumerate(spine_paths):
        try:
            raw = zf.read(mpath)
        except KeyError:
            infos.append(SpineInfo())
            continue
        html = _decode_xml_bytes(raw)
        parser = HtmlTextExtractor(strip_diacritics=strip_diacritics)
        try:
            parser.feed(html)
            parser.close()
        except Exception:  # HTMLParser rarely blows up on broken HTML
            pass

        blocks = parser.blocks
        if blocks and mpath in toc_targets:
            # If the table of contents points at this file, make its first block a chapter start.
            blocks = [replace(blocks[0], chapter=True)] + blocks[1:]

        info = SpineInfo(id_marks=dict(parser.id_marks))
        for block in blocks:
            pos = builder.add_block(block)
            info.block_positions.append(pos)
            if pos >= 0 and info.first_pos < 0:
                info.first_pos = pos
        infos.append(info)

    text = builder.finish()
    stats.text_bytes = len(text)
    stats.paragraphs = text.count(bytes([PARA]))
    stats.chapters = text.count(bytes([CHAPTER]))

    # 2) Build the table of contents in nav/ncx order.
    toc: list[TocEntry] = []
    for src in toc_sources:
        target, _, frag = src.href.partition("#")
        s_idx = lookup_spine(target) if target else None
        if s_idx is None:
            stats.toc_unresolved += 1
            continue
        info = infos[s_idx]
        pos = -1
        if frag:
            mark = info.id_marks.get(frag)
            if mark is None:
                mark = info.id_marks.get(unquote(frag))
            if mark is not None and 0 <= mark < len(info.block_positions):
                pos = info.block_positions[mark]
        if pos < 0:
            pos = info.first_pos
        if pos < 0:
            stats.toc_unresolved += 1
            continue
        t_title = normalize_text(src.title, strip_diacritics) or target
        if truncate:
            t_title = _fit_u8_string(t_title).decode("utf-8", "ignore")
        toc.append(TocEntry(text_pos=pos, title=t_title))
        stats.toc_resolved += 1

    stats.toc_entries = len(toc)

    # 3) Metadata.
    book_title = (title if title is not None else doc.title) or Path(path).stem
    book_author = author if author is not None else doc.author
    book_lang = (lang if lang is not None else doc.lang) or ""

    book_title = normalize_text(book_title, strip_diacritics) or Path(path).stem
    book_author = normalize_text(book_author, strip_diacritics)
    book_lang = re.sub(r"[^A-Za-z]", "", book_lang)[:8]

    if truncate:
        book_title = _fit_u8_string(book_title).decode("utf-8", "ignore")
        book_author = _fit_u8_string(book_author).decode("utf-8", "ignore")

    book = Book(
        title=book_title,
        author=book_author,
        lang=book_lang,
        text=text,
        toc=toc,
        flags=FLAG_HAS_TOC if toc else 0,
    )
    book.source = str(path)
    return book, stats


def convert_and_write(
    src: str | Path,
    dst: str | Path,
    *,
    title: str | None = None,
    author: str | None = None,
    lang: str | None = None,
    want_toc: bool = True,
    strip_diacritics: bool = False,
    verify: bool = False,
    verbose: bool = False,
) -> tuple[Path, ConvertStats]:
    """Convert the EPUB to `.epr` and write it to disk. `send.py` uses this function."""
    book, stats = convert_epub(
        src,
        title=title,
        author=author,
        lang=lang,
        want_toc=want_toc,
        strip_diacritics=strip_diacritics,
    )
    data = build_epr(book)
    out = Path(dst)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    if verify:
        check = read_epr(out.read_bytes())
        if check.text != book.text or len(check.toc) != len(book.toc):
            raise EprError(f"Verification failed: the written file could not be read back ({out}).")
    if verbose:
        print(f"Wrote: {out} ({len(data)} bytes)", file=sys.stderr)
    return out, stats


# --- CLI --------------------------------------------------------------------


def _dump(path: str | Path) -> int:
    """Print the header + the first 500 characters of the text (dump mode)."""
    book = read_epr_file(path)
    raw = Path(path).read_bytes()
    print(f"=== {path} ===")
    print(f"magic number  : {raw[:4]!r}")
    print(f"version       : {book.version}")
    print(f"flags         : 0x{book.flags:04X}" + (" (has TOC)" if book.has_toc else " (no TOC)"))
    print(f"title         : {book.title!r}")
    print(f"author        : {book.author!r}")
    print(f"language      : {book.lang!r}")
    print(f"encoding      : {book.encoding} (0 = UTF-8)")
    print(f"text_offset   : {book.text_offset}")
    print(f"text_length   : {len(book.text)}")
    print(f"toc_offset    : {book.toc_offset}")
    print(f"toc_count     : {len(book.toc)}")
    print(f"paragraphs    : {book.paragraphs()}")
    print(f"chapter end 0x0B: {book.chapters()}")
    print(f"chapters (TOC) : {len(book.toc)}")
    if book.toc:
        print("table of contents:")
        for i, entry in enumerate(book.toc[:40]):
            print(f"  {i:3d} @{entry.text_pos:<8d} {entry.title}")
        if len(book.toc) > 40:
            print(f"  ... ({len(book.toc) - 40} more rows)")
    preview = book.text_str.replace("\x0a", "\n¶ ").replace("\x0b", "\n\n§ ")
    print("--- text (first 500 characters) ---")
    print(preview[:500])
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="epub2epr.py",
        description=(
            "Convert an EPUB 2/3 file into Pocket Reader's .epr format. "
            "Line wrapping is done on the device; the converter does not add "
            "line breaks to the text."
        ),
        epilog=(
            "Examples:\n"
            "  epub2epr.py kitap.epub -o kitap.epr\n"
            "  epub2epr.py kitap.epub --title 'Başlık' --author 'Yazar' -v\n"
            "  epub2epr.py kitap.epub --no-toc --strip-diacritics\n"
            "  epub2epr.py kitap.epr --dump\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="source file (.epub) or, for --dump, an .epr")
    p.add_argument(
        "-o",
        "--output",
        help="output .epr path (default: input name with an .epr extension)",
    )
    p.add_argument("--title", help="override the book title (ignore the EPUB metadata)")
    p.add_argument("--author", help="override the author name")
    p.add_argument("--lang", help='override the language code (e.g. "tr")')
    p.add_argument(
        "--no-toc",
        action="store_true",
        help="do not produce a table of contents (the file gets slightly smaller)",
    )
    p.add_argument(
        "--strip-diacritics",
        action="store_true",
        help=(
            "Strip diacritics: İ->I, ı->i, ş->s, ğ->g, ç->c, ö->o, ü->u. "
            "Needed when you are forced to use a font without Turkish glyphs, "
            "BUT distinguishing information is lost (ş/s, ı/i become confused) "
            "and search/hyphenation behaviour breaks. If possible, build a "
            "Turkish-enabled font instead."
        ),
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="after writing, read the file back with read_epr() and verify it",
    )
    p.add_argument(
        "--dump",
        action="store_true",
        help="do not convert; print the header and first 500 characters of an existing .epr file",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="print detailed statistics")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.dump:
        try:
            return _dump(args.input)
        except EprError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: input not found: {src}", file=sys.stderr)
        return 2
    if src.suffix.lower() != ".epub":
        print(
            f"WARNING: '{src.name}' does not have an .epub extension; trying anyway.",
            file=sys.stderr,
        )

    out = Path(args.output) if args.output else src.with_suffix(".epr")

    try:
        book, stats = convert_epub(
            src,
            title=args.title,
            author=args.author,
            lang=args.lang,
            want_toc=not args.no_toc,
            strip_diacritics=args.strip_diacritics,
        )
        data = build_epr(book)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        if args.verify:
            again = read_epr(out.read_bytes())
            if again.text != book.text:
                raise EprError("Verification failed: the text differs when read back.")
            if len(again.toc) != len(book.toc):
                raise EprError("Verification failed: the table-of-contents row count differs.")
    except EprError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: could not write file: {out} ({exc})", file=sys.stderr)
        return 3

    print(f"Title  : {book.title}")
    if book.author:
        print(f"Author : {book.author}")
    if book.lang:
        print(f"Language: {book.lang}")
    print(f"Output : {out} ({len(data)} bytes)")
    if args.verbose:
        for line in stats.lines():
            print(line)
    if args.verify:
        print("Verification: OK (read back, text and TOC match)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
