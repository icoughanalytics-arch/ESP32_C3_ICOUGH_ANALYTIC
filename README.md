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
- **Active & Verified:** ระบบเฟิร์มแวร์สมบูรณ์และเสถียร
  - บันทึกและวิเคราะห์ไฟล์เสียงไอแบบเรียลไทม์ด้วย Pre-buffer RAM + LittleFS (ปรับขนาด 2.18 MB แบบตัด OTA)
  - รองรับ 3 โหมดผ่านปุ่มกด GPIO 3: Normal Mode (อัดเก็บลง Flash และ Batch Upload ทุก 10 นาที), Test Mode (อัดและส่งทันที 1 ไฟล์), และ WiFi Config Mode (เปิด SoftAP + Captive Portal หน้าตั้งค่าสวยงาม)
  - เชื่อมต่อ HTTP ไปยัง VPS Server พอร์ต 8000 พร้อมกลไกความปลอดภัยในการลบไฟล์เสียงทิ้งทันทีเมื่อส่งสำเร็จ เพื่อรักษาพื้นที่บน Flash ให้ว่างเสมอ

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
  - [x] พัฒนาระบบ Batch Upload (LittleFS Queue) และตัวตั้งค่า NVS Wi-Fi Manager (SoftAP + Captive Portal)
- [x] **Phase 3: Web Application & Checklist**
  - [x] พัฒนาหน้าเว็บคัดกรองร่วม Next.js แสดงสรุปรายงานผลและทำ Checklist 4 ข้อเพื่อประเมินไฟ เขียว/เหลือง/แดง สำเร็จเรียบร้อย
  - [x] แยกจัดหมวดหมู่ POC/Test event และบันทึกข้อมูลอย่างสมบูรณ์ลง Supabase
  - [x] ตั้งค่าความปลอดภัย HTTPS (Nginx Reverse Proxy + Certbot SSL) บนโดเมน `icough.chickenkiller.com` สำหรับการคุยกับ LINE OA
- [/] **Phase 4: Optimization, Enclosure & Battery Testing**
  - [/] พัฒนาและเพิ่มประสิทธิภาพความแม่นยำในการจำแนกประเภทการไอแต่ละแบบ (Final Cough Test & Model Accuracy Tuning)
  - [/] ทดสอบอัตราการใช้พลังงานของแบตเตอรี่ความจุ 520mAh เพื่อประเมินเวลาการทำงานจริงของระบบ
  - [/] ออกแบบตัวเคส (3D Enclosure) และสั่งพิมพ์ด้วยเครื่อง Elegoo 3D Printer เพื่อประกอบอุปกรณ์จริง


## License
TBD
