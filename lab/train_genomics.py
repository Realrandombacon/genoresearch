"""
Genomics training script — modified by the agent autonomously.
This is the equivalent of karpathy's train.py.

The agent modifies this file to experiment with:
  - Model architecture (CNN, RNN, Transformer, etc.)
  - Hyperparameters (learning rate, batch size, layers, etc.)
  - Data preprocessing (encoding, augmentation)
  - Training strategy (optimizer, scheduler, etc.)

Usage:
    python lab/train_genomics.py --config path/to/config.json --output path/to/result.json
"""

import os
import sys
import json
import time
import argparse

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_args():
    parser = argparse.ArgumentParser(description="Genomics model training")
    parser.add_argument("--config", type=str, required=True, help="Config JSON path")
    parser.add_argument("--output", type=str, required=True, help="Result JSON path")
    parser.add_argument("--time-budget", type=int, default=300, help="Time budget in seconds")
    return parser.parse_args()


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def encode_sequence(seq: str, vocab: dict = None) -> list[int]:
    """Encode a DNA/protein sequence to integers."""
    if vocab is None:
        # Default DNA vocab
        vocab = {"A": 0, "T": 1, "C": 2, "G": 3, "N": 4}
    return [vocab.get(c, len(vocab)) for c in seq.upper()]


def build_model(config: dict):
    """Build a simple model based on config. Override this for experiments."""
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        return None

    # Default: simple 1D CNN for sequence classification
    class GenomicsCNN(nn.Module):
        def __init__(self, vocab_size=5, embed_dim=32, num_filters=64,
                     kernel_size=7, num_classes=2, depth=3):
            super().__init__()
            self.embed = nn.Embedding(vocab_size, embed_dim)
            layers = []
            in_ch = embed_dim
            for i in range(depth):
                out_ch = num_filters * (2 ** i)
                layers.extend([
                    nn.Conv1d(in_ch, out_ch, kernel_size, padding=kernel_size // 2),
                    nn.ReLU(),
                    nn.MaxPool1d(2),
                ])
                in_ch = out_ch
            self.convs = nn.Sequential(*layers)
            self.classifier = nn.Sequential(
                nn.AdaptiveAvgPool1d(1),
                nn.Flatten(),
                nn.Linear(in_ch, num_classes),
            )

        def forward(self, x):
            x = self.embed(x).permute(0, 2, 1)  # (B, C, L)
            x = self.convs(x)
            return self.classifier(x)

    return GenomicsCNN(
        vocab_size=config.get("vocab_size", 5),
        embed_dim=config.get("embed_dim", 32),
        num_filters=config.get("num_filters", 64),
        kernel_size=config.get("kernel_size", 7),
        num_classes=config.get("num_classes", 2),
        depth=config.get("depth", 3),
    )


def train(config: dict, time_budget: int) -> dict:
    """
    Train the model within time budget. Returns metrics dict.
    """
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
    except ImportError:
        return {"val_loss": float("inf"), "error": "PyTorch not installed"}

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(config)
    if model is None:
        return {"val_loss": float("inf"), "error": "Failed to build model"}

    model = model.to(device)
    lr = config.get("learning_rate", 1e-3)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    # Generate synthetic data for now (real data loading comes later)
    seq_len = config.get("seq_len", 200)
    batch_size = config.get("batch_size", 32)
    num_batches = config.get("num_batches", 100)

    best_val_loss = float("inf")
    epoch = 0
    start = time.time()

    while (time.time() - start) < time_budget:
        epoch += 1
        model.train()
        train_loss = 0

        for _ in range(num_batches):
            if (time.time() - start) >= time_budget:
                break
            x = torch.randint(0, 5, (batch_size, seq_len), device=device)
            y = torch.randint(0, config.get("num_classes", 2), (batch_size,), device=device)

            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        avg_train = train_loss / num_batches

        # Validation
        model.eval()
        with torch.no_grad():
            val_x = torch.randint(0, 5, (batch_size * 4, seq_len), device=device)
            val_y = torch.randint(0, config.get("num_classes", 2), (batch_size * 4,), device=device)
            val_logits = model(val_x)
            val_loss = criterion(val_logits, val_y).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss

        print(f"Epoch {epoch}: train_loss={avg_train:.4f} val_loss={val_loss:.4f}")

    duration = time.time() - start
    return {
        "val_loss": best_val_loss,
        "epochs": epoch,
        "duration": round(duration, 1),
        "device": device,
    }


def main():
    args = parse_args()
    config = load_config(args.config)
    result = train(config, args.time_budget)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Result: val_loss={result.get('val_loss', '?')}")


if __name__ == "__main__":
    main()
