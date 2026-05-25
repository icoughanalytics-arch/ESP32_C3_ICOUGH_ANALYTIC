#include "ram_buffer_module.h"

static uint8_t* audio_buffer = nullptr;
static size_t head_index = 0;
static size_t data_size = 0;

bool ram_buffer_init() {
    if (audio_buffer) {
        ram_buffer_clear();
        return true;
    }
    audio_buffer = (uint8_t*)malloc(RAM_BUFFER_SIZE);
    if (!audio_buffer) {
        Serial.println("[ERR] Failed to allocate RAM buffer");
        return false;
    }
    Serial.printf("[RAM] Allocated %u bytes for pre-buffer\n", RAM_BUFFER_SIZE);
    return true;
}

void ram_buffer_write(const uint8_t* data, size_t size) {
    if (!audio_buffer || !data || size == 0) return;

    for (size_t i = 0; i < size; i++) {
        audio_buffer[head_index] = data[i];
        head_index = (head_index + 1) % RAM_BUFFER_SIZE;
        if (data_size < RAM_BUFFER_SIZE) data_size++;
    }
}

void ram_buffer_clear() {
    head_index = 0;
    data_size = 0;
}

size_t ram_buffer_get_data(uint8_t* out_buf, size_t max_size) {
    if (!audio_buffer || !out_buf || max_size == 0) return 0;

    size_t copy_size = data_size;
    if (copy_size > max_size) copy_size = max_size;

    size_t start_index = (head_index + RAM_BUFFER_SIZE - data_size) % RAM_BUFFER_SIZE;
    for (size_t i = 0; i < copy_size; i++) {
        out_buf[i] = audio_buffer[(start_index + i) % RAM_BUFFER_SIZE];
    }
    return copy_size;
}

size_t ram_buffer_size() {
    return data_size;
}
