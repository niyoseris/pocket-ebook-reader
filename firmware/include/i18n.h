#pragma once
#include <stdint.h>
/*
 * i18n.h -- all user-visible strings.
 *
 * English is the default. Build with -DLANG_TR to get Turkish instead, by
 * adding -DLANG_TR to build_flags in platformio.ini.
 *
 * Everything is a table of `const char*` indexed by the StrId enum, so adding
 * a language means adding one more table below -- the rest of the firmware
 * only ever says t(S_LIBRARY).
 *
 * The table is selected at compile time, so switching language costs no RAM
 * and no code: only one of the two tables is linked in.
 *
 * The strings are UTF-8. The Turkish glyphs (c, g, i, I, o, s, u and their
 * capital/dotted forms) must exist in the .epf font file as their own
 * codepoints -- tools/fontgen.py adds them automatically when it can find them
 * in the source TTF.
 */

enum StrId : uint8_t {
    S_APP_NAME,
    S_SPLASH_HINT,

    S_LIBRARY_TITLE,
    S_LIBRARY_EMPTY,
    S_LIBRARY_EMPTY_HINT,

    S_READER_PAGE,
    S_BOOK_END,

    S_MENU_TITLE,
    S_MENU_FONT_SIZE,
    S_MENU_FULL_REFRESH,
    S_MENU_SLEEP,
    S_MENU_WIFI,
    S_MENU_DELETE,
    S_MENU_ABOUT,
    S_MENU_BACK,
    S_MENU_DELETE_CONFIRM,

    S_ON,
    S_OFF,
    S_SECONDS,
    S_SCALE_X1,
    S_SCALE_X2,

    S_WIFI_TITLE,
    S_WIFI_STA_CONNECTING,
    S_WIFI_AP_MODE,
    S_WIFI_NETWORK,
    S_WIFI_PASSWORD,
    S_WIFI_ADDRESS,
    S_WIFI_EXIT_HINT,
    S_WIFI_HINT_1,
    S_WIFI_HINT_2,

    S_ABOUT_TITLE,
    S_ABOUT_L1,
    S_ABOUT_L2,
    S_ABOUT_L3,

    S_ERROR_TITLE,
    S_ERROR_NO_FONT,
    S_ERROR_NO_FONT_HINT,
    S_ERROR_NO_FS,
    S_ERROR_NO_BOOK,
    S_ERROR_BOOK_PARSE,

    S_SLEEP_TITLE,
    S_SLEEP_HINT,

    S_BATTERY_LOW,
    S_BATTERY_LOW_HINT,

    S_PAGINATING,
    S_BOOTING,

    S_YES,
    S_NO,

    S_STR_COUNT
};

#ifndef LANG_TR          /* English is the default; -DLANG_TR selects Turkish */

static const char* const STR_TABLE[S_STR_COUNT] = {
    "Pocket Reader",
    "READY",

    "LIBRARY",
    "No books",
    "Upload books over WiFi",

    "Page",
    "End of book",

    "MENU",
    "Font size",
    "Full refresh",
    "Sleep delay",
    "WiFi transfer",
    "Delete book",
    "About",
    "Back",
    "Delete this book?",

    "On",
    "Off",
    "s",
    "x1",
    "x2",

    "WIFI TRANSFER",
    "Connecting to",
    "Access point",
    "Network",
    "Password",
    "Address",
    "MENU = exit",
    "Open the address in a browser",
    "and drop an .epr file in",

    "ABOUT",
    "Pocket Reader",
    "Open source e-ink reader",
    "ESP32-C3 / SSD1680",

    "ERROR",
    "No font found",
    "Run tools/fontgen.py, then upload",
    "Filesystem mount failed",
    "No book selected",
    "Corrupt .epr file",

    "SLEEP",
    "Press a key",

    "Low battery",
    "Charge the device",

    "Paginating",
    "Starting up",

    "Yes",
    "No",
};

#else  /* Turkish (-DLANG_TR) */

static const char* const STR_TABLE[S_STR_COUNT] = {
    "Pocket Reader",
    "HAZIR",

    "KÜTÜPHANE",
    "Kitap yok",
    "WiFi ile kitap yükleyin",

    "Sayfa",
    "Kitabın sonu",

    "MENÜ",
    "Yazı boyutu",
    "Tam yenileme",
    "Uyku süresi",
    "WiFi aktarım",
    "Kitabı sil",
    "Hakkında",
    "Geri",
    "Kitap silinsin mi?",

    "Açık",
    "Kapalı",
    "sn",
    "x1",
    "x2",

    "WiFi AKTARIM",
    "Bağlanıyor",
    "Erişim noktası",
    "Ağ adı",
    "Şifre",
    "Adres",
    "MENÜ = çıkış",
    "Tarayıcıda adresi açın",
    "ve .epr dosyasını bırakın",

    "HAKKINDA",
    "Pocket Reader",
    "Açık kaynak e-mürekkep okuyucu",
    "ESP32-C3 / SSD1680",

    "HATA",
    "Font bulunamadı",
    "tools/fontgen.py çalıştırıp yükleyin",
    "Dosya sistemi bağlanamadı",
    "Kitap seçili değil",
    "Bozuk .epr dosyası",

    "UYKU",
    "Bir tuşa basın",

    "Pil zayıf",
    "Cihazı şarj edin",

    "Sayfalanıyor",
    "Başlatılıyor",

    "Evet",
    "Hayır",
};

#endif /* !LANG_TR */

/* Convenience accessor. */
static inline const char* t(StrId id) {
    return (id < S_STR_COUNT) ? STR_TABLE[id] : "";
}
