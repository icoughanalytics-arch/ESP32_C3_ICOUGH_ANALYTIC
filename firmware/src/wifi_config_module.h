#pragma once

#include <Arduino.h>

void wifi_config_start();
void wifi_config_loop();
void wifi_config_stop();
bool wifi_config_is_active();
