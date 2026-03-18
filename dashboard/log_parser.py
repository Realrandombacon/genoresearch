"""
Log parser — cached parsing of research.log for dashboard metrics.
"""

import os
import re
import threading

from config import RESEARCH_LOG

_log_cache_lock = threading.Lock()
_log_cache = {
    "mtime": 0,
    "size": 0,
    "lines": [],
    "cycles": [],
    "errors": [],
    "warnings": [],
    "tool_calls_from_log": {},
}


def _refresh_log_cache():
    """Re-parse log only when the file has been modified."""
    try:
        stat = os.stat(RESEARCH_LOG)
    except OSError:
        return

    with _log_cache_lock:
        if stat.st_mtime == _log_cache["mtime"] and stat.st_size == _log_cache["size"]:
            return  # no change

        try:
            with open(RESEARCH_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (FileNotFoundError, OSError):
            return

        cycles = []
        errors = []
        warnings = []
        tool_counts = {}
        cycle_num = 0
        cycle_tools = []
        cycle_errors = 0
        cycle_start = None

        for line in lines:
            # Cycle boundary
            if "Waiting for LLM" in line:
                if cycle_num > 0:
                    cycles.append({
                        "cycle": cycle_num,
                        "timestamp": cycle_start or "",
                        "tools": list(cycle_tools),
                        "n_tools": len(cycle_tools),
                        "errors": cycle_errors,
                    })
                cycle_num += 1
                cycle_tools = []
                cycle_errors = 0
                ts_match = re.search(r'\[([^\]]+)\]', line)
                cycle_start = ts_match.group(1) if ts_match else ""
                continue

            # Tool calls
            m2 = re.search(r'\[TOOL\]\s*(\w+)\|', line)
            if m2 and cycle_num > 0:
                tool_name = m2.group(1)
                cycle_tools.append(tool_name)
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            # Errors
            if "[ERROR]" in line:
                ts_match = re.search(r'\[([^\]]+)\]', line)
                ts = ts_match.group(1) if ts_match else ""
                errors.append({"timestamp": ts, "line": line.strip(), "cycle": cycle_num})
                cycle_errors += 1

            # Warnings
            if "[WARN]" in line:
                ts_match = re.search(r'\[([^\]]+)\]', line)
                ts = ts_match.group(1) if ts_match else ""
                warnings.append({"timestamp": ts, "line": line.strip(), "cycle": cycle_num})

        # Save last cycle
        if cycle_num > 0:
            cycles.append({
                "cycle": cycle_num,
                "timestamp": cycle_start or "",
                "tools": list(cycle_tools),
                "n_tools": len(cycle_tools),
                "errors": cycle_errors,
            })

        _log_cache["mtime"] = stat.st_mtime
        _log_cache["size"] = stat.st_size
        _log_cache["lines"] = lines
        _log_cache["cycles"] = cycles
        _log_cache["errors"] = errors
        _log_cache["warnings"] = warnings
        _log_cache["tool_calls_from_log"] = tool_counts


def _get_cached_cycles():
    """Return cached cycle data from the log."""
    _refresh_log_cache()
    with _log_cache_lock:
        return list(_log_cache["cycles"])


def _get_cached_errors():
    """Return cached error data from the log."""
    _refresh_log_cache()
    with _log_cache_lock:
        return list(_log_cache["errors"])


def _get_cached_warnings():
    """Return cached warning data from the log."""
    _refresh_log_cache()
    with _log_cache_lock:
        return list(_log_cache["warnings"])


def _get_log_tool_counts():
    """Return cached tool call counts from the log."""
    _refresh_log_cache()
    with _log_cache_lock:
        return dict(_log_cache["tool_calls_from_log"])
