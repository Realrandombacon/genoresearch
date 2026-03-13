"""
Genoresearch Dashboard — Real-time monitoring for the autonomous genomics research agent.

Flask backend + HTML/CSS/JS frontend with Plotly charts.
Reads the same data files as the orchestrator (memory.json, findings.tsv, research.log).

Usage:
    pip install flask
    python dashboard.py              # starts on http://localhost:5555
    python dashboard.py --port 8080  # custom port
"""

import os
import sys
import json
import csv
import datetime
import argparse
import collections
import re

from config import (
    DATA_DIR, SEQUENCES_DIR, FINDINGS_DIR, FINDINGS_FILE,
    RESEARCH_LOG, DASHBOARD_STATUS, MEMORY_FILE,
    LAB_RUNS_DIR, LAB_CHECKPOINTS_DIR,
)

from flask import Flask, jsonify, Response, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Helper readers
# ---------------------------------------------------------------------------

def read_memory():
    """Read and return the current memory.json."""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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
    except Exception:
        pass
    return findings


def read_log_tail(n=100):
    """Read last N lines of research.log."""
    lines = []
    try:
        with open(RESEARCH_LOG, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            lines = all_lines[-n:]
    except Exception:
        pass
    return [l.rstrip() for l in lines]


def read_log_full():
    """Read entire research.log for parsing."""
    try:
        with open(RESEARCH_LOG, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception:
        return []


def read_live_status():
    """Read live status from dashboard_status.json (written by orchestrator)."""
    try:
        with open(DASHBOARD_STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"running": False, "cycle": "?", "phase": "unknown",
                "current_tool": None, "last_thought": ""}


def list_sequences():
    """List all sequence files with metadata."""
    seqs = []
    try:
        for f in os.listdir(SEQUENCES_DIR):
            if f.lower().endswith((".fasta", ".fa", ".fna")):
                fpath = os.path.join(SEQUENCES_DIR, f)
                size = os.path.getsize(fpath)
                mtime = os.path.getmtime(fpath)
                # Read first line for description
                desc = ""
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        header = fp.readline().strip()
                        if header.startswith(">"):
                            desc = header[1:].strip()[:120]
                except Exception:
                    pass
                seqs.append({
                    "filename": f,
                    "accession": f.replace(".fasta", "").replace(".fa", ""),
                    "size_bytes": size,
                    "size_human": _human_size(size),
                    "description": desc,
                    "modified": datetime.datetime.fromtimestamp(mtime).isoformat(),
                })
    except Exception:
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
                # Read first few lines for preview
                preview = ""
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        lines = fp.readlines()[:5]
                        preview = " ".join(l.strip() for l in lines if l.strip() and not l.startswith("#"))[:200]
                except Exception:
                    pass
                findings.append({
                    "title": f.replace(".md", ""),
                    "filename": f,
                    "size": _human_size(size),
                    "modified": datetime.datetime.fromtimestamp(mtime).isoformat(),
                    "preview": preview,
                })
    except Exception:
        pass
    findings.sort(key=lambda x: x["modified"], reverse=True)
    return findings


def _human_size(b):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def parse_log_cycles():
    """Parse research.log to extract per-cycle data for timeline charts.

    Each LLM think cycle is delimited by:
        [timestamp] [INFO] Waiting for LLM response...
    Tool calls within a cycle:
        [timestamp] [TOOL] tool_name|...
    """
    lines = read_log_full()
    cycles = []
    cycle_num = 0
    cycle_tools = []
    cycle_start = None

    for line in lines:
        # Each "Waiting for LLM" marks the start of a new cycle
        if "Waiting for LLM" in line:
            # Save previous cycle if it had any content
            if cycle_num > 0:
                cycles.append({
                    "cycle": cycle_num,
                    "timestamp": cycle_start or "",
                    "tools": list(cycle_tools),
                    "n_tools": len(cycle_tools),
                })
            cycle_num += 1
            cycle_tools = []
            ts_match = re.search(r'\[([^\]]+)\]', line)
            cycle_start = ts_match.group(1) if ts_match else ""
            continue

        # Detect tool calls: [timestamp] [TOOL] tool_name|...
        m2 = re.search(r'\[TOOL\]\s*(\w+)\|', line)
        if m2 and cycle_num > 0:
            cycle_tools.append(m2.group(1))

    # Save last cycle
    if cycle_num > 0:
        cycles.append({
            "cycle": cycle_num,
            "timestamp": cycle_start or "",
            "tools": list(cycle_tools),
            "n_tools": len(cycle_tools),
        })

    return cycles


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    mem = read_memory()
    findings = read_findings()
    live = read_live_status()
    seqs = list_sequences()

    tool_stats = mem.get("tool_stats", {})
    total_calls = sum(tool_stats.values())
    n_findings = len(findings)
    session_count = mem.get("session_count", 0)
    n_explored = len(mem.get("explored", []))
    n_exhausted = len(mem.get("exhausted", []))
    n_sequences = len(seqs)
    total_seq_size = sum(s["size_bytes"] for s in seqs)

    # Count unique genes from sequence filenames
    genes = set()
    for s in seqs:
        acc = s["accession"]
        # Extract gene info from description
        desc = s.get("description", "").lower()
        for gene in ["brca1", "brca2", "tp53", "blvra", "egfr", "kras", "myc"]:
            if gene in desc or gene in acc.lower():
                genes.add(gene.upper())

    # Lab stats
    n_lab_runs = len(os.listdir(LAB_RUNS_DIR)) if os.path.isdir(LAB_RUNS_DIR) else 0
    n_checkpoints = len(os.listdir(LAB_CHECKPOINTS_DIR)) if os.path.isdir(LAB_CHECKPOINTS_DIR) else 0

    return jsonify({
        "session_count": session_count,
        "total_tool_calls": total_calls,
        "n_findings": n_findings,
        "n_explored": n_explored,
        "n_exhausted": n_exhausted,
        "n_sequences": n_sequences,
        "total_seq_size": _human_size(total_seq_size),
        "n_genes": len(genes),
        "genes_studied": sorted(genes),
        "n_lab_runs": n_lab_runs,
        "n_checkpoints": n_checkpoints,
        "tool_stats": tool_stats,
        "live": live,
    })


@app.route("/api/findings")
def api_findings():
    findings = read_findings()
    findings.reverse()  # newest first
    return jsonify(findings)


@app.route("/api/finding-files")
def api_finding_files():
    return jsonify(list_finding_files())


@app.route("/api/sequences")
def api_sequences():
    return jsonify(list_sequences())


@app.route("/api/tool-stats")
def api_tool_stats():
    mem = read_memory()
    tool_stats = mem.get("tool_stats", {})
    return jsonify(tool_stats)


@app.route("/api/log")
def api_log():
    n = request.args.get("n", 100, type=int)
    lines = read_log_tail(n)
    return jsonify(lines)


@app.route("/api/cycle-timeline")
def api_cycle_timeline():
    """Per-cycle tool usage for timeline chart."""
    cycles = parse_log_cycles()
    findings = read_findings()

    # Build cumulative findings over cycles
    # Map finding timestamps to approximate cycle numbers
    cycle_timestamps = {c["cycle"]: c["timestamp"] for c in cycles}

    # Tool usage per cycle
    cycle_nums = [c["cycle"] for c in cycles]
    tool_counts_per_cycle = [c["n_tools"] for c in cycles]

    # Cumulative tools
    cum_tools = []
    total = 0
    for c in tool_counts_per_cycle:
        total += c
        cum_tools.append(total)

    # Cumulative findings (approximate by timestamp)
    cum_findings = []
    f_count = 0
    finding_times = sorted([f.get("timestamp", "") for f in findings])
    fi = 0
    for c in cycles:
        ts = c.get("timestamp", "")
        while fi < len(finding_times) and finding_times[fi] <= ts:
            f_count += 1
            fi += 1
        cum_findings.append(f_count)

    return jsonify({
        "cycles": cycle_nums,
        "tools_per_cycle": tool_counts_per_cycle,
        "cum_tools": cum_tools,
        "cum_findings": cum_findings,
    })


@app.route("/api/tool-timeline")
def api_tool_timeline():
    """Tool usage broken down per cycle for stacked chart."""
    cycles = parse_log_cycles()

    # Get all unique tools
    all_tools = set()
    for c in cycles:
        all_tools.update(c["tools"])

    # Build per-tool per-cycle counts
    tool_series = {}
    for tool in sorted(all_tools):
        tool_series[tool] = []
        for c in cycles:
            tool_series[tool].append(c["tools"].count(tool))

    return jsonify({
        "cycles": [c["cycle"] for c in cycles],
        "tool_series": tool_series,
    })


@app.route("/api/sequence-stats")
def api_sequence_stats():
    """Detailed sequence analysis stats."""
    seqs = list_sequences()

    # Categorize sequences
    refseq_mrna = [s for s in seqs if s["accession"].startswith("NM_")]
    refseq_chromo = [s for s in seqs if s["accession"].startswith("NC_")]
    uniprot = [s for s in seqs if s["accession"].startswith("P") and s["accession"][1:].isdigit()]
    other = [s for s in seqs if s not in refseq_mrna + refseq_chromo + uniprot]

    # Size distribution
    sizes = [s["size_bytes"] for s in seqs]

    return jsonify({
        "total": len(seqs),
        "refseq_mrna": len(refseq_mrna),
        "refseq_chromo": len(refseq_chromo),
        "uniprot_protein": len(uniprot),
        "other": len(other),
        "sequences": seqs,
        "sizes": sizes,
        "total_size": _human_size(sum(sizes)) if sizes else "0 B",
    })


@app.route("/api/memory")
def api_memory():
    """Full memory state for detailed view."""
    mem = read_memory()
    return jsonify(mem)


# ---------------------------------------------------------------------------
# Main HTML Page
# ---------------------------------------------------------------------------

_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "templates", "dashboard.html")

@app.route("/")
def index():
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    return Response(html, mimetype="text/html")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genoresearch Dashboard")
    parser.add_argument("--port", type=int, default=5555,
                        help="Port to run on (default: 5555)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--debug", action="store_true",
                        help="Run in debug mode")
    args = parser.parse_args()

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║   🧬  Genoresearch Dashboard                             ║
    ║   Open: http://{args.host}:{args.port}                        ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    app.run(host=args.host, port=args.port, debug=args.debug)
