/*
 * storage.cpp -- LittleFS + NVS.
 */

#include "storage.h"
#include <LittleFS.h>
#include <Preferences.h>
#include <algorithm>
#include <string.h>

#define NVS_NAMESPACE   "pocketrdr"
/* NVS keys: 15 characters max. */
#define K_FONT_SCALE    "font_scale"
#define K_SLEEP_SEC     "sleep_sec"
#define K_FULLREFRESH   "fullref_every"
#define K_LAST_BOOK     "last_book"
#define K_LAST_PAGE     "last_page"
#define K_WIFI_SSID     "wifi_ssid"
#define K_WIFI_PASS     "wifi_pass"
#define K_PARTIAL       "partial_enabled"

static bool s_mounted = false;

bool storageMounted() { return s_mounted; }

bool storageInit() {
    Serial.printf("[fs] mounting LittleFS at %s\n", FS_MOUNT_POINT);

    /* Try a plain mount first; only format when the partition has never been
     * written (first boot) or is corrupt. */
    s_mounted = LittleFS.begin(false, FS_MOUNT_POINT, 10, "littlefs");
    if (!s_mounted) {
        Serial.println("[fs] mount failed, formatting...");
        s_mounted = LittleFS.begin(true, FS_MOUNT_POINT, 10, "littlefs");
    }
    if (!s_mounted) {
        Serial.println("[fs] LittleFS unavailable");
        return false;
    }

    const char* dirs[] = { BOOKS_DIR, FONT_DIR, CACHE_DIR };
    for (const char* d : dirs) {
        if (!LittleFS.exists(d)) {
            if (LittleFS.mkdir(d)) Serial.printf("[fs] created %s\n", d);
            else                   Serial.printf("[fs] cannot create %s\n", d);
        }
    }

    uint32_t total = 0, used = 0;
    storageSpace(&total, &used);
    Serial.printf("[fs] %u/%u bytes used\n", (unsigned)used, (unsigned)total);
    return true;
}

void storageSpace(uint32_t* total, uint32_t* used) {
    if (total) *total = s_mounted ? LittleFS.totalBytes()   : 0;
    if (used)  *used  = s_mounted ? LittleFS.usedBytes()    : 0;
}

bool storageExists(const char* path) {
    return s_mounted && path && LittleFS.exists(path);
}

static String baseName(const String& path) {
    const int slash = path.lastIndexOf('/');
    return (slash >= 0) ? path.substring(slash + 1) : path;
}

/* Case-insensitive compare, hand-rolled so we do not depend on strcasecmp
 * being declared by <string.h> on every newlib flavour. */
static int nocaseCompare(const char* a, const char* b) {
    while (*a && *b) {
        const int ca = tolower((unsigned char)*a);
        const int cb = tolower((unsigned char)*b);
        if (ca != cb) return ca - cb;
        a++;
        b++;
    }
    return (unsigned char)*a - (unsigned char)*b;
}

std::vector<BookEntry> storageListBooks() {
    std::vector<BookEntry> out;
    if (!s_mounted) return out;

    File dir = LittleFS.open(BOOKS_DIR);
    if (!dir || !dir.isDirectory()) {
        Serial.println("[fs] /books missing");
        return out;
    }

    File f = dir.openNextFile();
    while (f) {
        const String name = baseName(String(f.name()));
        if (!f.isDirectory() && name.endsWith(".epr")) {
            BookEntry e;
            e.path = String(BOOKS_DIR) + "/" + name;
            e.name = name;
            e.size = f.size();

            /* Pull the title/author straight out of the .epr header. */
            BookMeta meta;
            memset(&meta, 0, sizeof(meta));
            if (bookReadMeta(e.path.c_str(), &meta)) {
                e.title = meta.title;
                e.author = meta.author;
            } else {
                e.title = name;
                e.author = "?";
            }
            out.push_back(e);
        }
        f = dir.openNextFile();
    }
    dir.close();

    std::sort(out.begin(), out.end(), [](const BookEntry& a, const BookEntry& b) {
        return nocaseCompare(a.title.c_str(), b.title.c_str()) < 0;
    });

    Serial.printf("[fs] %u books\n", (unsigned)out.size());
    return out;
}

bool storageDeleteBook(const char* path) {
    if (!s_mounted || !path || !*path) return false;

    /* Never let a caller escape /books. */
    if (strncmp(path, BOOKS_DIR, strlen(BOOKS_DIR)) != 0) return false;
    if (strstr(path, "..")) return false;

    if (!LittleFS.exists(path)) return false;
    if (!LittleFS.remove(path)) {
        Serial.printf("[fs] remove failed: %s\n", path);
        return false;
    }
    Serial.printf("[fs] removed %s\n", path);
    return true;
}

