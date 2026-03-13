"""
Dashboard — writes status JSON for external monitoring.
"""

import json
import datetime
import logging

from config import DASHBOARD_STATUS

log = logging.getLogger("genoresearch.dashboard")


def write_status(running: bool = True, cycle: int = 0, phase: str = "idle",
                 current_tool: str = None, last_thought: str = ""):
    """Write current agent status to a JSON file for dashboard consumption."""
    status = {
        "running": running,
        "cycle": cycle,
        "phase": phase,
        "current_tool": current_tool,
        "last_thought": last_thought[:200] if last_thought else "",
        "timestamp": datetime.datetime.now().isoformat(),
    }
    try:
        with open(DASHBOARD_STATUS, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        log.warning("Failed to write dashboard status: %s", e)


def read_status() -> dict:
    """Read current status from the JSON file."""
    try:
        with open(DASHBOARD_STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"running": False, "cycle": 0, "phase": "unknown"}
