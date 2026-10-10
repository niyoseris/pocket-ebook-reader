# examples

Sample books go here. **No `.epr` files are committed to the repository** — they are generated.

```bash
cd ../tools
python3 make_sample_books.py            # writes into this folder
# or
python3 make_sample_books.py --out-dir ../firmware/data/books
```

Generated files:

| File | Size | What it exercises |
|---|---|---|
| `ornek-turkce.epr` | ~4 KB | **Turkish letters** (ç ğ ı İ ö ş ü), 3 chapters, paragraph indents |
| `sample-english.epr` | ~3 KB | Latin-1 coverage, plain text |
| `stress-test.epr` | ~200 KB | 40 chapters, ~3,000 paragraphs — pagination and the page-index cache |

## Why is no pre-built file committed?

`.gitignore` excludes `firmware/data/books/*.epr` and `examples/*.epr`. Reason:
`.epr` is a **generated** format and the generator script lives in the repository.
Any format change requires regenerating all the sample files; keeping binaries in
the repository would break that synchronisation.

We also do not want to fill the place where users put their own books with sample
files.

## Your own books

```bash
cd ../tools
python3 epub2epr.py ~/kitap.epub -o /tmp/kitap.epr
python3 send.py /tmp/kitap.epr

# or an entire folder
python3 send.py --dir ~/kitaplar/
```

## Licence of the sample texts

The Turkish and English texts inside `make_sample_books.py` were written
originally for this project and are covered by the repository's licence (MIT).
They contain no public-domain or copyrighted text.

The content of `stress-test.epr` is generated text (meaningless but
grammatically coherent) and is not something to read — it exists only to measure
pagination performance.
