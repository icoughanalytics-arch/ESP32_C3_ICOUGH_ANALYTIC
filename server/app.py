import os
import sys
import uuid
import json
import pickle
import datetime
import threading
from pathlib import Path
from time import strftime

import numpy as np
import librosa
import soundfile as sf
import torch
from torch import nn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

# กำหนดให้ Matplotlib รันแบบ Headless เพื่อความปลอดภัยบน Web Server
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa.display

# ป้องกัน TensorFlow พิมพ์ log แจ้งเตือนจำนวนมาก
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    import tensorflow as tf
    import tensorflow_hub as hub
    import csv
except ImportError:
    tf = None
    hub = None
    print("Warning: ไม่พบ tensorflow หรือ tensorflow-hub อาจส่งผลกระทบต่อ Cough Filter")

# ตั้งค่า Path ค้นหาโมดูลในโฟลเดอร์ server
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# นำเข้าตัววิเคราะห์ฟิสิกส์
try:
    from acoustic_rules import analyze_cough_acoustic
except ImportError:
    print("Error: ไม่พบโมดูล acoustic_rules.py ในเซิร์ฟเวอร์")
    sys.exit(1)

import line_bot

# กำหนดค่าคงที่
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
TEST_UPLOAD_DIR = UPLOAD_DIR / "test"
NORMAL_UPLOAD_DIR = UPLOAD_DIR / "normal"
TEST_UPLOAD_DIR.mkdir(exist_ok=True)
NORMAL_UPLOAD_DIR.mkdir(exist_ok=True)
MODEL_DIR = BASE_DIR / "models"
LABELS = ["bronchitis", "croup", "normal", "pneumonia"]
HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_NAME = "google/hear-pytorch"
DEFAULT_DEVICE_ID = "22222222-2222-2222-2222-222222222222"

# ตัวแปร Global สำหรับเก็บโมเดล
device = "cuda" if torch.cuda.is_available() else "cpu"
YAMNet_model = None
YAMNet_class_names = None
YAMNet_class_indices = None
HeAR_model = None
CNN_model = None
HeAR_classifier = None
acoustic_scaler = None
acoustic_model = None
ensemble_config = {
    "weight_cnn": 0.05,
    "weight_hear": 0.55,
    "weight_acoustic": 0.40
}
supabase_url = None
supabase_key = None
cron_secret = ""

spec_lock = threading.Lock()

