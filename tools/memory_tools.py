"""
Memory tools — wrappers that load memory and delegate to agent.memory functions.
These are registered as tools so the LLM can call them directly.

All tools use *args/**kwargs to handle Qwen's creative argument naming
(query=, text=, question=, search=, etc.)
"""

from agent.memory import (
    load_memory, save_memory,
    query_memory as _query_memory,
    my_stats as _my_stats,
    add_note, add_explored, mark_exhausted, dismiss_lead,
)


def _extract_str(args, kwargs, *valid_keys, default=""):
    """Extract a string value from args/kwargs regardless of what key Qwen uses."""
    # Try positional first
    if args:
        return str(args[0])
    # Try all valid keyword names Qwen might use
    for key in valid_keys:
        if key in kwargs:
            return str(kwargs[key])
    # Try ANY string kwarg as last resort
    for v in kwargs.values():
        if isinstance(v, str) and v.strip():
            return v
    return default


def query_memory(*args, **kwargs) -> str:
    """
    Search memory for findings, notes, and explored targets matching a question.

    Args:
        question: Keywords to search for in memory
    """
    question = _extract_str(args, kwargs,
                            "question", "query", "text", "search", "q",
                            default="")
    if not question:
        return "Usage: query_memory('search terms')"
    memory = load_memory()
    return _query_memory(memory, question)


def my_stats() -> str:
    """Return agent statistics — tool usage, findings count, sessions."""
    memory = load_memory()
    return _my_stats(memory)


def note(*args, **kwargs) -> str:
    """
    Save a free-form research note to persistent memory.
    Use this to record observations, hypotheses, or reminders for future cycles.

    Args:
        text: The note content to save
    """
    text = _extract_str(args, kwargs,
                        "text", "note", "content", "message", "observation",
                        default="")
    if not text:
        return "Usage: note('your note text here')"
    memory = load_memory()
    add_note(memory, text)
    save_memory(memory)
    return f"Note saved: '{text[:80]}...'" if len(text) > 80 else f"Note saved: '{text}'"


def mark_explored(*args, **kwargs) -> str:
    """
    Mark a research target as explored. Tracks what genes/topics you've investigated.

    Args:
        target: The gene, protein, or topic explored (e.g. 'BRCA1', 'TP53 variants')
        status: 'partial' if more work needed, 'complete' if fully explored
    """
    target = _extract_str(args, kwargs,
                          "target", "gene", "name", "topic",
                          default="")
    if not target:
        return "Usage: mark_explored('BRCA1', status='partial')"
    # Get status from second positional or kwargs
    status = "partial"
    if len(args) >= 2:
        status = str(args[1])
    elif "status" in kwargs:
        status = str(kwargs["status"])

    memory = load_memory()
    add_explored(memory, target, status)
    save_memory(memory)
    return f"Target '{target}' marked as explored (status: {status})"


def mark_done(*args, **kwargs) -> str:
    """
    Mark a target as fully exhausted — no more useful research to do on it.

    Args:
        target: The gene or topic to mark as exhausted
    """
    target = _extract_str(args, kwargs,
                          "target", "gene", "name", "topic",
                          default="")
    if not target:
        return "Usage: mark_done('BRCA1')"
    memory = load_memory()
    mark_exhausted(memory, target)
    save_memory(memory)
    return f"Target '{target}' marked as exhausted — will not revisit"


def dismiss(*args, **kwargs) -> str:
    """
    Dismiss a research lead as unproductive or a false lead.

    Args:
        target: The gene or topic to dismiss
        reason: Why it's being dismissed
    """
    target = _extract_str(args, kwargs,
                          "target", "gene", "name", "topic",
                          default="")
    if not target:
        return "Usage: dismiss('target_name', reason='why')"
    reason = ""
    if len(args) >= 2:
        reason = str(args[1])
    elif "reason" in kwargs:
        reason = str(kwargs["reason"])

    memory = load_memory()
    dismiss_lead(memory, target, reason)
    save_memory(memory)
    return f"Lead '{target}' dismissed: {reason}" if reason else f"Lead '{target}' dismissed"


def list_unexplored() -> str:
    """List targets that have been mentioned but not yet fully explored."""
    memory = load_memory()
    explored = {t.get("target", "") for t in memory.get("explored", [])}
    exhausted = set(memory.get("exhausted", []))
    dismissed = {d.get("target", "") for d in memory.get("dismissed", [])}

    # Also auto-detect genes from tool usage patterns + auto_tracked
    auto_targets = _auto_detect_targets(memory)
    # Add auto-tracked targets from update_memory
    auto_tracked = memory.get("auto_tracked", {})
    # Only show targets seen at least 2 times (filters noise)
    for target, info in auto_tracked.items():
        if info.get("count", 0) >= 2:
            auto_targets.add(target)

    done = explored | exhausted | dismissed
    all_targets = done | auto_targets

    if not all_targets:
        return "No targets explored yet — everything is unexplored. Start by searching databases."

    lines = ["Research coverage:"]

    # Auto-detected but never explicitly marked
    auto_only = auto_targets - done
    if auto_only:
        lines.append("  Auto-detected (not yet marked):")
        for t in sorted(auto_only):
            if t:
                lines.append(f"    - {t}")

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


def _auto_detect_targets(memory: dict) -> set:
    """Auto-detect research targets from findings and notes."""
    targets = set()

    # Extract gene names from findings
    for f in memory.get("findings", []):
        title = f.get("title", "")
        desc = f.get("description", "")
        for word in (title + " " + desc).split():
            # Common gene name patterns: all-caps 2-6 chars, or with numbers
            clean = word.strip(".,;:()[]'\"")
            if (2 <= len(clean) <= 8 and clean.isupper() and
                    clean.isalnum() and not clean.isdigit()):
                targets.add(clean)

    # Extract from notes
    for n in memory.get("notes", []):
        note_text = n.get("note", "")
        for word in note_text.split():
            clean = word.strip(".,;:()[]'\"")
            if (2 <= len(clean) <= 8 and clean.isupper() and
                    clean.isalnum() and not clean.isdigit()):
                targets.add(clean)

    # Filter out common non-gene words
    noise = {"DNA", "RNA", "THE", "AND", "FOR", "NOT", "BUT", "FROM",
             "TOOL", "WITH", "THIS", "THAT", "THEN", "ALSO", "LIKE",
             "EACH", "BOTH", "INTO", "OVER", "SUCH", "VERY", "MORE",
             "MOST", "SOME", "ONLY", "HAVE", "BEEN", "WERE", "WHAT",
             "WHEN", "WHERE", "WHO", "WHY", "HOW", "ALL", "ANY",
             "ERROR", "INFO", "WARN", "NOTE", "GENE", "USE",
             "OS", "AA", "BP", "KB", "MB", "GB"}
    return targets - noise
