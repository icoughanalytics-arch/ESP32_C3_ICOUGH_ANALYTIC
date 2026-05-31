# iCough Analytic

## Overview
โปรเจคดักจับและวิเคราะห์เสียงไอสำหรับเด็ก (อายุ 0-5 ปี) เพื่อคัดกรองโรคทางระบบทางเดินหายใจและแจ้งเตือน
- **Hardware (ESP32-C3 + INMP441)**: ดักฟังเสียงตลอดเวลา ตัดเสียงรบกวน (เช่น เสียงคนคุย) อัดเสียงไอแล้วส่งไปวิเคราะห์ที่ Server
- **Server (FastAPI)**: ทำการวิเคราะห์เสียงด้วย AI หากผลการวิเคราะห์เข้าข่าย 4 คลาสหลัก (ปอดบวม, หลอดลมอักเสบ (Bronchitis), โรคครูป (Croup), และสภาวะปกติ (Healthy)) จะทำ 3 อย่าง:
  1. แจ้งเตือนไปยัง Line ของผู้ปกครองผ่านลิงก์ URL + parameter
  2. บันทึกข้อมูลและผลวิเคราะห์ลง Supabase Database
  3. บันทึกไฟล์เสียงลง Supabase Storage
- **Frontend (Next.js)**: เมื่อผู้ปกครองกดลิงก์จาก Line จะเปิดมายังหน้าเว็บ Next.js เพื่อดึงผลวิเคราะห์จาก Parameter มาแสดง พร้อมให้ทำ Checklist ตรวจสอบอาการร่วม (เช่น หายใจเร็ว, ทรวงอกบุ๋ม, เสียงหายใจเข้าดังวี้ด, สัญญาณอันตรายรุนแรง) แล้วประเมินผลลัพธ์ร่วมกับ AI เพื่อสรุปผลเป็นไฟสัญญาณสัญลักษณ์ (เขียว/เหลือง/แดง) พร้อมภาพ Mel-Spectrogram เพื่อส่งต่อให้แพทย์วิเคราะห์อีกครั้ง

## Goals
- พัฒนาเฟิร์มแวร์ ESP32-C3 + INMP441 ให้สามารถอัดเสียงและกรองเสียงรบกวนเบื้องต้นได้
- พัฒนา FastAPI Server สำหรับรับเสียงไอ, เก็บข้อมูลลง Supabase (DB + Storage), และส่ง Line Notification
- พัฒนา AI โมเดลจำแนกเสียงไอครอบคลุม 4 คลาส (Healthy, Pneumonia, Bronchitis, Croup)
- พัฒนาเว็บแอป Next.js สำหรับแสดง Checklist คัดกรองอาการร่วมและแสดงผลสรุปในรูปแบบไฟสัญลักษณ์เขียว/เหลือง/แดง พร้อมแชร์ผลให้แพทย์ได้

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
- ประมวลผลและจำแนกเสียงไอด้วย AI (PyTorch CNN)
- **Supabase Integration**:
  - บันทึกรายละเอียดการวิเคราะห์ (คลาสโรค, ความมั่นใจ) ลง Supabase DB
  - อัปโหลดไฟล์เสียง `.wav` เก็บไว้ใน Supabase Storage
- **Line Notification**: ส่ง URL ที่ผูก Query Parameter (เช่น ID ของการบันทึกเสียง หรือข้อมูล AI) ผ่าน Line Notification เพื่อให้แจ้งเตือนไปยังผู้ปกครอง
- AI Pipeline ปัจจุบัน:
  - อ่านไฟล์เสียง
  - Resample เป็น 16 kHz mono
  - เลือกช่วงเสียงที่มีพลังงานสูงสุด ความยาว 3 วินาที
  - แปลงเป็น Log-Mel Spectrogram
  - ส่งเข้า CNN เพื่อจำแนกคลาส (Healthy, Pneumonia, Bronchitis, Croup)

## Operation Modes
ระบบจะแบ่งรูปแบบการแจ้งเตือนและการแสดงผลเป็น 3 โหมด เพื่อให้เหมาะกับการใช้งานจริงตอนเด็กนอนและการทดลองหน้างาน

