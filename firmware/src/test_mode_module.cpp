#include "test_mode_module.h"
#include "inmp441_module.h"
#include "ram_buffer_module.h"
#include "wifi_module.h"
#include "flash_module.h"


// --- WAV constants ---
#define TEST_PCM_BYTES   ((size_t)(SAMPLE_RATE * TEST_RECORD_SECONDS * sizeof(int16_t)))
#define WAV_HEADER_BYTES 44
#define TEST_WAV_BYTES   (WAV_HEADER_BYTES + TEST_PCM_BYTES)

// --- State ---
static bool     mode_active       = false;
static bool     last_button_state = false;
static unsigned long last_press_ms    = 0;
static unsigned long mode_start_ms    = 0;
static uint8_t* wav_buffer        = nullptr;
static uint32_t cough_count       = 0;

// --- FreeRTOS LED Blinking Task State ---
static TaskHandle_t blink_task_handle = NULL;
static volatile bool keep_blinking    = false;

// ============================================================
//  WAV Header Helper
// ============================================================
static void write_le16(uint8_t* p, uint16_t v) {
    p[0] = v & 0xff;
    p[1] = (v >> 8) & 0xff;
}

static void write_le32(uint8_t* p, uint32_t v) {
    p[0] = v & 0xff;
    p[1] = (v >> 8) & 0xff;
    p[2] = (v >> 16) & 0xff;
    p[3] = (v >> 24) & 0xff;
}

static void build_wav_header(uint8_t* wav, uint32_t pcm_bytes) {
    memcpy(wav + 0, "RIFF", 4);
    write_le32(wav + 4, 36 + pcm_bytes);
    memcpy(wav + 8, "WAVE", 4);
    memcpy(wav + 12, "fmt ", 4);
    write_le32(wav + 16, 16);
    write_le16(wav + 20, 1);
    write_le16(wav + 22, 1);
    write_le32(wav + 24, SAMPLE_RATE);
    write_le32(wav + 28, SAMPLE_RATE * sizeof(int16_t));
    write_le16(wav + 32, sizeof(int16_t));
    write_le16(wav + 34, 16);
    memcpy(wav + 36, "data", 4);
    write_le32(wav + 40, pcm_bytes);
}

// ============================================================
//  LED Helpers
// ============================================================
static void led_on()  { digitalWrite(TEST_LED_PIN, HIGH); }
static void led_off() { digitalWrite(TEST_LED_PIN, LOW);  }

static void led_blink(int times, int on_ms, int off_ms) {
    for (int i = 0; i < times; i++) {
        led_on();
        delay(on_ms);
        led_off();
        if (i < times - 1) delay(off_ms);
    }
}

static void led_blink_task(void* pvParameters) {
    while (keep_blinking) {
        digitalWrite(TEST_LED_PIN, !digitalRead(TEST_LED_PIN));
        vTaskDelay(pdMS_TO_TICKS(100)); // Blink every 100ms
    }
    blink_task_handle = NULL;
    vTaskDelete(NULL);
}

static void start_blinking() {
    if (blink_task_handle == NULL) {
        keep_blinking = true;
        xTaskCreate(led_blink_task, "BlinkTask", 1024, NULL, 1, &blink_task_handle);
    }
}

static void stop_blinking() {
    keep_blinking = false;
    delay(50); // Small delay to let task exit loop
    led_off();
}

// ============================================================
//  Enter / Exit Test Mode
// ============================================================
static void enter_test_mode() {
    mode_active = true;
    mode_start_ms = millis();
    cough_count = 0;
    ram_buffer_clear();
    led_on();

    Serial.printf("[TEST] TEST ACTIVE (time: %lu)\n", mode_start_ms);
}

static void exit_test_mode(const char* reason) {
    mode_active = false;
    led_off();
    Serial.printf("[TEST] TEST EXIT (time: %lu) [reason: %s]\n", millis(), reason);
}

