import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import librosa
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "cough_sound_data"
DEFAULT_MODEL_DIR = BASE_DIR / "models"
LABELS = ["bronchitis", "pneumonia"]


def label_from_name(path: Path) -> str:
    for parent in path.parents:
        parent_name = parent.name.lower()
        if parent_name in LABELS:
            return parent_name

    name = path.name.lower()
    if name.startswith("bronchitis"):
        return "bronchitis"
    if name.startswith("pneumonia"):
        return "pneumonia"
    raise ValueError(f"Cannot infer label from filename: {path.name}")


def scan_files(data_dir: Path):
    files = []
    for pattern in ("*.mp3", "*.wav", "*.m4a"):
        for path in sorted(data_dir.rglob(pattern)):
            files.append((path, label_from_name(path)))
    if not files:
        raise SystemExit(f"No audio files found in {data_dir}")
    return files


def stratified_split(items, val_ratio: float, seed: int):
    rng = random.Random(seed)
    groups = defaultdict(list)
    for item in items:
        groups[item[1]].append(item)

    train, val = [], []
    for label, group in groups.items():
        rng.shuffle(group)
        val_count = max(1, round(len(group) * val_ratio))
        val.extend(group[:val_count])
        train.extend(group[val_count:])

    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def load_log_mel(path: Path, sample_rate: int, duration: float, n_mels: int, augment: bool):
    samples = int(sample_rate * duration)
    audio, _ = librosa.load(path, sr=sample_rate, mono=True)

    if len(audio) < samples:
        audio = np.pad(audio, (0, samples - len(audio)))
    elif len(audio) > samples:
        if augment:
            frame = max(1, sample_rate // 10)
            energy = np.convolve(audio * audio, np.ones(frame, dtype=np.float32), mode="same")
            center = int(np.argmax(energy))
            jitter = random.randint(-sample_rate // 2, sample_rate // 2)
            start = center - samples // 2 + jitter
            start = max(0, min(start, len(audio) - samples))
        else:
            frame = max(1, sample_rate // 10)
            energy = np.convolve(audio * audio, np.ones(frame, dtype=np.float32), mode="same")
            center = int(np.argmax(energy))
            start = center - samples // 2
            start = max(0, min(start, len(audio) - samples))
        audio = audio[start : start + samples]

    if augment:
        shift = random.randint(-sample_rate // 10, sample_rate // 10)
        audio = np.roll(audio, shift)
        audio = audio + np.random.normal(0, 0.003, size=audio.shape).astype(np.float32)

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sample_rate,
        n_fft=512,
        hop_length=160,
        n_mels=n_mels,
        fmin=40,
        fmax=sample_rate // 2,
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    log_mel = (log_mel - log_mel.mean()) / (log_mel.std() + 1e-6)
    return log_mel.astype(np.float32)


class CoughDataset(Dataset):
    def __init__(self, items, sample_rate: int, duration: float, n_mels: int, augment: bool):
        self.items = items
        self.sample_rate = sample_rate
        self.duration = duration
        self.n_mels = n_mels
        self.augment = augment
        self.label_to_id = {label: idx for idx, label in enumerate(LABELS)}

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        path, label = self.items[index]
        features = load_log_mel(path, self.sample_rate, self.duration, self.n_mels, self.augment)
        return torch.from_numpy(features).unsqueeze(0), torch.tensor(self.label_to_id[label])


class TinyCoughCnn(nn.Module):
    def __init__(self, classes: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Dropout(0.15),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Dropout(0.2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(64, classes),
        )

    def forward(self, x):
        return self.net(x)


def evaluate(model, loader, device):
    model.eval()
    total, correct, loss_total = 0, 0, 0.0
    matrix = torch.zeros(len(LABELS), len(LABELS), dtype=torch.int64)
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        for features, labels in loader:
            features = features.to(device)
            labels = labels.to(device)
            logits = model(features)
            loss = criterion(logits, labels)
            preds = logits.argmax(dim=1)
            loss_total += loss.item() * labels.size(0)
            total += labels.size(0)
            correct += (preds == labels).sum().item()
            for truth, pred in zip(labels.cpu(), preds.cpu()):
                matrix[truth, pred] += 1

    recalls = []
    for class_id in range(len(LABELS)):
        class_total = matrix[class_id].sum().item()
        recalls.append(matrix[class_id, class_id].item() / max(class_total, 1))

    return {
        "loss": loss_total / max(total, 1),
        "accuracy": correct / max(total, 1),
        "balanced_accuracy": sum(recalls) / len(recalls),
        "recall_by_class": {label: recalls[idx] for idx, label in enumerate(LABELS)},
        "confusion_matrix": matrix.tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--n-mels", type=int, default=64)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    items = scan_files(args.data_dir)
    train_items, val_items = stratified_split(items, args.val_ratio, args.seed)
    print(f"files={len(items)} train={len(train_items)} val={len(val_items)}")
    for label in LABELS:
        print(f"{label}: {sum(1 for _, item_label in items if item_label == label)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_ds = CoughDataset(train_items, args.sample_rate, args.duration, args.n_mels, augment=True)
    val_ds = CoughDataset(val_items, args.sample_rate, args.duration, args.n_mels, augment=False)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    model = TinyCoughCnn(classes=len(LABELS)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    counts = torch.tensor(
        [sum(1 for _, label in train_items if label == class_name) for class_name in LABELS],
        dtype=torch.float32,
    )
    class_weights = (counts.sum() / (len(LABELS) * counts)).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    best_score = -1.0
    best_state = None
    history = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        total = 0
        for features, labels in train_loader:
            features = features.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(features)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * labels.size(0)
            total += labels.size(0)

        metrics = evaluate(model, val_loader, device)
        metrics["epoch"] = epoch
        metrics["train_loss"] = train_loss / max(total, 1)
        history.append(metrics)
        print(
            f"epoch={epoch:03d} train_loss={metrics['train_loss']:.4f} "
            f"val_loss={metrics['loss']:.4f} val_acc={metrics['accuracy']:.3f} "
            f"val_bal_acc={metrics['balanced_accuracy']:.3f}"
        )

        if metrics["balanced_accuracy"] > best_score:
            best_score = metrics["balanced_accuracy"]
            best_state = model.state_dict()

    args.model_dir.mkdir(exist_ok=True)
    model_path = args.model_dir / "cough_cnn.pt"
    if best_state is not None:
        model.load_state_dict(best_state)
    torch.save(
        {
            "model_state": model.state_dict(),
            "labels": LABELS,
            "sample_rate": args.sample_rate,
            "duration": args.duration,
            "n_mels": args.n_mels,
            "architecture": "TinyCoughCnn",
        },
        model_path,
    )

    final_metrics = evaluate(model, val_loader, device)
    metrics_path = args.model_dir / "cough_cnn_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "labels": LABELS,
                "files": len(items),
                "train_files": len(train_items),
                "val_files": len(val_items),
                "best_val_balanced_accuracy": best_score,
                "final_val": final_metrics,
                "history": history,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"saved_model={model_path}")
    print(f"saved_metrics={metrics_path}")


if __name__ == "__main__":
    main()
