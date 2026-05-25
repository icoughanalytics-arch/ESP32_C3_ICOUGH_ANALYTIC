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

## Roadmap
- ทดสอบไมโครโฟน (ปัจจุบัน)
- บันทึกเสียงลง buffer/SD
- ส่งไฟล์เสียงขึ้น Cloud ผ่าน Wi-Fi
- ระบบประหยัดพลังงาน

## License
TBD
