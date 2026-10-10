#pragma once
#include <Arduino.h>
#include <FS.h>          /* fs::File -- held open for the lifetime of a Book */
#include <vector>
#include "epd.h"

/*
 * ===========================================================================
 *  book.h -- .epr v1 ebook container
 * ===========================================================================
 *
 *  Layout:
 *    offset 0   : magic "EPR1" (4 bytes)
 *    offset 4   : uint16 version = 1
 *    offset 6   : uint16 flags            bit0 = has_toc
 *    offset 8   : uint32 text_offset
 *    offset 12  : uint32 text_length
 *    offset 16  : uint32 toc_offset       (0 if none)
 *    offset 20  : uint32 toc_count
 *    offset 24  : uint8  title_len,  char title[title_len]   (UTF-8)
 *                 uint8  author_len, char author[author_len] (UTF-8)
 *                 uint8  lang_len,   char lang[lang_len]     (ASCII)
 *                 uint8  encoding    (0 = UTF-8)
 *                 pad to text_offset with 0x00
 *
 *  Text block (UTF-8) control bytes:
 *    0x0A  paragraph break        (end the current line)
 *    0x0B  chapter/section break  (start a new page)
 *    everything else is literal text; '\r' is stripped
 *
 *  TOC block, toc_count entries:
 *    uint32 text_pos; uint8 len; char title[len]
 *
 *  Page index cache at /cache/<name>.idx:
 *    magic "PIDX", uint16 version, then the book size and the font metrics
 *    that the page breaks depend on. A mismatch means the cache is stale and
 *    is rebuilt from scratch.
 * ===========================================================================
 */

#define EPR_MAGIC           "EPR1"
#define EPR_VERSION         1

#define EPR_FLAG_HAS_TOC    0x0001

#define EPR_CTRL_PARAGRAPH  0x0A
#define EPR_CTRL_CHAPTER    0x0B

#define BOOK_TITLE_MAX      64
#define BOOK_AUTHOR_MAX     48
#define BOOK_LANG_MAX       8
#define BOOK_LINE_MAX       192
#define BOOK_PARA_INDENT    6      /* scale-1 pixels, for paragraph starts */

struct BookMeta {
    char     title[BOOK_TITLE_MAX];
    char     author[BOOK_AUTHOR_MAX];
    char     lang[BOOK_LANG_MAX];
    uint16_t flags;
    uint16_t encoding;
    uint32_t text_offset;
    uint32_t text_length;
    uint32_t toc_offset;
    uint32_t toc_count;
};

struct TocEntry {
    uint32_t text_pos;
    char     title[BOOK_TITLE_MAX];
};

/* Parse only the header of a .epr file (used by the library list). Does not
 * keep the file open. */
bool bookReadMeta(const char* path, BookMeta* out, uint32_t* file_size = nullptr);

class Book {
public:
    typedef void (*ProgressFn)(int percent, void* ctx);

    Book();
    ~Book();

    bool open(const char* path);
    void close();
    bool isOpen() const { return _open; }

    const BookMeta& meta() const { return _meta; }
    const char*     path() const { return _path; }
    uint32_t        size() const { return _size; }

    /* Read the TOC into RAM (a few hundred bytes at most). */
    bool loadToc();
    int  tocCount() const { return (int)_toc.size(); }
    const TocEntry* tocEntry(int i) const;

    /* Greedy word wrap into pages of `lines_per_page` lines, each no wider
     * than `max_width` logical pixels at `scale`. Only the uint32 start offset
     * of every page is stored. Uses /cache/<name>.idx when it is still valid;
     * otherwise rebuilds it and reports progress through `cb`. */
    bool paginate(int lines_per_page, int max_width, int scale,
                  ProgressFn cb = nullptr, void* ctx = nullptr);

    int  pageCount() const { return (int)_pages.size(); }
    int  linesPerPage() const { return _lines_per_page; }
    uint32_t pageOffset(int page) const;

    /* Draw page `page` with its first baseline at `top_baseline`. The wrap
     * width, line count and scale are the ones captured by paginate(), so the
     * rendered lines are guaranteed to be the ones that were paginated. */
    bool drawPage(Canvas& canvas, int page, int x, int top_baseline,
                  int line_height);

    /* 0..100, how far into the text this page starts. */
    int  percentForPage(int page) const;

    /* First page whose start offset is >= text_pos (for TOC jumps). */
    int  pageForTextPos(uint32_t text_pos) const;

    void invalidateIndexCache();

private:
    bool loadIndexCache(int lines_per_page, int max_width, int scale);
    bool saveIndexCache(int lines_per_page, int max_width, int scale) const;
    void cachePathFor(const char* book_path, char* out, size_t out_size) const;

    File                  _file;
    bool                  _open = false;
    char                  _path[96] = {0};
    uint32_t              _size = 0;
    BookMeta              _meta = {};
    std::vector<TocEntry> _toc;
    std::vector<uint32_t> _pages;
    int                   _lines_per_page = 0;
    int                   _max_width = 0;
    int                   _scale = 1;
};
