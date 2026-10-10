/*
 * ui.cpp -- all screens, drawing and input handling.
 *
 * Every screen draws into the logical canvas. The header is closed by a 2 px
 * rule and the status bar by a 1 px rule, as specified.
 */

#include "ui.h"
#include "font.h"
#include "wifi_xfer.h"
#include "power.h"
#include <LittleFS.h>
#include <vector>

/* --------------------------------------------------------------------------
 *  Layout, recomputed from the font metrics at init
 * ------------------------------------------------------------------------ */
static int s_line_h = 16;      /* fontLineHeight(1)      */
static int s_asc = 12;         /* fontAscent(1)          */
static int s_header_h = UI_HEADER_H;
static int s_status_h = UI_STATUS_H;
static int s_content_y = 0;
static int s_content_h = 0;

/* --------------------------------------------------------------------------
 *  State
 * ------------------------------------------------------------------------ */
static ScreenId  s_screen = SCR_SPLASH;
static bool      s_redraw = true;
static bool      s_redraw_full = true;
static RefreshKind s_refresh_hint = REFRESH_FULL;

static Settings  s_settings = { DEF_FONT_SCALE, DEF_SLEEP_SEC, DEF_FULL_REFRESH_EVERY,
                                0, 0, String(""), String(""), DEF_PARTIAL_ENABLED };
static bool      s_have_settings = false;

static std::vector<BookEntry> s_books;
static int       s_lib_index = 0;
static int       s_lib_top = 0;

static Book      s_book;
static int       s_book_index = -1;
static int       s_page = 0;

static int       s_menu_index = 0;
static bool      s_menu_confirm_delete = false;

static char      s_error_line1[48] = {0};
static char      s_error_line2[64] = {0};
static char      s_splash_sub[48] = {0};
static int       s_splash_progress = -1;

static bool      s_font_ok = false;
static bool      s_quiet = false;
static bool      s_low_battery = false;

/* Menu entries (indices must stay in this order). */
enum MenuItemId : uint8_t {
    MI_FONT_SIZE = 0,
    MI_FULL_REFRESH,
    MI_SLEEP,
    MI_WIFI,
    MI_DELETE,
    MI_ABOUT,
    MI_BACK,
    MI_COUNT
};

static const StrId kMenuLabels[MI_COUNT] = {
    S_MENU_FONT_SIZE, S_MENU_FULL_REFRESH, S_MENU_SLEEP,
    S_MENU_WIFI, S_MENU_DELETE, S_MENU_ABOUT, S_MENU_BACK
};

/* --------------------------------------------------------------------------
 *  Small drawing helpers
 * ------------------------------------------------------------------------ */

static void markRedraw(bool full) {
    s_redraw = true;
    if (full) s_redraw_full = true;
}

/* Draw a string, truncated with ".." if it does not fit in max_w. */
static void drawFitted(const char* s, int x, int baseline, int scale,
                       uint8_t ink, int max_w) {
    if (!s || !*s) return;
    canvas.setClipRect(x, baseline - fontAscent(scale) - 1, max_w,
                       fontLineHeight(scale) + 1);
    fontDrawText(canvas, s, x, baseline, scale, ink);
    canvas.clearClip();
}

static void drawHeader(const char* title, const char* right) {
    canvas.fillRect(0, 0, CANVAS_W, s_header_h - 2, COL_WHITE);
    const int baseline = 1 + s_asc;
    drawFitted(title, UI_MARGIN, baseline, 1, COL_BLACK, CANVAS_W - 2 * UI_MARGIN - 30);
    if (right && *right) {
        const int w = fontTextWidth(right, 1);
        fontDrawText(canvas, right, CANVAS_W - UI_MARGIN - w, baseline, 1, COL_BLACK);
    }
    /* 2 px rule under the header */
    canvas.fillRect(0, s_header_h - 2, CANVAS_W, 2, COL_BLACK);
}

/* 1 px rule above the status bar */
static void drawStatusRule() {
    canvas.fillRect(0, CANVAS_H - s_status_h, CANVAS_W, 1, COL_BLACK);
}

static void drawBatteryIcon(int x, int y, int pct) {
    const int w = 16, h = 7;
    canvas.drawRect(x, y, w, h, COL_BLACK);
    canvas.fillRect(x + w, y + 2, 2, h - 4, COL_BLACK);      /* nub */
    const int fill = (pct * (w - 4)) / 100;
    if (fill > 0) canvas.fillRect(x + 2, y + 2, fill, h - 4, COL_BLACK);
}

