import os
import sys
import numpy as np
import librosa

def main():
    file_path = "normalize_sound_data/pneumonia/P9_seg02.wav"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
    if not os.path.exists(file_path):
        print(f"Error: ไม่พบไฟล์เสียงที่ {file_path}")
        return

    print(f"วิเคราะห์ลักษณะกายภาพเสียง (Acoustic Features) ของไฟล์: {file_path}\n")

    try:
        # โหลดไฟล์เสียง 16kHz
        audio, sr = librosa.load(file_path, sr=16000, mono=True)
        
        # 1. คำนวณ RMS Energy (ความดังและความปะทุของเสียง)
        rms = librosa.feature.rms(y=audio)[0]
        mean_rms = np.mean(rms)
        max_rms = np.max(rms)
        
        # 2. คำนวณ Zero Crossing Rate (ZCR - อัตราการตัดข้ามแกนศูนย์)
        zcr = librosa.feature.zero_crossing_rate(y=audio)[0]
        mean_zcr = np.mean(zcr)
        max_zcr = np.max(zcr)
        
        # 3. คำนวณ Spectral Centroid (จุดศูนย์กลางความถี่เสียง)
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        mean_centroid = np.mean(centroid)
        
        # 4. คำนวณหาจำนวนยอดพลังงานย่อย (Local Peaks) ใน RMS เพื่อวัดความสะดุด/ความเปียก
        # ใช้เงื่อนไขหาจุดยอดที่สูงกว่า 20% ของจุดสูงสุด และเว้นระยะห่างขั้นต่ำ
        peaks = []
        threshold = max_rms * 0.20
        for i in range(1, len(rms) - 1):
            if rms[i] > rms[i-1] and rms[i] > rms[i+1] and rms[i] >= threshold:
                peaks.append(i)
                
        duration = len(audio) / sr

        print("-" * 50)
        print(f"สรุปค่าทางฟิสิกส์ของสัญญาณเสียง:")
        print(f"  - ความยาวไฟล์: {duration:.2f} วินาที")
        print(f"  - RMS Energy (ความดัง): เฉลี่ย {mean_rms:.4f} | สูงสุด {max_rms:.4f}")
        print(f"  - Zero Crossing Rate (ZCR): เฉลี่ย {mean_zcr:.4f} | สูงสุด {max_zcr:.4f}")
        print(f"  - Spectral Centroid (เฉลี่ย): {mean_centroid:.2f} Hz")
        print(f"  - จำนวนยอดพลังงานสะดุด (Local Peaks): {len(peaks)} ยอด")
        print("-" * 50)
        
        # วิเคราะห์ผลทางกายภาพเบื้องต้น
        print("วิเคราะห์ทางสรีรวิทยา:")
        if max_rms >= 0.03:
            print("  - [ผ่าน] มีการปะทะของพลังงานเด่นชัด (Explosive peak ตรวจพบ)")
        else:
            print("  - [ตก] พลังงานเบาเกินไป อาจเป็นเสียงลมพัดหรือเสียงห้องเงียบ")
            
        if 0.05 <= mean_zcr <= 0.35:
            print(f"  - [ผ่าน] อัตรา ZCR อยู่ในย่านเสียงไอและระบบหายใจ ({mean_zcr:.3f})")
        else:
            print(f"  - [ตก] อัตรา ZCR ไม่อยู่ในกลุ่มเป้าหมาย")
            
        if len(peaks) >= 3:
            print(f"  - พบลักษณะเสียงสะดุด {len(peaks)} ครั้ง บ่งชี้เสียงไอเปียก/มีเสมหะ (Wet Cough)")
        else:
            print(f"  - พบลักษณะการไหลของเสียงที่เรียบเนียน บ่งชี้เสียงไอแห้ง (Dry Cough)")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")

if __name__ == "__main__":
    main()
