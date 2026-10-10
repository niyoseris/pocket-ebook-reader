#pragma once
#include <Arduino.h>
#include "epd.h"
#include "book.h"
#include "buttons.h"
#include "storage.h"
#include "i18n.h"

/*
 * ui.h -- screens, input handling and the flush policy.
 *
 * Screens: SPLASH, LIBRARY, READER, MENU (overlay), WIFI, ERROR, INFO, SLEEP.
 *
 * Flush policy (decided by main.cpp, which owns the settings):
 *   screen change      -> full refresh
 *   page turn          -> partial refresh of the content area
 *   every N partials   -> full refresh, to clear ghosting
 * The UI is told which one is about to happen so the status bar can show the
 * truth for the frame being drawn.
 */

enum ScreenId : uint8_t {
    SCR_SPLASH = 0,
    SCR_LIBRARY,
    SCR_READER,
    SCR_MENU,
    SCR_WIFI,
    SCR_ERROR,
    SCR_INFO,
    SCR_SLEEP
};

enum RefreshKind : uint8_t {
    REFRESH_FULL = 0,
    REFRESH_PARTIAL = 1
};

/* Bind the canvas, load the font and list the library. Returns false if there
 * is no usable font -- the caller should still run the loop so the on-screen
 * error can be shown. */
bool uiInit(const Settings* settings);
void uiSetSettings(const Settings* settings);

/* True if something needs repainting. `needs_full` receives whether the screen
 * changed (or the user asked) and a full refresh should be used. */
bool uiTakeRedraw(bool* needs_full);
/* Draw the current screen into the canvas and set the dirty rectangle. */
void uiRender();

/* Tell the UI which refresh is about to happen, before uiRender(). */
void uiSetRefreshHint(RefreshKind kind);

ScreenId uiScreen();

/* Input. */
void uiHandleEvent(ButtonEvent e);

/* Deep-sleep wake-up handling: acts on the button that woke the device and
 * returns true if the caller should redraw and go straight back to sleep
 * (no splash, no library browse). */
bool uiHandleWake(uint8_t held_mask);

/* WIFI screen plumbing (the transfer module is owned by main.cpp). */
void uiShowWifi();
void uiLeaveWifi();

/* Book access. */
bool uiOpenBook(int index, int page);
void uiCloseBook();
bool uiHasBook();
int  uiBookIndex();
int  uiPage();
int  uiPageCount();
const char* uiBookTitle();

/* Library list (kept in RAM so the menu can delete from it). */
void uiReloadLibrary();
int  uiLibraryCount();

/* Splash / error helpers. progress < 0 hides the progress bar. */
void uiShowSplash(const char* subtitle, int progress);
void uiShowError(StrId line1, StrId line2);
void uiShowLibrary();
void uiShowSleepScreen(bool low_battery);

/* Ask for a repaint from outside the UI (e.g. the WiFi state changed). */
void uiRequestRedraw(bool full = false);

/* Quiet mode: used on the deep-sleep wake path so restoring the reader does
 * not flash a splash and a pair of full refreshes before the page appears. */
void uiSetQuiet(bool quiet);

/* Persist the reader position into `settings` (called by main before sleep). */
void uiSavePosition(Settings* settings);