/*
 * Status bar contents:
 *   left   -- caller supplied text (page x/y, list position, ...)
 *   right  -- battery icon + percent, plus the ghosting counter when partial
 *             refreshes are enabled.
 */
static void drawStatus(const char* left) {
    const int y = CANVAS_H - s_status_h;
    canvas.fillRect(0, y, CANVAS_W, s_status_h, COL_WHITE);
    drawStatusRule();

    const int baseline = y + 2 + s_asc;
    const int right_edge = CANVAS_W - UI_MARGIN;

    const int pct = batteryPercent();
    char right[8];
    snprintf(right, sizeof(right), "%d%%", pct);
    const int batt_text_w = fontTextWidth(right, 1);

    /* Battery icon + percentage sit flush right. */
    const int text_x = right_edge - batt_text_w;
    const int icon_x = text_x - 18;
    drawBatteryIcon(icon_x, y + 2 + (s_asc - 7) / 2, pct);
    fontDrawText(canvas, right, text_x, baseline, 1, COL_BLACK);

    /* Ghosting indicator, left of the battery. */
    int reserved = batt_text_w + 18 + 4;
    if (s_settings.partial_enabled) {
        char ghost[10];
        if (s_refresh_hint == REFRESH_PARTIAL) {
            snprintf(ghost, sizeof(ghost), "P%d", s_settings.full_refresh_every);
        } else {
            snprintf(ghost, sizeof(ghost), "TAM");
        }
        const int gw = fontTextWidth(ghost, 1);
        fontDrawText(canvas, ghost, icon_x - 5 - gw, baseline, 1, COL_BLACK);
        reserved += gw + 5;
    }

    if (left && *left) {
        drawFitted(left, UI_MARGIN, baseline, 1, COL_BLACK,
                   CANVAS_W - reserved - 2 * UI_MARGIN);
    }
}

static void drawCentered(const char* s, int baseline, int scale, uint8_t ink) {
    const int w = fontTextWidth(s, scale);
    fontDrawText(canvas, s, (CANVAS_W - w) / 2, baseline, scale, ink);
}

/* Draw a wrapped paragraph, returns the next baseline. */
static int drawWrapped(const char* s, int x, int baseline, int max_w, int scale,
                       uint8_t ink, int max_lines) {
    if (!s) return baseline;
    int lines = 0;
    while (*s && lines < max_lines) {
        int consumed = 0;
        const int n = fontWrapLine(s, max_w, scale, &consumed);
        char buf[BOOK_LINE_MAX];
        const int keep = (n < (int)sizeof(buf) - 1) ? n : (int)sizeof(buf) - 1;
        memcpy(buf, s, keep);
        buf[keep] = 0;
        fontDrawText(canvas, buf, x, baseline, scale, ink);
        baseline += fontLineHeight(scale);
        lines++;
        if (consumed <= 0) break;
        s += consumed;
    }
    return baseline;
}

/* --------------------------------------------------------------------------
 *  Screens
 * ------------------------------------------------------------------------ */

