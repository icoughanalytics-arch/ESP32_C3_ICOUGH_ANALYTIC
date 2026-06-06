import argparse
import sys
from pathlib import Path
import librosa
import numpy as np
import soundfile as sf

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = BASE_DIR / "raw_sound_data"
DEFAULT_OUT_DIR = BASE_DIR / "normalize_sound_data"
LABELS = ["bronchitis", "croup", "normal", "pneumonia"]

def rms_envelope(audio: np.ndarray, frame: int, hop: int):
    if len(audio) < frame:
        padded = np.pad(audio, (0, frame - len(audio)))
    else:
        padded = audio
    frames = librosa.util.frame(padded, frame_length=frame, hop_length=hop)
    return np.sqrt(np.mean(frames * frames, axis=0) + 1e-10)

def pick_centers(audio: np.ndarray, sample_rate: int, duration: float, max_segments: int):
    target = int(sample_rate * duration)
    # หากคลิปเสียงสั้นกว่าหรือเท่ากับความยาวเป้าหมาย (3 วินาที) ให้ใช้จุดกึ่งกลางจุดเดียว
    if len(audio) <= target:
        return [len(audio) // 2]

    frame = int(0.08 * sample_rate)
    hop = int(0.02 * sample_rate)
    env = rms_envelope(audio, frame, hop)
    threshold = max(float(np.percentile(env, 75)), float(env.max() * 0.35))
    candidate_frames = np.where(env >= threshold)[0]

    if len(candidate_frames) == 0:
        return [int(np.argmax(env) * hop)]

    centers = []
    min_gap = int(duration * sample_rate * 0.75) # ป้องกันไม่ให้ segment ซ้อนทับกันมากเกินไป
    for frame_idx in candidate_frames[np.argsort(env[candidate_frames])[::-1]]:
        center = int(frame_idx * hop + frame // 2)
        if all(abs(center - existing) >= min_gap for existing in centers):
            centers.append(center)
        if len(centers) >= max_segments:
            break
    return sorted(centers)

def make_segment(audio: np.ndarray, center: int, sample_rate: int, duration: float):
    target = int(sample_rate * duration)
    start = center - target // 2
    end = start + target

    pad_left = max(0, -start)
    pad_right = max(0, end - len(audio))
    start = max(0, start)
    end = min(len(audio), end)
    
    segment = audio[start:end]
    if pad_left or pad_right:
        segment = np.pad(segment, (pad_left, pad_right))

    segment = segment.astype(np.float32)
    # ทำ Zero-mean
    segment = segment - float(np.mean(segment))
    # Peak Normalization (ปรับความดังสูงสุดเป็น 0.95 เพื่อไม่ให้เสียงแตก)
    peak = float(np.max(np.abs(segment)))
    if peak > 1e-6:
        segment = segment / peak * 0.95
    return segment

def main():
    parser = argparse.ArgumentParser(description="Normalize and segment cough audio files to max 3 seconds.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--max-segments", type=int, default=15, help="Max segments to split from a single long file")
    args = parser.parse_args()

    if not args.raw_dir.exists():
        print(f"Error: Raw directory not found at {args.raw_dir}")
        sys.exit(1)

    print(f"Scanning raw files from: {args.raw_dir}")
    print(f"Output normalized files to: {args.out_dir}")

    for label in LABELS:
        class_raw_dir = args.raw_dir / label
        class_out_dir = args.out_dir / label

        if not class_raw_dir.exists():
            class_out_dir.mkdir(parents=True, exist_ok=True)
            print(f"Label '{label}': Directory not found in raw, created empty output directory.")
            continue

        class_out_dir.mkdir(parents=True, exist_ok=True)
        
        # ค้นหาไฟล์เสียง .mp3, .wav, .m4a, .webm
        audio_files = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.webm", "*.WAV", "*.MP3", "*.WEBM"):
            audio_files.extend(class_raw_dir.glob(ext))
        
        audio_files = sorted(list(set(audio_files)))
        print(f"Processing '{label}': Found {len(audio_files)} files.")

        processed_count = 0
        segment_total = 0
        corrupted_count = 0

        for file_path in audio_files:
            try:
                # โหลดไฟล์เสียงด้วย Librosa
                audio, sr = librosa.load(file_path, sr=args.sample_rate, mono=True)
            except Exception as e:
                print(f"  [Error] Failed to load {file_path.name}: {e}")
                corrupted_count += 1
                continue

            # ตรวจสอบความยาวเพื่อหาจํานวน segments
            duration_sec = len(audio) / args.sample_rate
            
            # ถ้าคลิปยาวเกิน 3.0 วินาที จะยอมให้ซอยได้หลาย segment ตามความเหมาะสม
            # ถ้าสั้นกว่านั้น จะได้ 1 segment เสมอ
            max_seg = args.max_segments if duration_sec > args.duration else 1
            
            centers = pick_centers(audio, args.sample_rate, args.duration, max_seg)
            
            for index, center in enumerate(centers, 1):
                segment = make_segment(audio, center, args.sample_rate, args.duration)
                
                # ตั้งชื่อไฟล์ผลลัพธ์
                output_name = f"{file_path.stem}_seg{index:02d}.wav"
                output_path = class_out_dir / output_name
                
                # เขียนไฟล์ .wav
                sf.write(output_path, segment, args.sample_rate, subtype="PCM_16")
                segment_total += 1
            
            processed_count += 1

        print(f"Label '{label}' summary: Loaded {processed_count} files, Generated {segment_total} segments (3s), Corrupted/Skipped {corrupted_count} files.")

    print("\nNormalization and Segmentation Complete!")
    print(f"Normalized files are stored under: {args.out_dir.resolve()}")

if __name__ == "__main__":
    main()
