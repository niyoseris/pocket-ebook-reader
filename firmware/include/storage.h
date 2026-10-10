#pragma once
#include <Arduino.h>
#include <vector>
#include "config.h"
#include "book.h"

/*
 * storage.h -- LittleFS (books, fonts, cache) + Preferences/NVS (settings).
 *
 * NVS key names are limited to 15 characters, which is why the setting is
 * stored as "fullref_every" and not "full_refresh_every".
 */

struct BookEntry {
    String   path;        /* /books/foo.epr */
    String   name;        /* foo.epr */
    String   title;
    String   author;
    uint32_t size;
};

struct Settings {
    uint8_t  font_scale;           /* 1 or 2 */
    uint16_t sleep_sec;            /* idle timeout, 0 = never */
    uint16_t full_refresh_every;   /* partial refreshes before a full one */
    int16_t  last_book_index;
    int32_t  last_page;
    String   wifi_ssid;
    String   wifi_pass;
    uint8_t  partial_enabled;
};

/* Mounts LittleFS at FS_MOUNT_POINT (formatting on first boot if needed) and
 * creates /books, /fonts and /cache. */
bool storageInit();
bool storageMounted();

void storageSpace(uint32_t* total, uint32_t* used);

/* All .epr files in /books, sorted by title. */
std::vector<BookEntry> storageListBooks();

bool storageDeleteBook(const char* path);
bool storageRenameBook(const char* path, const char* new_name);
bool storageExists(const char* path);

/* Settings (NVS namespace "pocketrdr"). */
void storageLoadSettings(Settings* s);
void storageSaveSettings(const Settings* s);
void storageSetWifi(const char* ssid, const char* pass);

/* Human-readable byte size ("1.2 MB"). `buf` needs >= 12 bytes. */
void storageFormatSize(uint32_t bytes, char* buf, size_t buf_size);
