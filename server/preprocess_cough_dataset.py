import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = BASE_DIR / "raw_sound_data"
DEFAULT_OUT_DIR = BASE_DIR / "processed_cough_data"
LABELS = ["bronchitis", "croup", "normal", "pneumonia"]


def label_from_path(path: Path) -> str:
    for parent in path.parents:
        if parent.name.lower() in LABELS:
            return parent.name.lower()
    name = path.name.lower()
    for label in LABELS:
        if name.startswith(label):
            return label
    raise ValueError(f"Cannot infer label from {path}")


def scan_audio(raw_dir: Path):
    files = []
    for ext in ("*.mp3", "*.wav", "*.m4a", "*.webm", "*.WAV", "*.MP3", "*.WEBM"):
        files.extend(raw_dir.rglob(ext))
    grouped = defaultdict(list)
    for path in sorted(files):
        grouped[label_from_path(path)].append(path)
    return grouped


def rms_envelope(audio: np.ndarray, frame: int, hop: int):
    if len(audio) < frame:
        padded = np.pad(audio, (0, frame - len(audio)))
    else:
        padded = audio
    frames = librosa.util.frame(padded, frame_length=frame, hop_length=hop)
    return np.sqrt(np.mean(frames * frames, axis=0) + 1e-10)


def pick_centers(audio: np.ndarray, sample_rate: int, duration: float, max_segments: int):
    target = int(sample_rate * duration)
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
    min_gap = int(duration * sample_rate * 0.75)
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
    segment = segment - float(np.mean(segment))
    peak = float(np.max(np.abs(segment)))
    if peak > 1e-6:
        segment = segment / peak * 0.95
    return segment


def clean_output(out_dir: Path):
    for subdir in ["train_segments", "raw_test"]:
        target = out_dir / subdir
        if target.exists():
            shutil.rmtree(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--test-per-class", type=int, default=10)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--max-segments-per-file", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    grouped = scan_audio(args.raw_dir)
    clean_output(args.out_dir)

    metadata_path = args.out_dir / "metadata.csv"
    args.out_dir.mkdir(exist_ok=True)
    rows = []

    for label in LABELS:
        files = grouped[label]
        if len(files) == 0:
            print(f"Warning: Class '{label}' has 0 files! Skipping...")
            continue

        actual_test_per_class = min(args.test_per_class, max(0, len(files) - 1))

        shuffled = files[:]
        rng.shuffle(shuffled)
        raw_test = sorted(shuffled[: actual_test_per_class])
        train_raw = sorted(shuffled[actual_test_per_class :])

        raw_test_dir = args.out_dir / "raw_test" / label
        train_dir = args.out_dir / "train_segments" / label
        raw_test_dir.mkdir(parents=True, exist_ok=True)
        train_dir.mkdir(parents=True, exist_ok=True)

        for source in raw_test:
            shutil.copy2(source, raw_test_dir / source.name)
            rows.append([label, "raw_test", source.name, "", str(source)])

        segment_count = 0
        for source in train_raw:
            audio, _ = librosa.load(source, sr=args.sample_rate, mono=True)
            centers = pick_centers(audio, args.sample_rate, args.duration, args.max_segments_per_file)
            for index, center in enumerate(centers, 1):
                segment = make_segment(audio, center, args.sample_rate, args.duration)
                output_name = f"{source.stem}_seg{index:02d}.wav"
                output_path = train_dir / output_name
                sf.write(output_path, segment, args.sample_rate, subtype="PCM_16")
                segment_count += 1
                rows.append([label, "train_segment", output_name, source.name, str(source)])

        print(f"{label}: raw={len(files)} raw_test={len(raw_test)} train_raw={len(train_raw)} train_segments={segment_count}")

    with metadata_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "split", "output_file", "source_file", "source_path"])
        writer.writerows(rows)
    print(f"metadata={metadata_path}")


if __name__ == "__main__":
    main()
