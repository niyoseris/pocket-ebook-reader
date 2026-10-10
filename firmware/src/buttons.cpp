/*
 * buttons.cpp -- debounce + short/long press detection.
 */

#include "buttons.h"
#include "esp_sleep.h"

namespace {

struct BtnState {
    uint8_t  pin;
    bool     raw;           /* most recent raw reading (true = pressed) */
    bool     stable;        /* debounced state */
    bool     long_sent;
    uint32_t last_edge;
    uint32_t press_start;
};

BtnState g_btns[3] = {
    { EV_UP,   false, false, false, 0, 0 },
    { EV_DOWN, false, false, false, 0, 0 },
    { EV_MENU, false, false, false, 0, 0 },
};

const ButtonEvent kShortEvent[3] = { EV_UP,  EV_DOWN,  EV_MENU };
const ButtonEvent kLongEvent[3]  = { EV_UP_LONG, EV_DOWN_LONG, EV_MENU_LONG };

uint16_t g_pending = 0;   /* queued events, drained by buttonsPoll() */

}  /* namespace */

void buttonsInit() {
    for (uint8_t i = 0; i < 3; i++) {
        /* The board has 100k external pull-ups; the internal pull-up is a
         * harmless parallel safety net for breadboards built without them
         * (and it also defines the level on the GPIO2 strapping pin). */
        pinMode(g_btns[i].pin, INPUT_PULLUP);
        const bool pressed = (digitalRead(g_btns[i].pin) == LOW);
        g_btns[i].raw = pressed;
        g_btns[i].stable = pressed;
        g_btns[i].long_sent = false;
        g_btns[i].last_edge = millis();
        g_btns[i].press_start = millis();
    }
}

uint8_t buttonsHeldMask() {
    uint8_t mask = 0;
    if (digitalRead(BTN_UP)   == LOW) mask |= BTN_MASK_UP;
    if (digitalRead(BTN_DOWN) == LOW) mask |= BTN_MASK_DOWN;
    if (digitalRead(BTN_MENU) == LOW) mask |= BTN_MASK_MENU;
    return mask;
}

ButtonEvent buttonsWakeEvent(uint8_t* held_mask) {
    if (held_mask) *held_mask = 0;

    const esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    if (cause != ESP_SLEEP_WAKEUP_EXT1 && cause != ESP_SLEEP_WAKEUP_TIMER) {
        return EV_NONE;                 /* ordinary power-on reset */
    }

    /* Give the pads a moment to settle: the RTC pull-ups only just came back
     * up, and a finger is usually still on the key that woke the device. */
    delay(5);

    const uint8_t mask = buttonsHeldMask();
    if (held_mask) *held_mask = mask;
    return mask ? EV_ANY_WAKE : EV_NONE;
}

uint16_t buttonsPollRaw() {
    const uint32_t now = millis();
    uint16_t events = 0;

    for (uint8_t i = 0; i < 3; i++) {
        BtnState& b = g_btns[i];

        const bool pressed = (digitalRead(b.pin) == LOW);
        if (pressed != b.raw) {          /* edge: restart the debounce window */
            b.raw = pressed;
            b.last_edge = now;
        }

        if (b.stable != b.raw && (now - b.last_edge) >= BTN_DEBOUNCE_MS) {
            b.stable = b.raw;
            if (b.stable) {
                b.press_start = now;
                b.long_sent = false;
            } else if (!b.long_sent) {
                events |= (1u << kShortEvent[i]);   /* released, was a short press */
            }
        }

        if (b.stable && !b.long_sent && (now - b.press_start) >= BTN_LONG_MS) {
            b.long_sent = true;
            events |= (1u << kLongEvent[i]);
        }
    }

    g_pending |= events;
    return events;
}

/* Preference order when several events are queued at once: long presses
 * first (they are deliberate), then MENU, then the page keys. */
static const ButtonEvent kPriority[] = {
    EV_MENU_LONG, EV_UP_LONG, EV_DOWN_LONG, EV_MENU, EV_UP, EV_DOWN
};

ButtonEvent buttonsPoll() {
    buttonsPollRaw();                    /* always refresh the button states */
    for (uint8_t i = 0; i < sizeof(kPriority) / sizeof(kPriority[0]); i++) {
        const ButtonEvent e = kPriority[i];
        if (g_pending & (1u << e)) {
            g_pending &= (uint16_t)~(1u << e);
            return e;
        }
    }
    return EV_NONE;
}

const char* buttonEventName(ButtonEvent e) {
    switch (e) {
        case EV_NONE:       return "NONE";
        case EV_UP:         return "UP";
        case EV_DOWN:       return "DOWN";
        case EV_MENU:       return "MENU";
        case EV_MENU_LONG:  return "MENU_LONG";
        case EV_UP_LONG:    return "UP_LONG";
        case EV_DOWN_LONG:  return "DOWN_LONG";
        case EV_ANY_WAKE:   return "ANY_WAKE";
        default:             return "?";
    }
}