static void renderSplash() {
    canvas.clear(COL_WHITE);

    const int title_baseline = CANVAS_H / 2 - 10;
    drawCentered(t(S_APP_NAME), title_baseline, 2, COL_BLACK);

    const char* sub = s_splash_sub[0] ? s_splash_sub : t(S_BOOTING);
    drawCentered(sub, title_baseline + 2 + fontLineHeight(1), 1, COL_BLACK);

    if (s_splash_progress >= 0) {
        const int bar_w = CANVAS_W - 40;
        const int bar_h = 8;
        const int bx = 20;
        const int by = CANVAS_H - 26;
        canvas.drawRect(bx, by, bar_w, bar_h, COL_BLACK);
        int fill = (s_splash_progress * (bar_w - 4)) / 100;
        if (fill < 0) fill = 0;
        if (fill > bar_w - 4) fill = bar_w - 4;
        canvas.fillRect(bx + 2, by + 2, fill, bar_h - 4, COL_BLACK);

        char buf[16];
        snprintf(buf, sizeof(buf), "%d%%", s_splash_progress);
        const int w = fontTextWidth(buf, 1);
        fontDrawText(canvas, buf, (CANVAS_W - w) / 2, by - 3, 1, COL_BLACK);
    }
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

static void renderLibrary() {
    canvas.clear(COL_WHITE);

    char right[16];
    snprintf(right, sizeof(right), "%d/%d",
             s_books.empty() ? 0 : s_lib_index + 1, (int)s_books.size());
    drawHeader(t(S_LIBRARY_TITLE), right);

    if (s_books.empty()) {
        const int b = s_content_y + s_line_h + 6;
        drawCentered(t(S_LIBRARY_EMPTY), b, 1, COL_BLACK);
        drawCentered(t(S_LIBRARY_EMPTY_HINT), b + s_line_h, 1, COL_BLACK);
        drawStatus("");
        return;
    }

    /* Rows: title + "author - size" on one line */
    const int row_h = s_line_h + 2;
    const int rows = s_content_h / row_h;
    if (s_lib_index < s_lib_top) s_lib_top = s_lib_index;
    if (s_lib_index >= s_lib_top + rows) s_lib_top = s_lib_index - rows + 1;
    if (s_lib_top < 0) s_lib_top = 0;

    for (int i = 0; i < rows; i++) {
        const int idx = s_lib_top + i;
        if (idx >= (int)s_books.size()) break;
        const BookEntry& e = s_books[idx];
        const int y = s_content_y + i * row_h;
        const int baseline = y + s_asc;

        char line[128];
        char sizebuf[12];
        storageFormatSize(e.size, sizebuf, sizeof(sizebuf));
        if (e.author.length() && e.author != "-") {
            snprintf(line, sizeof(line), "%s - %s", e.title.c_str(), e.author.c_str());
        } else {
            snprintf(line, sizeof(line), "%s", e.title.c_str());
        }

        if (idx == s_lib_index) {
            /* Inverted selection bar: white text on black. */
            canvas.fillRect(0, y, CANVAS_W, row_h, COL_BLACK);
            drawFitted(line, UI_MARGIN + 6, baseline, 1, COL_WHITE,
                       CANVAS_W - 2 * UI_MARGIN - 6);
            const int sw = fontTextWidth(sizebuf, 1);
            fontDrawText(canvas, sizebuf, CANVAS_W - UI_MARGIN - sw, baseline, 1, COL_WHITE);
        } else {
            drawFitted(line, UI_MARGIN + 6, baseline, 1, COL_BLACK,
                       CANVAS_W - 2 * UI_MARGIN - 6);
        }
    }

    /* scroll indicator */
    if (s_books.size() > (size_t)rows && rows > 0) {
        const int track_h = s_content_h;
        const int x = CANVAS_W - 2;
        canvas.fillRect(x, s_content_y, 2, track_h, COL_WHITE);
        const int thumb_h = track_h * rows / (int)s_books.size();
        const int max_top = (int)s_books.size() - rows;
        const int thumb_y = s_content_y +
                            (max_top > 0 ? (track_h - thumb_h) * s_lib_top / max_top : 0);
        canvas.fillRect(x, thumb_y, 2, thumb_h < 4 ? 4 : thumb_h, COL_BLACK);
    }

    char left[32];
    snprintf(left, sizeof(left), "%d/%d", s_lib_index + 1, (int)s_books.size());
    drawStatus(left);
}

static void renderReader() {
    canvas.clear(COL_WHITE);

    drawHeader(s_book.meta().title, nullptr);

    if (s_book.pageCount() > 0) {
        s_book.drawPage(canvas, s_page, UI_MARGIN, s_content_y + s_asc, s_line_h);
    }

    char left[48];
    if (s_book.pageCount() > 0) {
        const int pct = s_book.percentForPage(s_page);
        snprintf(left, sizeof(left), "%s %d/%d  %%%d",
                 t(S_READER_PAGE), s_page + 1, s_book.pageCount(), pct);
    } else {
        snprintf(left, sizeof(left), "%s", t(S_ERROR_NO_BOOK));
    }
    drawStatus(left);
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

static void menuValue(MenuItemId id, char* buf, size_t n) {
    switch (id) {
        case MI_FONT_SIZE:
            snprintf(buf, n, "%s", s_settings.font_scale >= 2 ? t(S_SCALE_X2) : t(S_SCALE_X1));
            break;
        case MI_FULL_REFRESH:
            snprintf(buf, n, "%s", t(S_ON));
            break;
        case MI_SLEEP:
            snprintf(buf, n, "%d%s", s_settings.sleep_sec, t(S_SECONDS));
            break;
        case MI_WIFI:
            snprintf(buf, n, "%s", t(S_OFF));
            break;
        case MI_DELETE:
        case MI_ABOUT:
        case MI_BACK:
        default:
            buf[0] = 0;
    }
}

static void renderMenu() {
    /* Keep the current screen underneath and overlay the menu box. */
    if (s_screen == SCR_MENU) {
        if (s_book.isOpen() && s_book.pageCount() > 0) {
            canvas.clear(COL_WHITE);
            drawHeader(s_book.meta().title, nullptr);
            s_book.drawPage(canvas, s_page, UI_MARGIN, s_content_y + s_asc, s_line_h);
        } else {
            canvas.clear(COL_WHITE);
            drawHeader(t(S_LIBRARY_TITLE), nullptr);
        }
    }

    const int rows = s_menu_confirm_delete ? 2 : (int)MI_COUNT;
    const int box_h = rows * (s_line_h + 2) + s_line_h + 8;
    const int box_y = (CANVAS_H - box_h) / 2;
    const int box_x = 10;
    const int box_w = CANVAS_W - 20;

    canvas.fillRect(box_x, box_y, box_w, box_h, COL_WHITE);
    canvas.drawRect(box_x, box_y, box_w, box_h, COL_BLACK);
    canvas.drawRect(box_x + 1, box_y + 1, box_w - 2, box_h - 2, COL_BLACK);

    int baseline = box_y + 3 + s_asc;
    const char* title = s_menu_confirm_delete ? t(S_MENU_DELETE_CONFIRM) : t(S_MENU_TITLE);
    drawCentered(title, baseline, 1, COL_BLACK);
    baseline += s_line_h + 4;

    const int item_h = s_line_h + 2;
    for (int i = 0; i < rows; i++) {
        const bool sel = (i == s_menu_index);
        const int y = baseline - s_asc;
        if (sel) canvas.fillRect(box_x + 2, y, box_w - 4, item_h, COL_BLACK);

        const uint8_t ink = sel ? COL_WHITE : COL_BLACK;

        if (s_menu_confirm_delete) {
            const StrId lbl = (i == 0) ? S_YES : S_NO;
            fontDrawText(canvas, t(lbl), box_x + 8, baseline, 1, ink);
        } else {
            const MenuItemId id = (MenuItemId)i;
            fontDrawText(canvas, t(kMenuLabels[id]), box_x + 8, baseline, 1, ink);
            char val[16];
            menuValue(id, val, sizeof(val));
            if (val[0]) {
                const int w = fontTextWidth(val, 1);
                fontDrawText(canvas, val, box_x + box_w - 8 - w, baseline, 1, ink);
            }
        }
        baseline += item_h;
    }

    drawStatus("");
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

static void renderWifi() {
    canvas.clear(COL_WHITE);
    drawHeader(t(S_WIFI_TITLE), wifiXferStateText());

    int baseline = s_content_y + s_asc;

    const WifiXferState st = wifiXferState();
    if (st == WIFI_XFER_CONNECTING) {
        char buf[64];
        snprintf(buf, sizeof(buf), "%s %s", t(S_WIFI_STA_CONNECTING), wifiXferAddress());
        fontDrawText(canvas, buf, UI_MARGIN, baseline, 1, COL_BLACK);
        baseline += s_line_h;
        fontDrawText(canvas, t(S_WIFI_HINT_1), UI_MARGIN, baseline, 1, COL_BLACK);
    } else {
        char buf[80];

        snprintf(buf, sizeof(buf), "%s: %s", t(S_WIFI_NETWORK), wifiXferSsid());
        drawFitted(buf, UI_MARGIN, baseline, 1, COL_BLACK, CANVAS_W - 2 * UI_MARGIN);
        baseline += s_line_h;

        if (st == WIFI_XFER_AP) {
            snprintf(buf, sizeof(buf), "%s: %s", t(S_WIFI_PASSWORD), wifiXferPass());
            drawFitted(buf, UI_MARGIN, baseline, 1, COL_BLACK, CANVAS_W - 2 * UI_MARGIN);
            baseline += s_line_h;
        }

        snprintf(buf, sizeof(buf), "%s: http://%s/", t(S_WIFI_ADDRESS), wifiXferAddress());
        drawFitted(buf, UI_MARGIN, baseline, 1, COL_BLACK, CANVAS_W - 2 * UI_MARGIN);
        baseline += s_line_h;

        fontDrawText(canvas, t(S_WIFI_HINT_1), UI_MARGIN, baseline, 1, COL_BLACK);
        baseline += s_line_h;
        fontDrawText(canvas, t(S_WIFI_HINT_2), UI_MARGIN, baseline, 1, COL_BLACK);
    }

    drawStatus(t(S_WIFI_EXIT_HINT));
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

static void renderError() {
    canvas.clear(COL_WHITE);
    drawHeader(t(S_ERROR_TITLE), nullptr);

    int baseline = s_content_y + s_asc + 6;
    drawCentered(s_error_line1, baseline, 1, COL_BLACK);
    baseline += s_line_h + 4;
    drawWrapped(s_error_line2, UI_MARGIN, baseline, CANVAS_W - 2 * UI_MARGIN, 1,
                COL_BLACK, 4);

    drawStatus("");
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

static void renderInfo() {
    canvas.clear(COL_WHITE);
    drawHeader(t(S_ABOUT_TITLE), nullptr);

    int baseline = s_content_y + s_asc + 2;
    fontDrawText(canvas, t(S_ABOUT_L1), UI_MARGIN, baseline, 1, COL_BLACK);
    baseline += s_line_h;
    fontDrawText(canvas, t(S_ABOUT_L2), UI_MARGIN, baseline, 1, COL_BLACK);
    baseline += s_line_h;
    fontDrawText(canvas, t(S_ABOUT_L3), UI_MARGIN, baseline, 1, COL_BLACK);
    baseline += s_line_h + 4;

    char buf[48];
    snprintf(buf, sizeof(buf), "v%s", POCKET_READER_VERSION);
    fontDrawText(canvas, buf, UI_MARGIN, baseline, 1, COL_BLACK);

    drawStatus("");
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

static void renderSleep() {
    canvas.clear(COL_WHITE);
    if (s_low_battery) {
        const int b = CANVAS_H / 2 - fontLineHeight(2) / 2;
        drawCentered(t(S_BATTERY_LOW), b, 2, COL_BLACK);
        drawCentered(t(S_BATTERY_LOW_HINT), b + fontLineHeight(2) + 2, 1, COL_BLACK);
    } else {
        const int b = CANVAS_H / 2 - 4;
        drawCentered(t(S_SLEEP_TITLE), b, 2, COL_BLACK);
        drawCentered(t(S_SLEEP_HINT), b + fontLineHeight(2), 1, COL_BLACK);
    }
    epdSetPartialWindow(0, 0, CANVAS_W, CANVAS_H);
}

/* --------------------------------------------------------------------------
 *  Public API
 * ------------------------------------------------------------------------ */

bool uiInit(const Settings* settings) {
    canvas.begin(epdFramebuffer());

    if (settings) {
        s_settings = *settings;
        s_have_settings = true;
    }

    s_font_ok = fontLoad(DEFAULT_FONT);
    if (!s_font_ok) {
        /* Try any .epf in /fonts before giving up. */
        File dir = LittleFS.open(FONT_DIR);
        if (dir && dir.isDirectory()) {
            File f = dir.openNextFile();
            while (f) {
                /* File::name() returns const char* on core 2.x and String on
                 * core 3.x; building a String covers both. */
                const String n = f.name();
                if (!f.isDirectory() && n.endsWith(".epf")) {
                    char path[96];
                    snprintf(path, sizeof(path), "%s/%s", FONT_DIR, n.c_str());
                    if (fontLoad(path)) { s_font_ok = true; break; }
                }
                f = dir.openNextFile();
            }
            dir.close();
        }
    }

    if (s_font_ok) {
        s_asc = fontAscent(1);
        s_line_h = fontLineHeight(1);
        s_header_h = (UI_HEADER_H > s_asc + 5) ? UI_HEADER_H : s_asc + 5;
        s_status_h = (UI_STATUS_H > s_asc + 4) ? UI_STATUS_H : s_asc + 4;
    }
    s_content_y = s_header_h + 1;
    s_content_h = CANVAS_H - s_status_h - 1 - s_content_y;

    if (!s_font_ok) {
        strncpy(s_error_line1, t(S_ERROR_NO_FONT), sizeof(s_error_line1) - 1);
        strncpy(s_error_line2, t(S_ERROR_NO_FONT_HINT), sizeof(s_error_line2) - 1);
        s_screen = SCR_ERROR;
    }

    s_redraw = true;
    s_redraw_full = true;
    return s_font_ok;
}

void uiSetSettings(const Settings* settings) {
    if (settings) {
        s_settings = *settings;
        s_have_settings = true;
    }
}

bool uiTakeRedraw(bool* needs_full) {
    if (!s_redraw) return false;
    s_redraw = false;
    if (needs_full) *needs_full = s_redraw_full;
    s_redraw_full = false;
    return true;
}

void uiSetRefreshHint(RefreshKind kind) { s_refresh_hint = kind; }

void uiRender() {
    if (!s_font_ok) { renderError(); return; }

    switch (s_screen) {
        case SCR_SPLASH:  renderSplash();  break;
        case SCR_LIBRARY: renderLibrary(); break;
        case SCR_READER:  renderReader();  break;
        case SCR_MENU:    renderMenu();    break;
        case SCR_WIFI:    renderWifi();    break;
        case SCR_INFO:    renderInfo();    break;
        case SCR_SLEEP:   renderSleep();   break;
        case SCR_ERROR:
        default:          renderError();   break;
    }
}

ScreenId uiScreen() { return s_screen; }

void uiShowError(StrId line1, StrId line2) {
    strncpy(s_error_line1, t(line1), sizeof(s_error_line1) - 1);
    strncpy(s_error_line2, t(line2), sizeof(s_error_line2) - 1);
    s_screen = SCR_ERROR;
    markRedraw(true);
}

void uiShowSplash(const char* subtitle, int progress) {
    if (subtitle) {
        strncpy(s_splash_sub, subtitle, sizeof(s_splash_sub) - 1);
        s_splash_sub[sizeof(s_splash_sub) - 1] = 0;
    } else {
        s_splash_sub[0] = 0;
    }
    s_splash_progress = progress;
    s_screen = SCR_SPLASH;
    markRedraw(true);
}

void uiReloadLibrary() {
    s_books = storageListBooks();
    if (s_lib_index >= (int)s_books.size()) s_lib_index = (int)s_books.size() - 1;
    if (s_lib_index < 0) s_lib_index = 0;
    if (s_lib_top > s_lib_index) s_lib_top = s_lib_index;
}

int uiLibraryCount() { return (int)s_books.size(); }

bool uiHasBook() { return s_book.isOpen() && s_book.pageCount() > 0; }
int  uiBookIndex() { return s_book_index; }
int  uiPage() { return s_page; }
int  uiPageCount() { return s_book.pageCount(); }
const char* uiBookTitle() { return s_book.isOpen() ? s_book.meta().title : ""; }

bool uiOpenBook(int index, int page);

/* --------------------------------------------------------------------------
 *  Menu actions
 * ------------------------------------------------------------------------ */

static void handleMenuSelect() {
    /* Two-step delete confirmation. */
    if (s_menu_confirm_delete) {
        if (s_menu_index == 0) {                       /* Evet */
            if (s_book.isOpen()) {
                const String p = s_book.path();
                s_book.close();
                s_book_index = -1;
                s_page = 0;
                storageDeleteBook(p.c_str());
            } else if (s_lib_index < (int)s_books.size()) {
                storageDeleteBook(s_books[s_lib_index].path.c_str());
            }
            uiReloadLibrary();
            s_screen = SCR_LIBRARY;
        } else {
            s_screen = uiHasBook() ? SCR_READER : SCR_LIBRARY;
        }
        s_menu_confirm_delete = false;
        s_menu_index = 0;
        markRedraw(true);
        return;
    }

    switch ((MenuItemId)s_menu_index) {
        case MI_FONT_SIZE: {
            s_settings.font_scale = (s_settings.font_scale >= 2) ? 1 : 2;
            storageSaveSettings(&s_settings);
            Serial.printf("[ui] font scale -> x%u\n", (unsigned)s_settings.font_scale);
            if (s_book.isOpen()) {
                /* Re-flow around the page we are looking at. */
                const uint32_t pos = s_book.pageOffset(s_page);
                const int scale = s_settings.font_scale;
                const int lh = fontLineHeight(scale);
                const int lines = (lh > 0) ? (s_content_h / lh) : 1;
                s_book.paginate(lines > 0 ? lines : 1, CANVAS_W - 2 * UI_MARGIN, scale);
                s_page = s_book.pageForTextPos(pos);
            }
            s_screen = uiHasBook() ? SCR_READER : SCR_LIBRARY;
            markRedraw(true);
            break;
        }

        case MI_FULL_REFRESH:
            s_screen = uiHasBook() ? SCR_READER : SCR_LIBRARY;
            markRedraw(true);
            break;

        case MI_SLEEP: {
            static const uint16_t steps[] = { 30, 60, 120, 300, 0 };
            const int n = sizeof(steps) / sizeof(steps[0]);
            int cur = 0;
            for (int i = 0; i < n; i++) if (steps[i] == s_settings.sleep_sec) cur = i;
            s_settings.sleep_sec = steps[(cur + 1) % n];
            storageSaveSettings(&s_settings);
            markRedraw(false);
            break;
        }

        case MI_WIFI:
            /* main.cpp sees SCR_WIFI and brings the radio up. */
            s_screen = SCR_WIFI;
            markRedraw(true);
            break;

        case MI_DELETE:
            s_menu_confirm_delete = true;
            s_menu_index = 0;
            markRedraw(true);
            break;

        case MI_ABOUT:
            s_screen = SCR_INFO;
            markRedraw(true);
            break;

        case MI_BACK:
        default:
            s_screen = uiHasBook() ? SCR_READER : SCR_LIBRARY;
            markRedraw(true);
            break;
    }
}

/* Pagination runs on the first open of a book; repaint the splash bar as it
 * goes. The panel is idle here, so a direct partial refresh is safe. */
static void paginateProgress(int percent, void* ctx) {
    (void)ctx;
    s_splash_progress = percent;
    s_splash_sub[0] = 0;
    strncpy(s_splash_sub, t(S_PAGINATING), sizeof(s_splash_sub) - 1);

    bool dummy = false;
    uiTakeRedraw(&dummy);      /* consume the pending flag */
    renderSplash();
    epdPartialRefresh();
}

bool uiOpenBook(int index, int page) {
    if (index < 0 || index >= (int)s_books.size()) return false;

    uiCloseBook();

    const char* path = s_books[index].path.c_str();
    if (!s_book.open(path)) {
        uiShowError(S_ERROR_BOOK_PARSE, S_ERROR_NO_BOOK);
        return false;
    }

    const int scale = (s_settings.font_scale >= 1 && s_settings.font_scale <= 2)
                          ? s_settings.font_scale : 1;
    const int line_h = fontLineHeight(scale);
    const int lines = (line_h > 0) ? (s_content_h / line_h) : 1;
    const int max_w = CANVAS_W - 2 * UI_MARGIN;

    /* Show something while a long book is being paginated for the first
     * time, then a full refresh so the partial progress bars have a base.
     * In quiet mode (deep-sleep wake path) nothing is drawn here: the panel
     * still shows the sleep screen and the page appears directly. */
    if (!s_quiet) {
        if (s_screen != SCR_SPLASH) {
            /* Coming from the library or the reader: put the splash up and
             * give the partial progress bars a base to draw on. */
            uiShowSplash(t(S_PAGINATING), 0);
            s_redraw = false;
            renderSplash();
            epdFullRefresh();
        } else {
            /* Cold boot already shows the splash: just relabel it. */
            strncpy(s_splash_sub, t(S_PAGINATING), sizeof(s_splash_sub) - 1);
            s_splash_progress = 0;
            s_redraw = false;
        }
    } else {
        s_redraw = false;
    }

    if (!s_book.paginate(lines > 0 ? lines : 1, max_w, scale,
                         s_quiet ? nullptr : paginateProgress, nullptr)) {
        s_book.close();
        uiShowError(S_ERROR_BOOK_PARSE, S_ERROR_BOOK_PARSE);
        return false;
    }

    s_book_index = index;
    s_page = page;
    if (s_page >= s_book.pageCount()) s_page = s_book.pageCount() - 1;
    if (s_page < 0) s_page = 0;

    s_screen = SCR_READER;
    markRedraw(true);
    return true;
}

void uiCloseBook() {
    s_book.close();
    s_book_index = -1;
    s_page = 0;
}

void uiSavePosition(Settings* settings) {
    if (!settings) return;
    settings->last_book_index = (int16_t)(s_book_index < 0 ? 0 : s_book_index);
    settings->last_page = (int32_t)s_page;
}

void uiShowWifi() { s_screen = SCR_WIFI; markRedraw(true); }
void uiLeaveWifi() { uiShowLibrary(); }

void uiShowLibrary() {
    if (!s_books.empty() && s_lib_index >= (int)s_books.size())
        s_lib_index = (int)s_books.size() - 1;
    s_screen = SCR_LIBRARY;
    markRedraw(true);
}

void uiShowSleepScreen(bool low_battery) {
    s_low_battery = low_battery;
    s_screen = SCR_SLEEP;
    markRedraw(true);
}

void uiRequestRedraw(bool full) { markRedraw(full); }

void uiSetQuiet(bool quiet) { s_quiet = quiet; }

void uiHandleEvent(ButtonEvent e) {
    if (!s_font_ok) return;

    switch (s_screen) {
        case SCR_LIBRARY: {
            if (e == BTN_UP && s_lib_index > 0) { s_lib_index--; markRedraw(false); }
            else if (e == BTN_DOWN && s_lib_index + 1 < (int)s_books.size()) {
                s_lib_index++; markRedraw(false);
            } else if (e == BTN_MENU && !s_books.empty()) {
                uiOpenBook(s_lib_index, 0);
            } else if (e == BTN_MENU_LONG) {
                s_menu_index = 0;
                s_menu_confirm_delete = false;
                s_screen = SCR_MENU;
                markRedraw(true);
            }
            break;
        }

        case SCR_READER: {
            if (e == BTN_UP && s_page > 0) { s_page--; markRedraw(false); }
            else if (e == BTN_DOWN && s_page + 1 < s_book.pageCount()) {
                s_page++; markRedraw(false);
            } else if (e == BTN_MENU || e == BTN_MENU_LONG) {
                s_menu_index = 0;
                s_menu_confirm_delete = false;
                s_screen = SCR_MENU;
                markRedraw(true);
            }
            break;
        }

        case SCR_MENU: {
            const int rows = s_menu_confirm_delete ? 2 : (int)MI_COUNT;
            if (e == BTN_UP) {
                s_menu_index = (s_menu_index + rows - 1) % rows;
                markRedraw(false);
            } else if (e == BTN_DOWN) {
                s_menu_index = (s_menu_index + 1) % rows;
                markRedraw(false);
            } else if (e == BTN_MENU || e == BTN_MENU_LONG) {
                handleMenuSelect();
            }
            break;
        }

        case SCR_WIFI: {
            if (e == BTN_MENU || e == BTN_MENU_LONG) {
                s_screen = SCR_LIBRARY;
                markRedraw(true);
            }
            break;
        }

        case SCR_INFO: {
            if (e != BTN_NONE) { s_screen = SCR_LIBRARY; markRedraw(true); }
            break;
        }

        case SCR_ERROR:
        case SCR_SPLASH:
        case SCR_SLEEP:
        default:
            break;
    }
}

bool uiHandleWake(uint8_t held_mask) {
    /* Coming back from deep sleep: act immediately on the button that woke the
     * device, without a splash screen. */
    if (rtcState.screen_before_sleep == SCR_READER && s_book.isOpen()) {
        if (held_mask & BTN_MASK_DOWN) {
            if (s_page + 1 < s_book.pageCount()) s_page++;
        } else if (held_mask & BTN_MASK_UP) {
            if (s_page > 0) s_page--;
        } else {
            return false;
        }
        s_screen = SCR_READER;
        markRedraw(true);
        return true;
    }

    if (rtcState.screen_before_sleep == SCR_LIBRARY) {
        if (held_mask & BTN_MASK_DOWN) {
            if (s_lib_index + 1 < (int)s_books.size()) s_lib_index++;
        } else if (held_mask & BTN_MASK_UP) {
            if (s_lib_index > 0) s_lib_index--;
        } else {
            return false;
        }
        s_screen = SCR_LIBRARY;
        markRedraw(true);
        return true;
    }

    return false;
}
