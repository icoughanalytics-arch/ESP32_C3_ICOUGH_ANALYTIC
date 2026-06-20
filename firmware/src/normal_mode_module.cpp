#include "normal_mode_module.h"
#include "inmp441_module.h"
#include "ram_buffer_module.h"
#include "wifi_module.h"
#include "flash_module.h"

// --- WAV constants ---
#define NORMAL_RECORD_SECONDS  3
#define NORMAL_PCM_BYTES       ((size_t)(SAMPLE_RATE * NORMAL_RECORD_SECONDS * sizeof(int16_t)))
#define WAV_HEADER_BYTES       44
#define COUGH_THRESHOLD_DB     -30.0f  // เกณฑ์ตรวจจับเสียงไอ (เท่ากับเทสโหมด)
#define BATCH_UPLOAD_COOLDOWN_MS 60000 // คูลดาวน์ 1 นาที เพื่อกันลูปอัปโหลดถี่เกินไปกรณีต่อ WiFi ไม่ติด

// --- State Variables ---
static unsigned long last_upload_ms = 0;
static const unsigned long UPLOAD_INTERVAL_MS = 600000; // 10 นาที (10 * 60 * 1000)
static uint32_t normal_cough_count = 0;
static bool is_recording = false;

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
//  Batch Upload Function
// ============================================================
static void trigger_batch_upload() {
    Serial.println("[NORMAL] Triggering batch upload of stored cough files...");
    
    // พยายามเชื่อมต่อและอัปโหลดไฟล์ในโฟลเดอร์ /normal
    // ฟังก์ชันนี้จะอัปโหลดและลบไฟล์ที่สำเร็จ ถ้าอัปโหลดไม่ผ่านจะเก็บไว้ลองใหม่รอบหน้า
    wifi_upload_directory_batch("/normal", "normal");
    
    // ตั้งค่าเวลาอัปโหลดล่าสุดเป็นตอนนี้ (ไม่ว่าอัปโหลดจะสำเร็จหรือไม่ก็ตาม เพื่อกันลูปเชื่อมต่อตลอดเวลาเมื่อ Flash เต็ม)
    last_upload_ms = millis();
    Serial.printf("[NORMAL] Storing next upload timer reference (cooldown 10m)\n");
}

// ============================================================
//  Record Normal Cough
// ============================================================
static void record_normal_cough() {
    is_recording = true;
    normal_cough_count++;
    
    char filename[40];
    snprintf(filename, sizeof(filename), "/normal/n_cough_%u_%u.wav", (unsigned int)(millis() / 1000), (unsigned int)normal_cough_count);
    
    Serial.printf("[NORMAL] Cough detected! Recording 3s WAV to Flash: %s\n", filename);
    
    // ตรวจสอบพื้นที่ว่างของ Flash ก่อนเขียนไฟล์ใหม่ (ถ้าเต็ม ให้พยายามเคลียร์พื้นที่ตามหลัก FIFO)
    if (flash_is_full()) {
        Serial.println("[NORMAL] Flash is full! Applying FIFO: trying to delete oldest files...");
        while (flash_is_full()) {
            if (!flash_delete_oldest_in_dir("/normal")) {
                Serial.println("[NORMAL] FIFO Failed: No more files can be deleted.");
                break;
            }
        }
        
        // หากลบจนสุดแล้วยังเต็มอยู่ ค่อยข้ามการบันทึก
        if (flash_is_full()) {
            Serial.println("[NORMAL] Flash is still full! Skipping record to prevent overflow.");
            is_recording = false;
            trigger_batch_upload();
            return;
        }
    }

    File file = LittleFS.open(filename, FILE_WRITE);
    if (!file) {
        Serial.println("[NORMAL] Error: Cannot open file in LittleFS for writing");
        is_recording = false;
        return;
    }

    // เขียน WAV Header ว่างๆ 44 bytes ก่อน
    uint8_t header[WAV_HEADER_BYTES];
    memset(header, 0, WAV_HEADER_BYTES);
    file.write(header, WAV_HEADER_BYTES);

    size_t total_pcm_bytes_written = 0;

    // 1. ดึงเสียงย้อนหลังจาก RAM Pre-buffer (เช่น ย้อนหลัง 1 วินาที = 32000 bytes)
    // เพื่อเก็บเสียงจังหวะเริ่มไอไม่ให้ตกหล่น
    size_t prebuf_size = ram_buffer_size();
    if (prebuf_size > 0) {
        // จำกัดการดึงย้อนหลังไว้สูงสุด 1.2 วินาที (38,400 bytes) เพื่อไม่ให้หนักเกินไป
        if (prebuf_size > 38400) prebuf_size = 38400;
        
        uint8_t* temp_ram = (uint8_t*)malloc(prebuf_size);
        if (temp_ram) {
            size_t copied = ram_buffer_get_data(temp_ram, prebuf_size);
            size_t written = file.write(temp_ram, copied);
            total_pcm_bytes_written += written;
            free(temp_ram);
            Serial.printf("[NORMAL] Restored %u bytes from RAM pre-buffer\n", (unsigned int)written);
        }
    }

    // 2. อัดเสียงสดจากไมโครโฟนต่อจนกว่าจะได้ขนาดครบ 3 วินาที
    int32_t raw_buf[READ_SAMPLES];
    int16_t pcm_buf[READ_SAMPLES];
    
    unsigned long rec_start = millis();
    while (total_pcm_bytes_written < NORMAL_PCM_BYTES) {
        size_t samples_read = 0;
        if (!mic_read(raw_buf, READ_SAMPLES, &samples_read)) {
            delay(5);
            continue;
        }
        mic_convert_to_pcm16(raw_buf, pcm_buf, samples_read);
        
        size_t bytes_to_write = samples_read * sizeof(int16_t);
        size_t remaining = NORMAL_PCM_BYTES - total_pcm_bytes_written;
        if (bytes_to_write > remaining) {
            bytes_to_write = remaining;
        }

        size_t written = file.write((const uint8_t*)pcm_buf, bytes_to_write);
        total_pcm_bytes_written += written;
    }
    unsigned long rec_ms = millis() - rec_start;

    // ย้อนกลับไปเขียน WAV Header ที่สมบูรณ์หัวไฟล์
    if (file.seek(0)) {
        build_wav_header(header, total_pcm_bytes_written);
        file.write(header, WAV_HEADER_BYTES);
    } else {
        Serial.println("[NORMAL] Error: Failed to seek to file start for header update");
    }
    file.close();

    Serial.printf("[NORMAL] Recorded %u PCM bytes to Flash in %u ms\n",
                  (unsigned int)total_pcm_bytes_written, (unsigned int)rec_ms);

    // ล้าง RAM pre-buffer เพื่อรับเสียงถัดไป
    ram_buffer_clear();
    is_recording = false;
    
    // เช็คอีกรอบหลังจากบันทึกเสร็จ หากทำให้ Flash เต็ม ให้สั่งอัปโหลดทันที
    if (flash_is_full()) {
        Serial.println("[NORMAL] Flash became full after record. Uploading now!");
        trigger_batch_upload();
    }
}

