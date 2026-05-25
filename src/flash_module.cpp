#include "flash_module.h"

bool flash_init() {
    if (!LittleFS.begin(true)) {
        Serial.println("[ERR] LittleFS Mount Failed");
        return false;
    }
    Serial.println("[FLASH] LittleFS Mount Success");
    return true;
}

bool flash_save_wav(const char* filename, const uint8_t* data, size_t size) {
    // TODO: Implement actual WAV writing logic
    return false;
}

bool flash_delete_file(const char* filename) {
    return LittleFS.remove(filename);
}

void flash_list_files() {
    // TODO: List files for debugging or uploading
}
