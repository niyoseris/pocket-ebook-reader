#pragma once
#include <Arduino.h>
#include "config.h"

/*
 * buttons.h -- three active-LOW buttons with software debounce.
 *
 * Timing: 25 ms debounce, a long press fires once at 700 ms while the button
 * is still held (so the UI can show feedback), and releasing after a long
 * press does NOT also produce a short press.
 *
 * Note the two distinct naming spaces: BTN_UP / BTN_DOWN / BTN_MENU are the
 * PIN macros from config.h, while EV_UP / EV_DOWN / EV_MENU are the events this
 * module reports. They must not share names -- the preprocessor would rewrite
 * the enum members and the file would not compile.
 *
 * BTN_MENU lives on GPIO20, which is not in the RTC domain, so the MENU key can
 * never appear as a wake source -- see config.h.
 */

enum ButtonEvent : uint8_t {
    EV_NONE = 0,
    EV_UP,
    EV_DOWN,
    EV_MENU,
    EV_MENU_LONG,
    EV_UP_LONG,
    EV_DOWN_LONG,
    EV_ANY_WAKE
};

/* Bit indices for buttonsHeldMask(). */
#define BTN_MASK_UP    (1u << 0)
#define BTN_MASK_DOWN  (1u << 1)
#define BTN_MASK_MENU  (1u << 2)

#define BTN_DEBOUNCE_MS  25
#define BTN_LONG_MS      700

void buttonsInit();

/* Returns the first event that happened since the last call, or EV_NONE.
 * Call it often (the main loop does) -- it is non-blocking. */
ButtonEvent buttonsPoll();

/* Which buttons are physically held right now. Used immediately after a deep
 * sleep wake to decide what the user meant. */
uint8_t buttonsHeldMask();

/* If this boot came from a deep-sleep wake with at least one button held,
 * returns EV_ANY_WAKE and fills `held_mask` with BTN_MASK_* bits; otherwise
 * returns EV_NONE. This is the only way EV_ANY_WAKE is ever produced -- it
 * cannot come out of the polling loop, because it is a property of the wake-up
 * itself, not of a button edge. */
ButtonEvent buttonsWakeEvent(uint8_t* held_mask = nullptr);

/* All events that were generated since the last call, OR-ed together as a set
 * of ButtonEvent bits. main.cpp uses this so a wake-up gesture that presses
 * UP and DOWN together is not lost. */
uint16_t buttonsPollRaw();

const char* buttonEventName(ButtonEvent e);