// ============================================================
//  Public API
// ============================================================
bool normal_mode_init() {
    if (!ram_buffer_init()) return false;
    normal_mode_reset_timer();
    Serial.println("[NORMAL] Normal Mode Module Initialized");
    return true;
}

void normal_mode_start() {
    normal_mode_reset_timer();
    ram_buffer_clear();
    is_recording = false;
    Serial.println("[NORMAL] Normal Mode Loop Started");
}

void normal_mode_loop() {
    unsigned long now = millis();

    // 1. ตรวจสอบ Timer 10 นาที หรือพื้นที่ Flash เต็ม (โดยเว้นระยะคูลดาวน์กันวนลูปหากไม่มีอินเทอร์เน็ต)
    bool time_to_upload = (now - last_upload_ms >= UPLOAD_INTERVAL_MS);
    bool flash_full_need_upload = flash_is_full() && (now - last_upload_ms >= BATCH_UPLOAD_COOLDOWN_MS);

    if (time_to_upload || flash_full_need_upload) {
        if (flash_is_full()) {
            Serial.println("[NORMAL] Flash is full! Forcing batch upload (with cooldown check)...");
        } else {
            Serial.println("[NORMAL] 10-minute timer reached! Forcing batch upload...");
        }
        trigger_batch_upload();
        // ดึงเวลาใหม่เพื่อความแม่นยำ
        now = millis();
    }

    // 2. ถ้ากำลังอยู่ในขั้นตอนอัดเสียงอยู่ ไม่ประมวลผลเพิ่ม
    if (is_recording) return;

    // 3. ฟังเสียงจากไมค์เพื่อใส่ลง circular RAM pre-buffer และวัดระดับความดัง
    static int32_t raw_buf[READ_SAMPLES];
    static int16_t pcm_buf[READ_SAMPLES];
    size_t samples_read = 0;

    if (!mic_read(raw_buf, READ_SAMPLES, &samples_read)) {
        return;
    }

    // แปลงเสียงและเขียนลง Pre-buffer
    mic_convert_to_pcm16(raw_buf, pcm_buf, samples_read);
    ram_buffer_write((const uint8_t*)pcm_buf, samples_read * sizeof(int16_t));

    // คำนวณความดังเพื่อตรวจจับเสียงไอ
    float rms = mic_calc_rms(raw_buf, samples_read);
    float db  = mic_calc_db(rms);

    // ตรวจจับเสียงไอ
    if (db > COUGH_THRESHOLD_DB) {
        Serial.printf("[NORMAL] Loud sound detected: dBFS=%.1f\n", db);
        record_normal_cough();
    }
}

void normal_mode_reset_timer() {
    last_upload_ms = millis();
    Serial.println("[NORMAL] Timer reset. Next upload in 10 minutes.");
}

bool normal_mode_is_recording() {
    return is_recording;
}
