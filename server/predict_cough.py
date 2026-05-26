import argparse
from pathlib import Path

import torch

from train_cough_cnn import TinyCoughCnn, load_log_mel


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = BASE_DIR / "models" / "cough_cnn.pt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()

    checkpoint = torch.load(args.model, map_location="cpu", weights_only=False)
    labels = checkpoint["labels"]
    model = TinyCoughCnn(classes=len(labels))
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    features = load_log_mel(
        args.audio,
        sample_rate=checkpoint["sample_rate"],
        duration=checkpoint["duration"],
        n_mels=checkpoint["n_mels"],
        augment=False,
    )
    x = torch.from_numpy(features).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(x), dim=1).squeeze(0)

    ranked = sorted(zip(labels, probs.tolist()), key=lambda item: item[1], reverse=True)
    for label, probability in ranked:
        print(f"{label}: {probability:.4f}")


if __name__ == "__main__":
    main()
