#pragma once

#include <Arduino.h>

// --- Pin Definitions ---
#define TEST_BUTTON_PIN   3     // ปุ่มกด active low (เปลี่ยนเป็น GPIO 3 เลี่ยงสัญญาณรบกวน)
#define TEST_LED_PIN      20    // LED แสดงสถานะ test mode

// --- Test Mode Config ---
#define TEST_MODE_TIMEOUT_MS    10000   // ออกจาก test mode อัตโนมัติหลัง 10 วินาที
#define TEST_DEBOUNCE_MS        200     // debounce สำหรับปุ่มกด
#define COUGH_THRESHOLD_DB      -30.0f  // dBFS ที่ถือว่าเสียงดังพอจะเป็นเสียงไอ
#define TEST_RECORD_SECONDS     3       // ระยะเวลาอัดเสียง 3 วินาที

bool test_mode_init();
void test_mode_loop();
bool test_mode_is_active();
void test_mode_start();
void test_mode_stop();

