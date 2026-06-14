import os
import sys
import pickle
import random
from pathlib import Path
import numpy as np
import librosa
import torch
from torch import nn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ตั้งค่า Path ค้นหาโมดูลในโฟลเดอร์ server
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

DATA_DIR = BASE_DIR / "normalize_sound_data"
MODEL_DIR = BASE_DIR / "models"
LABELS = ["bronchitis", "croup", "normal", "pneumonia"]

# นำเข้าโครงสร้างและฟังก์ชันของ CNN จากสคริปต์เดิม
from train_cough_cnn import TinyCoughCnn, load_log_mel
from train_hear_classifier import PyTorchRegularizedMLP

# ตั้งค่าที่เกี่ยวข้อง
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "normalize_sound_data"
LABELS = ["bronchitis", "croup", "normal", "pneumonia"]

def label_from_name(path: Path) -> str:
    for parent in path.parents:
        parent_name = parent.name.lower()
        if parent_name in LABELS:
            return parent_name
    name = path.name.lower()
    for label in LABELS:
        if name.startswith(label):
            return label
    raise ValueError(f"Cannot infer label from filename: {path.name}")

def scan_files(data_dir: Path):
    files = []
    for pattern in ("*.mp3", "*.wav", "*.m4a"):
        for path in sorted(data_dir.rglob(pattern)):
            try:
                files.append((path, label_from_name(path)))
            except ValueError:
                continue
    if not files:
        raise SystemExit(f"No audio files found in {data_dir}")
    return files

