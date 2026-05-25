#pragma once

#include <Arduino.h>

void wifi_init();
void wifi_connect();
void wifi_disconnect();
bool wifi_is_connected();
void wifi_upload_files();
