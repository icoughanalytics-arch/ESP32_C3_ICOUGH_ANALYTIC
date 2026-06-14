import os
import sys
import numpy as np
import librosa
import torch
from transformers import AutoModel

# ปลั๊กอิน Token ของ Hugging Face เพื่อดาวน์โหลดโมเดล
HF_TOKEN = "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"

# กำหนดโมเดลเป้าหมาย
MODEL_NAME = "google/hear-pytorch"

def test_google_hear():
    # 1. ค้นหาไฟล์เสียงเพื่อใช้ในการทดสอบ
    sound_dir = os.path.join(os.path.dirname(__file__), "normalize_sound_data")
    test_file = None
    
    # วิ่งหาไฟล์ .wav แรกสุดในโฟลเดอร์ย่อย
    for root, dirs, files in os.walk(sound_dir):
        for file in files:
            if file.endswith(".wav"):
                test_file = os.path.join(root, file)
                break
        if test_file:
            break
            
    if not test_file or not os.path.exists(test_file):
        print(f"Error: ไม่พบไฟล์เสียงสำหรับทดสอบใน {sound_dir}")
        return
        
    print(f"พบไฟล์เสียงสำหรับทดสอบ: {os.path.basename(test_file)}")
    
    # 2. โหลดและจัดการไฟล์เสียงให้สอดคล้องกับโมเดล HeAR (16kHz, mono)
    print("กำลังโหลดและปรับแต่งไฟล์เสียง...")
    audio, sr = librosa.load(test_file, sr=16000, mono=True)
    
    # โมเดล HeAR ถูกออกแบบมาสำหรับคลิปเสียงยาว 2 วินาที (32,000 samples)
    target_samples = 32000 
    if len(audio) < target_samples:
        # หากเสียงสั้นไป ให้ทำการ pad (เติมค่าศูนย์) ด้านท้าย
        print(f"เสียงสั้นกว่า 2 วินาที ({len(audio)} samples) -> ทำการ Pad เติมข้อมูลให้ครบ")
        audio = np.pad(audio, (0, target_samples - len(audio)))
    elif len(audio) > target_samples:
        # หากเสียงยาวไป ให้ตัดเหลือเฉพาะ 2 วินาทีแรก
        print(f"เสียงยาวกว่า 2 วินาที ({len(audio)} samples) -> ทำการตัดเหลือ 2 วินาทีแรก")
        audio = audio[:target_samples]
        
    # 3. โหลดตัวโมเดล Google HeAR จาก Hugging Face
    print("กำลังดาวน์โหลดและโหลดโมเดล Google HeAR จาก Hugging Face Hub (ขั้นตอนนี้อาจใช้เวลาสักครู่)...")
    try:
        # โหลด Model
        model = AutoModel.from_pretrained(MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
        
        # ตั้งค่าอุปกรณ์ประมวลผล (GPU/CPU) และรันโมเดลในโหมดประเมินผล
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()
        
        print(f"โหลดโมเดลสำเร็จ! อุปกรณ์ที่ใช้งานประมวลผล: {device.upper()}")
        print("\n--- Model Config ---")
        print(model.config)
        print("--------------------\n")
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลดโมเดล: {e}")
        print("คำแนะนำ: โปรดตรวจสอบว่าอีเมลของ Hugging Face ได้รับการยืนยันแล้ว และกดยอมรับ License ของ google/hear-pytorch เรียบร้อยแล้ว")
        return

    # 4. ประมวลผลแปลงคลื่นเสียงเป็น Log-Mel Spectrogram ขนาด 192x128
    print("กำลังสกัด Log-Mel Spectrogram จากคลื่นเสียง...")
    try:
        # ใช้ Librosa สกัด Mel Spectrogram
        mel = librosa.feature.melspectrogram(
            y=audio,
            sr=16000,
            n_fft=1024,
            hop_length=160,
            n_mels=128,
            power=2.0
        )
        # แปลงค่าแอมพลิจูดเป็นระดับเดซิเบล (dB)
        log_mel = librosa.power_to_db(mel, ref=np.max)
        
        # Normalize ข้อมูล
        log_mel = (log_mel - log_mel.mean()) / (log_mel.std() + 1e-6)
        
        # สลับแกน (Transpose) จาก (n_mels, frames) -> (frames, n_mels)
        spectrogram = log_mel.T
        
        # ปรับความยาวแกนเวลา (frames) ให้เท่ากับ 192 พอดี
        target_frames = 192
        if spectrogram.shape[0] < target_frames:
            # ถ้าเฟรมน้อยกว่า 192 ให้เติม 0 (Pad) ด้านท้าย
            pad_width = target_frames - spectrogram.shape[0]
            spectrogram = np.pad(spectrogram, ((0, pad_width), (0, 0)), mode='constant')
        elif spectrogram.shape[0] > target_frames:
            # ถ้าเฟรมมากกว่า 192 ให้ตัดส่วนเกินออก
            spectrogram = spectrogram[:target_frames, :]
            
        print(f"ขนาด Spectrogram ที่สกัดได้: {spectrogram.shape} (Time=192, Mels=128)")
        
        # แปลงเป็น PyTorch Tensor และเพิ่ม batch/channel dimensions -> Shape: [1, 1, 192, 128]
        pixel_values = torch.tensor(spectrogram, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการทำ Preprocessing: {e}")
        return

    # 5. ส่งสัญญาณ Spectrogram เข้าโมเดลเพื่อสกัดฟีเจอร์
    print("กำลังส่งสัญญาณ Spectrogram เข้าโมเดล HeAR เพื่อสกัดฟีเจอร์...")
    try:
        with torch.no_grad():
            outputs = model(pixel_values)
            # HeAR มักจะคืนค่า embeddings มาใน output (ขึ้นกับโมเดลแต่ละสถาปัตยกรรม)
            # เราจะดูชนิดและรูปร่างของฟิวเจอร์ที่ได้
            print("\n" + "=" * 50)
            print("สรุปผลลัพธ์จาก Google HeAR:")
            for key, val in outputs.items():
                if isinstance(val, torch.Tensor):
                    print(f"  - Key: {key} | Shape: {list(val.shape)}")
            print("=" * 50)
            print("ดาวน์โหลดและสกัดฟีเจอร์จาก Google HeAR สำเร็จ 100%! 🎉")
            
    except Exception as e:
        import traceback
        print("เกิดข้อผิดพลาดขณะส่งวิเคราะห์เสียง:")
        traceback.print_exc()
 
if __name__ == "__main__":
    test_google_hear()
