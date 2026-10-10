/*
 * main.cpp -- Pocket Reader
 *
 * Boot paths
 * ----------
 *  COLD BOOT: storage -> buttons -> power -> panel -> font -> splash ->
 *             last book (or the library).
 *
 *  DEEP-SLEEP WAKE: this is the important UX detail. The device does NOT show
 *             a splash and does NOT boot into the library. It restores the
 *             book silently, looks at which button woke it, performs that one
 *             action (next page / previous page / library cursor) and goes
 *             straight back to sleep. Opening the cover and pressing DOWN
 *             gives you the next page in about a second, with no UI noise.
 *
 * Flush policy (see ui.h): screen change = full refresh, page turn = partial
 * refresh, and a full refresh every `full_refresh_every` partials to clear
 * ghosting.
 */

#include <Arduino.h>
#include "config.h"
#include "epd.h"
#include "font.h"
#include "book.h"
#include "buttons.h"
#include "power.h"
#include "storage.h"
#include "ui.h"
#include "wifi_xfer.h"
#include "i18n.h"
#include "esp_sleep.h"

static Settings      g_settings;
static uint32_t      g_last_activity = 0;
static uint16_t      g_partials = 0;
static WifiXferState g_last_wifi_state = WIFI_XFER_OFF;

/* --------------------------------------------------------------------------
 *  Repaint
 * ------------------------------------------------------------------------ */
static void doRedraw() {
    bool full = false;
    if (!uiTakeRedraw(&full)) return;

    RefreshKind kind;
    if (full || !g_settings.partial_enabled) {
        kind = REFRESH_FULL;
    } else if (g_partials >= g_settings.full_refresh_every) {
        /* Ghosting sweep: enough partials have accumulated. */
        kind = REFRESH_FULL;
    } else {
        kind = REFRESH_PARTIAL;
    }

    /* Tell the UI which refresh this frame gets, so the status bar shows the
     * truth for the frame it is drawing. */
    uiSetRefreshHint(kind);
    uiRender();

    if (kind == REFRESH_FULL) {
        epdFullRefresh();
        g_partials = 0;
    } else {
        epdPartialRefresh();
        g_partials++;
    }
}

/* --------------------------------------------------------------------------
 *  Sleep
 * ------------------------------------------------------------------------ */
static void goToSleep() {
    const bool low = batteryIsLow();

    /* What the wake-up gesture should act on. Menu / WiFi / splash all fall
     * back to the reader or the library, so a wake never restores a modal. */
    ScreenId before = uiScreen();
    if (before == SCR_SLEEP || before == SCR_WIFI ||
        before == SCR_MENU  || before == SCR_SPLASH) {
        before = uiHasBook() ? SCR_READER : SCR_LIBRARY;
    }

    rtcState.screen_before_sleep = (uint8_t)before;
    rtcState.last_book_index = (int16_t)(uiBookIndex() < 0 ? 0 : uiBookIndex());
    rtcState.last_page = (int16_t)uiPage();
    rtcState.low_battery = low ? 1 : 0;

    uiSavePosition(&g_settings);
    storageSaveSettings(&g_settings);

    Serial.printf("[main] sleeping: screen=%u book=%d page=%d low=%d\n",
                  (unsigned)before, (int)rtcState.last_book_index,
                  (int)rtcState.last_page, (int)low);

    /* Put an image on the panel before powering it down -- e-ink keeps it. */
    uiShowSleepScreen(low);
    bool dummy = false;
    uiTakeRedraw(&dummy);
    uiRender();
    epdFullRefresh();

    /* Radio off, then deep sleep (never returns). */
    wifiXferStop();
    enterDeepSleep(BTN_WAKE_MASK);
}

/* --------------------------------------------------------------------------
 *  setup
 * ------------------------------------------------------------------------ */