# ----------------------------------------------------
# นิยามโครงสร้างสถาปัตยกรรมโมเดล PyTorch
# ----------------------------------------------------
class TinyCoughCnn(nn.Module):
    def __init__(self, classes: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Dropout(0.15),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Dropout(0.2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(64, classes),
        )
    def forward(self, x):
        return self.net(x)

class PyTorchRegularizedMLP(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=64, num_classes=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(hidden_dim, num_classes)
        )
    def forward(self, x):
        return self.net(x)

# ----------------------------------------------------
# ฟังก์ชันช่วยดาวน์โหลดและดึงการตั้งค่า
# ----------------------------------------------------
def load_supabase_credentials():
    global supabase_url, supabase_key, cron_secret, HF_TOKEN
    # พยายามอ่านจากไฟล์ .env ของ Next.js
    env_path = BASE_DIR.parent / "web" / "i-cough" / ".env"
    supabase_url = "https://tvbtogovalfhudduqssi.supabase.co"
    supabase_key = "sb_publishable_NAX5cakb_GxohbsICN75pQ_9s7lBZ4z"
    line_channel_secret = ""
    line_channel_access_token = ""
    line_register_code = "123456"
    cron_secret = "icough_cron_2026"
    
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line or raw_line.startswith("#"):
                        continue
                    if "=" in raw_line:
                        k, v = raw_line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == "NEXT_PUBLIC_SUPABASE_URL":
                            supabase_url = v
                        elif k == "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY":
                            supabase_key = v
                        elif k == "HF_TOKEN":
                            HF_TOKEN = v
                        elif k == "LINE_CHANNEL_SECRET":
                            line_channel_secret = v
                        elif k == "LINE_CHANNEL_ACCESS_TOKEN":
                            line_channel_access_token = v
                        elif k == "LINE_REGISTER_CODE":
                            line_register_code = v
                        elif k == "CRON_SECRET":
                            cron_secret = v
            print(f"Loaded config from .env: URL={supabase_url}, Key length={len(supabase_key)}")
        except Exception as e:
            print(f"Warning: เกิดข้อผิดพลาดในการเปิดไฟล์ .env: {e}")
    else:
        print("Warning: ไม่พบไฟล์ .env ใช้ค่า Fallback เริ่มต้น")
    
    # ตั้งค่า LINE Bot module
    line_bot.configure(
        channel_secret=line_channel_secret,
        channel_access_token=line_channel_access_token,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        register_code=line_register_code
    )
    if line_bot.is_configured():
        print(f"LINE Bot configured: register_code={line_register_code}")
    else:
        print("Warning: LINE Bot credentials not found in .env")

# ฟังก์ชันแปลง Spectrogram สำหรับ CNN
def load_log_mel_from_array(audio: np.ndarray, sample_rate: int, duration: float, n_mels: int):
    samples = int(sample_rate * duration)
    if len(audio) < samples:
        audio = np.pad(audio, (0, samples - len(audio)))
    elif len(audio) > samples:
        frame = max(1, sample_rate // 10)
        energy = np.convolve(audio * audio, np.ones(frame, dtype=np.float32), mode="same")
        center = int(np.argmax(energy))
        start = center - samples // 2
        start = max(0, min(start, len(audio) - samples))
        audio = audio[start : start + samples]

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sample_rate,
        n_fft=512,
        hop_length=160,
        n_mels=n_mels,
        fmin=40,
        fmax=sample_rate // 2,
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    log_mel = (log_mel - log_mel.mean()) / (log_mel.std() + 1e-6)
    return log_mel.astype(np.float32)

# ฟังก์ชันสกัดคุณลักษณะเด่นจาก Google HeAR
def extract_hear_embedding_from_array(audio: np.ndarray, model, target_device):
    target_samples = 32000 # 2 วินาที @ 16kHz
    if len(audio) < target_samples:
        audio = np.pad(audio, (0, target_samples - len(audio)))
    elif len(audio) > target_samples:
        audio = audio[:target_samples]
        
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=16000,
        n_fft=1024,
        hop_length=160,
        n_mels=128,
        power=2.0
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    log_mel = (log_mel - log_mel.mean()) / (log_mel.std() + 1e-6)
    spectrogram = log_mel.T
    
    target_frames = 192
    if spectrogram.shape[0] < target_frames:
        pad_width = target_frames - spectrogram.shape[0]
        spectrogram = np.pad(spectrogram, ((0, pad_width), (0, 0)), mode='constant')
    elif spectrogram.shape[0] > target_frames:
        spectrogram = spectrogram[:target_frames, :]
        
    pixel_values = torch.tensor(spectrogram, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(target_device)
    with torch.no_grad():
        outputs = model(pixel_values)
        # สารสกัด 512-dim embedding จาก 'pooler_output'
        embeddings = outputs["pooler_output"]
        return embeddings.cpu().numpy()

# ฟังก์ชันสร้างภาพ Spectrogram เพื่ออัปโหลดขึ้นหน้าเว็บ Next.js
def make_spectrogram_image(audio_path: Path, image_path: Path, sample_rate: int):
    audio, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160,
        n_mels=64,
        fmin=40,
        fmax=sr // 2,
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)

    with spec_lock:
        plt.figure(figsize=(7, 3), dpi=160)
        librosa.display.specshow(
            log_mel,
            sr=sr,
            hop_length=160,
            x_axis="time",
            y_axis="mel",
            cmap="magma",
            fmin=40,
            fmax=sr // 2,
        )
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.savefig(image_path, bbox_inches="tight", pad_inches=0)
        plt.close()

# ฟังก์ชันแจ้งเตือนทาง LINE Messaging API (ผ่าน line_bot module)
# ดูรายละเอียดใน line_bot.py

# ----------------------------------------------------
# เริ่มต้น FastAPI App
# ----------------------------------------------------
app = FastAPI(title="iCough Audio Analytics Server")

# ตั้งค่า CORS เพื่อให้ Next.js ฝั่ง frontend เรียกใช้ได้สะดวก
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Event Startup โหลดโมเดลทั้งหมดขึ้นมารอบแรก
# ----------------------------------------------------
@app.on_event("startup")
def startup_event():
    global YAMNet_model, YAMNet_class_names, YAMNet_class_indices
    global HeAR_model, CNN_model, HeAR_classifier
    global acoustic_scaler, acoustic_model, ensemble_config
    
    print("\n" + "=" * 60)
    print("🚀 เริ่มต้นระบบและดาวน์โหลดโหลดโมเดลทั้งหมดไปยังหน่วยความจำ...")
    print("=" * 60)
    
    # 1. ดึง Credentials ของ Supabase
    load_supabase_credentials()
    
    # 2. โหลด YAMNet จาก TF Hub
    try:
        print("-> กำลังโหลดโมเดล YAMNet (Cough Filter)...")
        if hub is not None:
            YAMNet_model = hub.load('https://tfhub.dev/google/yamnet/1')
            class_map_path = YAMNet_model.class_map_path().numpy()
            names = []
            with tf.io.gfile.GFile(class_map_path, 'r') as csv_file:
                reader = csv.reader(csv_file)
                next(reader)
                for row in reader:
                    if len(row) >= 3:
                        names.append(row[2])
            YAMNet_class_names = np.array(names)
            
            # ค้นหา index ของกลุ่มเสียงไอและระบบทางเดินหายใจ
            target_classes = ["Cough", "Grunt", "Throat clearing", "Sneeze", "Owl", "Hoot", "Whale vocalization"]
            YAMNet_class_indices = {}
            for c in target_classes:
                idx = np.where(YAMNet_class_names == c)[0]
                if len(idx) > 0:
                    YAMNet_class_indices[c] = idx[0]
            print("โหลดโมเดล YAMNet สำเร็จ!")
        else:
            print("Warning: ข้ามการโหลด YAMNet (เนื่องจากไม่ได้ติดตั้ง tensorflow-hub)")
    except Exception as e:
        print(f"Error loading YAMNet: {e}")
        
    # 3. โหลด Google HeAR จาก Hugging Face
    try:
        print(f"-> กำลังโหลดโมเดล Google HeAR ({MODEL_NAME}) จาก Hugging Face (ขั้นตอนนี้อาจใช้เวลา)...")
        print(f"   [DEBUG] HF_TOKEN length: {len(HF_TOKEN)}, starts with: '{HF_TOKEN[:8]}'")
        from transformers import AutoModel
        HeAR_model = AutoModel.from_pretrained(MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
        HeAR_model = HeAR_model.to(device)
        HeAR_model.eval()
        print(f"โหลดโมเดล Google HeAR สำเร็จ! อุปกรณ์: {device.upper()}")
    except Exception as e:
        print(f"Error loading Google HeAR: {e}")
        
    # 4. โหลด Custom CNN (Path A)
    cnn_path = MODEL_DIR / "cough_cnn.pt"
    if cnn_path.exists():
        try:
            print("-> กำลังโหลดโมเดล Custom CNN (Path A)...")
            cnn_checkpoint = torch.load(cnn_path, map_location=device, weights_only=False)
            CNN_model = TinyCoughCnn(classes=len(LABELS)).to(device)
            CNN_model.load_state_dict(cnn_checkpoint["model_state"])
            CNN_model.eval()
            print("โหลด Custom CNN สำเร็จ!")
        except Exception as e:
            print(f"Error loading Custom CNN: {e}")
    else:
        print(f"Warning: ไม่พบไฟล์โมเดล CNN ที่ {cnn_path}")
        
    # 5. โหลด HeAR MLP Classifier (Path B)
    hear_clf_path = MODEL_DIR / "hear_classifier.pt"
    if hear_clf_path.exists():
        try:
            print("-> กำลังโหลดโมเดล HeAR MLP Classifier (Path B)...")
            hear_checkpoint = torch.load(hear_clf_path, map_location=device, weights_only=False)
            HeAR_classifier = PyTorchRegularizedMLP(input_dim=512, hidden_dim=64, num_classes=len(LABELS)).to(device)
            HeAR_classifier.load_state_dict(hear_checkpoint["model_state"])
            HeAR_classifier.eval()
            print("โหลด HeAR MLP Classifier สำเร็จ!")
        except Exception as e:
            print(f"Error loading HeAR MLP Classifier: {e}")
    else:
        print(f"Warning: ไม่พบไฟล์ HeAR Classifier ที่ {hear_clf_path}")
        
    # 6. โหลด Acoustic ML Classifier (Path C)
    acoustic_clf_path = MODEL_DIR / "acoustic_classifier.pkl"
    if acoustic_clf_path.exists():
        try:
            print("-> กำลังโหลดโมเดล Acoustic ML Classifier (Path C)...")
            with open(acoustic_clf_path, 'rb') as f:
                acoustic_pack = pickle.load(f)
            acoustic_scaler = acoustic_pack["scaler"]
            acoustic_model = acoustic_pack["model"]
            print("โหลด Acoustic SVM Classifier สำเร็จ!")
        except Exception as e:
            print(f"Error loading Acoustic ML Classifier: {e}")
    else:
        print(f"Warning: ไม่พบไฟล์ Acoustic Classifier ที่ {acoustic_clf_path}")
        
    # 7. โหลดค่าน้ำหนัก Ensemble Config
    config_path = MODEL_DIR / "ensemble_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                ensemble_config = json.load(f)
            print(f"โหลดค่า Ensemble Config สำเร็จ: CNN={ensemble_config.get('weight_cnn')*100:.1f}%, HeAR={ensemble_config.get('weight_hear')*100:.1f}%, Acoustic={ensemble_config.get('weight_acoustic')*100:.1f}%")
        except Exception as e:
            print(f"Error parsing ensemble config: {e}")
            
    print("=" * 60)
    print("🎉 โมเดลทั้งหมดพร้อมประมวลผลเรียบร้อยแล้ว!")
    print("=" * 60 + "\n")

# ----------------------------------------------------
# ลอจิกการคัดกรองเสียงไอ (Cough Filter / Detection)
# ----------------------------------------------------
def run_cough_filter(audio_path: Path):
    """วิเคราะห์คัดกรองว่าเป็นเสียงไอจริงหรือไม่ โดยใช้ YAMNet ร่วมกับ RMS และ ZCR"""
    if YAMNet_model is None or YAMNet_class_indices is None:
        # Fallback กรณีไม่มี YAMNet ให้ผ่านไปวิเคราะห์โรคเลย
        print("Warning: ไม่มีโมเดล YAMNet ขออนุญาตข้าม Cough Filter")
        return True, 1.0, {"warning": "YAMNet model not loaded"}
        
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    scores, _, _ = YAMNet_model(audio)
    scores_numpy = scores.numpy()
    
    # ดึง CONFIG ของ Cough Filter
    class_factors = {
        "Cough": 2.0, "Grunt": 1.0, "Throat clearing": 1.0,
        "Sneeze": 1.0, "Owl": 1.0, "Hoot": 1.0, "Whale vocalization": 1.0
    }
    
    target_idxs = []
    target_weights = []
    for cls_name, factor in class_factors.items():
        if cls_name in YAMNet_class_indices:
            target_idxs.append(YAMNet_class_indices[cls_name])
            target_weights.append(factor)
            
    if len(target_idxs) > 0:
        weighted_scores = scores_numpy[:, target_idxs] * np.array(target_weights)
        resp_scores_per_frame = np.sum(weighted_scores, axis=1)
    else:
        resp_scores_per_frame = np.zeros(len(scores_numpy))
        
    max_resp = np.max(resp_scores_per_frame)
    ai_score = min(1.0, float(max_resp))
    
    # 2. ฟิสิกส์คัดกรอง (Acoustic components)
    rms = librosa.feature.rms(y=audio)[0]
    max_rms = np.max(rms)
    
    zcr = librosa.feature.zero_crossing_rate(y=audio)[0]
    mean_zcr = np.mean(zcr)
    
    # RMS Score
    rms_score_comp = min(50.0, (max_rms / 0.10) * 50.0)
    
    # ZCR Score
    zcr_dist = abs(mean_zcr - 0.20)
    zcr_score_comp = max(0.0, 50.0 - (zcr_dist / 0.15) * 50.0)
    
    acoustic_score = (rms_score_comp + zcr_score_comp) / 100.0
    
    # คะแนน Hybrid Score
    hybrid_score = (0.5 * ai_score) + (0.5 * acoustic_score)
    
    # เกณฑ์ตัดสินว่าเป็นเสียงไอ
    is_cough = (hybrid_score >= 0.35) and (max_resp >= 0.05)
    
    details = {
        "ai_confidence": float(ai_score),
        "acoustic_score": float(acoustic_score),
        "max_rms": float(max_rms),
        "mean_zcr": float(mean_zcr),
        "hybrid_score": float(hybrid_score)
    }
    return is_cough, hybrid_score, details

# ----------------------------------------------------
# REST API Endpoints
# ----------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "models": {
            "yamnet": YAMNet_model is not None,
            "hear": HeAR_model is not None,
            "cnn": CNN_model is not None,
            "hear_mlp": HeAR_classifier is not None,
            "acoustic_svm": acoustic_model is not None
        }
    }

@app.post("/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    device_code: str = Query("ICOUGH-REAL-MOCK-001", description="Device code or token of ESP32"),
    mode: str = Query("normal", description="Operation mode: 'normal' or 'test'")
):
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    filename = f"{strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{suffix}"
    
    target_dir = TEST_UPLOAD_DIR if mode == "test" else NORMAL_UPLOAD_DIR
    audio_path = target_dir / filename
    
    # 1. เขียนไฟล์เสียงลงเครื่องชั่วคราว
    try:
        audio_content = await file.read()
        audio_path.write_bytes(audio_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ไม่สามารถบันทึกไฟล์เสียงได้: {e}")
        
    # 2. รัน Cough Filter (คัดกรองเสียงไอ)
    try:
        is_cough, filter_score, filter_details = run_cough_filter(audio_path)
    except Exception as e:
        # หากเกิดข้อผิดพลาดในการคัดกรองเสียง ให้บันทึก log และอนุญาตให้ไปต่อได้ (กันระบบล่ม)
        print(f"Error during cough filter processing: {e}")
        is_cough, filter_score, filter_details = True, 1.0, {"error": str(e)}
        
    if not is_cough:
        # หากไม่ใช่เสียงไอ ให้ลบไฟล์และตอบกลับปฏิเสธทันที
        try:
            os.remove(audio_path)
        except Exception:
            pass
        return {
            "is_cough": False,
            "message": "สัญญาณเสียงถูกกรองออกเนื่องจากไม่ใช่เสียงไอ (ต่ำกว่าเกณฑ์คัดกรอง)",
            "details": filter_details
        }
        
    # 3. หากเป็นเสียงไอจริง ให้ประมวลผลโรค (Classification Pipeline)
    print(f"\n[Cough Detected] เริ่มการจำแนกโรคจากไฟล์เสียง {filename}...")
    
    # เจนรูปภาพ Spectrogram สำหรับการแสดงผลหน้าเว็บ
    spectrogram_filename = filename.replace(suffix, ".png")
    spectrogram_path = target_dir / spectrogram_filename
    try:
        make_spectrogram_image(audio_path, spectrogram_path, 16000)
    except Exception as e:
        print(f"Warning: ไม่สามารถสร้างรูป spectrogram ได้: {e}")
        
    # คำนวณทำนายจากโมเดลทั้ง 3 เส้นทาง
    probs_cnn = np.zeros(len(LABELS))
    probs_hear = np.zeros(len(LABELS))
    probs_acoustic = np.zeros(len(LABELS))
    
    audio_16k, sr = librosa.load(audio_path, sr=16000, mono=True)
    
    # --- Path A: CNN ---
    if CNN_model is not None:
        try:
            # ใช้ config CNN จากโมเดลหรือตั้งค่าเริ่มต้น (sr=16000, duration=3s, n_mels=64)
            features_cnn = load_log_mel_from_array(audio_16k, sample_rate=16000, duration=3.0, n_mels=64)
            x_cnn = torch.from_numpy(features_cnn).unsqueeze(0).unsqueeze(0).to(device)
            with torch.no_grad():
                outputs_cnn = torch.softmax(CNN_model(x_cnn), dim=1)
                probs_cnn = outputs_cnn.squeeze(0).cpu().numpy()
        except Exception as e:
            print(f"Error in CNN inference: {e}")
            
    # --- Path B: HeAR + MLP ---
    if HeAR_model is not None and HeAR_classifier is not None:
        try:
            embeddings_hear = extract_hear_embedding_from_array(audio_16k, HeAR_model, device)
            with torch.no_grad():
                inputs_hear = torch.tensor(embeddings_hear, dtype=torch.float32).to(device)
                outputs_hear = torch.softmax(HeAR_classifier(inputs_hear), dim=1)
                probs_hear = outputs_hear.squeeze(0).cpu().numpy()
        except Exception as e:
            print(f"Error in HeAR inference: {e}")
            
    # --- Path C: Acoustic SVM ---
    if acoustic_model is not None and acoustic_scaler is not None:
        try:
            _, feat_dict = analyze_cough_acoustic(audio_path)
            feat_vector = [
                feat_dict["wi_peaks"],
                feat_dict["mean_zcr"],
                feat_dict["mean_centroid"],
                feat_dict["er_croup"],
                feat_dict["er_bronchitis"],
                feat_dict["t_cough"]
            ]
            feat_vector_scaled = acoustic_scaler.transform([feat_vector])
            probs_acoustic = acoustic_model.predict_proba(feat_vector_scaled)[0]
        except Exception as e:
            print(f"Error in Acoustic ML inference: {e}")
            # ใช้แบบ Rule-based normalized probabilities แทนในกรณีฉุกเฉิน
            try:
                prob_dict, _ = analyze_cough_acoustic(audio_path)
                probs_acoustic = np.array([prob_dict[c] for c in LABELS])
            except Exception:
                pass

    # 4. รวมโมเดลแบบ Ensemble
    w_cnn = ensemble_config.get("weight_cnn", 0.05)
    w_hear = ensemble_config.get("weight_hear", 0.55)
    w_acoustic = ensemble_config.get("weight_acoustic", 0.40)
    
    # รวมผลลัพธ์ความน่าจะเป็น
    probs_ensemble = (w_cnn * probs_cnn) + (w_hear * probs_hear) + (w_acoustic * probs_acoustic)
    
    # บีบสเกลให้อัตราส่วนรวมกันเท่ากับ 1.0 พอดี
    sum_probs = np.sum(probs_ensemble)
    if sum_probs > 0:
        probs_ensemble = probs_ensemble / sum_probs
    else:
        probs_ensemble = np.array([0.25, 0.25, 0.25, 0.25])
        
    predictions = {LABELS[i]: float(probs_ensemble[i]) for i in range(len(LABELS))}
    
    # 5. คำนวณระดับความเสี่ยง (Risk Level) ตามกฎ
    risk_level = "moderate" # ค่าเริ่มต้น
    
    # หาคลาสและคะแนนสูงสุดที่ไม่ใช่ Healthy
    risk_labels = ["bronchitis", "croup", "pneumonia"]
    highest_risk_score = max(predictions[c] for c in risk_labels)
    
    if highest_risk_score >= 0.75:
        risk_level = "high"
    elif highest_risk_score >= 0.50:
        risk_level = "moderate"
    elif predictions["normal"] >= 0.80:
        risk_level = "low"
        
    print(f"ผลลัพธ์ Ensemble: {predictions} | ระดับความเสี่ยงเบื้องต้น: {risk_level.upper()}")
    
    # 6. อัปโหลดข้อมูลและภาพไปยัง Supabase
    audio_supabase_url = f"{supabase_url}/storage/v1/object/public/cough-audio/{filename}"
    spectrum_supabase_url = f"{supabase_url}/storage/v1/object/public/cough-spectrum/{spectrogram_filename}"
    record_uuid = str(uuid.uuid4())
    
    supabase_success = False
    if supabase_url and supabase_key:
        try:
            print("-> กำลังส่งไฟล์เสียงและภาพไปยัง Supabase Storage...")
            # อัปโหลดไฟล์เสียง
            audio_data = audio_path.read_bytes()
            upload_audio_res = requests.post(
                f"{supabase_url}/storage/v1/object/cough-audio/{filename}",
                headers={
                    "Authorization": f"Bearer {supabase_key}",
                    "apikey": supabase_key,
                    "Content-Type": "audio/wav"
                },
                data=audio_data,
                timeout=12
            )
            print(f"Supabase Storage (Audio) Response: {upload_audio_res.status_code} | {upload_audio_res.text}")
            
            # อัปโหลด Spectrogram รูปภาพ
            if spectrogram_path.exists():
                spectrum_data = spectrogram_path.read_bytes()
                upload_spec_res = requests.post(
                    f"{supabase_url}/storage/v1/object/cough-spectrum/{spectrogram_filename}",
                    headers={
                        "Authorization": f"Bearer {supabase_key}",
                        "apikey": supabase_key,
                        "Content-Type": "image/png"
                    },
                    data=spectrum_data,
                    timeout=12
                )
                print(f"Supabase Storage (Spectrogram) Response: {upload_spec_res.status_code} | {upload_spec_res.text}")
                
            # ค้นหา device_id ใน database
            device_id = DEFAULT_DEVICE_ID
            device_check_res = requests.get(
                f"{supabase_url}/rest/v1/device?device_code=eq.{device_code}",
                headers={
                    "Authorization": f"Bearer {supabase_key}",
                    "apikey": supabase_key
                },
                timeout=8
            )
            if device_check_res.status_code == 200 and len(device_check_res.json()) > 0:
                device_id = device_check_res.json()[0]["id"]
                
            # บันทึกข้อมูลการวิเคราะห์ลง DB
            print("-> กำลังบันทึกประวัติลง Supabase Database...")
            db_payload = {
                "id": record_uuid,
                "device_id": device_id,
                "spectrum_path": spectrum_supabase_url,
                "audio_path": audio_supabase_url,
                "pneumonia_score": float(predictions["pneumonia"]),
                "croup_score": float(predictions["croup"]),
                "bronchitis_score": float(predictions["bronchitis"]),
                "normal_score": float(predictions["normal"]),
                "risk_level": risk_level,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            
            db_res = requests.post(
                f"{supabase_url}/rest/v1/cough_record",
                headers={
                    "Authorization": f"Bearer {supabase_key}",
                    "apikey": supabase_key,
                    "Content-Type": "application/json"
                },
                json=db_payload,
                timeout=10
            )
            
            if db_res.status_code in (200, 201):
                supabase_success = True
                print("บันทึกข้อมูลและอัปโหลดไฟล์ไปที่ Supabase สำเร็จเรียบร้อย! 🎉")
            else:
                print(f"Warning: ไม่สามารถเซฟข้อมูลลง Supabase DB ได้: {db_res.status_code} | {db_res.text}")
        except Exception as e:
            print(f"Warning: เกิดปัญหาการเชื่อมต่อกับ Supabase: {e}")
            
    # 7. ยิงแจ้งเตือนทาง LINE Messaging API (เฉพาะ Test Mode + ทุกเช้า 6 โมง via cron)
    if mode == "test":
        report_url = f"https://example.com/result?id={record_uuid}"
        print(f"-> กำลังส่งแจ้งเตือนทาง LINE Messaging API (โหมด: {mode})...")
        line_bot.notify_cough_alert(device_code, record_uuid, risk_level, predictions, mode, report_url)
        
    return {
        "is_cough": True,
        "record_id": record_uuid,
        "device_code": device_code,
        "risk_level": risk_level,
        "predictions": predictions,
        "audio_url": audio_supabase_url if supabase_success else f"/audio/{filename}",
        "spectrum_url": spectrum_supabase_url if supabase_success else f"/audio/{spectrogram_filename}",
        "supabase_synced": supabase_success,
        "filter_details": filter_details
    }

@app.get("/audio/{filename}")
def get_audio(filename: str):
    # ค้นหาในโฟลเดอร์ test ก่อน แล้วค่อยค้นใน normal
    path = TEST_UPLOAD_DIR / filename
    if not path.exists():
        path = NORMAL_UPLOAD_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์เสียงหรือรูปภาพ")
        
    media_type = "audio/wav"
    if filename.endswith(".png"):
        media_type = "image/png"
        
    return FileResponse(path, media_type=media_type, filename=filename)

# ----------------------------------------------------
# LINE Webhook Endpoint
# ----------------------------------------------------
@app.post("/webhook/line")
async def webhook_line(request: Request):
    """รับ Webhook events จาก LINE Platform"""
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    
    if not line_bot.verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    data = json.loads(body)
    events = data.get("events", [])
    
    if events:
        line_bot.handle_webhook_events(events)
    
    return {"status": "ok"}

# ----------------------------------------------------
# Daily Summary Cron Endpoint
# ----------------------------------------------------
@app.get("/api/cron/daily-summary")
def daily_summary(key: str = Query("", description="API key for cron authentication")):
    """Endpoint สำหรับ crontab เรียกทุกเช้า 06:00 น. เพื่อส่งสรุปรายวัน"""
    if cron_secret and key != cron_secret:
        raise HTTPException(status_code=403, detail="Invalid cron key")
    
    print("\n" + "=" * 40)
    print("☀️ เริ่มต้นสร้างสรุปรายวัน...")
    print("=" * 40)
    
    results = line_bot.run_daily_summary()
    
    print(f"สรุป: {results['devices_processed']} devices, "
          f"{results['messages_sent']} messages sent")
    if results.get("errors"):
        print(f"Errors: {results['errors']}")
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
