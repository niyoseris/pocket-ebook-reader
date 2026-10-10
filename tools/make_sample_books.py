#!/usr/bin/env python3
"""Produce sample `.epr` books (into the examples/ folder).

It produces ready-made files that a user opening the device for the first time
can upload without converting anything.  **It uses no external library** and
does not need an EPUB: the container is built right here, by hand.

    python3 make_sample_books.py                 # produce into examples/
    python3 make_sample_books.py --out-dir /tmp  # into another folder

What it produces:
    ornek-turkce.epr    3 chapters of original Turkish text (ç ğ ı İ ö ş ü)
    sample-english.epr  a few paragraphs of original English text
    stress-test.epr     ~200 KB, 40 chapters -- exercises pagination and the page cache

Every file is read back with `epub2epr.read_epr()` and verified before it is
written; the header fields and table-of-contents records are also checked at the
raw byte level.
"""

from __future__ import annotations

import argparse
import random
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import epub2epr
    from epub2epr import CHAPTER, PARA, Book, TocEntry, build_epr, read_epr
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: epub2epr.py not found. It must be in the same folder as make_sample_books.py.\n"
    )
    raise SystemExit(4)

__all__ = [
    "BookBuilder",
    "build_turkish_sample",
    "build_english_sample",
    "build_stress_sample",
    "verify_bytes",
    "main",
]

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "examples"


class SampleError(Exception):
    """Error raised while producing a sample book."""


# --- builder ----------------------------------------------------------------


@dataclass
class BookBuilder:
    """Grows the text block and the table of contents together, by hand."""

    buf: bytearray = field(default_factory=bytearray)
    toc: list[TocEntry] = field(default_factory=list)

    def chapter(self, title: str) -> int:
        """Open a new chapter (0x0B) and add its table-of-contents record."""
        title = title.strip()
        if not title:
            raise SampleError("A chapter title cannot be empty.")
        while self.buf and self.buf[-1] in (PARA, CHAPTER):
            self.buf.pop()
        if self.buf:
            self.buf.append(CHAPTER)
        pos = len(self.buf)
        self.toc.append(TocEntry(text_pos=pos, title=title))
        self.buf.extend(title.encode("utf-8"))
        self.buf.append(PARA)
        return pos

    def paragraph(self, text: str) -> None:
        text = " ".join(text.split())
        if not text:
            return
        if b"\r" in text.encode("utf-8"):
            raise SampleError("Paragraph contains the forbidden \\r character.")
        self.buf.extend(text.encode("utf-8"))
        self.buf.append(PARA)

    def paragraphs(self, items) -> None:
        for item in items:
            self.paragraph(item)

    def text(self) -> bytes:
        out = bytearray(self.buf)
        while out and out[-1] in (PARA, CHAPTER):
            out.pop()
        return bytes(out)

    def stats(self) -> dict[str, int]:
        data = self.text()
        return {
            "chapters": data.count(bytes([CHAPTER])),
            "paragraphs": data.count(bytes([PARA])) + data.count(bytes([CHAPTER])),
            "text_bytes": len(data),
            "toc": len(self.toc),
        }


# --- Turkish sample ---------------------------------------------------------
# The prose below stays Turkish on purpose: it is a deliberate Turkish-language
# test fixture that proves the pipeline (and the fonts) cover Turkish glyphs
# (ç ğ ı İ ö ş ü).  Do not translate it.

TR_TITLE = "Deniz Feneri Notları"
TR_AUTHOR = "Pocket Reader Örnek Metni"
TR_LANG = "tr"

