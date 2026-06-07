import os
import sys
import numpy as np
import librosa
import soundfile as sf
import csv

# ป้องกันไม่ให้ TensorFlow พิมพ์ log แจ้งเตือนจำนวนมาก
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    import tensorflow as tf
    import tensorflow_hub as hub
except ImportError:
    print("Error: ไม่พบไลบรารี tensorflow หรือ tensorflow-hub")
    print("กรุณารันคำสั่งติดตั้ง: pip install tensorflow-cpu tensorflow-hub")
    sys.exit(1)

# ==============================================================================
# CONFIGURATION BLOCK: ปรับแต่งค่าน้ำหนัก เกณฑ์ และแฟกเตอร์ต่าง ๆ ได้ที่นี่
# ==============================================================================
CONFIG = {
    # 1. การถ่วงน้ำหนักรวม (Hybrid Weights)
    "WEIGHT_AI": 0.5,         # น้ำหนักความน่าเชื่อถือของ AI YAMNet (0.0 - 1.0)
    "WEIGHT_ACOUSTIC": 0.5,   # น้ำหนักความน่าเชื่อถือของฟิสิกส์เสียง (0.0 - 1.0)
    
    # 2. เกณฑ์การตัดสินว่าเป็นเสียงไอ (Decision Thresholds)
    "THRESHOLD_HYBRID": 0.35,  # คะแนนไฮบริดรวมที่จะจัดว่าเป็นเสียงไอ (35%)
    "MIN_AI_SCORE": 0.05,      # สัญญาณความมั่นใจขั้นต่ำของ AI ที่ต้องผ่าน (5%) ป้องกันเสียงเงียบจี่รบกวน
    
    # 3. แฟกเตอร์ถ่วงน้ำหนักรายคลาสของ YAMNet (YAMNet Class Factors)
    # คลาสเสียงเป้าหมายที่นำมารวมคะแนนในการวิเคราะห์ระบบหายใจ (0.0 = ปิดใช้งาน, 1.0 = ให้น้ำหนักเต็ม)
    "CLASS_FACTORS": {
        "Cough": 2.0,
        "Grunt": 1.0,
        "Throat clearing": 1.0,
        "Sneeze": 1.0,
        "Owl": 1.0,
        "Hoot": 1.0,
        "Whale vocalization": 1.0,
        
        # คลาสเพิ่มเติมที่คุณสามารถเพิ่มหรือเปิดทดลองปรับค่าน้ำหนักเองได้:
        "Animal": 0.0,
        "Roar": 0.0,
        "Roaring cats (lions, tigers)": 0.0,
        "Growling": 0.0,
        "Screaming": 0.0,
        "Speech": 0.0,
        "Laughter": 0.0
    },
    
    # 4. เกณฑ์พารามิเตอร์ทางฟิสิกส์ (Acoustic Parameters)
    "ACOUSTIC": {
        "RMS_THRESHOLD": 0.03,    # ความดัง RMS ต่ำสุดที่ยอมรับว่าเป็นเสียงกระแทก (Explosive Peak)
        "RMS_MAX_REF": 0.10,      # ค่า RMS ที่ใช้เป็นเกณฑ์คะแนนเต็ม (RMS >= 0.10 ได้ 50 คะแนนเต็ม)
        "ZCR_CENTER": 0.20,       # จุดศูนย์กลางของย่าน Zero Crossing Rate ที่เหมาะสมสำหรับการไอ
        "ZCR_SPREAD": 0.15,       # ระยะเบี่ยงเบน ZCR (ย่านกว้างครอบคลุม 0.05 ถึง 0.35)
        
        # สัดส่วนการแบ่งคะแนนเต็มของฟิสิกส์เสียง (รวมกันได้ 100)
        "SCORE_WEIGHT_RMS": 50.0, # น้ำหนักคะแนนด้านความดังปะทุ
        "SCORE_WEIGHT_ZCR": 50.0  # น้ำหนักคะแนนด้านอัตราการข้ามศูนย์ (ลักษณะลมหายใจ/ไอ)
    }
}
# ==============================================================================

