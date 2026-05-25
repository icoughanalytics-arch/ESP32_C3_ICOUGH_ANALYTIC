#pragma once

#include <Arduino.h>

#define WIFI_SSID "omgdigital_4064"
#define WIFI_PASSWORD "60F&003ii4@4"

#define SERVER_HOST "10.142.169.170"
#define SERVER_PORT 8000
#define SERVER_UPLOAD_PATH "/upload-audio"

#define WIFI_CONNECT_TIMEOUT_MS 15000
#define HTTP_RESPONSE_TIMEOUT_MS 10000

void wifi_init();
void wifi_connect();
void wifi_disconnect();
bool wifi_is_connected();
void wifi_upload_files();
bool wifi_upload_audio_wav(const char* filename, const uint8_t* data, size_t size);
