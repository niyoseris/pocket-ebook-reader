/*
 * power.cpp -- battery ADC + deep sleep.
 */

#include "power.h"
#include "epd.h"
#include <WiFi.h>
#include "driver/rtc_io.h"
#include "esp_sleep.h"

/* ext1 wake mode naming across IDF versions:
 *   IDF 4.x calls mode 0 ESP_EXT1_WAKEUP_ALL_LOW
 *   IDF 5.x renamed it      ESP_EXT1_WAKEUP_ANY_LOW
 * On the ESP32-C3 the ext1 hardware only implements "wake when any of the
 * selected pins goes low", so the register value (0) and the behaviour are
 * identical -- the rename is cosmetic for this chip. Kept as an alias so the
 * call site reads ESP_EXT1_WAKEUP_ANY_LOW on both cores. */
#ifndef ESP_EXT1_WAKEUP_ANY_LOW
  #define ESP_EXT1_WAKEUP_ANY_LOW ESP_EXT1_WAKEUP_ALL_LOW
#endif

/* RTC_DATA_ATTR: zero-initialised on power-on reset, preserved across deep
 * sleep. The initialiser is only applied on a cold boot, which is exactly the
 * behaviour we want. */
RTC_DATA_ATTR RtcState rtcState = {};

#define POWER_CACHE_MS   30000   /* re-measure at most every 30 s */
#define POWER_SAMPLES    15      /* per round (median) */
#define POWER_ROUNDS     8       /* rounds averaged together */
#define LOW_RETRY_US     (3600ULL * 1000000ULL)   /* 1 hour */

static uint32_t s_last_measure = 0;
static uint16_t s_cached_mv = 0;
static bool     s_measured = false;

/* Li-ion discharge curve, 4.20 V .. 3.30 V -> 100 .. 0 %.
 * Flat in the middle on purpose: that is what the chemistry does. */
struct VPoint { uint16_t mv; uint8_t pct; };
static const VPoint kCurve[] = {
    { 4200, 100 }, { 4100, 90 }, { 4000, 80 }, { 3930, 70 },
    { 3870,  60 }, { 3820, 50 }, { 3790, 40 }, { 3770, 30 },
    { 3740,  20 }, { 3680, 10 }, { 3450,  5 }, { 3300,  0 },
};
static const int kCurveLen = sizeof(kCurve) / sizeof(kCurve[0]);

void powerInit() {
    /* 11 dB attenuation: full scale ~3.1 V at the pin, which is 6.2 V at the
     * battery -- well above the 4.2 V a Li-ion cell ever reaches. */
    analogSetPinAttenuation(VBAT_ADC, ADC_11db);
    pinMode(VBAT_ADC, INPUT);
    s_measured = false;
    s_last_measure = 0;
}

/* One round of 15 samples, reduced with an insertion-sorted median. */
static uint16_t readMedianMv() {
    uint16_t s[POWER_SAMPLES];
    for (int i = 0; i < POWER_SAMPLES; i++) {
        s[i] = (uint16_t)analogReadMilliVolts(VBAT_ADC);
        delayMicroseconds(300);
    }
    for (int i = 1; i < POWER_SAMPLES; i++) {      /* insertion sort */
        const uint16_t v = s[i];
        int j = i - 1;
        while (j >= 0 && s[j] > v) { s[j + 1] = s[j]; j--; }
        s[j + 1] = v;
    }
    return s[POWER_SAMPLES / 2];
}

void powerUpdate() {
    const uint32_t now = millis();
    if (s_measured && (now - s_last_measure) < POWER_CACHE_MS) return;

    uint32_t acc = 0;
    for (int r = 0; r < POWER_ROUNDS; r++) acc += readMedianMv();
    const uint32_t pin_mv = acc / POWER_ROUNDS;

    /* Undo the 100k/100k divider. */
    uint32_t batt_mv = pin_mv * 2;

    /* Sanity clamp: a divider that is not fitted reads nonsense. */
    if (batt_mv > 4400) batt_mv = 4400;

    s_cached_mv = (uint16_t)batt_mv;
    s_last_measure = now;
    s_measured = true;

    Serial.printf("[power] pin %umV -> battery %umV (%u%%)\n",
                  (unsigned)pin_mv, (unsigned)s_cached_mv, batteryPercent());
}

