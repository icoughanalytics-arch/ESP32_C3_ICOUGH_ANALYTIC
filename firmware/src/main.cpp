#include <Arduino.h>
#include "inmp441_module.h"
#include "test_mode_module.h"
#include "normal_mode_module.h"
#include "wifi_config_module.h"
#include "flash_module.h"
#include "wifi_module.h"

// --- System State Definition ---
enum SystemState {
    STATE_NORMAL,
    STATE_TEST,
    STATE_WIFI_CONFIG
};

SystemState current_state = STATE_NORMAL;

// --- Button State variables ---
static bool last_btn_state = HIGH;
static unsigned long button_press_start_ms = 0;
static bool button_pressed_handled = false;

// ============================================================
//  Button Actions Handlers
// ============================================================
void handle_short_press() {
    if (current_state == STATE_NORMAL) {
        Serial.println("[MAIN] Switched to STATE_TEST (Short Press)");
        current_state = STATE_TEST;
        test_mode_start();
    } 
    else if (current_state == STATE_TEST) {
        Serial.println("[MAIN] Switched to STATE_NORMAL (Short Press from Test)");
        test_mode_stop();
        current_state = STATE_NORMAL;
        normal_mode_start(); // กลับมารีเซ็ตตัวนับ 10 นาทีใหม่
    } 
    else if (current_state == STATE_WIFI_CONFIG) {
        Serial.println("[MAIN] Switched to STATE_NORMAL (Short Press from WiFi Setup)");
        wifi_config_stop();
        current_state = STATE_NORMAL;
        normal_mode_start();
    }
}

void handle_long_press() {
    if (current_state != STATE_WIFI_CONFIG) {
        Serial.println("[MAIN] Switched to STATE_WIFI_CONFIG (Long Press 3s)");
        if (current_state == STATE_TEST) {
            test_mode_stop();
        }
        current_state = STATE_WIFI_CONFIG;
        wifi_config_start();
    } 
    else {
        Serial.println("[MAIN] Switched to STATE_NORMAL (Long Press from WiFi Setup)");
        wifi_config_stop();
        current_state = STATE_NORMAL;
        normal_mode_start();
    }
}

// ============================================================
//  Setup & Loop
// ============================================================
void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n=== iCough Analytic - Smart Monitor ===");

    // กำหนดขาปุ่มกด
    pinMode(TEST_BUTTON_PIN, INPUT_PULLUP);

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

    if (!normal_mode_init()) {
        Serial.println("[FATAL] Normal mode init failed. Halting.");
        while (true) { delay(1000); }
    }

    // เริ่มต้นเชื่อมต่อ WiFi เบื้องหลัง (NVS หรือ Hardcoded)
    wifi_init();
    Serial.println("[WIFI] Auto connecting to saved/default WiFi in background...");
    wifi_connect_stored(); 

    // สตาร์ทใน Normal Mode ทันที
    current_state = STATE_NORMAL;
    normal_mode_start();

    Serial.println("[MAIN] Ready. Normal mode listening is ACTIVE.");
    Serial.println("  - Short Press button (GPIO3) -> Enter/Exit Test Mode");
    Serial.println("  - Long Press 3 seconds -> Enter WiFi Configuration Mode");
}

void loop() {
    // --- 1. ตรวจจับและแยกแยะประเภทการกดปุ่ม (GPIO3) ---
    bool btn = digitalRead(TEST_BUTTON_PIN) == LOW; // Active Low

    if (btn && last_btn_state == HIGH) {
        // จังหวะเริ่มกดปุ่ม
        button_press_start_ms = millis();
        button_pressed_handled = false;
        last_btn_state = LOW;
        delay(10); // debounce สั้นๆ
    } 
    else if (!btn && last_btn_state == LOW) {
        // จังหวะปล่อยปุ่ม
        last_btn_state = HIGH;
        unsigned long press_duration = millis() - button_press_start_ms;
        if (!button_pressed_handled && press_duration >= 50 && press_duration < 3000) {
            handle_short_press();
        }
        delay(10); // debounce สั้นๆ
    } 
    else if (btn && last_btn_state == LOW) {
        // ปุ่มยังถูกกดค้างอยู่
        unsigned long press_duration = millis() - button_press_start_ms;
        if (!button_pressed_handled && press_duration >= 3000) {
            handle_long_press();
            button_pressed_handled = true; // ทำงานครั้งเดียวเมื่อครบ 3 วิ ไม่ทำซ้ำ
        }
    }

    // --- 2. การทำงานของลูปตาม State ปัจจุบัน ---
    switch (current_state) {
        case STATE_NORMAL:
            normal_mode_loop();
            break;

        case STATE_TEST:
            test_mode_loop();
            // ตรวจสอบว่าระบบทดสอบตัวเองจบลงแล้วหรือยัง (เช่น อัปโหลดเสร็จ หรือหมดเวลา 10 วิ)
            if (!test_mode_is_active()) {
                Serial.println("[MAIN] Test mode inactive. Switched to STATE_NORMAL");
                current_state = STATE_NORMAL;
                normal_mode_start();
            }
            break;

        case STATE_WIFI_CONFIG:
            wifi_config_loop();
            // ตรวจสอบว่า WiFi Config ยกเลิกตัวเอง (หมดเวลา 2 นาที)
            if (!wifi_config_is_active()) {
                Serial.println("[MAIN] WiFi Config inactive. Switched to STATE_NORMAL");
                current_state = STATE_NORMAL;
                normal_mode_start();
            }
            break;
    }
}
