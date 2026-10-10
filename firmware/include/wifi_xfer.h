#pragma once
#include <Arduino.h>

/*
 * wifi_xfer.h -- book transfer over WiFi.
 *
 * Modes:
 *   1. STA: the credentials saved in NVS are tried for 15 s. If they connect,
 *      the server runs on the LAN address.
 *   2. AP fallback: "PocketReader-XXXX" (password "readbooks", XXXX from the
 *      MAC) with a captive-portal style DNS server.
 *
 * The radio is only ever up in transfer mode. wifiXferStop() powers WiFi down
 * completely before the device sleeps -- that is what keeps standby at ~5 uA.
 *
 * Endpoints:
 *   GET  /        upload page (Turkish, self-contained HTML)
 *   POST /upload  multipart file, or a raw body with an X-Filename header
 *   GET  /list    JSON array of books
 *   POST /delete  {"name":"foo.epr"}   (or a "name" form/query argument)
 *   POST /wifi    {"ssid":"..","pass":".."}
 *   GET  /status  JSON status
 */

enum WifiXferState : uint8_t {
    WIFI_XFER_OFF = 0,
    WIFI_XFER_CONNECTING,     /* trying the saved STA credentials */
    WIFI_XFER_AP,             /* access point running */
    WIFI_XFER_STA,            /* joined an existing network */
    WIFI_XFER_ERROR
};

void wifiXferBegin();
void wifiXferLoop();
bool wifiXferActive();
void wifiXferStop();

WifiXferState wifiXferState();
const char*   wifiXferStateText();
const char*   wifiXferSsid();
const char*   wifiXferPass();
const char*   wifiXferAddress();     /* IP as a string, "" if not up */

/* Number of books uploaded/deleted during this transfer session (the UI can
 * use it to know when to re-list). */
uint32_t wifiXferBookCount();