### 1. Normal Night Mode
- ใช้ตอนอุปกรณ์เปิดทำงานช่วงเด็กนอน
- ESP32 สามารถส่งเสียงไอขึ้น server ได้หลายครั้งตลอดคืน
- Server วิเคราะห์และบันทึกทุก cough event ลง `cough_records`
- ไม่ควรให้ผู้ปกครองทำ checklist ทุกครั้งที่ไอ เพราะจะรบกวนและเกิดข้อมูลซ้ำ
- ตอนเช้าหน้าเว็บควรแสดงสรุปภาพรวมของคืนนั้น เช่น จำนวนครั้งที่ไอ, event ที่เสี่ยงที่สุด, โรคที่ AI พบมากสุด, confidence สูงสุด, และ timeline การไอ
- ผู้ปกครองทำ checklist เพียงครั้งเดียวต่อคืนหรือหนึ่ง sleep session เพื่อประกอบการประเมินผลรวม

### 2. Alert Mode
- ใช้เมื่อ server พบ event ที่เข้าเกณฑ์เสี่ยงสูง
- ตัวอย่างเงื่อนไข: AI ทำนาย pneumonia / bronchitis / croup ด้วย confidence สูง, หรือผลรวมเข้าเกณฑ์สีแดง
- Server ส่ง Line notification ทันที พร้อมลิงก์ไปยังหน้ารายงานของ event นั้น
- ผู้ปกครองสามารถเปิดดูและทำ checklist เฉพาะ event สำคัญ ไม่ต้องทำทุก event

### 3. Live Demo Mode
- ใช้สำหรับทดสอบหน้างาน, สาธิตระบบ, หรือ debug ระหว่างพัฒนา
- เมื่อ ESP32 ส่งเสียงไอขึ้น server หน้าเว็บควรแสดง event ล่าสุดทันที
- หน้าเว็บควรแสดงสถานะประมาณว่า กำลังวิเคราะห์, ผล AI, confidence, risk level, audio, spectrogram, และปุ่ม checklist
- โหมดนี้เน้น feedback เร็วกว่า workflow ใช้งานจริงตอนกลางคืน

หมายเหตุ: การเลือกว่าจะทำงานแบบ Normal Night, Alert, หรือ Live Demo ควรควบคุมที่ฝั่ง FastAPI/server เป็นหลัก เพราะ server เป็นจุดที่รับเสียง, วิเคราะห์ AI, บันทึก DB, และตัดสินใจว่าจะส่ง Line หรือ broadcast event สดให้หน้าเว็บหรือไม่

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

## Decision Logic (AI + Checklist)
เงื่อนไขการตัดสินใจขึ้นไฟสัญญาณเตือน (เขียว/เหลือง/แดง) บนหน้าจอแอปพลิเคชัน:

| AI Result (คะแนนกลุ่มโรค) | Checklist อาการร่วม | ผลสรุปไฟบนหน้าจอ | คำนิยาม / คำแนะนำแอป |
|---|---|---|---|
| โรคใดก็ได้ | ติ๊กถูกข้อ **ซี่โครงบุ๋ม / เสียงหายใจผิดปกติ (Stridor) / สัญญาณอันตราย** (>= 1 ข้อ) | 🔴 **ไฟสีแดง (High Risk)** | อันตรายขั้นวิกฤต เด็กมีสัญญาณภาวะทางเดินหายใจล้มเหลวเฉียบพลัน โปรดนำส่งห้องฉุกเฉินโรงพยาบาลที่ใกล้ที่สุดทันที |
| ครูป / ปอดบวม / หลอดลมอักเสบ (>= 75%) | ไม่ติ๊ก หรือติ๊กข้อ "หายใจเร็ว" | 🔴 **ไฟสีแดง (High Risk)** | อันตรายขั้นวิกฤต เด็กมีสัญญาณภาวะทางเดินหายใจล้มเหลวเฉียบพลัน โปรดนำส่งห้องฉุกเฉินโรงพยาบาลที่ใกล้ที่สุดทันที |
| ครูป / ปอดบวม / หลอดลมอักเสบ (50% - 74%) | ไม่ติ๊กถูกในข้อใดเลย | 🟡 **ไฟสีเหลือง (Moderate Risk)** | เฝ้าระวัง: เด็กมีภาวะหายใจเร็วเข้าเกณฑ์โรคปอดบวม แนะนำให้พบแพทย์ที่คลินิกหรือโรงพยาบาลชุมชนเพื่อรับยาปฏิชีวนะ |
| ทุกโรคคะแนนเท่ากันก้ำกึ่ง (Edge Case) | ไม่ติ๊กถูกในข้อใดเลย | 🟡 **ไฟสีเหลือง (Moderate Risk)** | เฝ้าระวัง: บังคับทำ Checklist ทันที |
| โรคใดก็ได้ | ติ๊กถูกข้อ **"หายใจเร็ว"** (ข้อเดียว) | 🟡 **ไฟสีเหลือง (Moderate Risk)** | เฝ้าระวัง: แนะนำให้พาเด็กไปพบแพทย์เพื่อตรวจประเมินซ้ำใน 48 ชั่วโมง |
| ปกติ (Healthy >= 80%) | ไม่ติ๊กเลยสักข้อ (ปกติทั้งหมด) | 🟢 **ไฟสีเขียว (Low Risk)** | เด็กมีความเสี่ยงต่ำ ปลอดภัยจากภาวะปอดบวม ให้ดูแลตามอาการที่บ้าน ดื่มน้ำอุ่นเพื่อละลายเสมหะ และมาพบแพทย์หากเด็กไข้ขึ้นหรือไอถี่ขึ้น |

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
1. **การระบุค่าผ่าน URL parameters**:
   - เมื่อกดลิงก์จาก Line มายัง Next.js จะส่งเฉพาะ `audio_id` แล้วให้ Next.js ไปดึงผลวิเคราะห์และข้อมูลเสียงจาก Supabase หรือต้องการให้ยัดผลการวิเคราะห์และข้อมูลเบื้องต้นใส่ไว้ใน URL Parameters เลย (เช่น `/cough-report?ai_class=pneumonia&score=0.85&audio_id=xxx`)?
2. **Line Notification Integration**:
   - ต้องการให้ส่งการแจ้งเตือนโดยใช้ระบบใด? (เช่น Line Notify, Line Messaging API - Broadcast/Push Message, หรือบริการ webhook อื่นๆ)
3. **Checklist & Override Logic**:
   - หน้า Checklist อาการร่วม 4 ข้อหลัก (หายใจเร็ว, ทรวงอกบุ๋ม, เสียงหายใจเข้าดังวี้ด, สัญญาณอันตรายรุนแรง) จะส่งผลต่อผลวิเคราะห์ปลายทางอย่างไร? (เช่น เป็นส่วนประกอบให้คุณหมออ่านเฉยๆ หรือให้โปรแกรมคำนวณและปรับเปลี่ยนระดับไฟสัญญาณเตือน เขียว/เหลือง/แดง แบบอัตโนมัติ)?
4. **การแสดงผล Mel-Spectrogram**:
   - รูปภาพ Mel-Spectrogram ต้องการให้ Server เจนเนอเรตออกมาเป็นไฟล์รูปภาพ (เช่น `.png`) บันทึกบน Supabase Storage เพื่อให้ Next.js โหลดมาแสดง หรือให้ Next.js เป็นตัววาดขึ้นมาเองผ่าน Canvas?

## Issue Log
- AI baseline ปัจจุบันยังจำแนกได้แค่ 2 คลาส (Pneumonia, Bronchitis) และยังต้องปรับปรุงความแม่นยำ
- ข้อมูลเสียง Croup และ Healthy (ปกติ) ยังขาดแคลน ต้องใช้ Dataset เพิ่มเติมหรือทำ Data Augmentation
- คุณภาพเสียงและเสียงรบกวนที่รับมาจาก ESP32-C3 อาจแตกต่างจาก Dataset ที่ใช้เทรน (MP3) ต้องระมัดระวังตอนทดสอบจริง