bool storageRenameBook(const char* path, const char* new_name) {
    if (!s_mounted || !path || !new_name || !*new_name) return false;
    if (!LittleFS.exists(path)) return false;

    /* The new name is a bare file name: no path separators, no "..". */
    if (strchr(new_name, '/') || strstr(new_name, "..")) return false;

    String dest = String(BOOKS_DIR) + "/" + new_name;
    if (LittleFS.exists(dest.c_str())) return false;

    if (LittleFS.rename(path, dest.c_str())) {
        Serial.printf("[fs] renamed %s -> %s\n", path, dest.c_str());
        return true;
    }
    return false;
}

/* -------------------------------------------------------------------------- */

void storageLoadSettings(Settings* s) {
    if (!s) return;

    s->font_scale         = DEF_FONT_SCALE;
    s->sleep_sec          = DEF_SLEEP_SEC;
    s->full_refresh_every = DEF_FULL_REFRESH_EVERY;
    s->last_book_index    = 0;
    s->last_page          = 0;
    s->wifi_ssid          = "";
    s->wifi_pass          = "";
    s->partial_enabled    = DEF_PARTIAL_ENABLED;

    if (!s_mounted) return;

    Preferences prefs;
    if (!prefs.begin(NVS_NAMESPACE, true /* read-only */)) {
        Serial.println("[nvs] open failed, using defaults");
        return;
    }

    s->font_scale         = prefs.getUChar(K_FONT_SCALE, DEF_FONT_SCALE);
    s->sleep_sec          = prefs.getUShort(K_SLEEP_SEC, DEF_SLEEP_SEC);
    s->full_refresh_every = prefs.getUShort(K_FULLREFRESH, DEF_FULL_REFRESH_EVERY);
    s->last_book_index    = prefs.getShort(K_LAST_BOOK, 0);
    s->last_page          = prefs.getInt(K_LAST_PAGE, 0);
    s->wifi_ssid          = prefs.getString(K_WIFI_SSID, "");
    s->wifi_pass          = prefs.getString(K_WIFI_PASS, "");
    s->partial_enabled    = prefs.getUChar(K_PARTIAL, DEF_PARTIAL_ENABLED);
    prefs.end();

    if (s->font_scale < 1 || s->font_scale > 2)      s->font_scale = DEF_FONT_SCALE;
    if (s->full_refresh_every < 1)                   s->full_refresh_every = DEF_FULL_REFRESH_EVERY;
    if (s->full_refresh_every > 1000)                s->full_refresh_every = 1000;
    if (s->sleep_sec > 3600)                         s->sleep_sec = 3600;

    Serial.printf("[nvs] scale=%u sleep=%us full=%u book=%d page=%d wifi=%s\n",
                  (unsigned)s->font_scale, (unsigned)s->sleep_sec,
                  (unsigned)s->full_refresh_every,
                  (int)s->last_book_index, (int)s->last_page,
                  s->wifi_ssid.length() ? s->wifi_ssid.c_str() : "(none)");
}

void storageSaveSettings(const Settings* s) {
    if (!s || !s_mounted) return;

    Preferences prefs;
    if (!prefs.begin(NVS_NAMESPACE, false)) return;

    prefs.putUChar(K_FONT_SCALE, s->font_scale);
    prefs.putUShort(K_SLEEP_SEC, s->sleep_sec);
    prefs.putUShort(K_FULLREFRESH, s->full_refresh_every);
    prefs.putShort(K_LAST_BOOK, s->last_book_index);
    prefs.putInt(K_LAST_PAGE, s->last_page);
    prefs.putUChar(K_PARTIAL, s->partial_enabled);
    prefs.end();
}

void storageSetWifi(const char* ssid, const char* pass) {
    if (!s_mounted) return;

    Preferences prefs;
    if (!prefs.begin(NVS_NAMESPACE, false)) return;
    prefs.putString(K_WIFI_SSID, ssid ? ssid : "");
    prefs.putString(K_WIFI_PASS, pass ? pass : "");
    prefs.end();
    Serial.printf("[nvs] wifi credentials saved (ssid=\"%s\")\n", ssid ? ssid : "");
}

void storageFormatSize(uint32_t bytes, char* buf, size_t buf_size) {
    if (!buf || buf_size == 0) return;
    if (bytes >= 1024u * 1024u) {
        snprintf(buf, buf_size, "%u.%u MB",
                 (unsigned)(bytes / (1024u * 1024u)),
                 (unsigned)((bytes % (1024u * 1024u)) / (1024u * 105u)));
    } else if (bytes >= 1024u) {
        snprintf(buf, buf_size, "%u KB", (unsigned)(bytes / 1024u));
    } else {
        snprintf(buf, buf_size, "%u B", (unsigned)bytes);
    }
}