void setup() {
    /* No while(!Serial) loop: on the ESP32-C3 the USB-CDC port only exists
     * when a host is attached, and waiting for it would hang a battery boot. */
    Serial.begin(115200);
    delay(60);
    Serial.printf("\n\n=== Pocket Reader %s ===\n", POCKET_READER_VERSION);

    if (rtcState.magic != RTC_MAGIC) {
        memset(&rtcState, 0, sizeof(rtcState));
        rtcState.magic = RTC_MAGIC;
    }
    rtcState.boot_count++;

    const bool woke = (rtcState.was_deep_sleep != 0);
    rtcState.was_deep_sleep = 0;
    const esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    Serial.printf("[main] boot #%u, wake cause %d, from sleep: %d\n",
                  (unsigned)rtcState.boot_count, (int)cause, (int)woke);

    if (!storageInit()) {
        Serial.println("[main] no filesystem -- showing an error");
    }
    buttonsInit();
    powerInit();
    epdInit();

    storageLoadSettings(&g_settings);
    /* The RTC copy is authoritative after a sleep (NVS writes are skipped on
     * the fast path). */
    g_settings.last_book_index = rtcState.last_book_index;
    g_settings.last_page = rtcState.last_page;

    const bool font_ok = uiInit(&g_settings);
    uiReloadLibrary();

    g_last_activity = millis();
    g_partials = 0;

    if (!storageMounted()) {
        uiShowError(S_ERROR_NO_FS, S_ERROR_NO_FONT_HINT);
        doRedraw();
        return;
    }

    if (!font_ok) {
        Serial.println("[main] no font -- error screen (buttons still polled)");
        uiShowError(S_ERROR_NO_FONT, S_ERROR_NO_FONT_HINT);
        doRedraw();
        return;
    }

    if (woke) {
        /* ---- DEEP-SLEEP WAKE PATH: no splash, act immediately ---- */
        uint8_t held = 0;
        const ButtonEvent wake_ev = buttonsWakeEvent(&held);
        if (wake_ev == BTN_ANY_WAKE) {
            Serial.printf("[main] BTN_ANY_WAKE, gesture mask 0x%02X\n", (unsigned)held);
        } else {
            Serial.println("[main] woke with no button held");
        }

        if (batteryIsLow() && rtcState.low_battery) {
            /* Still flat: show the warning again and go back to a timer
             * sleep. The buttons stay disarmed so a bag cannot drain it. */
            uiShowSleepScreen(true);
            doRedraw();
            enterDeepSleep(0);
        }

        /* Restore silently -- the page index cache makes this fast. */
        uiSetQuiet(true);
        if (rtcState.last_book_index >= 0 &&
            rtcState.last_book_index < uiLibraryCount()) {
            uiOpenBook(rtcState.last_book_index, rtcState.last_page);
        }
        uiSetQuiet(false);

        if (uiHandleWake(held)) {
            doRedraw();

            uiSavePosition(&g_settings);
            rtcState.screen_before_sleep = (uint8_t)uiScreen();
            rtcState.last_book_index = (int16_t)(uiBookIndex() < 0 ? 0 : uiBookIndex());
            rtcState.last_page = (int16_t)uiPage();
            rtcState.low_battery = batteryIsLow() ? 1 : 0;
            storageSaveSettings(&g_settings);

            wifiXferStop();
            enterDeepSleep(BTN_WAKE_MASK);
        }
        /* The gesture did not map to an action: fall through to a normal
         * boot so the user is never stuck on a dead panel. */
        Serial.println("[main] wake gesture unhandled -> normal boot");
    }

    /* ---- COLD BOOT: splash, then back to where we were ---- */
    uiShowSplash(nullptr, -1);
    doRedraw();

    const int idx = g_settings.last_book_index;
    if (idx >= 0 && idx < uiLibraryCount() && g_settings.last_page > 0) {
        if (!uiOpenBook(idx, (int)g_settings.last_page)) uiShowLibrary();
    } else {
        uiShowLibrary();
    }
    doRedraw();
}

/* --------------------------------------------------------------------------
 *  loop
 * ------------------------------------------------------------------------ */
void loop() {
    /* ---- WiFi transfer mode ---- */
    if (uiScreen() == SCR_WIFI) {
        if (!wifiXferActive()) wifiXferBegin();
        wifiXferLoop();

        const WifiXferState st = wifiXferState();
        if (st != g_last_wifi_state) {
            g_last_wifi_state = st;
            uiRequestRedraw();
        }

        /* The browser can add or delete books behind our back; keep the
         * library list in sync so leaving transfer mode shows the truth. */
        static uint32_t last_ops = 0;
        if (wifiXferBookCount() != last_ops) {
            last_ops = wifiXferBookCount();
            uiReloadLibrary();
            uiRequestRedraw();
        }
    } else if (wifiXferActive()) {
        wifiXferStop();
        g_last_wifi_state = WIFI_XFER_OFF;
    }

    /* ---- buttons (drain a few events per pass so nothing is lost) ---- */
    for (int i = 0; i < 4; i++) {
        const ButtonEvent e = buttonsPoll();
        if (e == BTN_NONE) break;
        g_last_activity = millis();
        Serial.printf("[main] event %s\n", buttonEventName(e));
        uiHandleEvent(e);
    }

    /* ---- repaint ---- */
    doRedraw();

    /* ---- idle timeout -> deep sleep (never during a transfer) ---- */
    if (g_settings.sleep_sec > 0 && uiScreen() != SCR_WIFI &&
        (uint32_t)(millis() - g_last_activity) > (uint32_t)g_settings.sleep_sec * 1000UL) {
        goToSleep();
    }

    /* Nothing to do: yield. delay() lets the idle task, the WiFi task and the
     * task watchdog run; the loop never spins on a register. */
    delay(10);
}