TR_CHAPTERS: list[tuple[str, list[str]]] = [
    (
        "Birinci Bölüm — Fenerin Işığı",
        [
            "Kıyıdaki küçük fener, yıllardır aynı saatte yanardı. İbrahim her akşam "
            "üşenmeden merdivenleri çıkar, camı siler, fitili düzeltirdi. Şöyle "
            "derdi: “Bu ışık bana değil, yolu şaşıranlara yanıyor.”",

            "O akşam gökyüzü kurşun gibiydi. Çılgın rüzgâr, çatıdaki örtüyü "
            "savurdu; dalgalar taşları ıslattı. İbrahim yine de çıktı. Elinde "
            "yalnızca eski bir çakmak ve bir tutam fitil vardı; ama içi rahattı, "
            "çünkü elli yıldır bu işi yapıyordu.",

            "Işık yandığında uzaktaki bir gemi dümen kırdı. İbrahim bunu görmedi, "
            "görmesine de gerek yoktu. Aşağı inip çayını koydu, ıslak paltosunu "
            "sobanın yanına astı ve defterine bir satır yazdı: “Bu gece de "
            "görevimizi yaptık.”",
        ],
    ),
    (
        "İkinci Bölüm — Şehrin Sesi",
        [
            "Şehre indiğinde ilk dikkatini çeken şey gürültüydü. Otobüsler, "
            "tezgâhlar, ışıklı tabelalar… Hepsi aynı anda konuşuyordu. İbrahim "
            "sağır olduğunu düşündü bir an; sonra anladı ki duymuyor değildi, "
            "yalnızca uzun zamandır bu kadar çok sesi bir arada işitmemişti.",

            "Bir kitapçıya girdi. Rafların arasında dolaşırken parmağını "
            "sırtlarda gezdirdi; çoğunun adını okuyamadı, ama dokunmak yetti. "
            "“Şu üçünü alayım,” dedi tezgâhtara. Tezgâhtar gülümsedi: “Bu "
            "üçüncüsü ağır bir kitap, dayı.” İbrahim omuz silkti: “Ağır olsun; "
            "ışığa ihtiyacı olan bir şey taşımıyorum ki.”",

            "Vitrindeki tabelada “ÖĞRENMEK İÇİN OKU” yazıyordu. İbrahim bunu "
            "görünce gülümsedi; elli yıl boyunca fenerin merdivenlerini çıkmış "
            "bir adam için tuhaf bir cümleydi, ama yanlış da değildi.",

            "Akşamüstü bir çay bahçesinde oturdu. Yandaki masada iki genç, "
            "üniversiteden ve sınavlardan konuşuyordu. İbrahim dinledi, dinledi, "
            "sonunda dayanamayıp sordu: “Peki ışık ne zaman yanıyor?” Gençler "
            "önce anlamadı; sonra biri, “Evin lambası mı?” dedi. İbrahim "
            "başını salladı: “Öyle bir şey işte.”",
        ],
    ),
    (
        "Üçüncü Bölüm — Kışın İlk Günü",
        [
            "Kar, gece yarısı başladı. Sabah kalktığında dünya bembeyazdı; "
            "fenerin demir korkulukları buz tutmuş, merdivenler kayganlaşmıştı. "
            "İbrahim tuz döktü, küredi, sonra her zamanki gibi yukarı çıktı.",

            "O gün ışığı yakan o değildi. Elektrik kesilmişti; jeneratör "
            "çalışmıyordu. Aşağıdaki odada, sobanın yanında üşümüş bir kedi "
            "buldu. Onu kucağına alıp içeri götürdü, süt ısıttı. “Bugün "
            "dinlenme günü,” dedi kediye, “ışığı başkası yaksın.”",

            "Ama gece, pencereye vuran bir aydınlıkla uyandı. Yukarıdan biri "
            "el fenerini yakıp söndürüyordu; hem de tam İbrahim'in ritminde. "
            "Kimdi? Bilmiyordu. Yine de gülümsedi, yorganını düzeltti ve "
            "“demek ki sıra bana gelmiş,” diye mırıldandı. Kedi kıpırdandı, "
            "sonra yeniden uyudu.",
        ],
    ),
]


