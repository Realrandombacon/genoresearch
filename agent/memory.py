"""
Persistent memory — JSON-backed research memory.
Tracks explored targets, findings, tool usage stats, and research notes.
"""

import json
import logging
import datetime

from config import MEMORY_FILE

log = logging.getLogger("genoresearch.memory")

DEFAULT_MEMORY = {
    "explored": [],        # list of {target, timestamp, status}
    "findings": [],        # list of {title, description, evidence, timestamp}
    "notes": [],           # free-form research notes
    "tool_stats": {},      # {tool_name: call_count}
    "exhausted": [],       # targets fully explored
    "dismissed": [],       # false leads
    "session_count": 0,
}


def load_memory() -> dict:
    """Load memory from disk, or create a fresh one."""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            mem = json.load(f)
        log.info("Loaded memory with %d findings", len(mem.get("findings", [])))
        return mem
    except (FileNotFoundError, json.JSONDecodeError):
        log.info("No existing memory — starting fresh")
        return dict(DEFAULT_MEMORY)


def save_memory(memory: dict):
    """Persist memory to disk."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    log.info("Memory saved (%d findings)", len(memory.get("findings", [])))


def update_memory(memory: dict, tool_name: str, result_snippet: str):
    """Update tool stats and add context from latest tool call."""
    stats = memory.setdefault("tool_stats", {})
    stats[tool_name] = stats.get(tool_name, 0) + 1


def summarize_memory(memory: dict) -> str:
    """Build a text summary of current memory state for the LLM."""
    lines = []
    findings = memory.get("findings", [])
    explored = memory.get("explored", [])
    exhausted = memory.get("exhausted", [])

    lines.append(f"Sessions: {memory.get('session_count', 0)}")
    lines.append(f"Findings: {len(findings)}")
    lines.append(f"Targets explored: {len(explored)}")
    lines.append(f"Exhausted targets: {len(exhausted)}")

    if findings:
        lines.append("\nRecent findings:")
        for f in findings[-5:]:
            lines.append(f"  - {f.get('title', '?')}: {f.get('description', '')[:100]}")

    if explored:
        lines.append("\nRecent targets:")
        for t in explored[-5:]:
            lines.append(f"  - {t.get('target', '?')} ({t.get('status', '?')})")

    return "\n".join(lines)


def add_finding(memory: dict, title: str, description: str, evidence: str = ""):
    """Record a new finding."""
    memory.setdefault("findings", []).append({
        "title": title,
        "description": description,
        "evidence": evidence,
        "timestamp": datetime.datetime.now().isoformat(),
    })
    log.info("Finding recorded: %s", title)


def add_explored(memory: dict, target: str, status: str = "partial"):
    """Mark a target as explored."""
    memory.setdefault("explored", []).append({
        "target": target,
        "status": status,
        "timestamp": datetime.datetime.now().isoformat(),
    })


def mark_exhausted(memory: dict, target: str):
    """Mark a target as fully explored — don't revisit."""
    memory.setdefault("exhausted", []).append(target)


def dismiss_lead(memory: dict, target: str, reason: str = ""):
    """Dismiss a false lead."""
    memory.setdefault("dismissed", []).append({
        "target": target,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat(),
    })


def add_note(memory: dict, note: str):
    """Add a free-form research note."""
    memory.setdefault("notes", []).append({
        "note": note,
        "timestamp": datetime.datetime.now().isoformat(),
    })


def query_memory(memory: dict, question: str) -> str:
    """Simple keyword search across memory."""
    q = question.lower()
    results = []

    for f in memory.get("findings", []):
        if q in f.get("title", "").lower() or q in f.get("description", "").lower():
            results.append(f"Finding: {f['title']} — {f['description'][:100]}")

    for n in memory.get("notes", []):
        if q in n.get("note", "").lower():
            results.append(f"Note: {n['note'][:100]}")

    for t in memory.get("explored", []):
        if q in t.get("target", "").lower():
            results.append(f"Explored: {t['target']} ({t['status']})")

    if not results:
        return "No matching memory entries found."
    return "\n".join(results[:10])


def my_stats(memory: dict) -> str:
    """Return agent stats."""
    stats = memory.get("tool_stats", {})
    total_calls = sum(stats.values())
    lines = [
        f"Total tool calls: {total_calls}",
        f"Findings: {len(memory.get('findings', []))}",
        f"Targets explored: {len(memory.get('explored', []))}",
        f"Sessions: {memory.get('session_count', 0)}",
    ]
    if stats:
        lines.append("Tool usage:")
        for name, count in sorted(stats.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count}")
    return "\n".join(lines)
