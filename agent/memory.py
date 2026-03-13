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
    """Update tool stats and auto-track explored targets from search results."""
    stats = memory.setdefault("tool_stats", {})
    stats[tool_name] = stats.get(tool_name, 0) + 1

    # Auto-track genes/targets when search or fetch tools are used
    if tool_name in ("ncbi_search", "ncbi_fetch", "uniprot_search", "uniprot_fetch",
                     "gene_info", "blast_search", "analyze_sequence", "pubmed_search"):
        _auto_track_targets(memory, tool_name, result_snippet)


def _auto_track_targets(memory: dict, tool_name: str, result: str):
    """Auto-detect and track gene/protein targets from tool results."""
    import re
    tracked = memory.setdefault("auto_tracked", {})  # {target: {tools, first_seen, last_seen}}

    targets_found = set()

    # Extract gene symbols from results (uppercase 2-8 char alphanumeric words)
    # Common gene patterns: BRCA1, TP53, EGFR, KRAS, etc.
    for word in result.split():
        clean = word.strip(".,;:()[]'\"")
        if (2 <= len(clean) <= 8 and clean[0].isalpha() and
                clean.isupper() and clean.isalnum() and not clean.isdigit()):
            targets_found.add(clean)

    # Also extract from "Gene: NAME" pattern in gene_info results
    gene_match = re.search(r"Gene:\s+(\w+)", result)
    if gene_match:
        targets_found.add(gene_match.group(1))

    # Filter noise
    noise = {"DNA", "RNA", "THE", "AND", "FOR", "NOT", "BUT", "FROM",
             "TOOL", "WITH", "THIS", "THAT", "THEN", "ALSO", "LIKE",
             "ERROR", "INFO", "WARN", "NOTE", "GENE", "USE",
             "OS", "AA", "BP", "KB", "MB", "GB", "NCBI", "BLAST",
             "FASTA", "UNIPROT", "PUBMED", "PMID", "FOUND", "SEARCH",
             "TOTAL", "RESULTS", "SAVED", "FETCHED", "HEADER",
             "LENGTH", "TYPE", "NAME", "ORGANISM", "FUNCTION"}
    targets_found -= noise

    ts = datetime.datetime.now().isoformat()
    for target in targets_found:
        if target in tracked:
            tracked[target]["tools"].append(tool_name)
            tracked[target]["last_seen"] = ts
            tracked[target]["count"] = tracked[target].get("count", 1) + 1
        else:
            tracked[target] = {
                "tools": [tool_name],
                "first_seen": ts,
                "last_seen": ts,
                "count": 1,
            }


def summarize_memory(memory: dict) -> str:
    """Build a text summary of current memory state for the LLM."""
    import os
    from config import FINDINGS_DIR, SEQUENCES_DIR

    lines = []
    findings = memory.get("findings", [])
    explored = memory.get("explored", [])
    exhausted = memory.get("exhausted", [])

    lines.append(f"Sessions: {memory.get('session_count', 0)}")
    lines.append(f"Targets explored: {len(explored)}")
    lines.append(f"Exhausted targets: {len(exhausted)}")

    # Count actual finding files on disk (more reliable than memory)
    finding_files = []
    if os.path.isdir(FINDINGS_DIR):
        finding_files = [f for f in os.listdir(FINDINGS_DIR) if f.endswith(".md")]
    lines.append(f"Saved findings on disk: {len(finding_files)}")

    # Count sequence files on disk
    seq_files = []
    if os.path.isdir(SEQUENCES_DIR):
        seq_files = [f for f in os.listdir(SEQUENCES_DIR)
                     if f.lower().endswith((".fasta", ".fa", ".fna"))]
    lines.append(f"Downloaded sequences: {len(seq_files)}")

    # Show finding titles from disk
    if finding_files:
        lines.append("\nPrevious findings (use read_finding(N) for details):")
        for fname in sorted(finding_files)[:10]:
            title = fname.replace(".md", "")
            lines.append(f"  - {title}")

    # Show sequence filenames
    if seq_files:
        lines.append(f"\nDownloaded sequences (use list_sequences() for details):")
        for fname in sorted(seq_files)[:10]:
            lines.append(f"  - {fname}")
        if len(seq_files) > 10:
            lines.append(f"  ... and {len(seq_files) - 10} more")

    if explored:
        lines.append("\nRecent targets:")
        for t in explored[-5:]:
            lines.append(f"  - {t.get('target', '?')} ({t.get('status', '?')})")

    # Notes
    notes = memory.get("notes", [])
    if notes:
        lines.append("\nResearch notes:")
        for n in notes[-5:]:
            lines.append(f"  - {n.get('note', '')[:120]}")

    # Guidance
    lines.append("\nIMPORTANT: Before starting new research, call list_findings() and "
                 "list_sequences() to review what you've already done. Avoid duplicating work.")

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
