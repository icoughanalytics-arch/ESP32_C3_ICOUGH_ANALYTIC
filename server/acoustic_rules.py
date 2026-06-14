import numpy as np
import librosa
from scipy import signal

def analyze_cough_acoustic(file_path):
    """
    ฟังก์ชันสกัดคุณสมบัติทางฟิสิกส์ (Acoustic Features) และวิเคราะห์คะแนนความสอดคล้องกับคลาสโรค 4 คลาส
    ตามเกณฑ์ทางสรีรวิทยาที่กำหนดใน project.md
    """
    # โหลดไฟล์เสียง 16kHz
    audio, sr = librosa.load(file_path, sr=16000, mono=True)
    duration = len(audio) / sr
    
    # ----------------------------------------------------
    # 1. คำนวณหาจุดปะทุหลัก (Explosive Peak) และระยะเวลาไอ (T_cough)
    # ----------------------------------------------------
    rms = librosa.feature.rms(y=audio, frame_length=512, hop_length=128)[0]
    times_rms = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=128)
    
    max_rms = np.max(rms)
    peak_idx = np.argmax(rms)
    peak_time = times_rms[peak_idx]
    
    # คำนวณหาขอบเขตระยะเวลาไอ (T_cough)
    # สัญญาณจะเริ่มเมื่อความดัง > 10% ของจุดสูงสุด และจบเมื่อเบากว่า 10%
    threshold_rms = max_rms * 0.10
    start_frame = 0
    end_frame = len(rms) - 1
    
    # ค้นหาจุดเริ่มต้น (เดินย้อนกลับจาก peak)
    for i in range(peak_idx, 0, -1):
        if rms[i] < threshold_rms:
            start_frame = i
            break
            
    # ค้นหาจุดสิ้นสุด (เดินไปข้างหน้าจาก peak)
    for i in range(peak_idx, len(rms)):
        if rms[i] < threshold_rms:
            end_frame = i
            break
            
    t_start = times_rms[start_frame]
    t_end = times_rms[end_frame]
    t_cough = t_end - t_start
    
    # ----------------------------------------------------
    # 2. คำนวณดัชนีความเปียก (Wetness Index - WI)
    # ----------------------------------------------------
    # นับจำนวนยอดพลังงานย่อย (Local Peaks) ในช่วง 150 ms (0.15s) หลังจากจุด peak หลัก
    window_150ms_samples = int(0.15 * sr)
    peak_sample = int(peak_time * sr)
    post_cough_segment = audio[peak_sample : min(len(audio), peak_sample + window_150ms_samples)]
    
    wi_peaks = 0
    if len(post_cough_segment) > 128:
        post_rms = librosa.feature.rms(y=post_cough_segment, frame_length=128, hop_length=32)[0]
        # ค้นหาจุดยอดท้องถิ่น (Local Peaks)
        max_post_rms = np.max(post_rms) if len(post_rms) > 0 else 0.001
        threshold = max_post_rms * 0.20
        for i in range(1, len(post_rms) - 1):
            if post_rms[i] > post_rms[i-1] and post_rms[i] > post_rms[i+1] and post_rms[i] >= threshold:
                wi_peaks += 1
                
    # ----------------------------------------------------
    # 3. คำนวณหาค่าเฉลี่ย ZCR และ Spectral Centroid
    # ----------------------------------------------------
    zcr = librosa.feature.zero_crossing_rate(y=audio, frame_length=512, hop_length=128)[0]
    mean_zcr = np.mean(zcr)
    
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sr, n_fft=512, hop_length=128)[0]
    mean_centroid = np.mean(centroid)
    
    # ----------------------------------------------------
    # 4. คำนวณอัตราส่วนพลังงานย่านความถี่ (Spectral Energy Ratio - ER)
    # ----------------------------------------------------
    # แปลง Fourier
    stft = np.abs(librosa.stft(audio, n_fft=512, hop_length=128))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=512)
    
    # คำนวณพลังงานรวมแต่ละความถี่
    total_energy = np.sum(stft, axis=1)
    sum_total_energy = np.sum(total_energy) + 1e-6
    
    # Croup Stridor Detector (วิเคราะห์ย่าน 800 - 1800 Hz)
    idx_800_1800 = np.where((freqs >= 800) & (freqs <= 1800))[0]
    er_croup = np.sum(total_energy[idx_800_1800]) / sum_total_energy
    
    # Bronchitis Wheezing Detector (วิเคราะห์ย่าน 300 - 800 Hz)
    idx_300_800 = np.where((freqs >= 300) & (freqs <= 800))[0]
    er_bronchitis = np.sum(total_energy[idx_300_800]) / sum_total_energy

    # ----------------------------------------------------
    # 5. คำนวณคะแนนตามกฎความสอดคล้อง (Acoustic Rule Scoring)
    # ----------------------------------------------------
    scores = {
        "bronchitis": 0.0,
        "croup": 0.0,
        "normal": 0.0,
        "pneumonia": 0.0
    }
    
    # Rule A: WI (ความเปียกมีเสมหะ)
    if wi_peaks >= 3:
        scores["bronchitis"] += 30
        scores["pneumonia"] += 30
    else:
        scores["normal"] += 30
        scores["croup"] += 30
        
    # Rule B: ZCR (ข้ามแกนศูนย์)
    if 0.05 <= mean_zcr <= 0.12:
        scores["bronchitis"] += 20
        scores["pneumonia"] += 20
    elif 0.18 <= mean_zcr <= 0.35:
        scores["normal"] += 20
        scores["croup"] += 20
        
    # Rule C: Spectral Centroid (จุดศูนย์ถ่วงความถี่)
    if mean_centroid < 2100:
        scores["bronchitis"] += 20
        scores["pneumonia"] += 20
    elif mean_centroid > 2800:
        scores["croup"] += 30
        
    # Rule D: ER (อัตราส่วนพลังงานเพื่อหาสิ่งแปลกปลอมในลมหายใจ)
    if er_croup > 0.40:
        scores["croup"] += 40
    if er_bronchitis > 0.35:
        scores["bronchitis"] += 30
        
    # Rule E: T_cough (ระยะเวลาไอ)
    if 0.15 <= t_cough <= 0.30:
        scores["croup"] += 15
    elif 0.20 <= t_cough <= 0.50:
        scores["normal"] += 15
    elif 0.50 <= t_cough <= 0.80:
        scores["bronchitis"] += 15
        
    # ----------------------------------------------------
    # 6. Normalize คะแนนให้เป็นความน่าจะเป็น (%) โดยการใช้ Softmax
    # ----------------------------------------------------
    score_vals = np.array([scores[c] for c in ["bronchitis", "croup", "normal", "pneumonia"]])
    
    # ใช้ Softmax เพื่อแปลงเป็น Probability Distribution ที่เหมาะสม
    exp_scores = np.exp(score_vals / 10.0) # หารด้วย Temperature=10 เพื่อไม่ให้มั่นใจเกินไป
    probabilities = exp_scores / np.sum(exp_scores)
    
    prob_dict = {
        "bronchitis": float(probabilities[0]),
        "croup": float(probabilities[1]),
        "normal": float(probabilities[2]),
        "pneumonia": float(probabilities[3])
    }
    
    # รายละเอียดคุณลักษณะเสียงสำหรับรายงานผล
    features_dict = {
        "wi_peaks": wi_peaks,
        "mean_zcr": float(mean_zcr),
        "mean_centroid": float(mean_centroid),
        "er_croup": float(er_croup),
        "er_bronchitis": float(er_bronchitis),
        "t_cough": float(t_cough)
    }
    
    return prob_dict, features_dict
