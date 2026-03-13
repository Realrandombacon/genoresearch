"""
Memory tools — wrappers that load memory and delegate to agent.memory functions.
These are registered as tools so the LLM can call them directly.
"""

from agent.memory import (
    load_memory,
    query_memory as _query_memory,
    my_stats as _my_stats,
)


def query_memory(question: str) -> str:
    """
    Search memory for findings, notes, and explored targets matching a question.

    Args:
        question: Keywords to search for in memory
    """
    memory = load_memory()
    return _query_memory(memory, question)


def my_stats() -> str:
    """Return agent statistics — tool usage, findings count, sessions."""
    memory = load_memory()
    return _my_stats(memory)


def list_unexplored() -> str:
    """List targets that have been mentioned but not yet fully explored."""
    memory = load_memory()
    explored = {t.get("target", "") for t in memory.get("explored", [])}
    exhausted = set(memory.get("exhausted", []))
    dismissed = {d.get("target", "") for d in memory.get("dismissed", [])}

    done = explored | exhausted | dismissed
    if not done:
        return "No targets explored yet — everything is unexplored. Start by searching databases."

    lines = ["Research coverage:"]
    if explored - exhausted:
        lines.append("  Partially explored (can revisit):")
        for t in sorted(explored - exhausted):
            if t:
                lines.append(f"    - {t}")
    if exhausted:
        lines.append("  Fully exhausted (skip):")
        for t in sorted(exhausted):
            lines.append(f"    - {t}")
    if dismissed:
        lines.append("  Dismissed leads:")
        for d in memory.get("dismissed", []):
            lines.append(f"    - {d.get('target', '?')}: {d.get('reason', '')}")

    return "\n".join(lines)
