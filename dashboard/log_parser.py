"""
Log parser — cached parsing of research.log for dashboard metrics.

Reads two log files when available:
  - RESEARCH_LOG: live log written by the agent (parsed on every mtime change)
  - RESEARCH_LOG_ARCHIVE: older archive kept on disk for historical analysis
    (parsed once and cached; only re-parsed if its mtime changes)

The archive is typically large (100+ MB) and changes rarely, so caching its
parse result is critical. If the archive file is missing, the dashboard
silently falls back to the live log only.
"""

import os
import re
import threading

from config import RESEARCH_LOG, RESEARCH_LOG_ARCHIVE

# ---------------------------------------------------------------------------
# Caches — keyed by file path
# ---------------------------------------------------------------------------

_log_cache_lock = threading.Lock()
_log_cache = {
    "mtime": 0,
    "size": 0,
    "lines": [],
    "cycles": [],
    "errors": [],
    "warnings": [],
    "tool_calls_from_log": {},
    "loaded": False,  # distinguishes "not yet parsed" from "parsed and empty"
}

_archive_cache_lock = threading.Lock()
_archive_cache = {
    "mtime": 0,
    "size": 0,
    "lines": [],
    "cycles": [],
    "errors": [],
    "warnings": [],
    "tool_calls_from_log": {},
    "loaded": False,  # distinguishes "not yet parsed" from "parsed and empty"
}


# ---------------------------------------------------------------------------
# Generic per-file parser
# ---------------------------------------------------------------------------

def _parse_log(path):
    """Parse one log file and return (cycles, errors, warnings, tool_counts, lines)."""
    cycles = []
    errors = []
    warnings = []
    tool_counts = {}
    cycle_num = 0
    cycle_tools = []
    cycle_errors = 0
    cycle_start = None

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (FileNotFoundError, OSError):
        return [], [], [], {}, []

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

    return cycles, errors, warnings, tool_counts, lines


# ---------------------------------------------------------------------------
# Cache refreshers — one per file, mtime-gated
# ---------------------------------------------------------------------------

def _refresh_cache_for(path, cache, lock):
    """Parse `path` and store into `cache` only when the file has changed."""
    try:
        stat = os.stat(path)
    except OSError:
        # File missing — mark as loaded-but-empty so we don't keep stat'ing it
        with lock:
            if not cache["loaded"]:
                cache.update({
                    "mtime": 0, "size": 0, "lines": [],
                    "cycles": [], "errors": [], "warnings": [],
                    "tool_calls_from_log": {}, "loaded": True,
                })
        return

    with lock:
        if (cache["loaded"] and
                stat.st_mtime == cache["mtime"] and
                stat.st_size == cache["size"]):
            return  # no change

        cycles, errors, warnings, tool_counts, lines = _parse_log(path)
        cache.update({
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "lines": lines,
            "cycles": cycles,
            "errors": errors,
            "warnings": warnings,
            "tool_calls_from_log": tool_counts,
            "loaded": True,
        })


def _refresh_log_cache():
    """Re-parse live log only when the file has been modified."""
    _refresh_cache_for(RESEARCH_LOG, _log_cache, _log_cache_lock)


def _refresh_archive_cache():
    """Re-parse archive log only when the file has been modified."""
    _refresh_cache_for(RESEARCH_LOG_ARCHIVE, _archive_cache, _archive_cache_lock)


# ---------------------------------------------------------------------------
# Merged getters — combine live + archive
# ---------------------------------------------------------------------------

def _merge_counts(a, b):
    """Sum two {key: count} dicts."""
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return out


def _combined_lines():
    """Return all lines from both logs (archive first, then live)."""
    _refresh_archive_cache()
    _refresh_log_cache()
    with _archive_cache_lock, _log_cache_lock:
        return list(_archive_cache["lines"]) + list(_log_cache["lines"])


def _combined_cycles():
    _refresh_archive_cache()
    _refresh_log_cache()
    with _archive_cache_lock, _log_cache_lock:
        return list(_archive_cache["cycles"]) + list(_log_cache["cycles"])


def _combined_errors():
    _refresh_archive_cache()
    _refresh_log_cache()
    with _archive_cache_lock, _log_cache_lock:
        return list(_archive_cache["errors"]) + list(_log_cache["errors"])


def _combined_warnings():
    _refresh_archive_cache()
    _refresh_log_cache()
    with _archive_cache_lock, _log_cache_lock:
        return list(_archive_cache["warnings"]) + list(_log_cache["warnings"])


def _combined_tool_counts():
    _refresh_archive_cache()
    _refresh_log_cache()
    with _archive_cache_lock, _log_cache_lock:
        return _merge_counts(
            _archive_cache["tool_calls_from_log"],
            _log_cache["tool_calls_from_log"],
        )


# ---------------------------------------------------------------------------
# Public API — names kept stable so callers don't need to change
# ---------------------------------------------------------------------------

def _get_cached_cycles():
    return _combined_cycles()


def _get_cached_errors():
    return _combined_errors()


def _get_cached_warnings():
    return _combined_warnings()


def _get_log_tool_counts():
    return _combined_tool_counts()