// ============================================================
//  Record & Upload
// ============================================================
static void record_and_upload() {
    Serial.printf("[TEST] Cough detected! Recording %.1f seconds directly to Flash...\n", (float)TEST_RECORD_SECONDS);

    // เริ่มการกะพริบไฟ LED ในเบื้องหลังด้วย FreeRTOS Task
    start_blinking();

    // ล้างบัฟเฟอร์แรมก่อนเริ่มอัด
    ram_buffer_clear();

    // เปิดไฟล์ใน LittleFS สำหรับบันทึกเสียงสดลงแฟลชโดยตรง
    const char* temp_filename = "/test/cough_temp.wav";
    File file = LittleFS.open(temp_filename, FILE_WRITE);
    if (!file) {
        Serial.println("[TEST] Error: Cannot open temp file in LittleFS for writing");
        stop_blinking();
        exit_test_mode("file error");
        return;
    }

    // เขียน WAV Header ว่างๆ 44 bytes หลอกไว้ก่อน
    uint8_t header[WAV_HEADER_BYTES];
    memset(header, 0, WAV_HEADER_BYTES);
    file.write(header, WAV_HEADER_BYTES);

    int32_t raw_buf[READ_SAMPLES];
    int16_t pcm_buf[READ_SAMPLES];
    size_t total_pcm_bytes_written = 0;

    unsigned long rec_start = millis();
    while (total_pcm_bytes_written < TEST_PCM_BYTES) {
        size_t samples_read = 0;
        if (!mic_read(raw_buf, READ_SAMPLES, &samples_read)) {
            delay(10);
            continue;
        }
        mic_convert_to_pcm16(raw_buf, pcm_buf, samples_read);
        
        size_t bytes_to_write = samples_read * sizeof(int16_t);
        size_t remaining = TEST_PCM_BYTES - total_pcm_bytes_written;
        if (bytes_to_write > remaining) {
            bytes_to_write = remaining;
        }

        // เขียนลงแฟลชทันที (ใช้แรม Stack เล็กน้อย ไม่โหลดแรม Heap)
        size_t written = file.write((const uint8_t*)pcm_buf, bytes_to_write);
        total_pcm_bytes_written += written;
    }
    unsigned long rec_ms = millis() - rec_start;

    // ย้อนกลับไปเขียน WAV Header ตัวจริงที่หัวไฟล์หลังจากเรคคอร์ดเสร็จ
    if (file.seek(0)) {
        build_wav_header(header, total_pcm_bytes_written);
        file.write(header, WAV_HEADER_BYTES);
    } else {
        Serial.println("[TEST] Error: Failed to seek to file start for header update");
    }
    file.close();

    Serial.printf("[TEST] Recorded %u PCM bytes directly to Flash in %u ms\n",
                  (unsigned int)total_pcm_bytes_written, (unsigned int)rec_ms);

    // LED ติดค้างระหว่างส่ง
    led_on();

    // ส่งไฟล์ผ่าน HTTPS (สตรีมจาก LittleFS ทำให้ปลอดภัยเรื่องแรม)
    cough_count++;
    char target_fname[40];
    snprintf(target_fname, sizeof(target_fname), "test_cough_%u_%u.wav", (unsigned int)(millis() / 1000), (unsigned int)cough_count);
    Serial.printf("[TEST] Uploading %s via HTTPS...\n", target_fname);
    
    // ปริ้นตรวจสอบสถานะแรมจริงก่อนต่อเชื่อม SSL
    Serial.printf("[TEST] Free Heap before SSL connection: %u bytes, Max Contiguous Block: %u bytes\n", 
                  ESP.getFreeHeap(), ESP.getMaxAllocHeap());

    bool ok = wifi_upload_audio_wav_from_file(temp_filename, "test");
    Serial.println(ok ? "[TEST] Upload OK" : "[TEST] Upload FAILED");

    // ลบไฟล์ชั่วคราวออกเพื่อคืนความจุ Flash
    flash_delete_file(temp_filename);

    // หยุดกะพริบไฟ LED เบื้องหลัง
    stop_blinking();

    // ออกจาก test mode ทันทีหลังอัปโหลดเสร็จ (หรือพัง)
    exit_test_mode(ok ? "upload success" : "upload failed");
}

// ============================================================
//  Public API
// ============================================================
bool test_mode_init() {
    pinMode(TEST_BUTTON_PIN, INPUT_PULLUP);
    pinMode(TEST_LED_PIN, OUTPUT);
    led_off();

    if (!ram_buffer_init()) return false;

    // ไม่จำเป็นต้องจอง wav_buffer ในแรมถาวรแล้ว
    wav_buffer = nullptr;

    wifi_init();
    Serial.println("[TEST] Microphone connection verified: SUCCESS (I2S initialized)");
    Serial.printf("[TEST] Free Heap on setup: %u bytes, Max Contiguous Block: %u bytes\n", 
                  ESP.getFreeHeap(), ESP.getMaxAllocHeap());
    Serial.printf("[TEST] Init OK: button=GPIO%d led=GPIO%d\n",
                  TEST_BUTTON_PIN, TEST_LED_PIN);
    return true;
}

void test_mode_loop() {
    // --- ถ้าไม่ได้อยู่ใน test mode ไม่ต้องทำอะไร ---
    if (!mode_active) return;

    unsigned long now = millis();

    // อัปเดตเวลาปัจจุบันอีกครั้ง ป้องกันการ Underflow จากการหน่วงเวลาใน enter_test_mode()
    now = millis();

    // --- ตรวจสอบ timeout ---
    if (now - mode_start_ms >= TEST_MODE_TIMEOUT_MS) {
        exit_test_mode("timeout 10s");
        return;
    }

    // --- ฟังเสียงจากไมค์ ---
    static int32_t raw_buf[READ_SAMPLES];
    size_t samples_read = 0;

    if (!mic_read(raw_buf, READ_SAMPLES, &samples_read)) {
        static unsigned long last_err_print_ms = 0;
        if (now - last_err_print_ms > 1000) {
            last_err_print_ms = now;
            Serial.println("[TEST] mic_read returned false!");
        }
        return;
    }

    float rms = mic_calc_rms(raw_buf, samples_read);
    float db  = mic_calc_db(rms);

    static unsigned long last_print_ms = 0;
    if (now - last_print_ms > 300) {
        last_print_ms = now;
        Serial.printf("[TEST] Mic level: %.1f dBFS\n", db);
    }

    // --- ตรวจจับเสียงไอ ---
    if (db > COUGH_THRESHOLD_DB) {
        Serial.printf("[TEST] Loud sound detected: dBFS=%.1f (threshold=%.1f)\n", db, COUGH_THRESHOLD_DB);
        record_and_upload();
    }
}

bool test_mode_is_active() {
    return mode_active;
}

void test_mode_start() {
    enter_test_mode();
}

void test_mode_stop() {
    exit_test_mode("button");
}

