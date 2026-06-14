import os
import sys
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, accuracy_score

# นำเข้าโมดูลวิเคราะห์กฎที่เราเพิ่งสร้าง
from acoustic_rules import analyze_cough_acoustic

# ตั้งค่าที่เกี่ยวข้อง
BASE_DIR = Path(__file__).resolve().parent
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
    items = scan_files(DATA_DIR)
    print(f"พบไฟล์เสียงทั้งหมด {len(items)} ไฟล์ เริ่มทำนายโดยใช้กฎเกณฑ์ทางฟิสิกส์ (Acoustic Rules)...")
    
    true_labels = []
    pred_labels = []
    label_to_id = {name: idx for idx, name in enumerate(LABELS)}
    
    success_count = 0
    
    for idx, (path, label) in enumerate(items, 1):
        if idx % 20 == 0 or idx == len(items):
            sys.stdout.write(f"\rประมวลผลไฟล์ [{idx}/{len(items)}]: {path.name}")
            sys.stdout.flush()
            
        try:
            # รันการวิเคราะห์ทางฟิสิกส์
            probs, features = analyze_cough_acoustic(path)
            
            # หาคลาสที่ได้เปอร์เซ็นต์คะแนนสูงสุดจากกฎฟิสิกส์
            pred_class = max(probs, key=probs.get)
            
            true_labels.append(label_to_id[label])
            pred_labels.append(label_to_id[pred_class])
            success_count += 1
            
        except Exception as e:
            print(f"\nเกิดข้อผิดพลาดกับไฟล์ {path.name}: {e}")
            
    print(f"\n\nวิเคราะห์สำเร็จ: {success_count} / {len(items)} ไฟล์")
    
    # คำนวณความแม่นยำ
    if success_count > 0:
        acc = accuracy_score(true_labels, pred_labels)
        print("\n" + "="*50)
        print(f"ความแม่นยำรวมของ Acoustic Rules (Rule-based Accuracy): {acc*100:.2f}%")
        print("="*50)
        
        # แสดงรายงานละเอียด
        print("\nรายงานผลการวิเคราะห์คลาสโรค (Detailed Classification Report):")
        print(classification_report(true_labels, pred_labels, target_names=LABELS, zero_division=0))
        
    else:
        print("ไม่มีไฟล์ประมวลผลสำเร็จ")

if __name__ == "__main__":
    main()
