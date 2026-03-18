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
import re
import argparse

from flask import Flask, jsonify, Response, request

from dashboard.log_parser import (
    _get_cached_cycles, _get_cached_errors,
    _get_cached_warnings, _get_log_tool_counts,
)
from dashboard.data_layer import (
    read_memory, read_findings, read_log_tail, read_live_status,
    read_gene_queue, list_sequences, list_finding_files,
    _human_size, _merge_tool_stats, _extract_genes_from_sequences,
)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

PIPELINE_STEPS = [
    "discover", "profile", "analyze", "translate",
    "compare", "annotate", "hypothesize",
]


@app.route("/api/status")
def api_status():
    """Return overall system status."""
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
    """Return all findings in reverse chronological order."""
    findings = read_findings()
    findings.reverse()
    return jsonify(findings)


@app.route("/api/finding-files")
def api_finding_files():
    """Return all finding file metadata."""
    return jsonify(list_finding_files())


@app.route("/api/sequences")
def api_sequences():
    """Return all sequence file metadata."""
    return jsonify(list_sequences())


@app.route("/api/tool-stats")
def api_tool_stats():
    """Return merged tool usage statistics."""
    mem = read_memory()
    memory_stats = mem.get("tool_stats", {})
    log_stats = _get_log_tool_counts()
    merged = _merge_tool_stats(memory_stats, log_stats)
    return jsonify(merged)


@app.route("/api/log")
def api_log():
    """Return recent log lines."""
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

    # Errors per tool
    errors_per_tool = {}
    for e in errors:
        line = e.get("line", "")
        m = re.search(r'\[TOOL\]\s*(\w+)', line)
        if m:
            tool = m.group(1)
            errors_per_tool[tool] = errors_per_tool.get(tool, 0) + 1

    # Errors per cycle
    errors_by_cycle = {}
    for e in errors:
        c = e.get("cycle", 0)
        errors_by_cycle[c] = errors_by_cycle.get(c, 0) + 1

    cycle_nums = [c["cycle"] for c in cycles]
    errors_per_cycle = [errors_by_cycle.get(c, 0) for c in cycle_nums]

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
    """Serve the dashboard HTML page."""
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

    print(f"\n    Genoresearch Dashboard\n    Open: http://{args.host}:{args.port}\n")

    app.run(host=args.host, port=args.port, debug=args.debug)