def build_turkish_sample() -> Book:
    """Produce the three-chapter original Turkish sample book."""
    b = BookBuilder()
    for title, paragraphs in TR_CHAPTERS:
        b.chapter(title)
        b.paragraphs(paragraphs)
    text = b.text()
    missing = [ch for ch in "çğıİöşüÇĞÖŞÜ" if ch not in text.decode("utf-8")]
    if missing:
        raise SampleError(
            "The Turkish sample text is missing these letters: " + " ".join(missing)
        )
    return Book(
        title=TR_TITLE,
        author=TR_AUTHOR,
        lang=TR_LANG,
        text=text,
        toc=b.toc,
        flags=epub2epr.FLAG_HAS_TOC,
    )


# --- English sample ---------------------------------------------------------

EN_TITLE = "The Lamp Keeper's Morning"
EN_AUTHOR = "Pocket Reader Sample Text"
EN_LANG = "en"

EN_CHAPTERS: list[tuple[str, list[str]]] = [
    (
        "Chapter One — Before Sunrise",
        [
            "The harbour was quiet at four in the morning. Marta walked the "
            "pier with a thermos in one hand and a notebook in the other, "
            "counting the boats that had come in overnight. There were "
            "eleven, one more than yesterday.",

            "She did not write this down to prove anything. She wrote it "
            "down because the ink looked honest on paper, and because the "
            "first cup of coffee tasted better when there was a number "
            "beside it.",

            "By five the sky had turned the colour of wet slate. A gull "
            "landed on the rail and studied her without apology. Marta "
            "raised her thermos in a small salute, and the bird, apparently "
            "satisfied, went back to sleep.",
        ],
    ),
    (
        "Chapter Two — The Small Ledger",
        [
            "The ledger lived in a drawer that stuck in humid weather. Marta "
            "had owned it for nine years, and in that time it had recorded "
            "every arrival, every departure, and three weddings that had "
            "taken place on the pier without permission.",

            "She did not think of it as a diary. A diary implies an "
            "audience, even if the audience is only your future self. The "
            "ledger asked for nothing. It simply waited, page open, for "
            "whatever the morning decided to leave behind.",

            "When the sun finally cleared the breakwater, she closed the "
            "drawer, locked the office, and walked home the long way. It "
            "was the only way she knew to make a short walk last.",
        ],
    ),
]


def build_english_sample() -> Book:
    """Produce the two-chapter original English sample book."""
    b = BookBuilder()
    for title, paragraphs in EN_CHAPTERS:
        b.chapter(title)
        b.paragraphs(paragraphs)
    return Book(
        title=EN_TITLE,
        author=EN_AUTHOR,
        lang=EN_LANG,
        text=b.text(),
        toc=b.toc,
        flags=epub2epr.FLAG_HAS_TOC,
    )


# --- stress test ------------------------------------------------------------

TR_SYLLABLES = [
    "ka", "ra", "le", "mi", "şö", "ğü", "çı", "ta", "ne", "si", "ba", "lu",
    "öz", "yü", "dı", "gi", "har", "yol", "gün", "ışık", "den", "giz", "söz",
    "kır", "toz", "ben", "sen", "bir", "iki", "üç", "yaz", "kış", "süz",
]
TR_WORDS = [
    "ışık", "defter", "kıyı", "gemici", "sabah", "çay", "sessizlik", "rüzgâr",
    "gölge", "yolculuk", "taş", "çığlık", "öykü", "şiir", "gündüz", "gece",
    "yağmur", "bulut", "ıslak", "sıcak", "üşümek", "gülümsemek", "anlatmak",
    "dinlemek", "bakmak", "yürümek", "düşünmek", "unutmak", "hatırlamak",
]


def _tr_sentence(rng: random.Random, words: int) -> str:
    parts: list[str] = []
    for i in range(words):
        if i and rng.random() < 0.12:
            parts.append(rng.choice(TR_WORDS))
            continue
        length = rng.randint(2, 4)
        parts.append("".join(rng.choice(TR_SYLLABLES) for _ in range(length)))
    text = " ".join(parts)
    return text.capitalize() + rng.choice([".", ".", ".", "…", "?", "!"])


