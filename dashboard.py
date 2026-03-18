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
import json
import csv
import datetime
import argparse
import re
import threading

from config import (
    SEQUENCES_DIR, FINDINGS_DIR, FINDINGS_FILE,
    RESEARCH_LOG, DASHBOARD_STATUS, MEMORY_FILE,
    BASE_DIR,
)

from flask import Flask, jsonify, Response, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Log cache — avoid re-reading 77k lines every 12 seconds
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
        except Exception:
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
    _refresh_log_cache()
    with _log_cache_lock:
        return list(_log_cache["cycles"])


def _get_cached_errors():
    _refresh_log_cache()
    with _log_cache_lock:
        return list(_log_cache["errors"])


def _get_cached_warnings():
    _refresh_log_cache()
    with _log_cache_lock:
        return list(_log_cache["warnings"])


def _get_log_tool_counts():
    _refresh_log_cache()
    with _log_cache_lock:
        return dict(_log_cache["tool_calls_from_log"])


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
    """Read last N lines of research.log from cache."""
    _refresh_log_cache()
    with _log_cache_lock:
        lines = _log_cache["lines"][-n:] if _log_cache["lines"] else []
    return [l.rstrip() for l in lines]


def read_live_status():
    """Read live status from dashboard_status.json (written by orchestrator)."""
    try:
        with open(DASHBOARD_STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"running": False, "cycle": "?", "phase": "unknown",
                "current_tool": None, "last_thought": ""}


def read_gene_queue():
    """Read gene_queue.json for pipeline status."""
    queue_file = os.path.join(BASE_DIR, "gene_queue.json")
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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


def _merge_tool_stats(memory_stats, log_stats):
    """Merge tool stats from memory.json and log parsing for live accuracy."""
    merged = dict(memory_stats)
    for tool, count in log_stats.items():
        # Use the higher count — log is real-time, memory may lag
        merged[tool] = max(merged.get(tool, 0), count)
    return merged


def _extract_genes_from_sequences(seqs):
    """Dynamically extract ALL gene names from sequence descriptions using regex."""
    genes = set()
    for s in seqs:
        desc = s.get("description", "")
        # Match (GENENAME) pattern — most common in NCBI FASTA headers
        matches = re.findall(r'\(([A-Z][A-Z0-9]{1,15})\)', desc)
        for m in matches:
            # Filter out obvious non-gene tokens
            if m not in ("DNA", "RNA", "CDS", "UTR", "MRNA", "PREDICTED", "PARTIAL",
                         "COMPLETE", "HOMO", "SAPIENS", "VARIANT", "ISOFORM",
                         "TRANSCRIPT", "PROTEIN", "CHROMOSOME", "GENOME",
                         "ASSEMBLY", "SEQUENCE", "REGION", "CHAIN"):
                genes.add(m)

        # Also try to match gene= pattern in descriptions
        gene_eq = re.findall(r'gene[=:]\s*([A-Z][A-Z0-9]{1,15})', desc, re.IGNORECASE)
        for g in gene_eq:
            genes.add(g.upper())

    return sorted(genes)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

PIPELINE_STEPS = [
    "discover", "profile", "analyze", "translate",
    "compare", "annotate", "hypothesize",
]


