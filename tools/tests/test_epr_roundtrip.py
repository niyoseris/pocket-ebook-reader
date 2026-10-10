#!/usr/bin/env python3
"""End-to-end tests for the `.epr` format (only `unittest`).

Run:
    cd tools && python3 -m unittest discover -s tests -v
    cd tools && python3 tests/test_epr_roundtrip.py

Coverage:
  * build_epr -> read_epr roundtrip, header fields and padding bytes
  * raw byte level checks of the format contract (offsets, 0x0A/0x0B)
  * rejection of corrupt files (magic number, version, truncated file, \\r, overflowing TOC)
  * EPUB 3 (nav.xhtml) and EPUB 2 (toc.ncx) conversion, end to end
  * HTML cleaning rules: <script> is dropped, <img> -> [resim], entities are
    decoded, soft hyphen/zero-width removed, NFC applied
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = TESTS_DIR.parent
for candidate in (str(TOOLS_DIR), str(TESTS_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import epub2epr  # noqa: E402
from epub2epr import (  # noqa: E402
    CHAPTER,
    FLAG_HAS_TOC,
    HEADER_SIZE,
    MAGIC,
    PARA,
    Book,
    EprError,
    TocEntry,
    build_epr,
    read_epr,
)

from make_tiny_epub import (  # noqa: E402
    TINY_AUTHOR,
    TINY_LANG,
    TINY_TITLE,
    make_tiny_epub,
    make_tiny_epub2,
)


def sample_book() -> Book:
    """A small book with a known byte layout."""
    text = bytearray()
    toc: list[TocEntry] = []

    toc.append(TocEntry(text_pos=len(text), title="Bölüm Bir"))
    text.extend("Birinci bölümün metni.".encode("utf-8"))
    text.append(PARA)
    text.extend("İkinci paragraf: çğıöşü.".encode("utf-8"))
    text.append(PARA)

    text.append(CHAPTER)
    toc.append(TocEntry(text_pos=len(text), title="Bölüm İki"))
    text.extend("İkinci bölüm burada başlar.".encode("utf-8"))
    text.append(PARA)

    return Book(
        title="Deneme Kitabı",
        author="Test Yazarı",
        lang="tr",
        text=bytes(text),
        toc=toc,
        flags=FLAG_HAS_TOC,
    )


class TestEprRoundtrip(unittest.TestCase):
    """build_epr <-> read_epr roundtrip and the raw byte layout."""

    def test_build_and_read_roundtrip(self) -> None:
        book = sample_book()
        raw = build_epr(book)
        again = read_epr(raw)

        self.assertEqual(again.title, book.title)
        self.assertEqual(again.author, book.author)
        self.assertEqual(again.lang, book.lang)
        self.assertEqual(again.text, book.text)
        self.assertEqual(len(again.toc), len(book.toc))
        for a, b in zip(again.toc, book.toc):
            self.assertEqual(a.text_pos, b.text_pos)
            self.assertEqual(a.title, b.title)
        self.assertEqual(again.version, 1)
        self.assertTrue(again.has_toc)

    def test_explicit_header_layout(self) -> None:
        """The header fields and padding must match what the contract says."""
        book = sample_book()
        raw = build_epr(book)

        magic, version, flags, text_offset, text_length, toc_offset, toc_count = struct.unpack(
            "<4sHHIIII", raw[:HEADER_SIZE]
        )
        self.assertEqual(magic, b"EPR1")
        self.assertEqual(MAGIC, b"EPR1")
        self.assertEqual(version, 1)
        self.assertEqual(flags & 0x0001, 0x0001)
        self.assertEqual(flags, 1)
        self.assertEqual(text_length, len(book.text))
        self.assertEqual(toc_count, len(book.toc))
        # The fixed part of the header is 24 bytes; the whole file is of course longer.
        self.assertEqual(HEADER_SIZE, 24)
        self.assertEqual(len(raw[:HEADER_SIZE]), 24)
        self.assertGreater(len(raw), HEADER_SIZE)

        # text_offset: header + string block, aligned to a multiple of 4, zero padding in between.
        strings_end = (
            HEADER_SIZE
            + 1 + len(book.title.encode("utf-8"))
            + 1 + len(book.author.encode("utf-8"))
            + 1 + len(book.lang.encode("utf-8"))
            + 1  # encoding byte
        )
        self.assertGreaterEqual(text_offset, strings_end)
        self.assertEqual((text_offset - strings_end) % 4, 0)
        self.assertEqual(raw[strings_end:text_offset], b"\x00" * (text_offset - strings_end))

        # The string block itself.
        pos = HEADER_SIZE
        for expected in (book.title, book.author, book.lang):
            n = raw[pos]
            pos += 1
            self.assertEqual(raw[pos : pos + n].decode("utf-8"), expected)
            self.assertEqual(n, len(expected.encode("utf-8")))
            pos += n
        self.assertEqual(raw[pos], 0, "the encoding byte must be 0 (UTF-8)")
        pos += 1

        # The text and table-of-contents blocks are exactly where expected.
        self.assertEqual(raw[text_offset : text_offset + text_length], book.text)
        self.assertEqual(toc_offset, text_offset + text_length)
        self.assertEqual(raw[text_offset + text_length], 0)  # high byte of the first TOC record

    def test_toc_block_encoding(self) -> None:
        """TOC record: uint32 text_pos + uint8 len + UTF-8 title."""
        book = sample_book()
        raw = build_epr(book)
        _m, _v, _f, text_offset, text_length, toc_offset, toc_count = struct.unpack(
            "<4sHHIIII", raw[:HEADER_SIZE]
        )
        pos = toc_offset
        self.assertEqual(toc_count, 2)
        for expected in book.toc:
            text_pos = struct.unpack("<I", raw[pos : pos + 4])[0]
            n = raw[pos + 4]
            title = raw[pos + 5 : pos + 5 + n].decode("utf-8")
            pos += 5 + n
            self.assertEqual(text_pos, expected.text_pos)
            self.assertEqual(title, expected.title)
            self.assertLessEqual(text_pos, text_length)
        self.assertEqual(pos, len(raw), "there must be no leftover data after the TOC block")

    def test_control_bytes_survive(self) -> None:
        """0x0A and 0x0B are preserved verbatim in the text block, \\r never appears."""
        book = sample_book()
        again = read_epr(build_epr(book))
        self.assertEqual(again.text.count(bytes([PARA])), 3)
        self.assertEqual(again.text.count(bytes([CHAPTER])), 1)
        self.assertNotIn(b"\r", again.text)
        # The TOC position points at the FIRST BYTE of the text; the chapter end
        # byte (0x0B) sits right before it.  (Both the converter and the sample
        # generator use this contract.)
        self.assertEqual(again.text[again.toc[1].text_pos - 1], CHAPTER)
        tail = again.text[again.toc[1].text_pos :].decode("utf-8")
        self.assertTrue(
            tail.startswith("İkinci bölüm"),
            f"the TOC position must point at the first letter of the second chapter, but it shows: {tail!r}",
        )

    def test_no_toc(self) -> None:
        book = sample_book()
        book.toc = []
        book.flags = 0
        raw = build_epr(book)
        _m, _v, flags, _to, _tl, toc_offset, toc_count = struct.unpack(
            "<4sHHIIII", raw[:HEADER_SIZE]
        )
        self.assertEqual(flags, 0)
        self.assertEqual(toc_offset, 0)
        self.assertEqual(toc_count, 0)
        again = read_epr(raw)
        self.assertFalse(again.has_toc)
        self.assertEqual(again.toc, [])
        self.assertEqual(again.text, book.text)

    def test_empty_book_is_valid(self) -> None:
        raw = build_epr(Book(title="", author="", lang="", text=b"", toc=[]))
        again = read_epr(raw)
        self.assertEqual(again.text, b"")
        self.assertEqual(again.title, "")

    def test_file_roundtrip(self) -> None:
        book = sample_book()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deneme.epr"
            path.write_bytes(build_epr(book))
            again = epub2epr.read_epr_file(path)
            self.assertEqual(again.text, book.text)
            self.assertEqual(again.source, str(path))


class TestEprRejects(unittest.TestCase):
    """Corrupt inputs must not be accepted silently."""

    def test_rejects_bad_magic(self) -> None:
        raw = bytearray(build_epr(sample_book()))
        raw[0:4] = b"XXXX"
        with self.assertRaises(EprError):
            read_epr(bytes(raw))

    def test_rejects_wrong_version(self) -> None:
        raw = bytearray(build_epr(sample_book()))
        struct.pack_into("<H", raw, 4, 2)
        with self.assertRaises(EprError):
            read_epr(bytes(raw))

    def test_rejects_truncated(self) -> None:
        raw = build_epr(sample_book())
        with self.assertRaises(EprError):
            read_epr(raw[:10])
        with self.assertRaises(EprError):
            read_epr(raw[:-5])

    def test_rejects_carriage_return(self) -> None:
        book = sample_book()
        book.text = b"satir sonu\rburada"
        with self.assertRaises(EprError):
            build_epr(book)

    def test_rejects_long_title(self) -> None:
        book = sample_book()
        book.title = "A" * 300
        with self.assertRaises(EprError):
            build_epr(book)

    def test_rejects_toc_out_of_range(self) -> None:
        book = sample_book()
        book.toc[0].text_pos = 10_000
        with self.assertRaises(EprError):
            build_epr(book)

    def test_rejects_toc_offset_without_flag(self) -> None:
        raw = bytearray(build_epr(sample_book()))
        struct.pack_into("<H", raw, 6, 0)  # turn has_toc off
        with self.assertRaises(EprError):
            read_epr(bytes(raw))

    def test_rejects_bad_encoding(self) -> None:
        book = sample_book()
        raw = bytearray(build_epr(book))
        # encoding byte: the last byte of the string block
        strings_end = (
            HEADER_SIZE
            + 1 + len(book.title.encode())
            + 1 + len(book.author.encode())
            + 1 + len(book.lang.encode())
        )
        self.assertEqual(raw[strings_end], 0)
        raw[strings_end] = 7
        with self.assertRaises(EprError):
            read_epr(bytes(raw))


class TestNormalisation(unittest.TestCase):
    """Text normalisation rules."""

    def test_zero_width_and_soft_hyphen_removed(self) -> None:
        out = epub2epr.normalize_text("ka­lem ve ke​li﻿")
        self.assertEqual(out, "kalem ve keli")

    def test_whitespace_collapsed(self) -> None:
        out = epub2epr.normalize_text("  bir \n\n  iki\tüç   ")
        self.assertEqual(out, "bir iki üç")

    def test_exotic_spaces_become_plain_space(self) -> None:
        out = epub2epr.normalize_text("bir iki üç")
        self.assertEqual(out, "bir iki üç")

    def test_nfc_folds_combining_sequence(self) -> None:
        out = epub2epr.normalize_text("göl")
        self.assertEqual(out, "göl")
        self.assertEqual(len(out), 3)

    def test_strip_diacritics_turkish(self) -> None:
        out = epub2epr.normalize_text("Çığlık İstanbul şöğüç", strip_diacritics=True)
        self.assertEqual(out, "Ciglik Istanbul soguc")

    def test_html_blocks_and_control_bytes(self) -> None:
        parser = epub2epr.HtmlTextExtractor()
        parser.feed("<p>Bir</p><p>İki</p><h1>Başlık</h1><p>Üç</p>")
        parser.close()
        texts = [(b.text, b.chapter) for b in parser.blocks]
        self.assertEqual(
            texts,
            [("Bir", False), ("İki", False), ("Başlık", True), ("Üç", False)],
        )

    def test_script_and_style_dropped(self) -> None:
        parser = epub2epr.HtmlTextExtractor()
        parser.feed(
            "<head><title>gizli</title><style>p{color:red}</style></head>"
            "<body><p>görünür</p><script>var x=1;</script></body>"
        )
        parser.close()
        joined = "".join(b.text for b in parser.blocks)
        self.assertIn("görünür", joined)
        self.assertNotIn("gizli", joined)
        self.assertNotIn("color", joined)
        self.assertNotIn("var x", joined)

    def test_img_becomes_resim(self) -> None:
        parser = epub2epr.HtmlTextExtractor()
        parser.feed('<p>Önce <img src="a.png" alt="a"/> sonra</p>')
        parser.close()
        self.assertIn("[resim]", parser.blocks[0].text)

    def test_entities_decoded(self) -> None:
        parser = epub2epr.HtmlTextExtractor()
        parser.feed("<p>a &amp; b &#351; &mdash; c</p>")
        parser.close()
        self.assertEqual(parser.blocks[0].text, "a & b ş — c")


class TestTextBuilder(unittest.TestCase):
    """The control-byte logic that joins blocks together.

    Regression: `add_block` used to trim the trailing paragraph end
    UNCONDITIONALLY; that deleted the previous block's 0x0A and lost every
    paragraph end in the text, running the blocks together (like `BirBir`).
    """

    def test_paragraph_separators_survive(self) -> None:
        b = epub2epr.TextBuilder()
        b.add_block(epub2epr.Block("Bir"))
        b.add_block(epub2epr.Block("İki"))
        self.assertEqual(b.finish(), "Bir\nİki".encode("utf-8"))

    def test_chapter_break_replaces_paragraph_break(self) -> None:
        b = epub2epr.TextBuilder()
        b.add_block(epub2epr.Block("Bir"))
        b.add_block(epub2epr.Block("Başlık", chapter=True))
        b.add_block(epub2epr.Block("İki"))
        self.assertEqual(b.finish(), "Bir\x0bBaşlık\nİki".encode("utf-8"))

    def test_leading_chapter_break_is_not_emitted(self) -> None:
        """Offset 0 is already the start of the first page; an extra 0x0B could open a blank page."""
        b = epub2epr.TextBuilder()
        pos = b.add_block(epub2epr.Block("Başlık", chapter=True))
        self.assertEqual(pos, 0)
        self.assertEqual(b.finish(), "Başlık".encode("utf-8"))

    def test_no_adjacent_control_bytes(self) -> None:
        b = epub2epr.TextBuilder()
        b.add_block(epub2epr.Block("A", chapter=True))
        b.add_block(epub2epr.Block("B"))
        b.add_block(epub2epr.Block("C", chapter=True))
        b.add_block(epub2epr.Block("D", chapter=True))
        b.add_block(epub2epr.Block(""))
        out = b.finish()
        self.assertEqual(out, b"A\nB\x0bC\x0bD")
        for i in range(1, len(out)):
            self.assertFalse(
                out[i] in (PARA, CHAPTER) and out[i - 1] in (PARA, CHAPTER),
                f"two control bytes are adjacent (offset {i})",
            )

    def test_empty_blocks_are_skipped(self) -> None:
        b = epub2epr.TextBuilder()
        self.assertEqual(b.add_block(epub2epr.Block("")), -1)
        self.assertEqual(b.add_block(epub2epr.Block("   ")), -1)
        self.assertEqual(b.finish(), b"")

    def test_positions_point_at_first_text_byte(self) -> None:
        b = epub2epr.TextBuilder()
        self.assertEqual(b.add_block(epub2epr.Block("Bir")), 0)
        # "Bir" + 0x0A = 4 bytes
        self.assertEqual(b.add_block(epub2epr.Block("İki")), 4)
        # "Bir"(3) + 0x0A(1) + "İki" = İ(2)+k+i = 4 bytes, +0x0A = 9 bytes.
        # When a chapter start arrives the trailing 0x0A is trimmed and replaced by 0x0B.
        self.assertEqual(b.add_block(epub2epr.Block("Üç", chapter=True)), 9)
        out = b.finish()
        self.assertEqual(out[0], ord("B"))
        self.assertEqual(out[3], PARA)
        self.assertEqual(out[8], CHAPTER)
        self.assertEqual(out[9:], "Üç".encode("utf-8"))

class TestEpubConversion(unittest.TestCase):
    """EPUB -> .epr end-to-end conversion."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_epub3_end_to_end(self) -> None:
        src = make_tiny_epub(self.tmp)
        self.assertTrue(src.exists())
        book, stats = epub2epr.convert_epub(src)

        self.assertEqual(book.title, TINY_TITLE)
        self.assertEqual(book.author, TINY_AUTHOR)
        self.assertEqual(book.lang, TINY_LANG)

        text = book.text.decode("utf-8")
        self.assertNotIn("\r", text)
        self.assertNotIn("­", text)
        self.assertNotIn("​", text)
        self.assertIn("göl", text)
        self.assertIn("kalem", text)
        self.assertIn("[resim]", text)
        self.assertNotIn("gorunmemeli", text)
        self.assertNotIn("gizli", text)

        self.assertGreaterEqual(text.count("\x0b"), 2, "chapter starts missing")
        self.assertGreaterEqual(text.count("\x0a"), 8, "paragraph ends missing")

        # Regression: the paragraphs must really be SEPARATE.  Just counting
        # bytes is not enough — if the separator is dropped while joining blocks
        # the count can still match; so we explicitly check the gap between
        # known neighbouring paragraphs.
        self.assertIn("Birinci Bölüm\x0aKıyıda küçük bir fener", text)
        self.assertIn("her akşam yanardı.\x0aYumuşak tire", text)
        self.assertIn("Yaz.\x0a[resim]\x0aSon paragraf", text)
        self.assertIn("burada biter.\x0bİkinci Bölüm", text)
        # <blockquote> and <li> must open their own paragraph.
        self.assertIn("ilk paragrafı.\x0aAlıntı bloğu ayrı paragraf olur.", text)
        self.assertIn("gelen paragraf.\x0aBirinci madde\x0aİkinci madde", text)

        # No two control bytes may be adjacent anywhere (blank page/paragraph).
        for i in range(1, len(book.text)):
            self.assertFalse(
                book.text[i] in (PARA, CHAPTER) and book.text[i - 1] in (PARA, CHAPTER),
                f"two control bytes are adjacent (offset {i})",
            )

        titles = [e.title for e in book.toc]
        self.assertEqual(len(titles), 3)
        self.assertEqual(titles[0], "Birinci Bölüm")
        self.assertEqual(titles[1], "İkinci Bölüm")
        self.assertEqual(titles[2], "Bir Sahne")

        # TOC positions must increase and the first must start at 0.
        self.assertEqual(book.toc[0].text_pos, 0)
        self.assertLess(book.toc[0].text_pos, book.toc[1].text_pos)
        self.assertLess(book.toc[1].text_pos, book.toc[2].text_pos)
        # "Bir Sahne" must really land on a chapter start (0x0B).
        # NOTE: text_pos is a BYTE offset; indexing into the decoded str would
        # drift because of multi-byte characters.  So the comparison is done on
        # the raw bytes.
        self.assertEqual(book.text[book.toc[2].text_pos - 1], CHAPTER)
        self.assertEqual(
            book.text[book.toc[2].text_pos : book.toc[2].text_pos + 9],
            "Bir Sahne".encode("utf-8"),
        )

        # Can the text really be written to the file and read back?
        raw = build_epr(book)
        again = read_epr(raw)
        self.assertEqual(again.text, book.text)
        self.assertEqual(len(again.toc), 3)
        self.assertGreater(stats.text_bytes, 0)

    def test_epub2_ncx_fallback(self) -> None:
        src = make_tiny_epub2(self.tmp)
        book, _stats = epub2epr.convert_epub(src)
        titles = [e.title for e in book.toc]
        self.assertEqual(titles, ["Birinci Bölüm", "İkinci Bölüm", "Bir Sahne"])
        self.assertEqual(book.title, TINY_TITLE)
        self.assertEqual(book.toc[0].text_pos, 0)

    def test_no_toc_flag(self) -> None:
        src = make_tiny_epub(self.tmp)
        book, _stats = epub2epr.convert_epub(src, want_toc=False)
        self.assertEqual(book.toc, [])
        self.assertEqual(book.flags, 0)
        raw = build_epr(book)
        self.assertEqual(read_epr(raw).toc, [])

    def test_metadata_overrides(self) -> None:
        src = make_tiny_epub(self.tmp)
        book, _stats = epub2epr.convert_epub(
            src, title="Özel", author="Biri", lang="en"
        )
        self.assertEqual(book.title, "Özel")
        self.assertEqual(book.author, "Biri")
        self.assertEqual(book.lang, "en")

    def test_strip_diacritics(self) -> None:
        src = make_tiny_epub(self.tmp)
        book, _stats = epub2epr.convert_epub(src, strip_diacritics=True)
        text = book.text.decode("utf-8")
        self.assertIn("gol", text)
        self.assertNotIn("göl", text)

    def test_convert_and_write_then_dump(self) -> None:
        src = make_tiny_epub(self.tmp)
        out = self.tmp / "cikti.epr"
        path, _stats = epub2epr.convert_and_write(src, out, verify=True)
        self.assertTrue(path.exists())
        again = epub2epr.read_epr_file(path)
        self.assertEqual(again.title, TINY_TITLE)

        # --dump works and prints the title.
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = epub2epr.main(["--dump", str(path)])
        self.assertEqual(rc, 0)
        printed = buf.getvalue()
        self.assertIn("EPR1", printed)
        self.assertIn(TINY_TITLE, printed)
        self.assertIn("text_offset", printed)

    def test_missing_epub_gives_turkish_error(self) -> None:
        with self.assertRaises(EprError) as ctx:
            epub2epr.convert_epub(self.tmp / "yok.epub")
        self.assertIn("not found", str(ctx.exception))

    def test_not_a_zip_gives_turkish_error(self) -> None:
        bogus = self.tmp / "bogus.epub"
        bogus.write_bytes(b"bu bir zip degil")
        with self.assertRaises(EprError) as ctx:
            epub2epr.convert_epub(bogus)
        self.assertIn("ZIP", str(ctx.exception).upper())

    def test_zip_without_container(self) -> None:
        bogus = self.tmp / "bos.epub"
        with zipfile.ZipFile(bogus, "w") as zf:
            zf.writestr("birsey.txt", "merhaba")
        with self.assertRaises(EprError) as ctx:
            epub2epr.convert_epub(bogus)
        self.assertIn("container.xml", str(ctx.exception))

    def test_tiny_epub_zip_layout(self) -> None:
        """Is the generated EPUB really valid (mimetype first + stored)?"""
        src = make_tiny_epub(self.tmp)
        with zipfile.ZipFile(src) as zf:
            infos = zf.infolist()
            self.assertEqual(infos[0].filename, "mimetype")
            self.assertEqual(infos[0].compress_type, zipfile.ZIP_STORED)
            self.assertEqual(zf.read("mimetype"), b"application/epub+zip")
            names = {i.filename for i in infos}
            self.assertIn("META-INF/container.xml", names)
            self.assertIn("OEBPS/content.opf", names)
            self.assertIn("OEBPS/nav.xhtml", names)
            self.assertIn("OEBPS/ch1.xhtml", names)
            self.assertIn("OEBPS/ch2.xhtml", names)


