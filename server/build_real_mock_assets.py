import argparse
import shutil
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_SOURCE_DIR = BASE_DIR / "processed_cough_data" / "train_segments" / "bronchitis"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "web" / "i-cough" / "public" / "real-mock"
DEFAULT_SQL_PATH = PROJECT_DIR / "web" / "i-cough" / "supabase" / "seed_real_mock_data.sql"
DEVICE_ID = "22222222-2222-2222-2222-222222222222"
SUPABASE_STORAGE_BASE_URL = "https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public"


def make_spectrogram(audio_path: Path, image_path: Path, sample_rate: int):
    audio, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160,
        n_mels=64,
        fmin=40,
        fmax=sr // 2,
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)

    plt.figure(figsize=(7, 3), dpi=160)
    librosa.display.specshow(
        log_mel,
        sr=sr,
        hop_length=160,
        x_axis="time",
        y_axis="mel",
        cmap="magma",
        fmin=40,
        fmax=sr // 2,
    )
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(image_path, bbox_inches="tight", pad_inches=0)
    plt.close()


def score_for_index(index: int):
    rows = [
        ("0.1800", "0.0600", "0.6800", "0.0800", "moderate"),
        ("0.1200", "0.0500", "0.7400", "0.0900", "moderate"),
        ("0.0900", "0.0300", "0.8300", "0.0500", "high"),
        ("0.2100", "0.1000", "0.5700", "0.1200", "moderate"),
        ("0.0800", "0.0400", "0.4600", "0.4200", "low"),
        ("0.1400", "0.0800", "0.6600", "0.1200", "moderate"),
        ("0.1100", "0.0500", "0.7900", "0.0500", "high"),
        ("0.1900", "0.0700", "0.6100", "0.1300", "moderate"),
        ("0.1000", "0.0400", "0.5200", "0.3400", "low"),
        ("0.1600", "0.0600", "0.7000", "0.0800", "moderate"),
    ]
    return rows[index]


def build_sql(files):
    values = []
    for index, source_name in enumerate(files):
        num = index + 1
        pneumonia, croup, bronchitis, normal, risk = score_for_index(index)
        noti_time = "now() - interval '{} hours {} minutes'".format(11 - index, (index * 7) % 60)
        if risk != "high":
            noti_time = "null"

        values.append(
            f"""  (
    'bbbbbbbb-0000-0000-0000-{num:012d}',
    '{DEVICE_ID}',
    '{SUPABASE_STORAGE_BASE_URL}/cough-spectrum/spectrogram-{num:02d}.png',
    '{SUPABASE_STORAGE_BASE_URL}/cough-audio/audio-{num:02d}.wav',
    {pneumonia},
    {croup},
    {bronchitis},
    {normal},
    {noti_time},
    '{risk}',
    now() - interval '{11 - index} hours {(index * 7) % 60} minutes'
  )"""
        )

    return f"""-- Real-ish mock data generated from processed bronchitis train segments.
-- Run after schema_simple_3_tables.sql.

insert into public.device (id, device_name, device_code)
values (
  '{DEVICE_ID}',
  'iCough Real Mock Device',
  'ICOUGH-REAL-MOCK-001'
)
on conflict (id) do update set
  device_name = excluded.device_name,
  device_code = excluded.device_code;

delete from public.summary_record
where device_id = '{DEVICE_ID}';

delete from public.cough_record
where device_id = '{DEVICE_ID}';

insert into public.cough_record (
  id,
  device_id,
  spectrum_path,
  audio_path,
  pneumonia_score,
  croup_score,
  bronchitis_score,
  normal_score,
  noti_time,
  risk_level,
  created_at
)
values
{",\n".join(values)};
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sql-path", type=Path, default=DEFAULT_SQL_PATH)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sample-rate", type=int, default=16000)
    args = parser.parse_args()

    wav_files = sorted(args.source_dir.glob("*.wav"))[: args.limit]
    if len(wav_files) < args.limit:
        raise SystemExit(f"Need {args.limit} wav files, found {len(wav_files)} in {args.source_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.sql_path.parent.mkdir(parents=True, exist_ok=True)

    copied_names = []
    for index, source in enumerate(wav_files, start=1):
        audio_out = args.output_dir / f"audio-{index:02d}.wav"
        image_out = args.output_dir / f"spectrogram-{index:02d}.png"
        shutil.copy2(source, audio_out)
        make_spectrogram(source, image_out, args.sample_rate)
        copied_names.append(source.name)
        print(f"{index:02d}. {source.name} -> {audio_out.name}, {image_out.name}")

    args.sql_path.write_text(build_sql(copied_names), encoding="utf-8")
    print(f"\nWrote assets to: {args.output_dir}")
    print(f"Wrote seed SQL to: {args.sql_path}")


if __name__ == "__main__":
    main()