@app.route("/api/status")
def api_status():
    mem = read_memory()
    findings = read_findings()
    live = read_live_status()
    seqs = list_sequences()
    gene_queue = read_gene_queue()

    # Merge tool stats from memory + log for live accuracy
    memory_stats = mem.get("tool_stats", {})
    log_stats = _get_log_tool_counts()
    tool_stats = _merge_tool_stats(memory_stats, log_stats)
    total_calls = sum(tool_stats.values())

    n_findings = len(findings)
    session_count = mem.get("session_count", 0)
    n_explored = len(mem.get("explored", []))
    n_exhausted = len(mem.get("exhausted", []))
    n_sequences = len(seqs)
    total_seq_size = sum(s["size_bytes"] for s in seqs)

    # Dynamic gene detection from sequences
    genes = _extract_genes_from_sequences(seqs)

    # Gene queue stats
    gq_completed = len(gene_queue.get("completed", []))
    gq_in_progress = 1 if gene_queue.get("in_progress") else 0
    gq_queued = len(gene_queue.get("queue", []))
    gq_total = gq_completed + gq_in_progress + gq_queued
    current_gene = None
    if gene_queue.get("in_progress"):
        current_gene = gene_queue["in_progress"].get("gene")

    # Cycle count from cache
    cycles = _get_cached_cycles()
    total_cycles = len(cycles)

    # Error counts
    errors = _get_cached_errors()
    warnings = _get_cached_warnings()
    total_errors = len(errors)
    total_warnings = len(warnings)

    # Error rate
    error_rate = 0.0
    if total_calls > 0:
        error_rate = total_errors / total_calls

    # Success rate percentage
    success_rate = round((1.0 - error_rate) * 100, 1) if total_calls > 0 else 100.0

    return jsonify({
        "session_count": session_count,
        "total_tool_calls": total_calls,
        "n_findings": n_findings,
        "n_explored": n_explored,
        "n_exhausted": n_exhausted,
        "n_sequences": n_sequences,
        "total_seq_size": _human_size(total_seq_size),
        "n_genes": len(genes),
        "genes_detected": genes,
        "genes_explored_queue": gq_completed + gq_in_progress,
        "genes_queue_total": gq_total,
        "genes_queue_depth": gq_queued,
        "current_gene": current_gene,
        "total_cycles": total_cycles,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "success_rate": success_rate,
        "tool_stats": tool_stats,
        "live": live,
    })


@app.route("/api/findings")
def api_findings():
    findings = read_findings()
    findings.reverse()
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
    memory_stats = mem.get("tool_stats", {})
    log_stats = _get_log_tool_counts()
    merged = _merge_tool_stats(memory_stats, log_stats)
    return jsonify(merged)


@app.route("/api/log")
def api_log():
    n = request.args.get("n", 100, type=int)
    lines = read_log_tail(n)
    return jsonify(lines)


@app.route("/api/cycle-timeline")
def api_cycle_timeline():
    """Per-cycle tool usage for timeline chart (cached)."""
    cycles = _get_cached_cycles()
    findings = read_findings()

    cycle_nums = [c["cycle"] for c in cycles]
    tool_counts_per_cycle = [c["n_tools"] for c in cycles]
    errors_per_cycle = [c.get("errors", 0) for c in cycles]

    cum_tools = []
    total = 0
    for c in tool_counts_per_cycle:
        total += c
        cum_tools.append(total)

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
        "errors_per_cycle": errors_per_cycle,
        "cum_tools": cum_tools,
        "cum_findings": cum_findings,
    })


@app.route("/api/tool-timeline")
def api_tool_timeline():
    """Tool usage broken down per cycle for stacked chart (cached)."""
    cycles = _get_cached_cycles()

    all_tools = set()
    for c in cycles:
        all_tools.update(c["tools"])

    tool_series = {}
    for tool in sorted(all_tools):
        tool_series[tool] = []
        for c in cycles:
            tool_series[tool].append(c["tools"].count(tool))

    return jsonify({
        "cycles": [c["cycle"] for c in cycles],
        "tool_series": tool_series,
    })


