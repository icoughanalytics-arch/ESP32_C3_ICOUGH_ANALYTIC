#include <Arduino.h>
#include "inmp441_module.h"

void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n=== iCough Analytic ===");

    if (!mic_init()) {
        Serial.println("[FATAL] Mic init failed. Halting.");
        while (true) { delay(1000); }
    }
}

void loop() {
    mic_test_loop();
}
