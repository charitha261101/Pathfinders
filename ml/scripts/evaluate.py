# ml/scripts/evaluate.py

import sys
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.prediction_engine_pkg.model.lstm_network import PathWiseLSTM
from services.prediction_engine_pkg.model.feature_engineering import FeatureEngineer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# Health-score config
HEALTH_CFG = {
    "latency":     {"good": 30.0,  "bad": 200.0, "weight": 0.4},
    "jitter":      {"good": 5.0,   "bad": 50.0,  "weight": 0.3},
    "packet_loss": {"good": 0.1,   "bad": 5.0,   "weight": 0.3},
}
BROWNOUT_THRESHOLD = 50.0
METRIC_KEYS = ["latency", "jitter", "packet_loss"]


# Health-score helpers (single source of truth)

def _scale_metric(value, good, bad):
    """Map a metric value to a 0-100 score where good->100 and bad->0."""
    return torch.clamp(100.0 * (1.0 - (value - good) / (bad - good)), 0.0, 100.0)


def _composite_health(latency_mean, jitter_mean, packet_loss_mean):
    """Weighted composite health from per-metric horizon means."""
    lat_score = _scale_metric(latency_mean,
                              HEALTH_CFG["latency"]["good"],
                              HEALTH_CFG["latency"]["bad"])
    jit_score = _scale_metric(jitter_mean,
                              HEALTH_CFG["jitter"]["good"],
                              HEALTH_CFG["jitter"]["bad"])
    pkt_score = _scale_metric(packet_loss_mean,
                              HEALTH_CFG["packet_loss"]["good"],
                              HEALTH_CFG["packet_loss"]["bad"])
    return (
        HEALTH_CFG["latency"]["weight"]     * lat_score +
        HEALTH_CFG["jitter"]["weight"]      * jit_score +
        HEALTH_CFG["packet_loss"]["weight"] * pkt_score
    )


def health_from_predictions(preds):
    """Compute health score from prediction tensors {metric: (B, H)}."""
    return _composite_health(
        latency_mean=preds["latency"].mean(dim=1),
        jitter_mean=preds["jitter"].mean(dim=1),
        packet_loss_mean=preds["packet_loss"].mean(dim=1),
    )


def health_from_targets(targets):
    """Compute health score from target tensor (B, H, 3) ordered (lat, jit, loss)."""
    return _composite_health(
        latency_mean=targets[:, :, 0].mean(dim=1),
        jitter_mean=targets[:, :, 1].mean(dim=1),
        packet_loss_mean=targets[:, :, 2].mean(dim=1),
    )


# Data prep

def load_test_dataset(data_dir, smoke_test, val_fraction=0.2):
    """Load parquet data, engineer features, return the held-out test slice."""
    data_path = Path(data_dir)
    frames = [pd.read_parquet(p) for p in sorted(data_path.glob("*.parquet"))]
    if not frames:
        raise FileNotFoundError(f"No data found in {data_dir}")

    telemetry_df = pd.concat(frames, ignore_index=True)
    if smoke_test:
        telemetry_df = telemetry_df.groupby("link_id").head(5000).reset_index(drop=True)

    feature_engineer = FeatureEngineer()
    window_chunks, target_chunks = [], []
    for link_id, link_frame in telemetry_df.groupby("link_id"):
        link_frame = feature_engineer.compute_features(link_frame)
        windows, targets = feature_engineer.create_sequences(link_frame)
        if len(windows) == 0:
            continue
        windows = feature_engineer.normalize(windows, link_id, fit=True)
        window_chunks.append(windows)
        target_chunks.append(targets)

    windows = np.concatenate(window_chunks)
    targets = np.concatenate(target_chunks)

    split_idx = int(len(windows) * (1.0 - val_fraction))
    return windows[split_idx:], targets[split_idx:]


# Evaluation

def evaluate_model(model, test_loader, device):
    """
    Evaluation metrics for PVD compliance:
      1. Per-metric MSE / MAE (latency, jitter, packet_loss)
      2. Brownout recall    (caught actual brownouts)
      3. False-positive rate (false brownout alerts)
    """
    metric_buckets = {
        "mse_latency": [], "mse_jitter": [], "mse_packet_loss": [],
        "mae_latency": [], "mae_jitter": [], "mae_packet_loss": [],
        "brownout_recall": [], "false_positive_rate": [],
    }

    model.eval()
    with torch.no_grad():
        for window_batch, target_batch in test_loader:
            window_batch = window_batch.to(device)
            target_batch = target_batch.to(device)

            preds, _confidence = model(window_batch)

            for idx, metric in enumerate(METRIC_KEYS):
                error = preds[metric] - target_batch[:, :, idx]
                metric_buckets[f"mse_{metric}"].append((error ** 2).mean().item())
                metric_buckets[f"mae_{metric}"].append(error.abs().mean().item())

            actual_health = health_from_targets(target_batch)
            predicted_health = health_from_predictions(preds)

            actual_brownouts = actual_health < BROWNOUT_THRESHOLD
            predicted_brownouts = predicted_health < BROWNOUT_THRESHOLD

            if actual_brownouts.any():
                recall = (predicted_brownouts & actual_brownouts).sum() / actual_brownouts.sum()
                metric_buckets["brownout_recall"].append(recall.item())

            n_non_brownout = (~actual_brownouts).sum()
            if n_non_brownout > 0:
                fpr = (predicted_brownouts & ~actual_brownouts).sum() / n_non_brownout
                metric_buckets["false_positive_rate"].append(fpr.item())

    return {key: float(np.mean(values)) if values else 0.0 for key, values in metric_buckets.items()}


# Entrypoint

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate PathWise LSTM model")
    parser.add_argument("--data-dir", type=str, default="ml/data/synthetic")
    parser.add_argument("--checkpoint", type=str, default="ml/checkpoints/best_model.pt")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    test_windows, test_targets = load_test_dataset(
        args.data_dir, smoke_test=args.smoke_test, val_fraction=args.val_fraction,
    )
    test_dataset = TensorDataset(torch.tensor(test_windows), torch.tensor(test_targets))
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

    model = PathWiseLSTM().to(device)
    checkpoint_path = Path(args.checkpoint)
    if checkpoint_path.exists():
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        logger.info(f"Loaded model from {checkpoint_path}")
    else:
        logger.warning(f"No checkpoint found at {checkpoint_path}, using random weights")

    results = evaluate_model(model, test_loader, device)

    logger.info("=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)
    for key, value in results.items():
        logger.info(f"  {key}: {value:.6f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
