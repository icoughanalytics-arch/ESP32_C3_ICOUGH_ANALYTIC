# iCough Analytic

## Overview
โปรเจคดักจับและวิเคราะห์เสียงไอสำหรับเด็ก (อายุ 0-5 ปี)
อุปกรณ์ทำหน้าที่เป็นไมค์คอยฟังเสียงในห้อง ตัดเสียงคลิป 3 วินาทีส่งไปวิเคราะห์ที่ Cloud

## Goals
ทดสอบการทำงานของไมค์ INMP441 (I2S) ร่วมกับ ESP32-C3 อ่านค่า RMS และ dBFS เบื้องต้น

## Hardware
- ESP32-C3 (Lolin C3 Mini)
- INMP441 (I2S Microphone)

## Pin Map

| Function | Pin | Device | Direction | Notes |
|---|---|---|---|---|
| I2S BCLK | 4 | INMP441 | Output | Clock |
| I2S WS/LRCK | 5 | INMP441 | Output | Word Select |
| I2S DATA | 6 | INMP441 | Input | Data In |
| L/R | GND | INMP441 | - | เลือก Left channel |

## Electrical / Safety Notes
- ขา L/R ของไมค์ต้องต่อ GND
- อุปกรณ์เป้าหมายจะอยู่ใกล้เด็ก ควรคำนึงถึงแบตเตอรี่และความปลอดภัย

## Firmware Architecture
- ไมค์ (INMP441) ฟังเสียงตลอดเวลา
- เก็บเสียงพักไว้ใน RAM (Pre-buffer) แบบ Circular Buffer
- เมื่อเกิด Trigger (เช่น เสียงดังเกินกำหนด) จะอัดคลิปเสียงความยาว 3-5 วินาที
- เขียนไฟล์เสียง (.wav) ลงระบบไฟล์ LittleFS
- กลับไปฟังเสียงและเก็บลง Pre-buffer ต่อทันที
- เปิด Wi-Fi เป็นรอบเวลา (เช่น ทุก 5-10 นาที หรือเมื่อมีไฟล์ครบ N ไฟล์)
- อัปโหลดไฟล์เสียงทั้งหมดในคิว
- หากส่งสำเร็จค่อยลบไฟล์ออกจาก LittleFS

## Libraries
- Arduino `driver/i2s.h` (Built-in)

## Build & Upload
ใช้ PlatformIO
`pio run -t upload -t monitor`

## Current State
- เขียนโค้ดทดสอบไมค์ (main + inmp441_module) พิมพ์ค่า RMS และ dBFS

## Open Questions
- การเชื่อมต่อ Wi-Fi และส่งไฟล์เสียงขึ้น Cloud
- ระบบประหยัดพลังงาน

## Issue Log
- TBD
