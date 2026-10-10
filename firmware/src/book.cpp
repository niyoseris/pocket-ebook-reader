/*
 * book.cpp -- .epr v1 parser, pagination and page-index cache.
 */

#include "book.h"
#include "font.h"
#include <LittleFS.h>
#include <string.h>

#define IDX_MAGIC     "PIDX"
#define IDX_VERSION   1
#define IDX_HEADER    36
#define IDX_MAX_PAGES 40000

/* --------------------------------------------------------------------------
 * small little-endian helpers (the cache file format is explicit, so it does
 * not depend on struct layout)
 * ------------------------------------------------------------------------ */
static inline void putU16(uint8_t* b, uint16_t v) { b[0] = v & 0xFF; b[1] = (v >> 8) & 0xFF; }
static inline void putU32(uint8_t* b, uint32_t v) {
    b[0] = v & 0xFF; b[1] = (v >> 8) & 0xFF; b[2] = (v >> 16) & 0xFF; b[3] = (v >> 24) & 0xFF;
}
static inline uint16_t getU16(const uint8_t* b) { return (uint16_t)(b[0] | ((uint16_t)b[1] << 8)); }
static inline uint32_t getU32(const uint8_t* b) {
    return (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
           ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
}

static uint32_t decodeSeq(const uint8_t* s, int n) {
    if (n <= 1) return s[0];
    uint32_t cp = (uint32_t)(s[0] & (0xFF >> (n + 1)));
    for (int i = 1; i < n; i++) cp = (cp << 6) | (uint32_t)(s[i] & 0x3F);
    return cp;
}

static bool readStr(File& f, char* out, size_t out_size) {
    uint8_t len = 0;
    if (f.read(&len, 1) != 1) return false;
    if (out_size == 0) return false;
    size_t keep = len;
    if (keep > out_size - 1) keep = out_size - 1;

    char tmp[256];
    if (len) {
        const size_t got = f.read((uint8_t*)tmp, len);
        if (got != len) return false;
    }
    memcpy(out, tmp, keep);
    out[keep] = 0;
    return true;
}

/* ==========================================================================
 *  TextReader -- streaming, word-wrapping reader over the text block.
 *
 *  Deliberately the ONLY place that decides where a line ends, so pagination
 *  and rendering can never disagree: both simply call readLine() with the
 *  same inputs.
 * ========================================================================== */
namespace {

class TextReader {
public:
    void begin(File* f, uint32_t start, uint32_t end, int scale) {
        _f = f;
        _pos = start;
        _end = end;
        _rlen = 0;
        _ridx = 0;
        _scale = scale;
        _word_ready = false;
        _delim = 0;
        _wlen = 0;
        _wwidth = 0;
        _word_start = start;
        _last_break = 0;
        _para_start = false;
        if (_f) _f->seek(start);
    }

    /* True when the line that is about to be produced starts a paragraph.
     * Must be read BEFORE readLine(): readLine() updates it. */
    bool atParagraphStart() const { return _para_start; }

    /* The break that terminated the line produced by the last readLine():
     * 0 = wrapped/full, EPR_CTRL_PARAGRAPH, EPR_CTRL_CHAPTER. */
    uint8_t lastBreak() const { return _last_break; }

    /* File offset where the next line will start. */
    uint32_t nextLineOffset() const {
        return _word_ready ? _word_start : streamPos();
    }

    /* Produce one wrapped line. Returns 1 if a line was produced, 0 at the
     * end of the text block. */
    int readLine(int max_width, char* out, int out_size) {
        if (out_size < 2) { if (out_size) out[0] = 0; return 0; }
        out[0] = 0;
        int out_len = 0;
        int out_w = 0;
        bool first_word = true;
        _last_break = 0;

        for (;;) {
            if (!_word_ready) {
                if (!readWord()) return out_len > 0 ? 1 : 0;
                _word_ready = true;
            }

            /* The pending word does not fit and the line already has content:
             * end the line; the word stays pending for the next call. */
            if (out_len > 0 && out_w + _wwidth > max_width) return 1;

            for (int i = 0; i < _wlen && out_len < out_size - 1; i++)
                out[out_len++] = _word[i];
            out[out_len] = 0;
            out_w += _wwidth;
            first_word = false;
            _word_ready = false;

            if (_delim == ' ') {
                const int sp = fontGlyphAdvance(' ', _scale);
                if (out_len > 0 && out_w + sp <= max_width) {
                    if (out_len < out_size - 1) {
                        out[out_len++] = ' ';
                        out[out_len] = 0;
                    }
                    out_w += sp;
                }
                continue;
            }

            if (_delim == EPR_CTRL_PARAGRAPH || _delim == EPR_CTRL_CHAPTER) {
                _last_break = _delim;
                _para_start = (_delim == EPR_CTRL_PARAGRAPH);
                return 1;
            }

            if (_delim == 0) return out_len > 0 ? 1 : 0;   /* end of text */
        }
    }

private:
    uint32_t streamPos() const { return _pos - (uint32_t)(_rlen - _ridx); }

    int rawByte() {
        if (_ridx >= _rlen) {
            if (_pos >= _end) return -1;
            uint32_t want = _end - _pos;
            if (want > sizeof(_rbuf)) want = sizeof(_rbuf);
            if (!_f || !_f->seek(_pos)) return -1;
            const int n = (int)_f->read(_rbuf, want);
            if (n <= 0) return -1;
            _rlen = n;
            _ridx = 0;
            _pos += (uint32_t)n;
        }
        return _rbuf[_ridx++];
    }

    /* Next byte of text: '\r' is stripped, '\n' / 0x0B are passed through as
     * the paragraph / chapter controls. */
    int nextTextByte() {
        for (;;) {
            const int c = rawByte();
            if (c < 0) return -1;
            if (c == '\r') continue;
            return c;
        }
    }

    /* Read one word (plus the delimiter that ended it) into _word. */
    bool readWord() {
        _wlen = 0;
        _wwidth = 0;
        _word[0] = 0;
        _word_start = streamPos();

        for (;;) {
            const int c = nextTextByte();
            if (c < 0)          { _delim = 0; return _wlen > 0; }
            if (c == '\n')      { _delim = EPR_CTRL_PARAGRAPH; return true; }
            if (c == 0x0B)      { _delim = EPR_CTRL_CHAPTER;   return true; }
            if (c == ' ' || c == '\t') { _delim = ' '; return true; }

            uint8_t seq[4];
            int n = utf8SeqLen((uint8_t)c);
            seq[0] = (uint8_t)c;
            for (int i = 1; i < n; i++) {
                const int b = nextTextByte();
                if (b < 0) { n = i; break; }
                seq[i] = (uint8_t)b;
            }

            _wwidth += fontGlyphAdvance(decodeSeq(seq, n), _scale);
            if (_wlen + n < (int)sizeof(_word) - 1) {
                memcpy(_word + _wlen, seq, n);
                _wlen += n;
                _word[_wlen] = 0;
            }
        }
    }

    File*    _f = nullptr;
    uint32_t _pos = 0;          /* file offset just past the buffered chunk */
    uint32_t _end = 0;
    uint8_t  _rbuf[256];
    int      _rlen = 0;
    int      _ridx = 0;
    int      _scale = 1;

    char     _word[96];
    int      _wlen = 0;
    int      _wwidth = 0;
    uint32_t _word_start = 0;
    bool     _word_ready = false;
    uint8_t  _delim = 0;        /* delimiter that followed the last word */

    uint8_t  _last_break = 0;
    bool     _para_start = false;
};

}  /* namespace */

/* ==========================================================================
 *  Header parsing
 * ========================================================================== */

bool bookReadMeta(const char* path, BookMeta* out, uint32_t* file_size) {
    if (!path || !out) return false;
    File f = LittleFS.open(path, "r");
    if (!f) return false;

    const uint32_t sz = f.size();
    if (file_size) *file_size = sz;

    uint8_t h[24];
    if (f.read(h, 24) != 24) { f.close(); return false; }
    if (memcmp(h, EPR_MAGIC, 4) != 0) { f.close(); return false; }
    if (getU16(h + 4) != EPR_VERSION) { f.close(); return false; }

    memset(out, 0, sizeof(*out));
    out->flags       = getU16(h + 6);
    out->text_offset = getU32(h + 8);
    out->text_length = getU32(h + 12);
    out->toc_offset  = getU32(h + 16);
    out->toc_count   = getU32(h + 20);

    if (out->text_offset > sz || out->text_offset + out->text_length > sz) {
        f.close();
        return false;
    }

    if (!readStr(f, out->title,  sizeof(out->title)) ||
        !readStr(f, out->author, sizeof(out->author)) ||
        !readStr(f, out->lang,   sizeof(out->lang))) {
        f.close();
        return false;
    }

    uint8_t enc = 0;
    if (f.read(&enc, 1) == 1) out->encoding = enc;

    f.close();
    return true;
}

/* ==========================================================================
 *  Book
 * ========================================================================== */

Book::Book() {}
Book::~Book() { close(); }

bool Book::open(const char* path) {
    close();
    if (!path) return false;

    _file = LittleFS.open(path, "r");
    if (!_file) {
        Serial.printf("[book] cannot open %s\n", path);
        return false;
    }
    _size = _file.size();

    uint8_t h[24];
    if (_file.read(h, 24) != 24 || memcmp(h, EPR_MAGIC, 4) != 0 ||
        getU16(h + 4) != EPR_VERSION) {
        Serial.printf("[book] %s: not an EPR1 v1 file\n", path);
        close();
        return false;
    }

    memset(&_meta, 0, sizeof(_meta));
    _meta.flags       = getU16(h + 6);
    _meta.text_offset = getU32(h + 8);
    _meta.text_length = getU32(h + 12);
    _meta.toc_offset  = getU32(h + 16);
    _meta.toc_count   = getU32(h + 20);

    if (_meta.text_offset < 24 || _meta.text_offset > _size ||
        _meta.text_offset + _meta.text_length > _size) {
        Serial.printf("[book] %s: text block out of range\n", path);
        close();
        return false;
    }

    if (!readStr(_file, _meta.title,  sizeof(_meta.title)) ||
        !readStr(_file, _meta.author, sizeof(_meta.author)) ||
        !readStr(_file, _meta.lang,   sizeof(_meta.lang))) {
        Serial.printf("[book] %s: truncated header strings\n", path);
        close();
        return false;
    }
    uint8_t enc = 0;
    if (_file.read(&enc, 1) == 1) _meta.encoding = enc;

    if (!_meta.title[0])  strncpy(_meta.title, "Isimsiz", sizeof(_meta.title) - 1);
    if (!_meta.author[0]) strncpy(_meta.author, "-", sizeof(_meta.author) - 1);

    strncpy(_path, path, sizeof(_path) - 1);
    _path[sizeof(_path) - 1] = 0;
    _open = true;

    Serial.printf("[book] %s: \"%s\" / %s  text %u+%u  toc %u\n",
                  path, _meta.title, _meta.author,
                  (unsigned)_meta.text_offset, (unsigned)_meta.text_length,
                  (unsigned)_meta.toc_count);

    loadToc();
    return true;
}

void Book::close() {
    if (_file) _file.close();
    _open = false;
    _pages.clear();
    _pages.shrink_to_fit();
    _toc.clear();
    _path[0] = 0;
    _size = 0;
    _lines_per_page = 0;
    _max_width = 0;
    _scale = 1;
}

bool Book::loadToc() {
    _toc.clear();
    if (!_open || !_meta.toc_offset || !_meta.toc_count) return false;
    if (_meta.toc_offset >= _size) return false;

    if (!_file.seek(_meta.toc_offset)) return false;

    _toc.reserve(_meta.toc_count > 512 ? 512 : _meta.toc_count);
    for (uint32_t i = 0; i < _meta.toc_count; i++) {
        uint8_t buf[5];
        if (_file.read(buf, 5) != 5) break;
        TocEntry e;
        memset(&e, 0, sizeof(e));
        e.text_pos = getU32(buf);
        const uint8_t len = buf[4];
        if (len) {
            /* Read the whole (possibly over-long) title, but keep only what
             * fits in the fixed-size field. */
            char tmp[256];
            const uint8_t keep = (len < BOOK_TITLE_MAX - 1) ? len : BOOK_TITLE_MAX - 1;
            if (_file.read((uint8_t*)tmp, len) != len) break;
            memcpy(e.title, tmp, keep);
            e.title[keep] = 0;
        }
        _toc.push_back(e);
    }
    Serial.printf("[book] toc entries: %u\n", (unsigned)_toc.size());
    return !_toc.empty();
}

const TocEntry* Book::tocEntry(int i) const {
    if (i < 0 || i >= (int)_toc.size()) return nullptr;
    return &_toc[i];
}

/* ==========================================================================
 *  Page index cache
 * ========================================================================== */

void Book::cachePathFor(const char* book_path, char* out, size_t out_size) const {
    /* /books/foo.epr -> /cache/foo.idx */
    const char* base = strrchr(book_path, '/');
    base = base ? base + 1 : book_path;

    char stem[80];
    strncpy(stem, base, sizeof(stem) - 1);
    stem[sizeof(stem) - 1] = 0;
    char* dot = strrchr(stem, '.');
    if (dot) *dot = 0;

    snprintf(out, out_size, "%s/%s.idx", CACHE_DIR, stem);
}

bool Book::loadIndexCache(int lines_per_page, int max_width, int scale) {
    char path[128];
    cachePathFor(_path, path, sizeof(path));

    File f = LittleFS.open(path, "r");
    if (!f) return false;

    uint8_t h[IDX_HEADER];
    if (f.read(h, IDX_HEADER) != IDX_HEADER || memcmp(h, IDX_MAGIC, 4) != 0) {
        f.close();
        return false;
    }
    if (getU16(h + 4) != IDX_VERSION) { f.close(); return false; }

    const uint32_t page_count = getU32(h + 32);
    const bool stale =
        getU32(h + 8)  != _size ||
        getU32(h + 12) != _meta.text_offset ||
        getU32(h + 16) != _meta.text_length ||
        getU16(h + 20) != (uint16_t)fontCellHeight() ||
        getU16(h + 22) != (uint16_t)fontLineHeight(1) ||
        (int8_t)h[24]  != (int8_t)fontAscent(1) ||
        h[25]          != (uint8_t)scale ||
        getU16(h + 26) != (uint16_t)lines_per_page ||
        getU16(h + 28) != (uint16_t)max_width ||
        page_count == 0 || page_count > IDX_MAX_PAGES;

    if (stale || f.size() < IDX_HEADER + (uint64_t)page_count * 4) {
        f.close();
        Serial.printf("[book] index cache stale, rebuilding\n");
        return false;
    }

    _pages.resize(page_count);
    uint8_t buf[256];
    uint32_t done = 0;
    while (done < page_count) {
        uint32_t chunk = page_count - done;
        if (chunk > sizeof(buf) / 4) chunk = sizeof(buf) / 4;
        const size_t want = chunk * 4;
        if (f.read(buf, want) != want) { f.close(); _pages.clear(); return false; }
        for (uint32_t i = 0; i < chunk; i++)
            _pages[done + i] = getU32(buf + i * 4);
        done += chunk;
    }
    f.close();

    /* Paranoia: a cache is only usable if the offsets are ordered and inside
     * the text block. */
    for (size_t i = 0; i < _pages.size(); i++) {
        if (_pages[i] < _meta.text_offset ||
            _pages[i] >= _meta.text_offset + _meta.text_length) {
            _pages.clear();
            return false;
        }
        if (i && _pages[i] <= _pages[i - 1]) { _pages.clear(); return false; }
    }

    Serial.printf("[book] index cache hit: %u pages\n", (unsigned)_pages.size());
    return !_pages.empty();
}

bool Book::saveIndexCache(int lines_per_page, int max_width, int scale) const {
    if (_pages.empty()) return false;

    char path[128];
    cachePathFor(_path, path, sizeof(path));

    File f = LittleFS.open(path, "w");
    if (!f) {
        Serial.printf("[book] cannot write %s\n", path);
        return false;
    }

    uint8_t h[IDX_HEADER];
    memset(h, 0, sizeof(h));
    memcpy(h, IDX_MAGIC, 4);
    putU16(h + 4, IDX_VERSION);
    putU32(h + 8, _size);
    putU32(h + 12, _meta.text_offset);
    putU32(h + 16, _meta.text_length);
    putU16(h + 20, (uint16_t)fontCellHeight());
    putU16(h + 22, (uint16_t)fontLineHeight(1));
    h[24] = (uint8_t)(int8_t)fontAscent(1);
    h[25] = (uint8_t)scale;
    putU16(h + 26, (uint16_t)lines_per_page);
    putU16(h + 28, (uint16_t)max_width);
    putU32(h + 32, (uint32_t)_pages.size());
    f.write(h, IDX_HEADER);

    uint8_t buf[256];
    size_t i = 0;
    while (i < _pages.size()) {
        size_t chunk = _pages.size() - i;
        if (chunk > sizeof(buf) / 4) chunk = sizeof(buf) / 4;
        for (size_t k = 0; k < chunk; k++) putU32(buf + k * 4, _pages[i + k]);
        f.write(buf, chunk * 4);
        i += chunk;
    }
    f.close();
    Serial.printf("[book] index cached: %s (%u pages)\n", path, (unsigned)_pages.size());
    return true;
}

void Book::invalidateIndexCache() {
    char path[128];
    if (!_path[0]) return;
    cachePathFor(_path, path, sizeof(path));
    if (LittleFS.exists(path)) LittleFS.remove(path);
}

/* ==========================================================================
 *  Pagination
 * ========================================================================== */

bool Book::paginate(int lines_per_page, int max_width, int scale,
                    ProgressFn cb, void* ctx) {
    if (!_open) return false;
    if (lines_per_page < 1) lines_per_page = 1;
    if (scale < 1) scale = 1;

    const bool same_params = (_lines_per_page == lines_per_page &&
                              _max_width == max_width && _scale == scale);
    if (same_params && !_pages.empty()) return true;

    _lines_per_page = lines_per_page;
    _max_width = max_width;
    _scale = scale;
    _pages.clear();

    if (loadIndexCache(lines_per_page, max_width, scale)) return true;

    if (cb) cb(0, ctx);

    const uint32_t text_end = _meta.text_offset + _meta.text_length;
    const int para_indent = BOOK_PARA_INDENT * scale;

    TextReader r;
    char line[BOOK_LINE_MAX];

    uint32_t off = _meta.text_offset;
    _pages.push_back(off);

    while (off < text_end && _pages.size() < IDX_MAX_PAGES) {
        r.begin(&_file, off, text_end, scale);

        int lines = 0;
        while (lines < lines_per_page) {
            const int w = max_width - (r.atParagraphStart() ? para_indent : 0);
            if (r.readLine(w, line, sizeof(line)) == 0) break;
            lines++;
            if (r.lastBreak() == EPR_CTRL_CHAPTER) break;   /* new page */
        }

        const uint32_t next = r.nextLineOffset();
        if (next <= off || next >= text_end) break;         /* no progress / done */
        off = next;
        _pages.push_back(off);

        if (cb && (_pages.size() & 0x1F) == 0) {
            const uint32_t done = off - _meta.text_offset;
            cb((int)((uint64_t)done * 100 / (_meta.text_length ? _meta.text_length : 1)), ctx);
        }
        /* Give the WiFi task and the watchdog some air on long books. */
        if ((_pages.size() & 0x7F) == 0) delay(1);
    }

    if (cb) cb(100, ctx);
    Serial.printf("[book] paginated: %u pages, %d lines/page, w=%d, scale=%d\n",
                  (unsigned)_pages.size(), lines_per_page, max_width, scale);

    saveIndexCache(lines_per_page, max_width, scale);
    return !_pages.empty();
}

uint32_t Book::pageOffset(int page) const {
    if (page < 0 || page >= (int)_pages.size()) return _meta.text_offset;
    return _pages[page];
}

int Book::percentForPage(int page) const {
    if (_pages.empty() || page < 0) return 0;
    if (page >= (int)_pages.size()) return 100;
    if (!_meta.text_length) return 100;
    const uint32_t rel = _pages[page] - _meta.text_offset;
    const int pct = (int)((uint64_t)rel * 100 / _meta.text_length);
    return pct > 100 ? 100 : pct;
}

int Book::pageForTextPos(uint32_t text_pos) const {
    if (_pages.empty()) return 0;
    for (size_t i = 0; i < _pages.size(); i++)
        if (_pages[i] >= text_pos) return (int)i;
    return (int)_pages.size() - 1;
}

bool Book::drawPage(Canvas& canvas, int page, int x, int top_baseline,
                    int line_height) {
    if (!_open || _lines_per_page < 1) return false;
    if (page < 0 || page >= (int)_pages.size()) return false;

    const uint32_t text_end = _meta.text_offset + _meta.text_length;
    const int para_indent = BOOK_PARA_INDENT * _scale;

    TextReader r;
    r.begin(&_file, _pages[page], text_end, _scale);

    char line[BOOK_LINE_MAX];
    int baseline = top_baseline;

    for (int i = 0; i < _lines_per_page; i++) {
        const bool indent = r.atParagraphStart();
        const int w = _max_width - (indent ? para_indent : 0);
        if (r.readLine(w, line, sizeof(line)) == 0) break;
        if (line[0]) {
            fontDrawText(canvas, line, x + (indent ? para_indent : 0), baseline,
                         _scale, COL_BLACK);
        }
        baseline += line_height;
        if (r.lastBreak() == EPR_CTRL_CHAPTER) break;
    }
    return true;
}
