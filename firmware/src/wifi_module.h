#pragma once

#include <Arduino.h>

#define WIFI_SSID "diamondwifi"
#define WIFI_PASSWORD "12345678m"

// ngrok HTTPS endpoint
#define SERVER_HOST "d171-49-229-169-93.ngrok-free.app"
#define SERVER_PORT 443
#define SERVER_UPLOAD_PATH "/upload-audio"
#define SERVER_USE_HTTPS true

#define WIFI_CONNECT_TIMEOUT_MS 15000
#define HTTP_RESPONSE_TIMEOUT_MS 15000

void wifi_init();
void wifi_connect();
void wifi_disconnect();
bool wifi_is_connected();
void wifi_upload_files();
bool wifi_upload_audio_wav(const char* filename, const uint8_t* data, size_t size, const char* mode = "normal");
bool wifi_upload_audio_wav_from_file(const char* filepath, const char* mode = "normal");
bool wifi_save_credentials(const String &ssid, const String &password);
bool wifi_load_credentials(String &ssid, String &password);
void wifi_connect_stored();
bool wifi_upload_directory_batch(const char* dirpath, const char* mode);


