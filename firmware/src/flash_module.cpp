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
    if (!filename || !data || size == 0) return false;
    
    // มั่นใจว่าชื่อไฟล์เริ่มด้วย '/' สำหรับ LittleFS
    String path = filename;
    if (!path.startsWith("/")) {
        path = "/" + path;
    }

    File file = LittleFS.open(path, FILE_WRITE);
    if (!file) {
        Serial.printf("[FLASH] Failed to open file %s for writing\n", path.c_str());
        return false;
    }

    size_t written = file.write(data, size);
    file.close();
    
    if (written != size) {
        Serial.printf("[FLASH] Write incomplete: wrote %u of %u bytes\n", written, size);
        return false;
    }
    
    Serial.printf("[FLASH] Saved file %s (%u bytes) successfully\n", path.c_str(), (unsigned int)size);
    return true;
}

bool flash_delete_file(const char* filename) {
    String path = filename;
    if (!path.startsWith("/")) {
        path = "/" + path;
    }
    return LittleFS.remove(path);
}

void flash_list_files() {
    Serial.println("[FLASH] Listing files in LittleFS:");
    File root = LittleFS.open("/");
    if (!root || !root.isDirectory()) {
        Serial.println("[FLASH] Failed to open root directory");
        return;
    }

    File file = root.openNextFile();
    uint32_t total_size = 0;
    uint32_t count = 0;
    while (file) {
        Serial.printf("  - %s (%d bytes)\n", file.name(), (int)file.size());
        total_size += file.size();
        count++;
        file = root.openNextFile();
    }
    Serial.printf("[FLASH] Total: %u files, %u bytes used\n", count, total_size);
}
