# Hardware & Library Specs

## Hardware

| Part | Model | Interface | Notes |
|---|---|---|---|
| MCU | ESP32-C3 (Lolin C3 Mini) | - | - |
| Mic | INMP441 | I2S | Omni-directional, Bottom port |

## Pin Mapping (ESP32-C3)

| Component | ESP32-C3 Pin | Mode | Connection Details |
|---|---|---|---|
| **Button** | `GPIO 3` | INPUT_PULLUP | Active Low (Short: Test Mode / Long 3s: WiFi Config) |
| **LED** | `GPIO 10` | OUTPUT | Status Indicator |
| **INMP441 Mic (SD)** | `GPIO 6` | I2S DATA | Serial Data |
| **INMP441 Mic (WS)** | `GPIO 5` | I2S WS | Word Select / LRCK |
| **INMP441 Mic (SCK)** | `GPIO 4` | I2S BCLK | Bit Clock |
| **INMP441 Mic (L/R)** | `GND` | - | Selects Left Channel |

## Libraries

| Purpose | Library | Status | Notes |
|---|---|---|---|
| I2S Audio | driver/i2s.h (built-in) | active | ESP-IDF I2S driver |

## Datasheet / References
- ESP32-C3 Datasheet
- INMP441 Datasheet

## Hardware Issues
- ไม่พบปัญหาหลักในการเชื่อมต่อเบื้องต้น เสียงสัญญาณที่บันทึกชัดเจนดี 
- ขา L/R ของไมค์ต้องมั่นใจว่าต่อลง GND อย่างแน่นหนาเพื่อป้องกันเสียงรบกวน (Noise) และเลือกใช้ Left channel

## Test Notes
- [x] ทดสอบการอ่านค่าสัญญาณเสียงจากไมค์ INMP441 ผ่าน I2S ด้วย ESP32-C3 ได้สำเร็จ
- [x] คำนวณค่า RMS และแสดงผลระดับความดังเป็น dBFS บน Serial Monitor ได้รีลไทม์
- [x] ทดสอบส่งไฟล์เสียง WAV จาก ESP32-C3 ไปยัง FastAPI Server สำเร็จ สัญญาณเสียงมีความสมบูรณ์

