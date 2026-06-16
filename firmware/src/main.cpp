#include <Arduino.h>
#include "inmp441_module.h"
#include "test_mode_module.h"
#include "flash_module.h"

void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n=== iCough Analytic ===");

    if (!flash_init()) {
        Serial.println("[FATAL] Flash init failed. Halting.");
        while (true) { delay(1000); }
    }

    if (!mic_init()) {
        Serial.println("[FATAL] Mic init failed. Halting.");
        while (true) { delay(1000); }
    }

    if (!test_mode_init()) {
        Serial.println("[FATAL] Test mode init failed. Halting.");
        while (true) { delay(1000); }
    }

    Serial.println("[MAIN] Ready. Press button (GPIO3) to enter test mode.");
}

void loop() {
    test_mode_loop();
}
