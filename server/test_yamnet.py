import os
import sys
import numpy as np
import librosa
import soundfile as sf

# ป้องกันไม่ให้ TensorFlow พิมพ์ log แจ้งเตือนจำนวนมาก
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    import tensorflow as tf
    import tensorflow_hub as hub
except ImportError:
    print("Error: ไม่พบไลบรารี tensorflow หรือ tensorflow-hub")
    print("กรุณารันคำสั่งติดตั้ง: pip install tensorflow-cpu tensorflow-hub")
    sys.exit(1)

def main():
    print("กำลังโหลดโมเดล YAMNet จาก Google TF Hub... (อาจใช้เวลาสักครู่ในการรันครั้งแรก)")
    try:
        # โหลดโมเดล YAMNet จาก TensorFlow Hub
        yamnet_model = hub.load('https://tfhub.dev/google/yamnet/1')
        
        # ดึงพาธไฟล์ CSV ของคลาสและอ่านข้อมูลรายชื่อคลาส
        import csv
        class_map_path = yamnet_model.class_map_path().numpy()
        class_names = []
        with tf.io.gfile.GFile(class_map_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            next(reader)  # ข้าม header row (index,mid,display_name)
            for row in reader:
                if len(row) >= 3:
                    class_names.append(row[2])
        
        class_names = np.array(class_names)
        
        # ค้นหา Index ของคลาส "Cough"
        cough_idx = np.where(class_names == 'Cough')[0]
        if len(cough_idx) == 0:
            print("Error: ไม่พบดัชนีคลาส Cough ในโมเดล YAMNet")
            return
        cough_idx = cough_idx[0]
        print("โหลดโมเดล YAMNet สำเร็จ!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลดโมเดล: {e}")
        return

    # เช็คว่ามี Argument ส่งไฟล์เสียงมาทดสอบหรือไม่
    sample_file = None
    if len(sys.argv) > 1:
        custom_path = sys.argv[1]
        if os.path.exists(custom_path):
            sample_file = custom_path
        else:
            print(f"Error: ไม่พบไฟล์เสียงที่ระบุ: {custom_path}")
            return
            
    # หากไม่ได้ส่ง Argument มา ให้สแกนหาไฟล์ .wav แรกสุดเหมือนเดิม
    if not sample_file:
        sound_dir = os.path.join(os.path.dirname(__file__), "normalize_sound_data")
        # วนลูปหาไฟล์ .wav แรกสุดเพื่อใช้ทดสอบ
        for root, dirs, files in os.walk(sound_dir):
            for file in files:
                if file.endswith(".wav"):
                    sample_file = os.path.join(root, file)
                    break
            if sample_file:
                break

    if not sample_file:
        print(f"ไม่พบไฟล์เสียง .wav สำหรับทดสอบ")
        print("กรุณาตรวจสอบว่าระบุ path ถูกต้อง หรือมีไฟล์เสียงอยู่ในโฟลเดอร์ normalize_sound_data")
        return

    print(f"\nใช้ไฟล์เสียงสำหรับทดสอบ: {os.path.abspath(sample_file)}")

    try:
        # 1. โหลดและ resample ไฟล์เสียงเป็น 16,000 Hz Mono (ตามสเปก YAMNet)
        audio, sr = librosa.load(sample_file, sr=16000, mono=True)
        
        # 2. ป้อนเข้าโมเดล YAMNet
        # scores: (N_frames, 521), embeddings: (N_frames, 1024), spectrogram: (N_frames, 64)
        scores, embeddings, spectrogram = yamnet_model(audio)
        
        # 3. คำนวณหาคะแนนความเป็นเสียงไอเฉลี่ยตลอดคลิป
        cough_scores_over_time = scores[:, cough_idx].numpy()
        mean_cough_score = np.mean(cough_scores_over_time)
        max_cough_score = np.max(cough_scores_over_time)

        # 4. สรุปผลความน่าจะเป็น
        print("-" * 50)
        print(f"ผลการวิเคราะห์จาก YAMNet:")
        print(f"  - โอกาสเฉลี่ยว่าเป็นเสียงไอ: {mean_cough_score * 100:.2f}%")
        print(f"  - โอกาสสูงสุดในช่วงที่ไอ: {max_cough_score * 100:.2f}%")
        print("-" * 50)
        
        if mean_cough_score >= 0.20 or max_cough_score >= 0.45:
            print("สรุป: สัญญาณนี้จัดว่าเป็น [ เสียงไอจริง ]")
        else:
            print("สรุป: สัญญาณนี้จัดว่าเป็น [ ไม่ใช่เสียงไอ/เสียงรบกวนอื่น ]")
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการประมวลผลเสียง: {e}")

if __name__ == "__main__":
    main()