uint16_t batteryMilliVolts() {
    powerUpdate();
    return s_cached_mv;
}

float batteryVoltage() {
    return batteryMilliVolts() / 1000.0f;
}

uint8_t batteryPercent() {
    const uint16_t mv = s_cached_mv;
    if (mv >= kCurve[0].mv) return 100;
    if (mv <= kCurve[kCurveLen - 1].mv) return 0;

    for (int i = 0; i < kCurveLen - 1; i++) {
        if (mv <= kCurve[i].mv && mv >= kCurve[i + 1].mv) {
            const uint16_t hi = kCurve[i].mv;
            const uint16_t lo = kCurve[i + 1].mv;
            const uint8_t  hp = kCurve[i].pct;
            const uint8_t  lp = kCurve[i + 1].pct;
            const uint32_t num = (uint32_t)(mv - lo) * (hp - lp);
            return (uint8_t)(lp + num / (hi - lo));
        }
    }
    return 0;
}

bool batteryIsLow() {
    return batteryMilliVolts() < BATTERY_LOW_MV;
}

uint8_t powerWakeMask() {
    if (esp_sleep_get_wakeup_cause() != ESP_SLEEP_WAKEUP_EXT1) return 0;

    const uint64_t status = esp_sleep_get_ext1_wakeup_status();
    uint8_t mask = 0;
    if (status & (1ULL << BTN_UP))   mask |= BTN_MASK_UP;
    if (status & (1ULL << BTN_DOWN)) mask |= BTN_MASK_DOWN;
    if (status & (1ULL << BTN_MENU)) mask |= BTN_MASK_MENU;   /* never happens */
    return mask;
}

uint32_t powerUptimeSeconds() {
    return millis() / 1000;
}

void enterDeepSleep(uint64_t wake_mask) {
    rtcState.magic = RTC_MAGIC;
    rtcState.was_deep_sleep = 1;

    Serial.printf("[power] sleeping (boot #%u, book %d page %d)\n",
                  (unsigned)rtcState.boot_count,
                  (int)rtcState.last_book_index, (int)rtcState.last_page);
    Serial.flush();

    /* 1. Panel first: deep-sleep register, ~1 uA, image retained. */
    epdSleep();

    /* 2. Radio fully off. This is what keeps standby at ~5 uA -- an
     *    associated or even an idle WiFi stack would cost milliamps and
     *    flatten the cell in a day. */
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(50);

    const bool low = rtcState.low_battery != 0;

    if (low || wake_mask == 0) {
        /* Low battery: refuse to arm the buttons, so a pocket or a bag
         * cannot wake the device in a loop and drain what is left. Wake up
         * hourly to re-measure and to show the warning again. */
        Serial.println("[power] low battery -> timer wake only (button wake disabled)");
        esp_sleep_enable_timer_wakeup(LOW_RETRY_US);
    } else {
        /* esp_sleep_enable_ext1_wakeup() is the current IDF name for the
         * function the vendor examples call esp_deep_sleep_enable_ext1_wakeup()
         * -- same signature, same mask, no deprecation warning on IDF 5.x.
         * Mask = GPIO2 | GPIO3 (UP/DOWN), active LOW. The RTC domain needs its
         * own pull-ups armed: the digital-domain pull-ups are gone once the
         * chip powers down. */
        if (wake_mask & (1ULL << BTN_UP)) {
            rtc_gpio_pullup_en((gpio_num_t)BTN_UP);
            rtc_gpio_pulldown_dis((gpio_num_t)BTN_UP);
        }
        if (wake_mask & (1ULL << BTN_DOWN)) {
            rtc_gpio_pullup_en((gpio_num_t)BTN_DOWN);
            rtc_gpio_pulldown_dis((gpio_num_t)BTN_DOWN);
        }
        esp_sleep_enable_ext1_wakeup(wake_mask, ESP_EXT1_WAKEUP_ANY_LOW);
    }

    delay(20);
    esp_deep_sleep_start();
    /* not reached */
    while (true) { delay(1000); }
}
