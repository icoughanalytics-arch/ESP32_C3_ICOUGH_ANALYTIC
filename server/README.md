# iCough Audio Server

FastAPI server สำหรับรับไฟล์เสียง WAV จาก ESP32 แล้วเก็บไว้ใน `uploads/`

## Run

```bash
cd C:\MCU\ESP32\ESP32_C3_ICOUGH_ANALYTIC\server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Test

```bash
curl http://127.0.0.1:8000/health
```

ไฟล์ที่ ESP32 ส่งเข้ามาจะอยู่ใน `server/uploads/`
