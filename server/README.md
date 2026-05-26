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

## AI training baseline

Data folder:

```powershell
C:\MCU\ESP32\ESP32_C3_ICOUGH_ANALYTIC\server\cough_sound_data
```

Expected labels:

- `cough_sound_data\bronchitis\*.mp3`
- `cough_sound_data\pneumonia\*.mp3`

Install AI dependencies:

```powershell
cd C:\MCU\ESP32\ESP32_C3_ICOUGH_ANALYTIC\server
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple -r requirements-ai.txt
```

Train CNN with log-mel spectrogram input:

```powershell
.\.venv\Scripts\python.exe .\train_cough_cnn.py --epochs 25
```

Outputs:

- `models\cough_cnn.pt`
- `models\cough_cnn_metrics.json`

Predict one audio file:

```powershell
.\.venv\Scripts\python.exe .\predict_cough.py .\cough_sound_data\bronchitis\B1.mp3
```

Current note: this is only an experiment baseline. The first run with 173 MP3 files reached about `0.56` validation accuracy / `0.53` balanced accuracy, so it is not ready for medical use.

ไฟล์ที่ ESP32 ส่งเข้ามาจะอยู่ใน `server/uploads/`
