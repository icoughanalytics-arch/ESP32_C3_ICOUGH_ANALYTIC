#pragma once

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>

bool flash_init();
bool flash_save_wav(const char* filename, const uint8_t* data, size_t size);
bool flash_delete_file(const char* filename);
void flash_list_files();
size_t flash_get_free_space();
bool flash_is_full();
void flash_clean_directory(const char* dirpath);
bool flash_delete_oldest_in_dir(const char* dirpath);


