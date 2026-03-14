"""
Lab — ML experimentation engine (karpathy autoresearch style).
Autonomous training loop: modify → train → evaluate → keep/discard.
"""

from lab.trainer import LabTrainer
from lab.metrics import compute_metrics

__all__ = ["LabTrainer", "compute_metrics"]