class TestSampleBooks(unittest.TestCase):
    """The files produced by make_sample_books.py must be valid."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        import make_sample_books

        self.mod = make_sample_books

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_samples_are_valid_and_readable(self) -> None:
        for name, book in (
            ("ornek-turkce.epr", self.mod.build_turkish_sample()),
            ("sample-english.epr", self.mod.build_english_sample()),
        ):
            with self.subTest(name=name):
                path = self.tmp / name
                path.write_bytes(build_epr(book))
                info = self.mod.verify_bytes(path, book)
                again = read_epr(path.read_bytes())
                self.assertEqual(again.title, book.title)
                self.assertEqual(again.text, book.text)
                # The chapter count is the TOC records, not the count of 0x0B
                # bytes: the first chapter starts at offset 0 and no 0x0B is
                # written there (an extra byte would open a blank page); every
                # later chapter leaves one 0x0B.
                self.assertGreaterEqual(info["toc"], 2, "there must be at least two chapters")
                self.assertEqual(
                    info["chapters"],
                    info["toc"] - 1,
                    "every chapter except the first must leave one 0x0B",
                )
                self.assertGreaterEqual(info["paragraphs"], info["toc"])

    def test_turkish_sample_has_all_special_letters(self) -> None:
        book = self.mod.build_turkish_sample()
        text = book.text.decode("utf-8")
        for ch in "çğıİöşüÇĞÖŞÜ":
            with self.subTest(ch=ch):
                self.assertIn(ch, text)

    def test_stress_sample_size_and_chapters(self) -> None:
        book = self.mod.build_stress_sample(chapters=6, target_bytes=24 * 1024, seed=99)
        self.assertGreaterEqual(len(book.text), 20 * 1024)
        self.assertEqual(len(book.toc), 6)
        path = self.tmp / "stress.epr"
        path.write_bytes(build_epr(book))
        again = read_epr(path.read_bytes())
        self.assertEqual(len(again.toc), 6)
        self.assertNotIn(b"\r", again.text)

    def test_stress_sample_is_deterministic(self) -> None:
        a = self.mod.build_stress_sample(chapters=3, target_bytes=8 * 1024, seed=5)
        b = self.mod.build_stress_sample(chapters=3, target_bytes=8 * 1024, seed=5)
        self.assertEqual(a.text, b.text)


class TestFontFormat(unittest.TestCase):
    """The pure-Python parts of fontgen.py (Pillow not required)."""

    def setUp(self) -> None:
        try:
            import fontgen
        except SystemExit:
            self.skipTest("Pillow is not installed; fontgen could not be imported.")
            raise
        self.fontgen = fontgen

    def test_bitstream_packing_is_not_row_padded(self) -> None:
        """9x2 glyph: ceil(18/8) = 3 bytes (it would be 4 with row padding).

        Bit N = y*width + x, byte N>>3, mask 0x80 >> (N&7).
        """
        rows = [[True] + [False] * 8, [False] * 8 + [True]]
        packed = self.fontgen.pack_bits(rows)
        self.assertEqual(len(packed), 3)
        self.assertEqual(packed[0], 0b10000000)  # bit 0 = (0,0)
        self.assertEqual(packed[1], 0b00000000)
        self.assertEqual(packed[2], 0b01000000)  # bit 17 = (8,1)
        self.assertEqual(self.fontgen.unpack_bits(packed, 9, 2), rows)

    def test_roundtrip_many_shapes(self) -> None:
        import random

        rng = random.Random(3)
        for w, h in ((1, 1), (8, 8), (9, 3), (13, 17), (17, 5)):
            rows = [[rng.random() < 0.4 for _ in range(w)] for _ in range(h)]
            packed = self.fontgen.pack_bits(rows)
            self.assertEqual(len(packed), (w * h + 7) // 8)
            self.assertEqual(self.fontgen.unpack_bits(packed, w, h), rows)

    def test_epf_roundtrip(self) -> None:
        g = self.fontgen.Glyph(
            codepoint=ord("A"),
            advance=9,
            left=0,
            width=7,
            height=9,
            top=3,
            bits=self.fontgen.pack_bits(
                [[(x + y) % 3 == 0 for x in range(7)] for y in range(9)]
            ),
        )
        space = self.fontgen.Glyph(ord(" "), 4, 0, 0, 0, 0, b"")
        font = self.fontgen.FontData(
            height=14, ascent=11, descent=3, line_spacing=2, glyphs=[space, g]
        )
        raw = self.fontgen.build_epf(font)
        self.assertEqual(raw[:4], b"EPF1")
        self.assertEqual(raw[4], 1)
        again = self.fontgen.read_epf(raw)
        self.assertEqual(again.height, 14)
        self.assertEqual(again.ascent, 11)
        self.assertEqual(again.descent, 3)
        self.assertEqual(again.line_spacing, 2)
        self.assertEqual(len(again.glyphs), 2)
        self.assertEqual(again.glyphs[1].bits, g.bits)
        self.assertEqual(again.glyphs[0].bits, b"")

        ok, message = self.fontgen.self_test(font, raw)
        self.assertTrue(ok, message)

    def test_epf_rejects_bad_size(self) -> None:
        g = self.fontgen.Glyph(ord("A"), 9, 0, 7, 9, 3, b"\x00\x00\x00")
        font = self.fontgen.FontData(14, 11, 3, 2, [g])
        with self.assertRaises(self.fontgen.EpfError):
            self.fontgen.build_epf(font)

    def test_range_presets(self) -> None:
        cps = self.fontgen.expand_ranges(["turkish"])
        for ch in "ĞğİışŞ":
            self.assertIn(ord(ch), cps)
        digits = self.fontgen.expand_ranges(["digits"])
        self.assertEqual(digits, list(range(0x30, 0x3A)))
        with self.assertRaises(self.fontgen.EpfError):
            self.fontgen.expand_ranges(["boyle-bir-aralik-yok"])


class TestSendHelpers(unittest.TestCase):
    """send.py's network-free helpers."""

    def setUp(self) -> None:
        try:
            import send
        except SystemExit:
            self.skipTest("send.py could not be imported.")
            raise
        self.send = send

    def test_human_size(self) -> None:
        self.assertEqual(self.send.human_size(512), "512 B")
        self.assertEqual(self.send.human_size(1024), "1.00 KiB")
        self.assertEqual(self.send.human_size(1536), "1.50 KiB")

    def test_human_uptime(self) -> None:
        self.assertEqual(self.send.human_uptime(65), "1m 5s")
        self.assertEqual(self.send.human_uptime(3661), "1h 1m 1s")

    def test_ip_literal(self) -> None:
        self.assertTrue(self.send.is_ip_literal("192.168.1.42"))
        self.assertFalse(self.send.is_ip_literal("pocketreader.local"))

    def test_device_survives_ip_and_netloc(self) -> None:
        dev = self.send.Device(host="192.168.1.42", port=80)
        self.assertEqual(dev.base_url(), "http://192.168.1.42")
        dev = self.send.Device(host="192.168.1.42", port=8080)
        self.assertEqual(dev.base_url(), "http://192.168.1.42:8080")

    def test_mdns_failure_message_mentions_ip(self) -> None:
        err = self.send.DeviceError("x")
        self.assertIsInstance(err, Exception)


if __name__ == "__main__":
    unittest.main(verbosity=2)
