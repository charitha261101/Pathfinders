"""
PathWise AI - LSTM Training on Real-World Calibrated Data.

Pipeline stages:
  1. Load real-world calibrated parquet data (one file per link).
  2. Engineer 13 features per timestep.
  3. Build sliding-window datasets per link, then concatenate.
  4. Train PathWiseLSTM with the asymmetric PathWiseLoss.
  5. Evaluate on the held-out test set.
  6. Save the best checkpoint for inference.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import ConcatDataset, DataLoader, Dataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "services" / "prediction-engine"))
from model.lstm_network import PathWiseLSTM, PathWiseLoss

DATA_DIR = PROJECT_ROOT / "ml" / "data" / "real_world"
CHECKPOINT_DIR = PROJECT_ROOT / "ml" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


# Hyperparameters
WINDOW_SIZE         = 60
HORIZON             = 30
BATCH_SIZE          = 256
LEARNING_RATE       = 1e-3
WEIGHT_DECAY        = 1e-4
MAX_EPOCHS          = 50
EARLY_STOP_PATIENCE = 10
LR_PATIENCE         = 5
GRADIENT_CLIP       = 1.0
TRAIN_RATIO         = 0.70
VAL_RATIO           = 0.15

INPUT_FEATURES      = 13
HIDDEN_SIZE         = 128
NUM_LAYERS          = 2
DROPOUT             = 0.2
SEED                = 42

LINK_IDS = ["fiber-primary", "broadband-secondary", "satellite-backup", "5g-mobile"]


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# Feature Engineering

def engineer_features(telemetry_df):
    """Build the 13-feature matrix from raw 5-metric telemetry."""
    latency        = telemetry_df["latency_ms"].values.astype(np.float32)
    jitter         = telemetry_df["jitter_ms"].values.astype(np.float32)
    packet_loss    = telemetry_df["packet_loss_pct"].values.astype(np.float32)
    bandwidth_util = telemetry_df["bandwidth_util_pct"].values.astype(np.float32)
    rtt            = telemetry_df["rtt_ms"].values.astype(np.float32)

    mean_latency_30s = pd.Series(latency).rolling(30, min_periods=1).mean().values.astype(np.float32)
    std_latency_30s  = pd.Series(latency).rolling(30, min_periods=1).std().fillna(0).values.astype(np.float32)
    mean_jitter_30s  = pd.Series(jitter).rolling(30, min_periods=1).mean().values.astype(np.float32)

    ema_latency     = pd.Series(latency).ewm(alpha=0.3, adjust=False).mean().values.astype(np.float32)
    ema_packet_loss = pd.Series(packet_loss).ewm(alpha=0.3, adjust=False).mean().values.astype(np.float32)

    d_latency     = np.diff(latency,     prepend=latency[0]).astype(np.float32)
    d_jitter      = np.diff(jitter,      prepend=jitter[0]).astype(np.float32)
    d_packet_loss = np.diff(packet_loss, prepend=packet_loss[0]).astype(np.float32)

    return np.column_stack([
        latency, jitter, packet_loss, bandwidth_util, rtt,
        mean_latency_30s, std_latency_30s, mean_jitter_30s,
        ema_latency, ema_packet_loss,
        d_latency, d_jitter, d_packet_loss,
    ])


# Dataset

class TelemetryDataset(Dataset):
    """Sliding window dataset: WINDOW_SIZE input -> HORIZON target (lat, jit, loss)."""

    def __init__(self, features, raw_df, stride=1):
        self.features = features
        self.raw_latency     = raw_df["latency_ms"].values.astype(np.float32)
        self.raw_jitter      = raw_df["jitter_ms"].values.astype(np.float32)
        self.raw_packet_loss = raw_df["packet_loss_pct"].values.astype(np.float32)
        self.stride = stride
        self.n_samples = max(0, (len(features) - WINDOW_SIZE - HORIZON) // stride)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        start = idx * self.stride
        end = start + WINDOW_SIZE
        target_end = end + HORIZON

        x = torch.tensor(self.features[start:end], dtype=torch.float32)
        target = torch.stack([
            torch.tensor(self.raw_latency[end:target_end],     dtype=torch.float32),
            torch.tensor(self.raw_jitter[end:target_end],      dtype=torch.float32),
            torch.tensor(self.raw_packet_loss[end:target_end], dtype=torch.float32),
        ], dim=-1)
        return x, target


# Pipeline stages

def load_per_link_data():
    print("\n[1/5] Loading real-world calibrated data...")
    per_link_features = []
    per_link_dfs = []

    for link_id in LINK_IDS:
        path = DATA_DIR / f"{link_id}.parquet"
        if not path.exists():
            print(f"  [ERROR] Missing data: {path}")
            print("  Run 'python ml/scripts/fetch_real_data.py' first!")
            return None

        link_df = pd.read_parquet(path)
        print(f"  {link_id}: {len(link_df):,} points loaded")
        per_link_features.append(engineer_features(link_df))
        per_link_dfs.append(link_df)

    combined_features = np.concatenate(per_link_features, axis=0)
    print(
        f"\n  Combined: {sum(len(d) for d in per_link_dfs):,} points, "
        f"{combined_features.shape[1]} features"
    )
    return per_link_features, per_link_dfs


def compute_normalization(per_link_features):
    print("\n[2/5] Normalizing features...")
    combined = np.concatenate(per_link_features, axis=0)
    feat_means = combined.mean(axis=0)
    feat_stds = combined.std(axis=0)
    feat_stds[feat_stds < 1e-8] = 1.0

    normalized = (combined - feat_means) / feat_stds
    print(f"  Feature means: {np.round(feat_means, 2)}")
    print(f"  Feature stds:  {np.round(feat_stds, 2)}")
    return feat_means, feat_stds, normalized


def build_split_datasets(per_link_features, per_link_dfs, normalized_combined):
    print("\n[3/5] Creating train/val/test datasets...")
    train_chunks, val_chunks, test_chunks = [], [], []
    offset = 0

    for link_df in per_link_dfs:
        n_rows = len(link_df)
        link_features = normalized_combined[offset:offset + n_rows]
        link_df = link_df.reset_index(drop=True)

        train_end = int(n_rows * TRAIN_RATIO)
        val_end = int(n_rows * (TRAIN_RATIO + VAL_RATIO))

        train_chunks.append(TelemetryDataset(
            link_features[:train_end], link_df.iloc[:train_end], stride=15,
        ))
        val_chunks.append(TelemetryDataset(
            link_features[train_end:val_end], link_df.iloc[train_end:val_end], stride=30,
        ))
        test_chunks.append(TelemetryDataset(
            link_features[val_end:], link_df.iloc[val_end:].reset_index(drop=True), stride=30,
        ))
        offset += n_rows

    train_ds = ConcatDataset(train_chunks)
    val_ds = ConcatDataset(val_chunks)
    test_ds = ConcatDataset(test_chunks)

    print(f"  Train: {len(train_ds):,} windows")
    print(f"  Val:   {len(val_ds):,} windows")
    print(f"  Test:  {len(test_ds):,} windows")
    return train_ds, val_ds, test_ds


def build_loaders(train_ds, val_ds, test_ds):
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=0, pin_memory=False, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=0, pin_memory=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False,
                             num_workers=0, pin_memory=False)
    return train_loader, val_loader, test_loader


def build_model_and_optim(device):
    print("\n[4/5] Initializing model...")
    model = PathWiseLSTM(
        input_size=INPUT_FEATURES,
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT,
        horizon=HORIZON,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Architecture: PathWiseLSTM ({NUM_LAYERS}-layer, {HIDDEN_SIZE} hidden, attention)")
    print(f"  Parameters: {total_params:,} total, {trainable_params:,} trainable")

    criterion = PathWiseLoss(
        weights={"latency": 1.0, "jitter": 1.0, "packet_loss": 2.0},
        underestimate_penalty=2.0,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=LR_PATIENCE,
    )
    return model, criterion, optimizer, scheduler


def train_one_epoch(model, loader, criterion, optimizer, device, grad_clip):
    model.train()
    total_loss = 0.0
    n_batches = 0

    for x_batch, target_batch in loader:
        x_batch = x_batch.to(device)
        target_batch = target_batch.to(device)

        optimizer.zero_grad()
        preds, _confidence = model(x_batch)
        loss = criterion(preds, target_batch)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


def validate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    n_batches = 0
    pred_buf  = {"latency": [], "jitter": [], "packet_loss": []}
    target_buf = {"latency": [], "jitter": [], "packet_loss": []}

    with torch.no_grad():
        for x_batch, target_batch in loader:
            x_batch = x_batch.to(device)
            target_batch = target_batch.to(device)

            preds, _confidence = model(x_batch)
            loss = criterion(preds, target_batch)
            total_loss += loss.item()
            n_batches += 1

            for key in pred_buf:
                pred_buf[key].append(preds[key].cpu())
            target_buf["latency"].append(target_batch[:, :, 0].cpu())
            target_buf["jitter"].append(target_batch[:, :, 1].cpu())
            target_buf["packet_loss"].append(target_batch[:, :, 2].cpu())

    avg_loss = total_loss / max(n_batches, 1)

    metrics = {}
    for key in pred_buf:
        predicted = torch.cat(pred_buf[key])
        actual = torch.cat(target_buf[key])
        metrics[f"{key}_mae"] = (predicted - actual).abs().mean().item()
        metrics[f"{key}_rmse"] = ((predicted - actual) ** 2).mean().sqrt().item()
    return avg_loss, metrics


def save_best_checkpoint(model, optimizer, epoch, val_loss, val_metrics, feat_means, feat_stds):
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_loss": val_loss,
        "val_metrics": val_metrics,
        "means": feat_means.tolist(),
        "stds": feat_stds.tolist(),
        "hyperparameters": {
            "input_size": INPUT_FEATURES,
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "dropout": DROPOUT,
            "horizon": HORIZON,
            "window_size": WINDOW_SIZE,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
        },
        "training_data": "real_world_calibrated",
        "link_types": LINK_IDS,
    }
    torch.save(checkpoint, CHECKPOINT_DIR / "best_model.pt")


def run_training_loop(model, train_loader, val_loader, criterion, optimizer, scheduler,
                      device, feat_means, feat_stds):
    """Run training, save best checkpoint inline. Returns (best_val_loss, best_epoch, training_log)."""
    print(f"\n[5/5] Training for up to {MAX_EPOCHS} epochs...")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Learning rate: {LEARNING_RATE}")
    print(f"  Early stopping patience: {EARLY_STOP_PATIENCE}")
    print(f"  Gradient clip: {GRADIENT_CLIP}")
    print("-" * 70)

    best_val_loss = float("inf")
    best_epoch = 0
    epochs_no_improve = 0
    training_log = []

    for epoch in range(1, MAX_EPOCHS + 1):
        epoch_start = time.time()

        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device, GRADIENT_CLIP)
        val_loss, val_metrics = validate(model, val_loader, criterion, device)
        scheduler.step(val_loss)

        elapsed = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        log_entry = {
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "lr": current_lr,
            "elapsed": elapsed,
            **val_metrics,
        }
        training_log.append(log_entry)

        print(
            f"  Epoch {epoch:3d}/{MAX_EPOCHS} | "
            f"train={train_loss:.4f} val={val_loss:.4f} | "
            f"MAE lat={val_metrics['latency_mae']:.2f}ms "
            f"jit={val_metrics['jitter_mae']:.2f}ms "
            f"loss={val_metrics['packet_loss_mae']:.4f}% | "
            f"lr={current_lr:.1e} | {elapsed:.1f}s"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            epochs_no_improve = 0
            save_best_checkpoint(model, optimizer, epoch, val_loss, val_metrics, feat_means, feat_stds)
            print(f"    * New best model saved (val_loss={val_loss:.4f})")
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= EARLY_STOP_PATIENCE:
            print(
                f"\n  Early stopping at epoch {epoch} "
                f"(no improvement for {EARLY_STOP_PATIENCE} epochs)"
            )
            break

    return best_val_loss, best_epoch, training_log


def evaluate_test_set(model, test_loader, criterion, device):
    print("\n" + "=" * 70)
    print("Final Evaluation on Test Set")
    print("=" * 70)

    best_ckpt = torch.load(CHECKPOINT_DIR / "best_model.pt", map_location=device, weights_only=False)
    model.load_state_dict(best_ckpt["model_state_dict"])
    print(f"  Loaded best model from epoch {best_ckpt['epoch']}")

    test_loss, test_metrics = validate(model, test_loader, criterion, device)
    print(f"\n  Test Loss: {test_loss:.4f}")
    print(f"  Latency  - MAE: {test_metrics['latency_mae']:.2f}ms,  RMSE: {test_metrics['latency_rmse']:.2f}ms")
    print(f"  Jitter   - MAE: {test_metrics['jitter_mae']:.2f}ms,  RMSE: {test_metrics['jitter_rmse']:.2f}ms")
    print(f"  Pkt Loss - MAE: {test_metrics['packet_loss_mae']:.4f}%, RMSE: {test_metrics['packet_loss_rmse']:.4f}%")
    return test_loss, test_metrics


def summarize_health_scores(model, test_loader, device, max_samples=5000):
    print("\n  Running health score inference check...")
    model.eval()
    health_scores = []

    with torch.no_grad():
        for x_batch, _target in test_loader:
            x_batch = x_batch.to(device)
            preds, confidence_batch = model(x_batch)
            for i in range(len(x_batch)):
                latency_forecast     = preds["latency"][i].cpu().numpy()
                jitter_forecast      = preds["jitter"][i].cpu().numpy()
                packet_loss_forecast = preds["packet_loss"][i].cpu().numpy()
                confidence = confidence_batch[i].item()

                latency_score     = max(0, min(100, 100 * (1 - (latency_forecast.mean()     - 30)  / 170)))
                jitter_score      = max(0, min(100, 100 * (1 - (jitter_forecast.mean()      - 5)   / 45)))
                packet_loss_score = max(0, min(100, 100 * (1 - (packet_loss_forecast.mean() - 0.1) / 4.9)))

                raw = 0.4 * latency_score + 0.3 * jitter_score + 0.3 * packet_loss_score
                health_scores.append(raw * (0.5 + 0.5 * confidence))

            if len(health_scores) > max_samples:
                break

    health_score_array = np.array(health_scores)
    n = len(health_score_array)
    critical = (health_score_array < 30).mean() * 100
    warning  = ((health_score_array >= 30) & (health_score_array < 70)).mean() * 100
    healthy  = (health_score_array >= 70).mean() * 100

    print(f"  Health Score Distribution (n={n}):")
    print(f"    Mean: {health_score_array.mean():.1f}, Std: {health_score_array.std():.1f}")
    print(f"    Min:  {health_score_array.min():.1f}, Max: {health_score_array.max():.1f}")
    print(f"    <30 (critical): {(health_score_array < 30).sum()} ({critical:.1f}%)")
    print(f"    30-70 (warning): {((health_score_array >= 30) & (health_score_array < 70)).sum()} ({warning:.1f}%)")
    print(f"    >=70 (healthy): {(health_score_array >= 70).sum()} ({healthy:.1f}%)")
    return health_score_array


def write_training_log(training_log, best_epoch, best_val_loss, test_loss, test_metrics, health_score_array):
    log_path = CHECKPOINT_DIR / "training_log.json"
    payload = {
        "training_log": training_log,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "health_score_stats": {
            "mean": float(health_score_array.mean()),
            "std":  float(health_score_array.std()),
            "critical_pct": float((health_score_array < 30).mean() * 100),
            "warning_pct":  float(((health_score_array >= 30) & (health_score_array < 70)).mean() * 100),
            "healthy_pct":  float((health_score_array >= 70).mean() * 100),
        },
    }
    with open(log_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Training log saved: {log_path}")
    return log_path


def main():
    print("=" * 70)
    print("PathWise AI - LSTM Training Pipeline (Real-World Data)")
    print("=" * 70)

    set_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"PyTorch: {torch.__version__}")
    print(f"Seed: {SEED}")

    loaded = load_per_link_data()
    if loaded is None:
        return
    per_link_features, per_link_dfs = loaded

    feat_means, feat_stds, normalized_combined = compute_normalization(per_link_features)

    train_ds, val_ds, test_ds = build_split_datasets(
        per_link_features, per_link_dfs, normalized_combined,
    )
    train_loader, val_loader, test_loader = build_loaders(train_ds, val_ds, test_ds)

    model, criterion, optimizer, scheduler = build_model_and_optim(device)

    best_val_loss, best_epoch, training_log = run_training_loop(
        model, train_loader, val_loader, criterion, optimizer, scheduler,
        device, feat_means, feat_stds,
    )

    test_loss, test_metrics = evaluate_test_set(model, test_loader, criterion, device)
    health_score_array = summarize_health_scores(model, test_loader, device)
    write_training_log(
        training_log, best_epoch, best_val_loss, test_loss, test_metrics, health_score_array,
    )

    print("\n" + "=" * 70)
    print(f"Training complete! Best model at epoch {best_epoch}:")
    print(f"  Checkpoint: {CHECKPOINT_DIR / 'best_model.pt'}")
    print(f"  Val Loss:   {best_val_loss:.4f}")
    print(f"  Test Loss:  {test_loss:.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
