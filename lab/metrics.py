"""
Metrics — evaluation functions for genomics ML models.
"""

import logging
import math

log = logging.getLogger("genoresearch.metrics")


def compute_metrics(predictions: list, targets: list) -> dict:
    """
    Compute classification/regression metrics.

    Returns dict with accuracy, precision, recall, f1, loss.
    """
    if not predictions or not targets:
        return {"error": "Empty predictions or targets"}

    if len(predictions) != len(targets):
        return {"error": f"Length mismatch: {len(predictions)} vs {len(targets)}"}

    # Detect task type
    if all(isinstance(t, (int, bool)) for t in targets):
        return _classification_metrics(predictions, targets)
    else:
        return _regression_metrics(predictions, targets)


def _classification_metrics(preds: list, targets: list) -> dict:
    """Binary/multiclass classification metrics."""
    correct = sum(1 for p, t in zip(preds, targets) if p == t)
    total = len(targets)
    accuracy = correct / total

    # For binary classification
    unique_labels = sorted(set(targets))
    if len(unique_labels) == 2:
        pos = unique_labels[1]
        tp = sum(1 for p, t in zip(preds, targets) if p == pos and t == pos)
        fp = sum(1 for p, t in zip(preds, targets) if p == pos and t != pos)
        fn = sum(1 for p, t in zip(preds, targets) if p != pos and t == pos)

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)

        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "total": total,
        }

    return {"accuracy": round(accuracy, 4), "total": total}


def _regression_metrics(preds: list, targets: list) -> dict:
    """Regression metrics — MSE, MAE, R-squared."""
    n = len(targets)
    errors = [p - t for p, t in zip(preds, targets)]
    mse = sum(e ** 2 for e in errors) / n
    mae = sum(abs(e) for e in errors) / n
    rmse = math.sqrt(mse)

    mean_t = sum(targets) / n
    ss_res = sum((p - t) ** 2 for p, t in zip(preds, targets))
    ss_tot = sum((t - mean_t) ** 2 for t in targets)
    r2 = 1 - (ss_res / max(ss_tot, 1e-8))

    return {
        "mse": round(mse, 6),
        "rmse": round(rmse, 6),
        "mae": round(mae, 6),
        "r2": round(r2, 4),
        "total": n,
    }


def bits_per_byte(loss: float) -> float:
    """Convert cross-entropy loss (nats) to bits per byte (karpathy metric)."""
    return loss / math.log(2)
