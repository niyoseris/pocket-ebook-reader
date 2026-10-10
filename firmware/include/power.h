#pragma once
#include <Arduino.h>
#include "config.h"

/*
 * power.h -- battery measurement, deep sleep and the RTC-resident state that
 * survives a deep sleep.
 *
 * Battery: 100k/100k divider on VBAT_ADC (GPIO5 = ADC2_CH0 on the ESP32-C3),
 * so the real cell voltage is exactly twice what the pin sees. The divider
 * leaks ~21 uA at 4.2 V permanently; that is the price of not needing a
 * MOSFET gate on the divider.
 *
 * Note on ADC2: unlike the classic ESP32, the ESP32-C3's ADC2 has a single
 * channel and is NOT taken over by the WiFi driver, so it stays readable in
 * transfer mode.
 */

#define RTC_MAGIC   0x504B5452u   /* "PKTR" */

struct RtcState {
    uint32_t magic;
    uint32_t boot_count;
    int16_t  last_book_index;
    int16_t  last_page;
    uint8_t  was_deep_sleep;
    uint8_t  screen_before_sleep;   /* ScreenId, kept as a byte */
    uint8_t  low_battery;           /* 1 = button wake disabled */
    uint8_t  reserved[5];
};

/* Lives in RTC slow memory: zeroed on a cold boot, preserved across deep
 * sleep.
 *
 * The RTC_DATA_ATTR attribute is deliberately only on the DEFINITION in
 * power.cpp. RTC_DATA_ATTR expands to a __COUNTER__-suffixed section name, so
 * putting it on both the declaration and the definition would give the two
 * different section names and the compiler would complain about the conflict. */
extern RtcState rtcState;

void powerInit();

/* Refresh the cached reading if it is older than `POWER_CACHE_MS`. */
void powerUpdate();

float    batteryVoltage();      /* volts, e.g. 3.87 */
uint16_t batteryMilliVolts();   /* millivolts, e.g. 3870 */
uint8_t  batteryPercent();      /* 0..100 */
bool     batteryIsLow();        /* below BATTERY_LOW_MV */

/* Which buttons caused the wake-up (BTN_MASK_* bits); 0 if not an ext1 wake. */
uint8_t  powerWakeMask();
uint32_t powerUptimeSeconds();

/* Draw the sleep screen *before* calling this: the panel keeps whatever is on
 * it, and epdSleep() drops the panel to ~1 uA.
 *
 * `wake_mask` is BTN_WAKE_MASK normally. When the battery is critically low
 * the mask is ignored and the device arms a 1-hour timer instead, so a flat
 * cell cannot be drained by accidental wake-ups. This function never
 * returns. */
void enterDeepSleep(uint64_t wake_mask = BTN_WAKE_MASK) __attribute__((noreturn));
