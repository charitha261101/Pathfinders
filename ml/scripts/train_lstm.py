"""
Train the PathWiseLSTM model on synthetic telemetry data.

Reads parquet files, engineers 13 features, creates sliding windows
(60-step input -> 30-step forecast target), trains, and saves checkpoint.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import ConcatDataset, DataLoader, Dataset, random_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "services" / "prediction-engine"))

from model.lstm_network import PathWiseLSTM, PathWiseLoss


# Hyperparameters / config
INPUT_LEN       = 60
HORIZON         = 30
WINDOW_STRIDE   = 30
ROLLING_WINDOW  = 30
EMA_ALPHA       = 0.3

INPUT_FEATURES  = 13
HIDDEN_SIZE     = 128
NUM_LAYERS      = 2
DROPOUT         = 0.2

BATCH_SIZE      = 512
LEARNING_RATE   = 1e-3
MAX_EPOCHS      = 10
EARLY_STOP_PATIENCE = 5
LR_PATIENCE     = 3
GRADIENT_CLIP   = 1.0
VAL_FRACTION    = 0.10
MIN_VAL_SAMPLES = 1000
SEED            = 42

LOSS_WEIGHTS    = {"latency": 1.0, "jitter": 1.0, "packet_loss": 2.0}
UNDERESTIMATE_PENALTY = 2.0

DATA_DIR        = PROJECT_ROOT / "ml" / "data" / "synthetic"
CHECKPOINT_DIR  = PROJECT_ROOT / "ml" / "checkpoints"


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# Feature Engineering

def rolling_mean(values, window=ROLLING_WINDOW):
    series = pd.Series(values)
    return series.rolling(window, min_periods=1).mean().values.astype(np.float32)


def rolling_std(values, window=ROLLING_WINDOW):
    series = pd.Series(values)
    return series.rolling(window, min_periods=1).std().fillna(0).values.astype(np.float32)


def ema(values, alpha=EMA_ALPHA):
    series = pd.Series(values)
    return series.ewm(alpha=alpha, adjust=False).mean().values.astype(np.float32)


def build_features(telemetry_df):
    """Build 13 features from raw 5-column telemetry DataFrame."""
    latency        = telemetry_df["latency_ms"].values.astype(np.float32)
    jitter         = telemetry_df["jitter_ms"].values.astype(np.float32)
    packet_loss    = telemetry_df["packet_loss_pct"].values.astype(np.float32)
    bandwidth_util = telemetry_df["bandwidth_util_pct"].values.astype(np.float32)
    rtt            = telemetry_df["rtt_ms"].values.astype(np.float32)

    feature_matrix = np.column_stack([
        latency, jitter, packet_loss, bandwidth_util, rtt,
        rolling_mean(latency), rolling_std(latency),
        rolling_mean(jitter),
        ema(latency), ema(packet_loss),
        np.diff(latency, prepend=latency[0]),
        np.diff(jitter, prepend=jitter[0]),
        np.diff(packet_loss, prepend=packet_loss[0]),
    ])
    return feature_matrix


# Dataset

class TelemetryDataset(Dataset):
    """Sliding window dataset: INPUT_LEN steps -> HORIZON target steps."""

    def __init__(self, features, input_len=INPUT_LEN, horizon=HORIZON, stride=WINDOW_STRIDE):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.input_len = input_len
        self.horizon = horizon
        max_start = len(features) - input_len - horizon
        self.indices = list(range(0, max_start, stride))

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        start = self.indices[idx]
        x = self.features[start: start + self.input_len]
        y = self.features[start + self.input_len: start + self.input_len + self.horizon, :3]
        return x, y


# Pipeline stages

def load_link_features(data_dir):
    parquet_files = sorted(data_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(
            f"No parquet files found in {data_dir}. Run generate_synthetic_data.py first."
        )

    print(f"Loading data from {len(parquet_files)} files...")
    per_link_features = []
    for parquet_path in parquet_files:
        telemetry_df = pd.read_parquet(parquet_path)
        print(f"  {parquet_path.stem}: {len(telemetry_df):,} rows ... ", end="", flush=True)
        start = time.time()
        per_link_features.append(build_features(telemetry_df))
        print(f"features built in {time.time() - start:.1f}s")
    return per_link_features


def compute_norm_stats(per_link_features):
    combined = np.vstack(per_link_features)
    means = combined.mean(axis=0)
    stds = combined.std(axis=0) + 1e-8
    print(f"Total data points: {len(combined):,}")
    return means, stds


def build_dataset(per_link_features, means, stds):
    per_link_datasets = [TelemetryDataset((feats - means) / stds) for feats in per_link_features]
    return ConcatDataset(per_link_datasets)


def split_train_val(full_dataset):
    n_total = len(full_dataset)
    n_val = max(MIN_VAL_SAMPLES, int(n_total * VAL_FRACTION))
    n_train = n_total - n_val
    print(f"Train samples: {n_train:,} | Validation samples: {n_val:,}")
    return random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(SEED),
    )


def build_model_and_optim():
    model = PathWiseLSTM(
        input_size=INPUT_FEATURES,
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT,
        horizon=HORIZON,
    )
    criterion = PathWiseLoss(weights=LOSS_WEIGHTS, underestimate_penalty=UNDERESTIMATE_PENALTY)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=LR_PATIENCE, factor=0.5)
    return model, criterion, optimizer, scheduler


def run_one_epoch(model, loader, criterion, optimizer=None):
    """One pass over loader. If optimizer given, train; else validate."""
    is_training = optimizer is not None
    model.train(is_training)

    total_loss = 0.0
    n_batches = 0

    context = torch.enable_grad() if is_training else torch.no_grad()
    with context:
        for x_batch, y_batch in loader:
            if is_training:
                optimizer.zero_grad()
            preds, _confidence = model(x_batch)
            loss = criterion(preds, y_batch)
            if is_training:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
                optimizer.step()
            total_loss += loss.item()
            n_batches += 1

    return total_loss / max(n_batches, 1)


def save_checkpoint(model, optimizer, epoch, val_loss, means, stds, path):
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": epoch,
            "val_loss": val_loss,
            "means": means.tolist(),
            "stds": stds.tolist(),
        },
        path,
    )


def train():
    set_seed(SEED)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    per_link_features = load_link_features(DATA_DIR)
    means, stds = compute_norm_stats(per_link_features)

    full_dataset = build_dataset(per_link_features, means, stds)
    train_ds, val_ds = split_train_val(full_dataset)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=False)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model, criterion, optimizer, scheduler = build_model_and_optim()
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {n_params:,}")
    print("Training on CPU...")
    print("-" * 60)

    best_val_loss = float("inf")
    epochs_no_improve = 0
    checkpoint_path = CHECKPOINT_DIR / "best_model.pt"

    for epoch in range(1, MAX_EPOCHS + 1):
        epoch_start = time.time()

        avg_train_loss = run_one_epoch(model, train_loader, criterion, optimizer)
        avg_val_loss = run_one_epoch(model, val_loader, criterion, optimizer=None)
        scheduler.step(avg_val_loss)

        elapsed = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]
        marker = ""

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            epochs_no_improve = 0
            marker = " * BEST"
            save_checkpoint(model, optimizer, epoch, avg_val_loss, means, stds, checkpoint_path)
        else:
            epochs_no_improve += 1

        print(
            f"Epoch {epoch:2d}/{MAX_EPOCHS} | "
            f"Train: {avg_train_loss:.4f} | Val: {avg_val_loss:.4f} | "
            f"LR: {current_lr:.1e} | {elapsed:.1f}s{marker}"
        )

        if epochs_no_improve >= EARLY_STOP_PATIENCE:
            print(f"Early stopping at epoch {epoch} (no improvement for {EARLY_STOP_PATIENCE} epochs)")
            break

    print("-" * 60)
    print(f"Training complete. Best val loss: {best_val_loss:.4f}")
    print(f"Checkpoint saved to: {checkpoint_path}")


if __name__ == "__main__":
    train()
