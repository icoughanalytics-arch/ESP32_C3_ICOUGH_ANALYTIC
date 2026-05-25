#pragma once

#include <Arduino.h>

// ขนาดของ Pre-buffer สำหรับเก็บเสียง
// ตัวอย่าง: 3 วินาที @ 16kHz 16-bit = 96,000 bytes
#define RAM_BUFFER_SIZE (100 * 1024)

bool ram_buffer_init();
void ram_buffer_write(const uint8_t* data, size_t size);
void ram_buffer_clear();
size_t ram_buffer_get_data(uint8_t* out_buf, size_t max_size);
