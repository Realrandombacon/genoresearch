"""
Dashboard — writes status JSON for external monitoring.
"""

import json
import os
import datetime
import logging

from config import DASHBOARD_STATUS, BASE_DIR

log = logging.getLogger("genoresearch.dashboard")


def _read_gene_queue_current():
    """Read the current gene from gene_queue.json, if any."""
    queue_file = os.path.join(BASE_DIR, "gene_queue.json")
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            gq = json.load(f)
        if gq.get("in_progress"):
            return gq["in_progress"].get("gene")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return None


def write_status(running: bool = True, cycle: int = 0, phase: str = "idle",
                 current_tool: str = None, last_thought: str = "",
                 total_cycles: int = 0, errors_this_session: int = 0,
                 tools_this_session: int = 0):
    """Write current agent status to a JSON file for dashboard consumption."""
    current_gene = _read_gene_queue_current()

    status = {
        "running": running,
        "cycle": cycle,
        "phase": phase,
        "current_tool": current_tool,
        "last_thought": last_thought[:200] if last_thought else "",
        "timestamp": datetime.datetime.now().isoformat(),
        "total_cycles": total_cycles,
        "errors_this_session": errors_this_session,
        "tools_this_session": tools_this_session,
        "current_gene": current_gene,
    }
    try:
        with open(DASHBOARD_STATUS, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
    except (OSError, TypeError) as e:
        log.warning("Failed to write dashboard status: %s", e)


def read_status() -> dict:
    """Read current status from the JSON file."""
    try:
        with open(DASHBOARD_STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"running": False, "cycle": 0, "phase": "unknown"}