def run_yamnet_inference(file_path, yamnet_model, class_indices):
    """รันการทำนายด้วย YAMNet บนไฟล์เสียงหนึ่งไฟล์ ร่วมกับเกณฑ์ฟิสิกส์ (Hybrid Logic)"""
    audio, sr = librosa.load(file_path, sr=16000, mono=True)
    scores, embeddings, spectrogram = yamnet_model(audio)
    
    mean_scores = np.mean(scores.numpy(), axis=0)
    top_indices = np.argsort(mean_scores)[::-1][:5]
    
    scores_numpy = scores.numpy()
    
    # 1. คำนวณคะแนนรวมของ AI YAMNet รายเฟรมแบบถ่วงน้ำหนักคลาสตาม CONFIG
    target_idxs = []
    target_weights = []
    
    for class_name, factor in CONFIG["CLASS_FACTORS"].items():
        if factor > 0.0 and class_name in class_indices:
            target_idxs.append(class_indices[class_name])
            target_weights.append(factor)
            
    if len(target_idxs) > 0:
        # คูณคะแนนรายเฟรมด้วยตัวคูณแฟกเตอร์ของแต่ละคลาสย่อย
        weighted_scores_per_class = scores_numpy[:, target_idxs] * np.array(target_weights)
        resp_scores_per_frame = np.sum(weighted_scores_per_class, axis=1)
    else:
        resp_scores_per_frame = np.zeros(len(scores_numpy))
        
    mean_resp = np.mean(resp_scores_per_frame)
    max_resp = np.max(resp_scores_per_frame)
    
    # บีบคะแนน AI ให้อยู่ในช่วง 0.0 - 1.0 (0-100%) เพื่อความสม่ำเสมอ
    ai_score = min(1.0, float(max_resp))
    
    # 2. คำนวณคะแนนเดี่ยวคลาสไอปกติและเสียงหวีด Stridor สำหรับแสดงผล
    cough_idx = class_indices.get("Cough")
    mean_cough = mean_scores[cough_idx] if cough_idx is not None else 0.0
    max_cough = np.max(scores_numpy[:, cough_idx]) if cough_idx is not None else 0.0
    
    grunt_idx = class_indices.get("Grunt")
    mean_grunt = mean_scores[grunt_idx] if grunt_idx is not None else 0.0
    max_grunt = np.max(scores_numpy[:, grunt_idx]) if grunt_idx is not None else 0.0
    
    # 3. สกัดลักษณะทางฟิสิกส์แบบละเอียด (Acoustic Scoring 0-100%) ตาม CONFIG
    rms = librosa.feature.rms(y=audio)[0]
    max_rms = np.max(rms)
    
    zcr = librosa.feature.zero_crossing_rate(y=audio)[0]
    mean_zcr = np.mean(zcr)
    
    # RMS Score: คิดสัดส่วนแบบเส้นตรงจากความปะทะ เทียบกับ RMS_MAX_REF
    rms_score_component = min(
        CONFIG["ACOUSTIC"]["SCORE_WEIGHT_RMS"], 
        (max_rms / CONFIG["ACOUSTIC"]["RMS_MAX_REF"]) * CONFIG["ACOUSTIC"]["SCORE_WEIGHT_RMS"]
    )
    
    # ZCR Score: คะแนนเต็มที่ ZCR_CENTER และลดลงเมื่อใกล้ขอบ ZCR_SPREAD
    zcr_dist = abs(mean_zcr - CONFIG["ACOUSTIC"]["ZCR_CENTER"])
    zcr_score_component = max(
        0.0, 
        CONFIG["ACOUSTIC"]["SCORE_WEIGHT_ZCR"] - (zcr_dist / CONFIG["ACOUSTIC"]["ZCR_SPREAD"]) * CONFIG["ACOUSTIC"]["SCORE_WEIGHT_ZCR"]
    )
    
    # คะแนนฟิสิกส์รวม (0.0 - 1.0)
    acoustic_score = (rms_score_component + zcr_score_component) / 100.0
    
    # 4. คำนวณคะแนนไฮบริด (Hybrid Score) จากการถ่วงน้ำหนักรวมใน CONFIG
    hybrid_score = (CONFIG["WEIGHT_AI"] * ai_score) + (CONFIG["WEIGHT_ACOUSTIC"] * acoustic_score)
    
    # เกณฑ์ผ่าน: คะแนนไฮบริด >= THRESHOLD_HYBRID และต้องมีความน่าจะเป็นใน AI ขั้นต่ำ >= MIN_AI_SCORE
    is_cough = (hybrid_score >= CONFIG["THRESHOLD_HYBRID"]) and (max_resp >= CONFIG["MIN_AI_SCORE"])
    
    # ดึงคลาสโชว์ Stridor รายงาน
    stridor_idxs = [class_indices[c] for c in ["Owl", "Hoot", "Whale vocalization"] if c in class_indices]
    mean_stridor = np.mean(np.sum(scores_numpy[:, stridor_idxs], axis=1)) if stridor_idxs else 0.0
    max_stridor = np.max(np.sum(scores_numpy[:, stridor_idxs], axis=1)) if stridor_idxs else 0.0
    
    return {
        "mean_scores": mean_scores,
        "top_indices": top_indices,
        "mean_cough": mean_cough,
        "max_cough": max_cough,
        "mean_grunt": mean_grunt,
        "max_grunt": max_grunt,
        "mean_stridor": mean_stridor,
        "max_stridor": max_stridor,
        "mean_resp": mean_resp,
        "max_resp": max_resp,
        "ai_score": ai_score,
        "max_rms": max_rms,
        "mean_zcr": mean_zcr,
        "acoustic_score": acoustic_score,
        "hybrid_score": hybrid_score,
        "is_cough": is_cough
    }

