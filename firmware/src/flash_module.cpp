#include "flash_module.h"

bool flash_init() {
    if (!LittleFS.begin(true)) {
        Serial.println("[ERR] LittleFS Mount Failed");
        return false;
    }
    Serial.println("[FLASH] LittleFS Mount Success");

    // สร้างไดเรกทอรี /normal และ /test ถ้ายังไม่มี
    if (!LittleFS.exists("/normal")) {
        LittleFS.mkdir("/normal");
    }
    if (!LittleFS.exists("/test")) {
        LittleFS.mkdir("/test");
    }

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

size_t flash_get_free_space() {
    return LittleFS.totalBytes() - LittleFS.usedBytes();
}

bool flash_is_full() {
    // กำหนดให้เต็มถ้าพื้นที่เหลือน้อยกว่า 150KB (เนื่องจากไฟล์ 3s WAV ใช้พื้นที่ประมาณ 96KB)
    return flash_get_free_space() < (150 * 1024);
}

void flash_clean_directory(const char* dirpath) {
    Serial.printf("[FLASH] Cleaning directory: %s\n", dirpath);
    File dir = LittleFS.open(dirpath);
    if (!dir || !dir.isDirectory()) {
        Serial.printf("[FLASH] Directory %s not found or not a dir\n", dirpath);
        return;
    }

    // ใน LittleFS ลิสต์ไฟล์โดยการวนลูป
    File file = dir.openNextFile();
    while (file) {
        // บางเวอร์ชันของ ESP32 file.name() คืนค่าเฉพาะชื่อไฟล์ย่อย บางเวอร์ชันคืน path เต็ม
        // ดังนั้นเราจะตรวจเช็คเพื่อลบไฟล์ให้ถูกต้อง
        String filepath = file.name();
        if (!filepath.startsWith("/")) {
            // ถ้าเป็นชื่อย่อย ให้ต่อ path
            String dir_str = dirpath;
            if (!dir_str.endsWith("/")) dir_str += "/";
            if (dir_str.startsWith("/")) {
                filepath = dir_str + filepath;
            } else {
                filepath = "/" + dir_str + filepath;
            }
        }
        
        file.close(); // ปิดไฟล์ก่อนลบเพื่อไม่ให้ lock
        Serial.printf("[FLASH] Deleting file: %s\n", filepath.c_str());
        LittleFS.remove(filepath);
        
        file = dir.openNextFile();
    }
    Serial.printf("[FLASH] Finished cleaning directory: %s\n", dirpath);
}

