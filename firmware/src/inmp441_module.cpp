#include "inmp441_module.h"

// ============================================================
//  INMP441 – I2S Microphone Implementation
// ============================================================

bool mic_init() {
    i2s_config_t cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate          = SAMPLE_RATE,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,   // INMP441 ต่อ L/R -> GND (LEFT)
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = DMA_BUF_COUNT,
        .dma_buf_len          = DMA_BUF_LEN,
        .use_apll             = false,
        .tx_desc_auto_clear   = false,
        .fixed_mclk           = 0
    };

    i2s_pin_config_t pins = {
        .bck_io_num   = I2S_BCLK_PIN,
        .ws_io_num    = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = I2S_DATA_PIN
    };

    if (i2s_driver_install(I2S_PORT, &cfg, 0, NULL) != ESP_OK) {
        Serial.println("[MIC] i2s_driver_install FAILED");
        return false;
    }
    if (i2s_set_pin(I2S_PORT, &pins) != ESP_OK) {
        Serial.println("[MIC] i2s_set_pin FAILED");
        return false;
    }
    i2s_zero_dma_buffer(I2S_PORT);
    Serial.println("[MIC] INMP441 init OK");
    return true;
}

bool mic_read(int32_t* buf, size_t num_samples, size_t* out_samples_read) {
    size_t bytes_read = 0;
    esp_err_t err = i2s_read(
        I2S_PORT,
        (void*)buf,
        num_samples * sizeof(int32_t),
        &bytes_read,
        portMAX_DELAY
    );
    if (err != ESP_OK) {
        Serial.printf("[MIC] i2s_read failed: %d (0x%X)\n", err, err);
        *out_samples_read = 0;
        return false;
    }
    *out_samples_read = bytes_read / sizeof(int32_t);
    return true;
}

// คำนวณ RMS จาก raw 32-bit I2S samples
// INMP441 ส่งข้อมูล 18-bit ชิดซ้าย (MSB) ของ 32-bit word
// shift right 14 เพื่อให้ได้ค่า 18-bit signed
void mic_convert_to_pcm16(const int32_t* in_buf, int16_t* out_buf, size_t num_samples) {
    for (size_t i = 0; i < num_samples; i++) {
        int32_t sample18 = in_buf[i] >> 14;
        int32_t sample16 = sample18 >> 2;
        if (sample16 > 32767) sample16 = 32767;
        if (sample16 < -32768) sample16 = -32768;
        out_buf[i] = (int16_t)sample16;
    }
}

float mic_calc_rms(const int32_t* buf, size_t num_samples) {
    if (num_samples == 0) return 0.0f;
    double sum = 0.0;
    for (size_t i = 0; i < num_samples; i++) {
        float sample = (float)(buf[i] >> 14);   // normalize to ~18-bit
        sum += (double)(sample * sample);
    }
    return sqrtf((float)(sum / num_samples));
}

// แปลง RMS -> dBFS (relative to full scale 18-bit = 131072)
float mic_calc_db(float rms) {
    if (rms <= 0.0f) return -120.0f;
    const float full_scale = 131072.0f;  // 2^17
    return 20.0f * log10f(rms / full_scale);
}

void mic_test_loop() {
    static int32_t audio_buf[READ_SAMPLES];
    size_t samples_read = 0;

    if (!mic_read(audio_buf, READ_SAMPLES, &samples_read)) {
        Serial.println("[ERR] mic_read failed");
        delay(100);
        return;
    }

    float rms = mic_calc_rms(audio_buf, samples_read);
    float db  = mic_calc_db(rms);

    // แสดงผล: จำนวน sample, RMS, dBFS
    Serial.printf("samples=%4u  RMS=%8.1f  dBFS=%6.1f", samples_read, rms, db);

    // Bar meter แสดง relative loudness (0 ถึง 40 ช่อง)
    int bar_len = (int)((db + 80.0f) * 40.0f / 60.0f);
    if (bar_len < 0)  bar_len = 0;
    if (bar_len > 40) bar_len = 40;

    Serial.print("  [");
    for (int i = 0; i < 40; i++) {
        Serial.print(i < bar_len ? "#" : " ");
    }
    Serial.println("]");

    delay(200);
}
