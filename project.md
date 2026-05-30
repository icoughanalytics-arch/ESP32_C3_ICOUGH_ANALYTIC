# iCough Analytic

## Overview
โปรเจคดักจับและวิเคราะห์เสียงไอสำหรับเด็ก (อายุ 0-5 ปี)
อุปกรณ์ทำหน้าที่เป็นไมค์คอยฟังเสียงในห้อง ตัดเสียงคลิป 3 วินาทีส่งไปวิเคราะห์ที่ Cloud

## Goals
- ทดสอบการทำงานของไมค์ INMP441 (I2S) ร่วมกับ ESP32-C3 อ่านค่า RMS และ dBFS เบื้องต้น
- รับไฟล์เสียงไอจาก ESP32-C3 เข้า server
- ทดลองสร้าง AI baseline สำหรับจำแนกเสียงไอด้วย Mel-Spectrogram + CNN
- เป้าหมายระยะถัดไปตามเอกสาร `iCough Analytics 2.pdf`: จำแนก 4 คลาส ได้แก่ Healthy, Pneumonia, Bronchitis, Croup

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

## Server / AI Architecture
- FastAPI server รับไฟล์เสียงจาก ESP32 ผ่าน endpoint `/upload-audio`
- เก็บไฟล์เสียงที่รับเข้ามาไว้ที่ `server/uploads/`
- ชุดข้อมูลทดลองอยู่ที่ `server/cough_sound_data/`
- AI baseline ปัจจุบันใช้ Python + PyTorch + librosa
- Pipeline ปัจจุบัน:
  - อ่านไฟล์ MP3
  - resample เป็น 16 kHz mono
  - เลือกช่วงเสียงที่มีพลังงานสูงสุด ความยาว 3 วินาที
  - แปลงเป็น log-mel spectrogram
  - ส่งเข้า CNN ขนาดเล็กเพื่อจำแนกคลาส

## Dataset
- ข้อมูลปัจจุบันเป็น MP3 ขนาดเล็ก 2 คลาส
- `bronchitis`: 91 ไฟล์
- `pneumonia`: 82 ไฟล์
- รวมทั้งหมด: 173 ไฟล์
- ยังขาดข้อมูล `healthy` และ `croup` สำหรับเป้าหมาย 4 คลาส

## AI Baseline Result
- สคริปต์เทรน: `server/train_cough_cnn.py`
- สคริปต์ทำนายไฟล์เดี่ยว: `server/predict_cough.py`
- สคริปต์ preprocess dataset: `server/preprocess_cough_dataset.py`
- dependency AI: `server/requirements-ai.txt`
- output model: `server/models/cough_cnn.pt`
- output metrics: `server/models/cough_cnn_metrics.json`
- ผลเทรน baseline ล่าสุด:
  - train files: 139
  - validation files: 34
  - validation accuracy: ประมาณ 0.56
  - balanced accuracy: ประมาณ 0.53
  - pneumonia recall ยังต่ำมาก โมเดลยังเอนเอียงไปทาง bronchitis
- สถานะ: pipeline ใช้งานได้แล้ว แต่โมเดลยังไม่พร้อมใช้จริงทางการแพทย์

## Dataset Preprocessing Plan
- เก็บไฟล์ดิบเดิมไว้เสมอ ไม่แก้ทับ
- กันไฟล์ raw test ไว้คลาสละ 10 ไฟล์ก่อนเทรน
- ไฟล์ที่เหลือนำเข้า preprocess:
  - resample เป็น 16 kHz mono
  - หา energy peak ของเสียงไอ
  - ตัดเป็น window 3 วินาทีรอบ peak
  - normalize volume
  - export เป็น `.wav`
- output ปัจจุบัน:
  - `server/processed_cough_data/raw_test/`
  - `server/processed_cough_data/train_segments/`
  - `server/processed_cough_data/metadata.csv`
- ผล preprocess ล่าสุด:
  - bronchitis raw 91, raw test 10, train raw 81, train segments 118
  - pneumonia raw 82, raw test 10, train raw 72, train segments 122
  - รวม train segments 240 คลิป
- คำเตือน: validation ระดับ segment อาจทำให้คะแนนดูดีเกินจริง ถ้ามีหลาย segment จากไฟล์ต้นทางเดียวกันปน train/validation ภายหลังควร split ตาม source file หรือ patient id

## Build & Upload
ใช้ PlatformIO
`pio run -t upload -t monitor`

## Current State
- เขียนโค้ดทดสอบไมค์ (main + inmp441_module) พิมพ์ค่า RMS และ dBFS
- ทดสอบส่งไฟล์เสียงจาก ESP32-C3 เข้า server ได้แล้ว
- เสียงที่ส่งมาชัดระดับหนึ่ง
- ทำ AI baseline 2 คลาสด้วย PyTorch CNN + log-mel spectrogram แล้ว
- อ่านเอกสาร `iCough Analytics 2.pdf` แล้ว พบว่าเป้าหมายระบบเต็มต้องมี 4 คลาสและมี Checklist override logic

## Open Questions
- ระบบประหยัดพลังงาน
- จะเก็บข้อมูลเสียงจาก ESP32 จริงให้ครบ 4 คลาสอย่างไร
- ต้องทำหน้าเว็บ 3 ส่วน: สถิติ, ประเมินความเสี่ยง, ประวัติสำหรับแพทย์
- ต้องเพิ่ม Checklist อาการร่วม และ logic ไฟเขียว/เหลือง/แดง
- ควร export ภาพ Mel-Spectrogram เพื่อใช้ตรวจคุณภาพข้อมูลด้วยตา
- ควรทดลอง transfer learning จากโมเดลเสียง open source เมื่อข้อมูลมากขึ้น

## Issue Log
- AI baseline ปัจจุบันยังแยก pneumonia / bronchitis ได้ไม่ดีพอ
- ข้อมูลปัจจุบันมีแค่ 2 คลาส ยังไม่ตรงสเปกเต็ม 4 คลาส
- dataset อาจมีความยาวไฟล์และคุณภาพเสียงไม่สม่ำเสมอ ต้องตรวจด้วย spectrogram
