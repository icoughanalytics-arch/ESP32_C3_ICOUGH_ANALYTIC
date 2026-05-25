# iCough Firmware

Firmware PlatformIO สำหรับ ESP32-C3 + INMP441

## Current Test Mode

โหมดปัจจุบัน:

1. อ่านเสียงจาก INMP441
2. แปลงเป็น PCM 16-bit mono 16 kHz
3. เก็บใน RAM 3 วินาที
4. สร้าง WAV ใน RAM
5. ส่งไปที่ Python server ผ่าน `POST /upload-audio`

## Before Upload

แก้ค่าใน `src/wifi_module.h`

```cpp
#define WIFI_SSID "your-wifi"
#define WIFI_PASSWORD "your-password"
#define SERVER_HOST "10.142.169.170"
```

`SERVER_HOST` ต้องเป็น IP ของเครื่องที่รัน server และ ESP32 ต้องอยู่ Wi-Fi วงเดียวกัน

## Build

```bash
cd C:\MCU\ESP32\ESP32_C3_ICOUGH_ANALYTIC\firmware
pio run
```

## Upload / Monitor

```bash
pio run -t upload
pio device monitor -b 115200
```