@app.route("/api/gene-queue")
def api_gene_queue():
    """Gene pipeline queue status."""
    gq = read_gene_queue()

    current = None
    if gq.get("in_progress"):
        ip = gq["in_progress"]
        steps_done = ip.get("steps_done", [])
        steps_remaining = [s for s in PIPELINE_STEPS if s not in steps_done]
        current = {
            "gene": ip.get("gene"),
            "started": ip.get("started"),
            "steps_done": steps_done,
            "steps_remaining": steps_remaining,
            "current_step": steps_remaining[0] if steps_remaining else "complete",
            "progress_pct": round(len(steps_done) / len(PIPELINE_STEPS) * 100, 1),
        }

    completed = []
    for g in gq.get("completed", []):
        completed.append({
            "gene": g.get("gene"),
            "finished": g.get("finished"),
            "steps_done": g.get("steps_done", []),
            "n_steps": len(g.get("steps_done", [])),
        })

    queue = []
    for g in gq.get("queue", []):
        queue.append({
            "gene": g.get("gene"),
            "priority": g.get("priority", "normal"),
            "source": g.get("source", ""),
        })

    skipped = gq.get("skipped", [])
    n_completed = len(completed)
    n_queued = len(queue)
    n_in_progress = 1 if current else 0
    n_total = n_completed + n_in_progress + n_queued
    completion_pct = round(n_completed / n_total * 100, 1) if n_total > 0 else 0.0

    return jsonify({
        "current": current,
        "completed": completed,
        "queue": queue,
        "skipped": skipped,
        "n_completed": n_completed,
        "n_queued": n_queued,
        "n_total": n_total,
        "completion_pct": completion_pct,
        "seed_index": gq.get("seed_index", 0),
        "pipeline_steps": PIPELINE_STEPS,
    })


@app.route("/api/error-rate")
def api_error_rate():
    """Error and warning rate statistics."""
    errors = _get_cached_errors()
    warnings = _get_cached_warnings()
    cycles = _get_cached_cycles()

    # Errors per tool (parse tool name from error lines)
    errors_per_tool = {}
    for e in errors:
        line = e.get("line", "")
        m = re.search(r'\[TOOL\]\s*(\w+)', line)
        if m:
            tool = m.group(1)
            errors_per_tool[tool] = errors_per_tool.get(tool, 0) + 1

    # Errors per cycle for chart
    errors_by_cycle = {}
    for e in errors:
        c = e.get("cycle", 0)
        errors_by_cycle[c] = errors_by_cycle.get(c, 0) + 1

    cycle_nums = [c["cycle"] for c in cycles]
    errors_per_cycle = [errors_by_cycle.get(c, 0) for c in cycle_nums]

    # Total tool calls from log for rate calculation
    log_stats = _get_log_tool_counts()
    total_calls = sum(log_stats.values())
    error_rate = len(errors) / total_calls if total_calls > 0 else 0.0

    return jsonify({
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "error_rate": round(error_rate, 4),
        "errors_per_tool": errors_per_tool,
        "cycle_nums": cycle_nums,
        "errors_per_cycle": errors_per_cycle,
        "recent_errors": errors[-20:],
    })


@app.route("/api/pipeline-status")
def api_pipeline_status():
    """Show gene research pipeline stages and current position."""
    gq = read_gene_queue()

    current_step = None
    current_gene = None
    steps_status = {}

    if gq.get("in_progress"):
        ip = gq["in_progress"]
        current_gene = ip.get("gene")
        done = ip.get("steps_done", [])
        for step in PIPELINE_STEPS:
            if step in done:
                steps_status[step] = "done"
            elif current_step is None:
                steps_status[step] = "active"
                current_step = step
            else:
                steps_status[step] = "pending"
    else:
        for step in PIPELINE_STEPS:
            steps_status[step] = "idle"

    return jsonify({
        "pipeline_steps": PIPELINE_STEPS,
        "steps_status": steps_status,
        "current_step": current_step,
        "current_gene": current_gene,
    })


@app.route("/api/sequence-stats")
def api_sequence_stats():
    """Detailed sequence analysis stats."""
    seqs = list_sequences()

    refseq_mrna = [s for s in seqs if s["accession"].startswith("NM_")]
    refseq_chromo = [s for s in seqs if s["accession"].startswith("NC_")]
    uniprot = [s for s in seqs if s["accession"].startswith("P") and s["accession"][1:].isdigit()]
    other = [s for s in seqs if s not in refseq_mrna + refseq_chromo + uniprot]

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
