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


def save_finding(*args, title: str = "", description: str = "",
                  evidence: str = "", **kwargs) -> str:
    """
    Log a research finding to memory and TSV.

    Args:
        title: Short title for the finding
        description: Detailed description
        evidence: Supporting evidence (tool output, accession IDs, etc.)
    """
    # Qwen sometimes passes: save_finding('filename.txt', title='...', description='...')
    # or save_finding('title', 'description', 'evidence') positionally.
    # Handle both gracefully.
    if args:
        if not title and len(args) >= 1:
            # First positional could be a filename (ignore) or the actual title
            candidate = str(args[0])
            if candidate.endswith(('.txt', '.md', '.json', '.csv')):
                # It's a filename — skip it, use kwargs
                pass
            else:
                title = candidate
        if not description and len(args) >= 2:
            description = str(args[1])
        if not evidence and len(args) >= 3:
            evidence = str(args[2])
    # Also absorb any unexpected kwargs Qwen invents (content=, query=, etc.)
    if not title:
        for key in ("query", "name", "finding", "topic", "subject", "text", "summary"):
            if key in kwargs:
                title = str(kwargs[key])
                break
    if not description:
        for key in ("content", "details", "result", "findings", "info", "data", "body"):
            if key in kwargs:
                description = str(kwargs[key])
                break
    if not evidence:
        for key in ("source", "reference", "ref", "pmid", "accession"):
            if key in kwargs:
                evidence = str(kwargs[key])
                break
    if not title:
        title = "Untitled Finding"
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
    """List all recorded findings with their index numbers.
    Use read_finding(number) to read the full content of a specific finding.
    """
    # List from actual finding files on disk (more reliable than memory)
    findings_from_files = []
    if os.path.isdir(FINDINGS_DIR):
        for fname in sorted(os.listdir(FINDINGS_DIR)):
            if fname.endswith(".md"):
                fpath = os.path.join(FINDINGS_DIR, fname)
                mtime = os.path.getmtime(fpath)
                findings_from_files.append({
                    "filename": fname,
                    "title": fname.replace(".md", ""),
                    "modified": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                })

    if not findings_from_files:
        return "No findings recorded yet. Use save_finding(title, description, evidence) to log discoveries."

    # Sort by modification time (newest first)
    findings_from_files.sort(key=lambda x: x["modified"], reverse=True)

    lines = [f"Total findings: {len(findings_from_files)}",
             "  (Use read_finding(number) to read full content)"]
    for i, f in enumerate(findings_from_files, 1):
        lines.append(f"  {i}. [{f['modified']}] {f['title']}")

    return "\n".join(lines)


def read_finding(*args, **kwargs) -> str:
    """
    Read the full content of a specific finding by number or title.

    Args:
        finding_id: Finding number (from list_findings) or partial title match
    """
    # Extract the identifier
    finding_id = ""
    if args:
        finding_id = str(args[0])
    if not finding_id:
        for key in ("finding_id", "id", "number", "index", "title", "name", "query"):
            if key in kwargs:
                finding_id = str(kwargs[key])
                break
    if not finding_id:
        return "[ERROR] No finding specified. Usage: read_finding(1) or read_finding('BRCA1')"

    # Get list of finding files
    if not os.path.isdir(FINDINGS_DIR):
        return "No findings directory found."

    files = sorted([f for f in os.listdir(FINDINGS_DIR) if f.endswith(".md")])
    if not files:
        return "No findings recorded yet."

    # Sort by modification time (newest first) to match list_findings order
    files.sort(key=lambda f: os.path.getmtime(os.path.join(FINDINGS_DIR, f)), reverse=True)

    # Try numeric index first
    try:
        idx = int(finding_id) - 1  # 1-indexed
        if 0 <= idx < len(files):
            fpath = os.path.join(FINDINGS_DIR, files[idx])
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            return f"[Finding #{idx + 1}: {files[idx]}]\n\n{content[:3000]}"
    except ValueError:
        pass

    # Try partial title match
    query = finding_id.lower()
    for fname in files:
        if query in fname.lower():
            fpath = os.path.join(FINDINGS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            return f"[Finding: {fname}]\n\n{content[:3000]}"

    return f"No finding matching '{finding_id}'. Use list_findings() to see available findings."


def list_sequences() -> str:
    """
    List all downloaded sequence files (.fasta) with their descriptions.
    Shows what's already been fetched so you don't re-download.
    """
    from config import SEQUENCES_DIR

    if not os.path.isdir(SEQUENCES_DIR):
        return "No sequences directory found."

    files = []
    for fname in os.listdir(SEQUENCES_DIR):
        if fname.lower().endswith((".fasta", ".fa", ".fna")):
            fpath = os.path.join(SEQUENCES_DIR, fname)
            size = os.path.getsize(fpath)
            # Read header line
            header = ""
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith(">"):
                        header = first_line[1:].strip()[:120]
            except Exception:
                pass
            files.append({
                "filename": fname,
                "size": size,
                "header": header,
            })

    if not files:
        return "No sequence files downloaded yet. Use ncbi_fetch() or uniprot_fetch() to download sequences."

    files.sort(key=lambda x: x["filename"])

    lines = [f"Downloaded sequences: {len(files)} files"]
    for f in files:
        size_str = f"{f['size']:,} bytes"
        if f['size'] > 1_000_000:
            size_str = f"{f['size'] / 1_000_000:.1f} MB"
        elif f['size'] > 1000:
            size_str = f"{f['size'] / 1000:.1f} KB"
        lines.append(f"  • {f['filename']} ({size_str})")
        if f['header']:
            lines.append(f"    {f['header']}")

    return "\n".join(lines)
