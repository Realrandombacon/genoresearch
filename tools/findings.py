"""
Findings tool — log and retrieve research findings.
Writes to both memory and TSV file.
"""

import os
import csv
import datetime
import logging

from config import FINDINGS_FILE, FINDINGS_DIR, MEMORY_FILE
from agent.memory import load_memory, save_memory, add_finding

log = logging.getLogger("genoresearch.findings")


def save_finding(title: str, description: str, evidence: str = "") -> str:
    """
    Log a research finding to memory and TSV.

    Args:
        title: Short title for the finding
        description: Detailed description
        evidence: Supporting evidence (tool output, accession IDs, etc.)
    """
    ts = datetime.datetime.now().isoformat()

    # Save to memory
    memory = load_memory()
    add_finding(memory, title, description, evidence)
    save_memory(memory)

    # Append to TSV
    file_exists = os.path.exists(FINDINGS_FILE)
    with open(FINDINGS_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        if not file_exists:
            writer.writerow(["timestamp", "title", "description", "evidence"])
        writer.writerow([ts, title, description[:500], evidence[:500]])

    # Save detailed finding as individual file
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60]
    detail_path = os.path.join(FINDINGS_DIR, f"{safe_title}.md")
    with open(detail_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Date:** {ts}\n\n")
        f.write(f"## Description\n{description}\n\n")
        if evidence:
            f.write(f"## Evidence\n```\n{evidence}\n```\n")

    log.info("Finding saved: %s", title)
    return f"Finding logged: '{title}' — saved to memory, TSV, and {detail_path}"


def list_findings() -> str:
    """List all recorded findings."""
    memory = load_memory()
    findings = memory.get("findings", [])

    if not findings:
        return "No findings recorded yet."

    lines = [f"Total findings: {len(findings)}"]
    for i, f in enumerate(findings, 1):
        lines.append(f"  {i}. [{f.get('timestamp', '?')[:10]}] {f.get('title', '?')}")
        lines.append(f"     {f.get('description', '')[:120]}")
    return "\n".join(lines)
