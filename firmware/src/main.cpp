#include <Arduino.h>
#include "inmp441_module.h"
#include "audio_test_module.h"

void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n=== iCough Analytic ===");

    if (!mic_init()) {
        Serial.println("[FATAL] Mic init failed. Halting.");
        while (true) { delay(1000); }
    }

    if (!audio_upload_test_init()) {
        Serial.println("[FATAL] Audio test init failed. Halting.");
        while (true) { delay(1000); }
    }
}

void loop() {
    audio_upload_test_loop();
}
