# iCough Analytic (Firmware)

โปรเจคดักจับและวิเคราะห์เสียงไอสำหรับเด็ก (อายุ 0-5 ปี) ส่วน Firmware สำหรับ ESP32-C3

## Features
- ทดสอบอ่านเสียงจากไมค์ INMP441 ผ่าน I2S
- คำนวณค่าพลังงานเสียง (RMS) และแสดงผลความดัง (dBFS)

## Hardware
- ESP32-C3 (Lolin C3 Mini)
- INMP441 I2S Microphone

## Pin Map

| Function | Pin | Notes |
|---|---|---|
| BCLK | 4 | |
| WS (LRCLK) | 5 | |
| DATA IN | 6 | |
| L/R | GND | |

## Wiring Notes
- ต่อ L/R ลง GND เพื่อเลือกใช้ไมค์ฝั่งซ้าย
- ใช้ไฟ 3.3V

## Firmware Status
- POC: ทดสอบไมโครโฟนและคำนวณ dBFS เบื้องต้น

## Getting Started

```bash
pio run
pio run -t upload
pio device monitor -b 115200
```

## Safety
ระมัดระวังการประกอบกับแหล่งจ่ายไฟ แบตเตอรี่ โดยเฉพาะหากอุปกรณ์สุดท้ายต้องไปอยู่ใกล้เด็ก

## Roadmap & Status
- [x] **Phase 1: Hardware Integration**
  - [x] ทดสอบไมโครโฟน INMP441 ผ่าน I2S บน ESP32-C3
  - [x] คำนวณความดังเป็น dBFS แสดงผลรีลไทม์
- [x] **Phase 2: Cloud Connection & AI Backend**
  - [x] ส่งไฟล์เสียงไอจาก ESP32 ขึ้น Cloud/FastAPI Server ผ่าน Wi-Fi
  - [x] ระบบจำแนกโรค 4 คลาส (CNN + Google HeAR + Acoustic ML) ด้วยเทคนิค Ensemble (ความแม่นยำ 68.18%)
  - [x] เชื่อมโยงระบบจัดเก็บประวัติเสียงไอและรูป Spectrogram ลงฐานข้อมูล Supabase (DB + Storage)
  - [x] ส่งลิงก์รายงานผลการวิเคราะห์และแจ้งเตือน Line Notify ไปยังผู้ปกครองเมื่อเสี่ยงสูง
- [/] **Phase 3: Web Application & Checklist**
  - [/] พัฒนาหน้าเว็บคัดกรองร่วม Next.js แสดงสรุปรายงานผลและทำ Checklist 4 ข้อเพื่อประเมินไฟ เขียว/เหลือง/แดง (กำลังพัฒนา)
- [ ] **Phase 4: Power Optimization**
  - [ ] พัฒนาระบบประหยัดพลังงานของเฟิร์มแวร์ ESP32 (Deep Sleep / Light Sleep)


## License
TBD