def main():
    print("กำลังโหลดโมเดล YAMNet จาก Google TF Hub... (อาจใช้เวลาสักครู่ในการรันครั้งแรก)")
    try:
        yamnet_model = hub.load('https://tfhub.dev/google/yamnet/1')
        class_map_path = yamnet_model.class_map_path().numpy()
        class_names = []
        with tf.io.gfile.GFile(class_map_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            next(reader)  # ข้าม header row (index,mid,display_name)
            for row in reader:
                if len(row) >= 3:
                    class_names.append(row[2])
        class_names = np.array(class_names)
        
        # แมปดัชนีคลาสทั้งหมดที่ระบุใน CONFIG และใช้รายงาน
        class_indices = {}
        for class_name in list(CONFIG["CLASS_FACTORS"].keys()) + ["Cough", "Grunt", "Throat clearing", "Sneeze", "Owl", "Hoot", "Whale vocalization"]:
            if class_name not in class_indices:
                idx = np.where(class_names == class_name)[0]
                if len(idx) > 0:
                    class_indices[class_name] = idx[0]
            
        print("โหลดโมเดล YAMNet สำเร็จ!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลดโมเดล: {e}")
        return

    # ตรวจสอบ Argument
    target_path = None
    if len(sys.argv) > 1:
        custom_path = sys.argv[1]
        if os.path.exists(custom_path):
            target_path = custom_path
        else:
            print(f"Error: ไม่พบไฟล์หรือโฟลเดอร์ที่ระบุ: {custom_path}")
            return
            
    # Fallback สแกนหาไฟล์ .wav แรกสุดหากไม่ได้ระบุ Argument
    if not target_path:
        sound_dir = os.path.join(os.path.dirname(__file__), "normalize_sound_data")
        for root, dirs, files in os.walk(sound_dir):
            for file in files:
                if file.endswith(".wav"):
                    target_path = os.path.join(root, file)
                    break
            if target_path:
                break

    if not target_path:
        print("ไม่พบไฟล์เสียง .wav สำหรับทดสอบ")
        return

    # กรณี 1: เป็นโฟลเดอร์ (Directory)
    if os.path.isdir(target_path):
        print(f"\nสแกนและประมวลผลไฟล์เสียงในโฟลเดอร์: {os.path.abspath(target_path)}")
        audio_files = []
        for ext in ("*.wav", "*.mp3", "*.m4a"):
            for path in sorted(os.listdir(target_path)):
                if path.lower().endswith(ext.replace("*", "")):
                    audio_files.append(os.path.join(target_path, path))
        
        if not audio_files:
            print(f"ไม่พบไฟล์เสียง .wav, .mp3, .m4a ภายใต้โฟลเดอร์นี้")
            return
            
        print(f"พบไฟล์เสียงทั้งหมด {len(audio_files)} ไฟล์ กำลังเริ่มวิเคราะห์...\n")
        
        success_count = 0
        cough_count = 0
        
        for idx, file_path in enumerate(audio_files, 1):
            file_name = os.path.basename(file_path)
            try:
                res = run_yamnet_inference(file_path, yamnet_model, class_indices)
                status = "[ เสียงไอจริง ]" if res["is_cough"] else "[ ไม่ใช่เสียงไอ ]"
                print(f"[{idx}/{len(audio_files)}] {file_name}")
                print(f"  - คะแนนไฮบริด: {res['hybrid_score']*100:.2f}% (AIสูงสุด {res['ai_score']*100:.1f}%, ฟิสิกส์ {res['acoustic_score']*100:.1f}%) -> {status}")
                print("  - Top 3 classes:")
                for i in range(3):
                    t_idx = res["top_indices"][i]
                    c_name = class_names[t_idx]
                    c_score = res["mean_scores"][t_idx]
                    print(f"    {i+1}. {c_name} ({c_score * 100:.2f}%)")
                print()
                
                success_count += 1
                if res["is_cough"]:
                    cough_count += 1
            except Exception as e:
                print(f"[{idx}/{len(audio_files)}] {file_name} -> เกิดข้อผิดพลาด: {e}")
        
        print("\n" + "=" * 50)
        print(f"สรุปผลการวิเคราะห์ระดับโฟลเดอร์:")
        print(f"  - ประมวลผลสำเร็จ: {success_count} / {len(audio_files)} ไฟล์")
        if success_count > 0:
            print(f"  - คัดกรองผ่านเป็นเสียงไอจริง: {cough_count} ไฟล์ ({cough_count/success_count*100:.2f}%)")
        print("=" * 50)

    # กรณี 2: เป็นไฟล์เดี่ยว (File)
    else:
        print(f"\nใช้ไฟล์เสียงสำหรับทดสอบ: {os.path.abspath(target_path)}")
        try:
            res = run_yamnet_inference(target_path, yamnet_model, class_indices)
            
            # สรุปผลความน่าจะเป็น
            print("-" * 50)
            print("ผลการวิเคราะห์ Top 5 คลาสที่มีคะแนนสูงสุดจาก YAMNet:")
            for idx in res["top_indices"]:
                class_name = class_names[idx]
                print(f"  - {class_name}: {res['mean_scores'][idx] * 100:.2f}%")
            print("-" * 50)
            
            print(f"รายละเอียดวิเคราะห์สัญญาณทางเดินหายใจ (Respiratory Analysis):")
            print(f"  - คลาสไอปกติ (Cough): เฉลี่ย {res['mean_cough']*100:.2f}% | สูงสุด {res['max_cough']*100:.2f}%")
            print(f"  - คลาสเสียงเค้นในลำคอ (Grunt): เฉลี่ย {res['mean_grunt']*100:.2f}% | สูงสุด {res['max_grunt']*100:.2f}%")
            print(f"  - คลาสเสียงหวีด Stridor (Owl+Hoot+Whale): เฉลี่ย {res['mean_stridor']*100:.2f}% | สูงสุด {res['max_stridor']*100:.2f}%")
            print(f"  - คะแนนเฉลี่ย YAMNet (รายเฟรม): {res['mean_resp']*100:.2f}% (สูงสุดในเสี้ยววินาทีเดียวกัน: {res['ai_score']*100:.2f}%)")
            print("-" * 50)
            
            print(f"รายละเอียดวิเคราะห์ทางฟิสิกส์ (Acoustic Analysis):")
            print(f"  - พลังงานเสียงปะทะ (RMS): สูงสุด {res['max_rms']:.4f} (เกณฑ์ผ่าน >= {CONFIG['ACOUSTIC']['RMS_THRESHOLD']})")
            print(f"  - อัตรา ZCR เฉลี่ย: {res['mean_zcr']:.4f} (ย่านเป้าหมาย {CONFIG['ACOUSTIC']['ZCR_CENTER']} +/- {CONFIG['ACOUSTIC']['ZCR_SPREAD']})")
            print(f"  - คะแนนวิเคราะห์ฟิสิกส์: {res['acoustic_score']*100:.2f}%")
            print("-" * 50)
            
            print(f"คะแนนสรุปไฮบริด (Hybrid Ensemble):")
            print(f"  - คะแนนไฮบริด (AI {CONFIG['WEIGHT_AI']*100:.0f}% + ฟิสิกส์ {CONFIG['WEIGHT_ACOUSTIC']*100:.0f}%): {res['hybrid_score']*100:.2f}%")
            print("-" * 50)
            
            if res["is_cough"]:
                print("สรุป: สัญญาณนี้จัดว่าเป็น [ เสียงไอจริง ] (ผ่านเกณฑ์กรองสัญญาณทางเดินหายใจไฮบริด)")
            else:
                print("สรุป: สัญญาณนี้จัดว่าเป็น [ ไม่ใช่เสียงไอ/เสียงรบกวนอื่น ]")
                
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการประมวลผลเสียง: {e}")

if __name__ == "__main__":
    main()
