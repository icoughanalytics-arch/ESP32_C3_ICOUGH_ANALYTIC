#pragma once

#include <Arduino.h>
#include <driver/i2s.h>

// ============================================================
//  INMP441 I2S Microphone Module
//  Board  : Lolin C3 Mini (ESP32-C3)
//  Pinout : BCLK=4  WS/LRCK=5  SD/DATA=6
// ============================================================

// --- Pin Definitions ---
#define I2S_PORT        I2S_NUM_0
#define I2S_BCLK_PIN    4
#define I2S_WS_PIN      5
#define I2S_DATA_PIN    6

// --- I2S Config ---
#define SAMPLE_RATE     16000   // 16 kHz
#define SAMPLE_BITS     32      // INMP441 ส่งมา 32-bit (18-bit valid, MSB-first)
#define DMA_BUF_COUNT   4
#define DMA_BUF_LEN     256     // samples per DMA buffer

// --- Read Config ---
#define READ_SAMPLES    512     // จำนวน sample ต่อ 1 รอบอ่าน

bool  mic_init();
bool  mic_read(int32_t* buf, size_t num_samples, size_t* out_samples_read);
void  mic_convert_to_pcm16(const int32_t* in_buf, int16_t* out_buf, size_t num_samples);
float mic_calc_rms(const int32_t* buf, size_t num_samples);
float mic_calc_db(float rms);
void  mic_test_loop();
