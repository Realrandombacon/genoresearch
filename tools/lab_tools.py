"""
Lab tools — wrappers around LabTrainer for the orchestrator to call.
"""

from lab.trainer import LabTrainer


def lab_train(config_name: str = "default") -> str:
    """
    Run an ML experiment with a named config.

    Args:
        config_name: Experiment config — 'default', 'large', 'small', or custom
    """
    configs = {
        "default": {"hidden_size": 64, "num_layers": 2, "lr": 0.001, "epochs": 20},
        "small": {"hidden_size": 32, "num_layers": 1, "lr": 0.01, "epochs": 10},
        "large": {"hidden_size": 128, "num_layers": 3, "lr": 0.0005, "epochs": 30},
    }
    config = configs.get(config_name, configs["default"])
    config["name"] = config_name

    trainer = LabTrainer()
    result = trainer.run_experiment(config)

    if result.get("error"):
        return f"[ERROR] Lab experiment failed: {result['error']}"

    return (
        f"Lab experiment '{config_name}' complete\n"
        f"  Metric: {result.get('metric', 'N/A')}\n"
        f"  Best so far: {result.get('best', 'N/A')}\n"
        f"  Kept: {result.get('kept', False)}\n"
        f"  Duration: {result.get('duration', 'N/A')}s"
    )


def lab_status() -> str:
    """Return current ML lab experiment status and history."""
    trainer = LabTrainer()
    return trainer.get_status()
