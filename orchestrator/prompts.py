"""
Prompt templates — reflection prompts, queue bulletins, auto-completion logic.
"""

import re

from agent.ui import log as ui_log


# Map tools to the pipeline step they naturally complete
_TOOL_STEP_MAP = {
    "gene_info": "discover",
    "ncbi_fetch": "profile",
    "analyze_sequence": "analyze",
    "translate_sequence": "translate",
    "uniprot_fetch": "translate",
    "blast_search": "compare",
    "compare_sequences": "compare",
    "uniprot_search": "annotate",
    "hypothesize": "hypothesize",
    "save_finding": "hypothesize",
}

# Pattern to extract gene names from finding titles/results
_GENE_NAME_RE = re.compile(r'\b(C\d+orf\d+|LOC\d+|[A-Z][A-Z0-9]{1,10})\b')


def _build_queue_bulletin(just_completed: str) -> str:
    """Build a concise queue status bulletin for the reflection prompt.

    Tells the agent exactly what the queue looks like after completing a gene:
    - How many genes are waiting vs completed
    - What seed family is current
    - Whether it needs to discover new genes or just call next_gene()

    This replaces the need for the agent to call queue_status() as a tool
    (which wastes a turn). The info is injected for free after save_finding.
    """
    try:
        from tools.gene_queue import _load_queue, SEED_PREFIXES
        from config import FINDINGS_DIR
        import os

        q = _load_queue()
        queue_size = len(q.get("queue", []))
        completed = len(q.get("completed", []))
        skipped = len(q.get("skipped", []))
        seed_idx = q.get("seed_index", 0)
        total_seeds = len(SEED_PREFIXES)

        # Count findings on disk (actual output)
        findings_on_disk = 0
        if os.path.isdir(FINDINGS_DIR):
            findings_on_disk = len([f for f in os.listdir(FINDINGS_DIR) if f.endswith(".md")])

        lines = []
        lines.append(f"Genes in queue: {queue_size}")
        lines.append(f"Completed: {completed} | Findings on disk: {findings_on_disk} | Skipped: {skipped}")
        lines.append(f"Seed families: {seed_idx}/{total_seeds} searched")

        if queue_size > 0:
            next_genes = [g["gene"] for g in q["queue"][:3]]
            lines.append(f"Next up: {', '.join(next_genes)}")
            lines.append("Action: call next_gene() to start the next gene.")
        elif seed_idx < total_seeds:
            prefix = SEED_PREFIXES[seed_idx]
            lines.append(f"Queue is EMPTY. Next seed family: '{prefix}'")
            lines.append(f"Action: call next_gene() — it will guide you to discover new genes from '{prefix}'.")
        else:
            lines.append("Queue is EMPTY and all seed families searched.")
            lines.append("Action: call next_gene() for broader discovery suggestions.")

        return "\n".join(lines)
    except Exception:
        return "Queue status unavailable. Call next_gene() to continue."


def _auto_complete_step(tool_name: str, result_str: str):
    """Auto-mark pipeline steps done when the corresponding tool succeeds."""
    if "[ERROR]" in result_str or "[REJECTED]" in result_str:
        return

    step = _TOOL_STEP_MAP.get(tool_name)
    if not step:
        return

    try:
        from tools.gene_queue import (
            complete_step as _cs,
            _load_queue,
        )

        # save_finding already calls complete_gene() internally — skip here
        # to avoid double-completion race condition
        if tool_name == "save_finding":
            return

        # --- Normal step completion ---
        q = _load_queue()
        if not q.get("in_progress"):
            return
        done = q["in_progress"].get("steps_done", [])
        if step not in done:
            _cs(step)
            ui_log("INFO", f"Auto-completed pipeline step '{step}' (from {tool_name})")
    except Exception:
        pass  # Don't crash the orchestrator for pipeline tracking


def _build_reflection_prompt(tool_name: str, result_str: str,
                             turn: int, max_turns: int,
                             soft_turns: int = 12) -> str:
    """Build a lightweight reflection prompt after a tool execution."""
    # Truncate result for the reflection prompt (keep it focused)
    result_preview = result_str[:1500]
    if len(result_str) > 1500:
        result_preview += "\n... (truncated)"

    # After add_to_queue succeeds, tell agent to start analyzing
    if tool_name == "add_to_queue" and "Added" in result_str:
        return (
            f"[orchestrator] Turn {turn} — GENE QUEUED\n\n"
            f"{result_preview}\n\n"
            "Gene added successfully! Now call advance_seed() then next_gene() to START ANALYZING it.\n"
            "TOOL: advance_seed()"
        )

    # After add_to_queue rejects (duplicate), count consecutive rejections
    if tool_name == "add_to_queue" and "already" in result_str.lower():
        return (
            f"[orchestrator] Turn {turn} — DUPLICATE REJECTED\n\n"
            f"{result_preview}\n\n"
            "This gene was already done. If you've had 3+ rejections in a row,\n"
            "this seed family is exhausted. Call advance_seed() then next_gene().\n"
            "Do NOT keep trying more genes from the same search results."
        )

    # After save_finding, direct Qwen to move to next gene
    # Include a queue status bulletin so the agent knows what's ahead
    if tool_name == "save_finding":
        # Extract gene name from the result so the agent knows what to avoid
        gene_match = _GENE_NAME_RE.search(result_str)
        completed_gene = gene_match.group(1) if gene_match else "the gene you just analyzed"

        # Build queue bulletin — tell the agent the state of its worklist
        queue_bulletin = _build_queue_bulletin(completed_gene)

        return (
            f"[orchestrator] Turn {turn} — FINDING SAVED\n\n"
            f"Finding for **{completed_gene}** saved successfully.\n\n"
            f"GOOD WORK! {completed_gene} is DONE — do NOT re-analyze it.\n\n"
            f"═══ QUEUE STATUS ═══\n"
            f"{queue_bulletin}\n\n"
            "NEXT ACTION: TOOL: next_gene()"
        )

    # Dynamic pacing — no pressure early, gentle nudge after soft cap
    if turn < soft_turns:
        pacing = "Take your time — explore all relevant sources before saving."
    elif turn < max_turns - 2:
        pacing = "You've done thorough research. When ready, save your finding."
    else:
        pacing = "Wrap up and save your finding now."

    return (
        f"[orchestrator] Turn {turn} — REFLECTION\n\n"
        f"Tool result from {tool_name}:\n{result_preview}\n\n"
        "Before your next action, REFLECT briefly:\n"
        "1. EVALUATE: What useful data did this tool give me? What's still missing?\n"
        "2. TOOL REVIEW: Which sources have I already queried? Which scoring dimensions am I missing?\n"
        f"3. PLAN: {pacing}\n\n"
        "Scoring reminders:\n"
        "  COVERAGE: InterPro domains, STRING interactions, HPA expression, ClinVar, conservation, AlphaFold\n"
        "  DEPTH: 400+ char description, quantitative data, named entities\n"
        "  INSIGHT: functional hypothesis, cross-domain reasoning, mechanistic proposal\n\n"
        "Now call your next tool using TOOL: format."
    )
