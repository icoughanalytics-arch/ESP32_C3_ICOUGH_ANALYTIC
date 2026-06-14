import os
import sys
import pickle
import random
from pathlib import Path
import numpy as np
import torch

try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.metrics import classification_report, accuracy_score
    from sklearn.utils.class_weight import compute_class_weight
except ImportError:
    print("Error: ไม่พบไลบรารี scikit-learn")
    print("กรุณารันคำสั่ง: pip install scikit-learn")
    sys.exit(1)

# นำเข้าตัวดึงลักษณะฟิสิกส์ที่เราเขียนไว้
from acoustic_rules import analyze_cough_acoustic

# ตั้งค่าที่เกี่ยวข้อง
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "normalize_sound_data"
MODEL_DIR = BASE_DIR / "models"
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
    MODEL_DIR.mkdir(exist_ok=True)
    cache_path = MODEL_DIR / "acoustic_features.pt"
    
    items = scan_files(DATA_DIR)
    
    features_list = []
    labels_list = []
    label_to_id = {name: idx for idx, name in enumerate(LABELS)}
    
    # 1. ระบบดึงข้อมูลฟิสิกส์และแคช (Cache)
    if cache_path.exists():
        print(f"กำลังโหลดค่าฟิสิกส์จาก Cache: {cache_path}...")
        cache_data = torch.load(cache_path, weights_only=False)
        features_list = cache_data["features"]
        labels_list = cache_data["labels"]
        print(f"โหลดแคชสำเร็จ! จำนวนตัวอย่าง: {len(features_list)}")
    else:
        print("ไม่พบไฟล์แคช เริ่มต้นคำนวณลักษณะฟิสิกส์จากไฟล์เสียงเสียงไอทั้งหมด...")
        for idx, (path, label) in enumerate(items, 1):
            if idx % 20 == 0 or idx == len(items):
                sys.stdout.write(f"\rสกัดฟิสิกส์ไฟล์ [{idx}/{len(items)}]: {path.name}")
                sys.stdout.flush()
                
            try:
                # รันสกัดฟิสิกส์จากโมดูลหลัก
                _, feat_dict = analyze_cough_acoustic(path)
                
                # แปลงเป็น Vector 6 มิติ
                feat_vector = [
                    feat_dict["wi_peaks"],
                    feat_dict["mean_zcr"],
                    feat_dict["mean_centroid"],
                    feat_dict["er_croup"],
                    feat_dict["er_bronchitis"],
                    feat_dict["t_cough"]
                ]
                
                features_list.append(feat_vector)
                labels_list.append(label_to_id[label])
            except Exception as e:
                print(f"\nเกิดข้อผิดพลาดกับไฟล์ {path.name}: {e}")
                
        print("\nสกัดข้อมูลเสร็จสิ้น กำลังบันทึก Cache...")
        features_list = np.array(features_list)
        labels_list = np.array(labels_list)
        torch.save({"features": features_list, "labels": labels_list}, cache_path)
        print(f"บันทึก Cache สำเร็จที่ {cache_path}")

    # 2. เตรียมข้อมูลและแบ่งกลุ่มแบบ Stratified
    X = np.array(features_list)
    y = np.array(labels_list)
    
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    # ทำการปรับสเกลตัวแปรฟิสิกส์ (Standardization)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    results = {}
    
    # ----------------------------------------------------
    # Model A: SVM (Linear Kernel)
    # ----------------------------------------------------
    svm_linear = SVC(kernel='linear', class_weight='balanced', C=1.0, probability=True, random_state=42)
    svm_linear.fit(X_train_scaled, y_train)
    preds_svm_linear = svm_linear.predict(X_val_scaled)
    acc_svm_linear = accuracy_score(y_val, preds_svm_linear)
    results["SVM (Linear Kernel)"] = (acc_svm_linear, svm_linear)
    
    # ----------------------------------------------------
    # Model B: SVM (RBF Kernel)
    # ----------------------------------------------------
    svm_rbf = SVC(kernel='rbf', class_weight='balanced', C=2.0, gamma='scale', probability=True, random_state=42)
    svm_rbf.fit(X_train_scaled, y_train)
    preds_svm_rbf = svm_rbf.predict(X_val_scaled)
    acc_svm_rbf = accuracy_score(y_val, preds_svm_rbf)
    results["SVM (RBF Kernel)"] = (acc_svm_rbf, svm_rbf)
    
    # ----------------------------------------------------
    # Model C: Random Forest
    # ----------------------------------------------------
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
    rf.fit(X_train_scaled, y_train)
    preds_rf = rf.predict(X_val_scaled)
    acc_rf = accuracy_score(y_val, preds_rf)
    results["Random Forest"] = (acc_rf, rf)
    
    # ----------------------------------------------------
    # Model D: Decision Tree (กฎเงื่อนไขการตัดสินใจแบบเรียนรู้ด้วย AI)
    # ----------------------------------------------------
    dt = DecisionTreeClassifier(max_depth=4, class_weight='balanced', random_state=42)
    dt.fit(X_train_scaled, y_train)
    preds_dt = dt.predict(X_val_scaled)
    acc_dt = accuracy_score(y_val, preds_dt)
    results["Decision Tree"] = (acc_dt, dt)
    
    # ----------------------------------------------------
    # ตารางเปรียบเทียบผลลัพธ์
    # ----------------------------------------------------
    print("\n" + "="*50)
    print(f"{'โมเดล AI (ใช้ฟิสิกส์ 6 ตัว)':<30} | {'Validation Accuracy':<18}")
    print("="*50)
    for model_name, (acc, _) in sorted(results.items(), key=lambda item: item[1][0], reverse=True):
        print(f"{model_name:<30} | {acc*100:.2f}%")
    print("="*50)
    
    # สรุปและแสดงผลโมเดลที่ดีที่สุด
    best_name, (best_acc, best_model) = max(results.items(), key=lambda item: item[1][0])
    print(f"\nโมเดลฟิสิกส์ที่ดีที่สุดคือ: {best_name} (Acc: {best_acc*100:.2f}%)")
    
    preds_best = best_model.predict(X_val_scaled)
    print("\nรายงานผลการวิเคราะห์คลาสโรค (Detailed Classification Report):")
    print(classification_report(y_val, preds_best, target_names=LABELS, zero_division=0))
    
    # บันทึกโมเดลและ scaler ไว้ใช้งานจริง
    save_path = MODEL_DIR / "acoustic_classifier.pkl"
    with open(save_path, 'wb') as f:
        pickle.dump({
            "scaler": scaler,
            "model": best_model,
            "model_type": "sklearn_acoustic",
            "labels": LABELS
        }, f)
    print(f"บันทึกโมเดลฟิสิกส์และ Scaler สำเร็จที่: {save_path}")

if __name__ == "__main__":
    main()