def main():
    # ----------------------------------------------------
    # 1. โหลดข้อมูลแคชและสแกนไฟล์
    # ----------------------------------------------------
    hear_cache_path = MODEL_DIR / "hear_embeddings.pt"
    acoustic_cache_path = MODEL_DIR / "acoustic_features.pt"
    cnn_model_path = MODEL_DIR / "cough_cnn.pt"
    hear_classifier_path = MODEL_DIR / "hear_classifier.pt"
    acoustic_classifier_path = MODEL_DIR / "acoustic_classifier.pkl"
    
    # เช็คว่ามีโมเดลครบไหม
    missing = [p for p in [cnn_model_path, hear_classifier_path, acoustic_classifier_path, hear_cache_path, acoustic_cache_path] if not p.exists()]
    if missing:
        print(f"Error: ข้อมูลหรือโมเดลไม่ครบ ขาดไฟล์: {[p.name for p in missing]}")
        print("กรุณารัน train_cough_cnn.py, train_hear_classifier.py และ train_acoustic_classifier.py ให้ครบก่อน")
        return

    items = scan_files(DATA_DIR)
    print(f"โหลดรายการไฟล์เสียงสำเร็จ จำนวน {len(items)} ไฟล์")
    
    # ----------------------------------------------------
    # 2. โหลดโมเดลทั้งหมดขึ้นมาทำงาน
    # ----------------------------------------------------
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"กำลังโหลดโมเดลทั้งหมดไปยังอุปกรณ์: {device.upper()}...")
    
    # โหลด CNN (Path A)
    cnn_checkpoint = torch.load(cnn_model_path, map_location=device, weights_only=False)
    cnn_model = TinyCoughCnn(classes=len(LABELS)).to(device)
    cnn_model.load_state_dict(cnn_checkpoint["model_state"])
    cnn_model.eval()
    
    # โหลด HeAR Classifier (Path B)
    hear_checkpoint = torch.load(hear_classifier_path, map_location=device, weights_only=False)
    hear_clf = PyTorchRegularizedMLP(input_dim=512, hidden_dim=64, num_classes=len(LABELS)).to(device)
    hear_clf.load_state_dict(hear_checkpoint["model_state"])
    hear_clf.eval()
    
    # โหลด Acoustic ML Classifier (Path C)
    with open(acoustic_classifier_path, 'rb') as f:
        acoustic_pack = pickle.load(f)
    acoustic_scaler = acoustic_pack["scaler"]
    acoustic_model = acoustic_pack["model"]
    
    # ----------------------------------------------------
    # 3. รันดึงทำนายเดี่ยวจากโมเดลทั้ง 3 เส้นทาง
    # ----------------------------------------------------
    print("\nกำลังคำนวณและดึงผลทำนายจากทุก Paths...")
    
    # โหลดข้อมูลแคชของ HeAR และ Acoustic
    hear_data = torch.load(hear_cache_path, weights_only=False)
    X_hear = hear_data["embeddings"]
    y_labels = hear_data["labels"]
    
    acoustic_data = torch.load(acoustic_cache_path, weights_only=False)
    X_acoustic = acoustic_data["features"]
    
    # ตัวเก็บผลลัพธ์ความน่าจะเป็น (Probability) ของแต่ละโมเดล
    # ขนาด (N, 4)
    probs_cnn = []
    probs_hear = []
    probs_acoustic = []
    
    # ดึงผล HeAR จาก MLP Classifier
    with torch.no_grad():
        inputs_hear = torch.tensor(X_hear, dtype=torch.float32).to(device)
        outputs_hear = torch.softmax(hear_clf(inputs_hear), dim=1)
        probs_hear = outputs_hear.cpu().numpy()
        
    # ดึงผล Acoustic จาก SVM (ใช้ predict_proba เพื่อเอา % มั่นใจ)
    X_acoustic_scaled = acoustic_scaler.transform(X_acoustic)
    probs_acoustic = acoustic_model.predict_proba(X_acoustic_scaled)
    
    # ดึงผล CNN จาก Spectrogram โหลดแบบ realtime (เนื่องจากรันเร็วและไม่ซ้ำซ้อน)
    for idx, (path, _) in enumerate(items, 1):
        if idx % 50 == 0 or idx == len(items):
            sys.stdout.write(f"\rประมวลผลลักษณะพิเศษฝั่ง CNN [{idx}/{len(items)}]")
            sys.stdout.flush()
            
        # โหลดและ Preprocess Spectrogram สำหรับ CNN (64 mels)
        features_cnn = load_log_mel(
            path,
            sample_rate=cnn_checkpoint["sample_rate"],
            duration=cnn_checkpoint["duration"],
            n_mels=cnn_checkpoint["n_mels"],
            augment=False
        )
        x_cnn = torch.from_numpy(features_cnn).unsqueeze(0).unsqueeze(0).to(device)
        
        with torch.no_grad():
            outputs_cnn = torch.softmax(cnn_model(x_cnn), dim=1)
            prob_c = outputs_cnn.squeeze(0).cpu().numpy()
        probs_cnn.append(prob_c)
        
    probs_cnn = np.array(probs_cnn)
    print("\nดึงผลลัพธ์โมเดลย่อยเสร็จเรียบร้อย!")
    
    # ----------------------------------------------------
    # 4. แบ่งกลุ่มข้อมูลการทดสอบแบบเดียวกัน (Validation Split)
    # ----------------------------------------------------
    indices = list(range(len(items)))
    # ใช้ Stratify และ Random State เดียวกับที่เราใช้เทรน
    _, val_idx = train_test_split(
        indices, test_size=0.2, stratify=y_labels, random_state=42
    )
    
    y_val = y_labels[val_idx]
    val_probs_cnn = probs_cnn[val_idx]
    val_probs_hear = probs_hear[val_idx]
    val_probs_acoustic = probs_acoustic[val_idx]
    
    # ----------------------------------------------------
    # 5. รันระบบ Grid Search ค้นหาน้ำหนักที่ดีที่สุด
    # ----------------------------------------------------
    print("\nกำลังค้นหาค่าน้ำหนัก Ensemble (Weights Grid Search) ที่ดีที่สุด...")
    best_acc = 0.0
    best_weights = None
    
    # ค้นหาค่า w_A, w_B, w_C ในช่วง 0.0 ถึง 1.0 ห่างกันทีละ 0.05
    step = 0.05
    for w_a in np.arange(0.0, 1.01, step):
        for w_b in np.arange(0.0, 1.01 - w_a, step):
            w_c = 1.0 - w_a - w_b
            if w_c < -1e-6:
                continue
            w_c = max(0.0, w_c) # ป้องกันค่าติดลบจากเศษจุดทศนิยม
            
            # คำนวณความน่าจะเป็นของ Ensemble
            ensemble_probs = (w_a * val_probs_cnn) + (w_b * val_probs_hear) + (w_c * val_probs_acoustic)
            preds = ensemble_probs.argmax(axis=1)
            
            acc = accuracy_score(y_val, preds)
            if acc > best_acc:
                best_acc = acc
                best_weights = (w_a, w_b, w_c)
                
    w_a, w_b, w_c = best_weights
    print("=" * 60)
    print("สรุปผลการวิเคราะห์ควบรวมโมเดล (Ensemble Result):")
    print(f"  - ค่าน้ำหนักที่ดีที่สุด: CNN={w_a*100:.1f}%, HeAR={w_b*100:.1f}%, Acoustic={w_c*100:.1f}%")
    print(f"  - ความแม่นยำ Validation Accuracy สูงสุด: {best_acc*100:.2f}%")
    print("=" * 60)
    
    # คำนวณผลทำนายจริงด้วยค่าน้ำหนักที่ดีที่สุดเพื่อดึงตารางสรุป
    best_ensemble_probs = (w_a * val_probs_cnn) + (w_b * val_probs_hear) + (w_c * val_probs_acoustic)
    best_preds = best_ensemble_probs.argmax(axis=1)
    
    print("\nรายงานผลการวิเคราะห์คลาสโรค (Detailed Classification Report):")
    print(classification_report(y_val, best_preds, target_names=LABELS))
    
    # บันทึกข้อมูลค่าน้ำหนักเก็บไว้ในไฟล์ config ของ Server เพื่อใช้งานจริง
    ensemble_config_path = MODEL_DIR / "ensemble_config.json"
    config_data = {
        "weight_cnn": float(w_a),
        "weight_hear": float(w_b),
        "weight_acoustic": float(w_c),
        "best_val_accuracy": float(best_acc)
    }
    ensemble_config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    print(f"บันทึกไฟล์ตั้งค่าค่าน้ำหนักสำหรับรวมพลังเรียบร้อยที่: {ensemble_config_path}")

if __name__ == "__main__":
    import json
    main()
