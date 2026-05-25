#include "audio_test_module.h"
#include "inmp441_module.h"
#include "ram_buffer_module.h"
#include "wifi_module.h"

#define TEST_RECORD_SECONDS 3
#define TEST_PCM_BYTES (SAMPLE_RATE * TEST_RECORD_SECONDS * sizeof(int16_t))
#define WAV_HEADER_BYTES 44
#define TEST_WAV_BYTES (WAV_HEADER_BYTES + TEST_PCM_BYTES)

static uint8_t* wav_buffer = nullptr;
static bool upload_done = false;

static void write_le16(uint8_t* p, uint16_t value) {
    p[0] = value & 0xff;
    p[1] = (value >> 8) & 0xff;
}

static void write_le32(uint8_t* p, uint32_t value) {
    p[0] = value & 0xff;
    p[1] = (value >> 8) & 0xff;
    p[2] = (value >> 16) & 0xff;
    p[3] = (value >> 24) & 0xff;
}

static void write_wav_header(uint8_t* wav, uint32_t pcm_bytes) {
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

bool audio_upload_test_init() {
    if (!ram_buffer_init()) return false;

    wav_buffer = (uint8_t*)malloc(TEST_WAV_BYTES);
    if (!wav_buffer) {
        Serial.println("[TEST] Failed to allocate WAV buffer");
        return false;
    }

    write_wav_header(wav_buffer, TEST_PCM_BYTES);
    wifi_init();
    Serial.printf("[TEST] Ready: %u sec, %u bytes WAV\n", TEST_RECORD_SECONDS, TEST_WAV_BYTES);
    return true;
}

void audio_upload_test_loop() {
    if (upload_done) {
        delay(1000);
        return;
    }

    static int32_t raw_buf[READ_SAMPLES];
    static int16_t pcm_buf[READ_SAMPLES];

    Serial.println("[TEST] Audio test starts soon");
    for (int i = 3; i > 0; i--) {
        Serial.printf("[TEST] Speak in %d...\n", i);
        delay(1000);
    }

    Serial.printf("[TEST] Recording now: speak anything for %u seconds\n", TEST_RECORD_SECONDS);
    ram_buffer_clear();

    unsigned long record_start_ms = millis();
    while (ram_buffer_size() < TEST_PCM_BYTES) {
        size_t samples_read = 0;
        if (!mic_read(raw_buf, READ_SAMPLES, &samples_read)) {
            Serial.println("[TEST] mic_read failed");
            delay(100);
            continue;
        }

        mic_convert_to_pcm16(raw_buf, pcm_buf, samples_read);
        size_t bytes_to_write = samples_read * sizeof(int16_t);
        size_t remaining = TEST_PCM_BYTES - ram_buffer_size();
        if (bytes_to_write > remaining) bytes_to_write = remaining;
        ram_buffer_write((const uint8_t*)pcm_buf, bytes_to_write);
    }
    unsigned long record_ms = millis() - record_start_ms;

    size_t copied = ram_buffer_get_data(wav_buffer + WAV_HEADER_BYTES, TEST_PCM_BYTES);
    Serial.printf("[TEST] Captured %u/%u PCM bytes in %u ms\n",
                  (unsigned int)copied,
                  (unsigned int)TEST_PCM_BYTES,
                  (unsigned int)record_ms);
    Serial.printf("[TEST] WAV ready bytes=%u sample_rate=%u bits=16 channels=1\n",
                  (unsigned int)TEST_WAV_BYTES,
                  (unsigned int)SAMPLE_RATE);
    Serial.printf("[TEST] Saved in RAM only: pcm=%u bytes wav=%u bytes\n",
                  (unsigned int)copied,
                  (unsigned int)TEST_WAV_BYTES);
    Serial.println("[TEST] Uploading recorded WAV...");

    bool ok = wifi_upload_audio_wav("mic_test_3s.wav", wav_buffer, TEST_WAV_BYTES);
    Serial.println(ok ? "[TEST] Upload OK" : "[TEST] Upload FAILED");
    upload_done = true;
}