def _tr_paragraph(rng: random.Random) -> str:
    sentences = [_tr_sentence(rng, rng.randint(7, 16)) for _ in range(rng.randint(3, 6))]
    return " ".join(sentences)


def build_stress_sample(
    chapters: int = 40,
    target_bytes: int = 200 * 1024,
    seed: int = 1337,
) -> Book:
    """~200 KB of generated multi-chapter Turkish text (pagination test).

    With the same `seed` it produces byte-for-byte the same file on every run.
    """
    rng = random.Random(seed)
    b = BookBuilder()
    per_chapter = max(1, target_bytes // chapters)

    for i in range(1, chapters + 1):
        title = f"Bölüm {i} — {_tr_sentence(rng, 3).rstrip('.,;:!?…')}"
        b.chapter(title)
        start = len(b.buf)
        while len(b.buf) - start < per_chapter:
            b.paragraph(_tr_paragraph(rng))

    text = b.text()
    if len(text) < target_bytes * 0.85:
        raise SampleError(
            f"Stress test is smaller than expected: {len(text)} bytes "
            f"(goal ~{target_bytes})."
        )
    return Book(
        title="Stres Testi — 40 Bölüm",
        author=f"Üretilmiş metin (seed={seed})",
        lang="tr",
        text=text,
        toc=b.toc,
        flags=epub2epr.FLAG_HAS_TOC,
    )


# --- verification -----------------------------------------------------------


def verify_bytes(path: Path, book: Book) -> dict[str, object]:
    """Verify the written file both at a high level and at the raw byte level."""
    raw = path.read_bytes()
    again = read_epr(raw)  # high-level parser

    if again.text != book.text:
        raise SampleError(f"{path.name}: the text block differs when read back.")
    if len(again.toc) != len(book.toc):
        raise SampleError(
            f"{path.name}: table-of-contents row count differs "
            f"({len(again.toc)} != {len(book.toc)})."
        )
    if again.title != book.title or again.author != book.author:
        raise SampleError(f"{path.name}: title/author differ when read back.")
    if again.lang != book.lang:
        raise SampleError(f"{path.name}: the language field differs.")

    # --- raw byte checks (format contract) ---
    magic, version, flags, text_offset, text_length, toc_offset, toc_count = struct.unpack(
        "<4sHHIIII", raw[:24]
    )
    if magic != b"EPR1":
        raise SampleError(f"{path.name}: magic number is not 'EPR1': {magic!r}")
    if version != 1:
        raise SampleError(f"{path.name}: version is not 1: {version}")
    if flags & 0x0001 != 0x0001:
        raise SampleError(f"{path.name}: has_toc flag is not set (flags=0x{flags:04X})")
    if text_length != len(book.text):
        raise SampleError(f"{path.name}: text_length in the header is wrong.")
    if raw[text_offset : text_offset + text_length] != book.text:
        raise SampleError(f"{path.name}: text_offset points at the wrong place.")
    if toc_offset != text_offset + text_length:
        raise SampleError(f"{path.name}: toc_offset is not immediately after the text.")
    if toc_count != len(book.toc):
        raise SampleError(f"{path.name}: toc_count in the header is wrong.")
    if toc_offset + sum(5 + len(e.title.encode()) for e in book.toc) > len(raw):
        raise SampleError(f"{path.name}: the table-of-contents block runs past the end of the file.")

    # Decode the table-of-contents records one by one, by hand.
    pos = toc_offset
    for i, expected in enumerate(book.toc):
        text_pos = struct.unpack("<I", raw[pos : pos + 4])[0]
        n = raw[pos + 4]
        title = raw[pos + 5 : pos + 5 + n].decode("utf-8")
        pos += 5 + n
        if text_pos != expected.text_pos or title != expected.title:
            raise SampleError(f"{path.name}: table-of-contents record {i} is corrupt.")
        if text_pos > text_length:
            raise SampleError(f"{path.name}: record {i} points outside the text.")
        # Is the record really a chapter start? (must begin at 0 or with 0x0B)
        if text_pos != 0 and raw[text_offset + text_pos - 1] != CHAPTER:
            raise SampleError(
                f"{path.name}: record {i} (offset {text_pos}) does not line up "
                f"with a 0x0B chapter start."
            )
    if b"\r" in raw[text_offset : text_offset + text_length]:
        raise SampleError(f"{path.name}: forbidden \\r in the text block.")

    return {
        "file_bytes": len(raw),
        "text_bytes": text_length,
        "chapters": book.text.count(bytes([CHAPTER])),
        "paragraphs": book.text.count(bytes([PARA])) + book.text.count(bytes([CHAPTER])),
        "toc": len(again.toc),
        "text_offset": text_offset,
        "header_bytes": text_offset,
    }


# --- CLI --------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="make_sample_books.py",
        description=(
            "Produce ready-to-upload sample .epr files in the examples/ folder. "
            "No EPUB is needed; the container is built directly and is read back "
            "with epub2epr.read_epr() for verification before it is written."
        ),
        epilog=(
            "Examples:\n"
            "  make_sample_books.py\n"
            "  make_sample_books.py --out-dir /tmp/ornek --seed 7\n"
            "  make_sample_books.py --stress-kb 64 --stress-chapters 10\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT),
        help=f"output folder (default: {DEFAULT_OUT})",
    )
    p.add_argument("--stress-kb", type=int, default=200, help="stress test size, KiB (default: 200)")
    p.add_argument("--stress-chapters", type=int, default=40, help="stress test chapter count (default: 40)")
    p.add_argument("--seed", type=int, default=1337, help="stress test randomness seed (default: 1337)")
    p.add_argument("-v", "--verbose", action="store_true", help="detailed statistics for each file")
    return p


def _print_stats(name: str, info: dict[str, object], verbose: bool) -> None:
    # NOTE: `chapters` is the count of 0x0B bytes and is NOT EQUAL to the
    # number of chapters — the first chapter starts at offset 0 and no 0x0B is
    # written there.  The meaningful number for the user is the TOC records;
    # both are shown separately.
    print(
        f"  {name:<22} {info['file_bytes']:>8} bytes  "
        f"{info['toc']:>3} chapters  {info['paragraphs']:>5} paragraphs  "
        f"{info['chapters']:>3} chapter ends (0x0B)"
    )
    if verbose:
        print(
            f"      text {info['text_bytes']} bytes, header {info['header_bytes']} bytes, "
            f"text_offset {info['text_offset']}"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    out_dir = Path(args.out_dir).expanduser()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR: could not create folder: {out_dir} ({exc})", file=sys.stderr)
        return 3

    try:
        jobs: list[tuple[str, Book]] = [
            ("ornek-turkce.epr", build_turkish_sample()),
            ("sample-english.epr", build_english_sample()),
            (
                "stress-test.epr",
                build_stress_sample(
                    chapters=args.stress_chapters,
                    target_bytes=args.stress_kb * 1024,
                    seed=args.seed,
                ),
            ),
        ]
    except SampleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    results: list[tuple[Path, dict[str, object]]] = []
    for name, book in jobs:
        try:
            raw = build_epr(book)
        except epub2epr.EprError as exc:
            print(f"ERROR ({name}): could not build the container: {exc}", file=sys.stderr)
            return 2
        path = out_dir / name
        try:
            path.write_bytes(raw)
        except OSError as exc:
            print(f"ERROR: could not write: {path} ({exc})", file=sys.stderr)
            return 3
        try:
            results.append((path, verify_bytes(path, book)))
        except SampleError as exc:
            print(f"ERROR: verification failed: {exc}", file=sys.stderr)
            try:
                path.unlink()
            except OSError:
                pass
            return 4

    print(f"Sample books written: {out_dir}")
    for path, info in results:
        _print_stats(path.name, info, args.verbose)
    print("Verification: OK — every file checked with read_epr() and at the raw byte level.")
    print()
    print("Now upload to the device:")
    print(f"    python3 send.py {results[0][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
