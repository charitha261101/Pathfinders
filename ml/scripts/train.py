# ml/scripts/train.py

import sys
import argparse
import logging
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.prediction_engine_pkg.model.lstm_network import PathWiseLSTM
from services.prediction_engine_pkg.model.feature_engineering import FeatureEngineer
from services.prediction_engine_pkg.model.trainer import LSTMTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# Defaults / model config
DEFAULT_MODEL_CONFIG = {
    "hidden_size": 128,
    "num_layers": 2,
    "dropout": 0.2,
}


# Helpers

def set_seed(seed):
    """Seed Python, NumPy, and Torch for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def pick_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_telemetry(data_dir):
    """Concatenate every parquet file in data_dir into a single DataFrame."""
    data_path = Path(data_dir)
    frames = []
    for parquet_path in sorted(data_path.glob("*.parquet")):
        frame = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {len(frame):,} rows from {parquet_path.name}")
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No parquet files found in {data_dir}")
    return pd.concat(frames, ignore_index=True)


def build_windows(telemetry_df, feature_engineer):
    """Engineer features and build (windows, targets) arrays per link."""
    window_chunks = []
    target_chunks = []

    for link_id, link_frame in telemetry_df.groupby("link_id"):
        link_frame = feature_engineer.compute_features(link_frame)
        windows, targets = feature_engineer.create_sequences(link_frame)
        if len(windows) == 0:
            continue
        windows = feature_engineer.normalize(windows, link_id, fit=True)
        window_chunks.append(windows)
        target_chunks.append(targets)
        logger.info(f"  {link_id}: {len(windows)} sequences")

    if not window_chunks:
        raise RuntimeError("Feature engineering produced zero sequences.")

    return np.concatenate(window_chunks), np.concatenate(target_chunks)


def chronological_split(windows, targets, val_fraction):
    """Chronological (non-shuffled) train/val split."""
    split_idx = int(len(windows) * (1.0 - val_fraction))
    return (
        windows[:split_idx],
        windows[split_idx:],
        targets[:split_idx],
        targets[split_idx:],
    )


# Entrypoint

def parse_args():
    parser = argparse.ArgumentParser(description="Train PathWise LSTM model")
    parser.add_argument("--data-dir", type=str, default="ml/data/synthetic")
    parser.add_argument("--checkpoint-dir", type=str, default="ml/checkpoints")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-fraction", type=float, default=0.2,
                        help="Fraction of data reserved for validation")
    parser.add_argument("--patience", type=int, default=10,
                        help="Early-stopping patience (epochs)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke-test", action="store_true",
                        help="Quick training with reduced data for CI")
    return parser.parse_args()


def main():
    args = parse_args()
    set_seed(args.seed)
    device = pick_device()
    logger.info(f"Device: {device} | seed: {args.seed}")

    # 1. Load
    logger.info("Loading data...")
    telemetry_df = load_telemetry(args.data_dir)

    if args.smoke_test:
        telemetry_df = telemetry_df.groupby("link_id").head(5000).reset_index(drop=True)
        logger.info(f"Smoke test: reduced to {len(telemetry_df):,} rows")

    # 2. Feature engineering / windowing
    logger.info("Computing features...")
    feature_engineer = FeatureEngineer()
    windows, targets = build_windows(telemetry_df, feature_engineer)

    # 3. Split
    train_x, val_x, train_y, val_y = chronological_split(
        windows, targets, val_fraction=args.val_fraction
    )
    logger.info(f"Training set:   {len(train_x)} samples")
    logger.info(f"Validation set: {len(val_x)} samples")

    # 4. Model
    model = PathWiseLSTM(
        input_size=FeatureEngineer.NUM_FEATURES,
        horizon=FeatureEngineer.HORIZON,
        **DEFAULT_MODEL_CONFIG,
    )

    # 5. Train
    trainer = LSTMTrainer(
        model=model,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.epochs,
        patience=args.patience,
        checkpoint_dir=args.checkpoint_dir,
    )

    logger.info("Starting training...")
    history = trainer.train(train_x, train_y, val_x, val_y)

    best_val_loss = min(history["val_loss"])
    logger.info(f"Training complete. Best val loss: {best_val_loss:.6f}")
    logger.info(f"Model saved to {args.checkpoint_dir}/best_model.pt")


if __name__ == "__main__":
    main()
