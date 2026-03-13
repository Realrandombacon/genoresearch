"""
Lab trainer — autonomous ML experimentation loop (karpathy autoresearch style).
Modifies config → trains → evaluates → keeps/discards → repeats.
"""

import os
import json
import time
import shutil
import logging
import subprocess
import datetime

from config import LAB_RUNS_DIR, LAB_CHECKPOINTS_DIR, BASE_DIR

log = logging.getLogger("genoresearch.lab")


class LabTrainer:
    """
    Manages ML experiments for genomics models.
    Each experiment:
      1. Gets a config (model type, hyperparams)
      2. Runs training for a fixed time budget
      3. Evaluates on validation set
      4. Keeps or discards based on metric improvement
    """

    TRAIN_SCRIPT = os.path.join(BASE_DIR, "lab", "train_genomics.py")
    TIME_BUDGET_SECONDS = 300  # 5 min per experiment (like karpathy)

    def __init__(self):
        self.history = self._load_history()
        self.best_metric = self.history.get("best_metric", float("inf"))
        self.experiment_count = self.history.get("experiment_count", 0)

    def run_experiment(self, config: dict) -> dict:
        """
        Run a single training experiment.

        Args:
            config: Dict with model/training hyperparams

        Returns:
            Dict with results {metric, improved, config, duration}
        """
        self.experiment_count += 1
        exp_id = f"exp_{self.experiment_count:04d}"
        exp_dir = os.path.join(LAB_RUNS_DIR, exp_id)
        os.makedirs(exp_dir, exist_ok=True)

        # Save config
        config_path = os.path.join(exp_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        log.info("Starting experiment %s with config: %s", exp_id, config)
        start = time.time()

        # Run training
        result = self._run_training(config, exp_dir)
        duration = time.time() - start

        # Evaluate
        metric = result.get("val_loss", float("inf"))
        improved = metric < self.best_metric

        if improved:
            log.info("Experiment %s IMPROVED: %.4f -> %.4f", exp_id, self.best_metric, metric)
            self.best_metric = metric
            self._save_checkpoint(exp_dir)
        else:
            log.info("Experiment %s: %.4f (best: %.4f) — discarded",
                     exp_id, metric, self.best_metric)

        # Record result
        entry = {
            "exp_id": exp_id,
            "config": config,
            "metric": metric,
            "improved": improved,
            "duration": round(duration, 1),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.history.setdefault("experiments", []).append(entry)
        self.history["best_metric"] = self.best_metric
        self.history["experiment_count"] = self.experiment_count
        self._save_history()

        return entry

    def get_status(self) -> str:
        """Return current lab status."""
        lines = [
            f"Lab Status:",
            f"  Experiments run: {self.experiment_count}",
            f"  Best metric: {self.best_metric:.4f}" if self.best_metric < float("inf") else "  Best metric: N/A",
        ]
        recent = self.history.get("experiments", [])[-5:]
        if recent:
            lines.append("  Recent experiments:")
            for e in recent:
                marker = "+" if e.get("improved") else "-"
                lines.append(f"    [{marker}] {e['exp_id']}: {e.get('metric', '?'):.4f} ({e.get('duration', '?')}s)")
        return "\n".join(lines)

    def _run_training(self, config: dict, exp_dir: str) -> dict:
        """Execute training script as subprocess with timeout."""
        config_path = os.path.join(exp_dir, "config.json")
        result_path = os.path.join(exp_dir, "result.json")

        cmd = [
            "python", self.TRAIN_SCRIPT,
            "--config", config_path,
            "--output", result_path,
            "--time-budget", str(self.TIME_BUDGET_SECONDS),
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.TIME_BUDGET_SECONDS + 60,
                cwd=BASE_DIR,
            )

            # Save stdout/stderr
            with open(os.path.join(exp_dir, "stdout.log"), "w") as f:
                f.write(proc.stdout)
            if proc.stderr:
                with open(os.path.join(exp_dir, "stderr.log"), "w") as f:
                    f.write(proc.stderr)

            # Read result
            if os.path.exists(result_path):
                with open(result_path) as f:
                    return json.load(f)

            return {"val_loss": float("inf"), "error": "No result file produced"}

        except subprocess.TimeoutExpired:
            log.warning("Training timed out for %s", exp_dir)
            return {"val_loss": float("inf"), "error": "timeout"}
        except Exception as e:
            log.error("Training failed: %s", e)
            return {"val_loss": float("inf"), "error": str(e)}

    def _save_checkpoint(self, exp_dir: str):
        """Copy best experiment to checkpoints."""
        best_dir = os.path.join(LAB_CHECKPOINTS_DIR, "best")
        if os.path.exists(best_dir):
            shutil.rmtree(best_dir)
        shutil.copytree(exp_dir, best_dir)
        log.info("Best checkpoint saved to %s", best_dir)

    def _load_history(self) -> dict:
        """Load experiment history."""
        path = os.path.join(LAB_RUNS_DIR, "history.json")
        try:
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"experiments": [], "best_metric": float("inf"), "experiment_count": 0}

    def _save_history(self):
        """Persist experiment history."""
        path = os.path.join(LAB_RUNS_DIR, "history.json")
        with open(path, "w") as f:
            json.dump(self.history, f, indent=2)
