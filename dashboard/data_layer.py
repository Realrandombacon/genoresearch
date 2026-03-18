"""
Data layer — file readers and data utilities for the dashboard.
"""

import os
import json
import csv
import datetime
import re

from config import (
    SEQUENCES_DIR, FINDINGS_DIR, FINDINGS_FILE,
    DASHBOARD_STATUS, MEMORY_FILE, BASE_DIR,
)


def read_memory():
    """Read and return the current memory.json."""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"explored": [], "findings": [], "notes": [],
                "tool_stats": {}, "exhausted": [], "dismissed": [],
                "session_count": 0}


def read_findings():
    """Read findings.tsv and return as list of dicts."""
    EXPECTED_FIELDS = ["timestamp", "title", "description", "evidence"]
    findings = []
    try:
        with open(FINDINGS_FILE, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
            if not lines:
                return findings
            first = lines[0].strip().split("\t")
            import io
            if first[0].lower() in ("timestamp", "id", "finding_id"):
                reader = csv.DictReader(io.StringIO("".join(lines)), delimiter="\t")
            else:
                reader = csv.DictReader(
                    io.StringIO("".join(lines)), delimiter="\t",
                    fieldnames=EXPECTED_FIELDS
                )
            for row in reader:
                if row.get("timestamp"):
                    findings.append(dict(row))
    except (FileNotFoundError, OSError):
        pass
    return findings


def read_log_tail(n=100):
    """Read last N lines of research.log from cache."""
    from dashboard.log_parser import _refresh_log_cache, _log_cache_lock, _log_cache
    _refresh_log_cache()
    with _log_cache_lock:
        lines = _log_cache["lines"][-n:] if _log_cache["lines"] else []
    return [l.rstrip() for l in lines]


def read_live_status():
    """Read live status from dashboard_status.json."""
    try:
        with open(DASHBOARD_STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"running": False, "cycle": "?", "phase": "unknown",
                "current_tool": None, "last_thought": ""}


def read_gene_queue():
    """Read gene_queue.json for pipeline status."""
    queue_file = os.path.join(BASE_DIR, "gene_queue.json")
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {
            "queue": [],
            "in_progress": None,
            "completed": [],
            "skipped": [],
            "seed_index": 0,
            "stats": {"genes_queued": 0, "genes_completed": 0, "genes_skipped": 0},
        }


def list_sequences():
    """List all sequence files with metadata."""
    seqs = []
    try:
        for f in os.listdir(SEQUENCES_DIR):
            if f.lower().endswith((".fasta", ".fa", ".fna")):
                fpath = os.path.join(SEQUENCES_DIR, f)
                size = os.path.getsize(fpath)
                mtime = os.path.getmtime(fpath)
                desc = ""
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        header = fp.readline().strip()
                        if header.startswith(">"):
                            desc = header[1:].strip()[:120]
                except (FileNotFoundError, OSError):
                    pass
                seqs.append({
                    "filename": f,
                    "accession": f.replace(".fasta", "").replace(".fa", ""),
                    "size_bytes": size,
                    "size_human": _human_size(size),
                    "description": desc,
                    "modified": datetime.datetime.fromtimestamp(mtime).isoformat(),
                })
    except (FileNotFoundError, OSError):
        pass
    seqs.sort(key=lambda x: x["modified"], reverse=True)
    return seqs


def list_finding_files():
    """List all finding markdown files."""
    findings = []
    try:
        for f in os.listdir(FINDINGS_DIR):
            if f.lower().endswith(".md"):
                fpath = os.path.join(FINDINGS_DIR, f)
                size = os.path.getsize(fpath)
                mtime = os.path.getmtime(fpath)
                preview = ""
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        lines = fp.readlines()[:5]
                        preview = " ".join(l.strip() for l in lines if l.strip() and not l.startswith("#"))[:200]
                except (FileNotFoundError, OSError):
                    pass
                findings.append({
                    "title": f.replace(".md", ""),
                    "filename": f,
                    "size": _human_size(size),
                    "modified": datetime.datetime.fromtimestamp(mtime).isoformat(),
                    "preview": preview,
                })
    except (FileNotFoundError, OSError):
        pass
    findings.sort(key=lambda x: x["modified"], reverse=True)
    return findings


def _human_size(b):
    """Convert bytes to human-readable size string."""
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def _merge_tool_stats(memory_stats, log_stats):
    """Merge tool stats from memory.json and log parsing for live accuracy."""
    merged = dict(memory_stats)
    for tool, count in log_stats.items():
        merged[tool] = max(merged.get(tool, 0), count)
    return merged


def _extract_genes_from_sequences(seqs):
    """Dynamically extract ALL gene names from sequence descriptions using regex."""
    genes = set()
    for s in seqs:
        desc = s.get("description", "")
        matches = re.findall(r'\(([A-Z][A-Z0-9]{1,15})\)', desc)
        for m in matches:
            if m not in ("DNA", "RNA", "CDS", "UTR", "MRNA", "PREDICTED", "PARTIAL",
                         "COMPLETE", "HOMO", "SAPIENS", "VARIANT", "ISOFORM",
                         "TRANSCRIPT", "PROTEIN", "CHROMOSOME", "GENOME",
                         "ASSEMBLY", "SEQUENCE", "REGION", "CHAIN"):
                genes.add(m)

        gene_eq = re.findall(r'gene[=:]\s*([A-Z][A-Z0-9]{1,15})', desc, re.IGNORECASE)
        for g in gene_eq:
            genes.add(g.upper())

    return sorted(genes)
