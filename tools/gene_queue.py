"""
Gene queue — systematic worklist for mapping understudied human genes.
Tracks discovery, pipeline progress, and prioritization.
"""

import json
import os
import logging
import datetime

from config import BASE_DIR

log = logging.getLogger("genoresearch.gene_queue")

QUEUE_FILE = os.path.join(BASE_DIR, "gene_queue.json")

# Pipeline steps every gene must go through
PIPELINE_STEPS = [
    "discover",     # Found the gene, confirmed it's understudied
    "profile",      # gene_info + ncbi_fetch mRNA sequence
    "analyze",      # analyze_sequence (composition, motifs)
    "translate",    # translate_sequence (protein prediction)
    "compare",      # BLAST or compare_sequences with known genes
    "annotate",     # uniprot_search/fetch for domain info
    "hypothesize",  # save_finding with function hypothesis
]

# Seed families — systematic starting points for dark gene discovery
# These are known to contain many uncharacterized genes
SEED_PREFIXES = [
    # Chromosome ORFs (C1orf1 through C22orf)
    "C1orf", "C2orf", "C3orf", "C4orf", "C5orf", "C6orf", "C7orf",
    "C8orf", "C9orf", "C10orf", "C11orf", "C12orf", "C13orf", "C14orf",
    "C15orf", "C16orf", "C17orf", "C18orf", "C19orf", "C20orf", "C21orf",
    "C22orf",
    # FAM genes (family with sequence similarity)
    "FAM",
    # KIAA genes (large-scale cDNA project, many uncharacterized)
    "KIAA",
    # TMEM genes (transmembrane proteins, many unknown)
    "TMEM",
    # LINC genes (long intergenic non-coding RNA)
    "LINC",
]


def _load_queue() -> dict:
    """Load the gene queue from disk."""
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "queue": [],              # [{gene, source, added, priority}]
            "in_progress": None,      # {gene, started, steps_done: []}
            "completed": [],          # [{gene, finished, steps_done, hypothesis}]
            "skipped": [],            # [{gene, reason}]
            "seed_index": 0,          # which seed prefix to search next
            "stats": {
                "genes_queued": 0,
                "genes_completed": 0,
                "genes_skipped": 0,
            },
        }


def _save_queue(queue: dict):
    """Save the gene queue to disk."""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def next_gene(*args, **kwargs) -> str:
    """
    Get the next gene to study from the worklist.
    Returns the gene name and what pipeline steps to do.
    If the queue is empty, suggests a search to populate it.
    """
    q = _load_queue()

    # If there's a gene in progress, remind the agent
    if q["in_progress"]:
        gene = q["in_progress"]["gene"]
        done = q["in_progress"].get("steps_done", [])
        remaining = [s for s in PIPELINE_STEPS if s not in done]
        if remaining:
            next_step = remaining[0]
            step_instructions = _step_instructions(next_step, gene)
            return (
                f"CURRENT GENE: {gene} (in progress)\n"
                f"Steps completed: {', '.join(done) if done else 'none'}\n"
                f"Steps remaining: {', '.join(remaining)}\n\n"
                f"NEXT STEP: {next_step}\n{step_instructions}"
            )
        else:
            # All steps done — auto-complete
            complete_gene(gene)
            # Fall through to pick next

    # Pick from queue
    if not q["queue"]:
        # Queue empty — suggest discovery
        seed_idx = q.get("seed_index", 0)
        if seed_idx < len(SEED_PREFIXES):
            prefix = SEED_PREFIXES[seed_idx]
            return (
                f"QUEUE EMPTY — time to discover new genes!\n"
                f"Search suggestion: ncbi_search('{prefix}', db='gene', max_results=5)\n"
                f"Then use add_to_queue() for any uncharacterized genes you find.\n"
                f"Seed family: {prefix} ({seed_idx + 1}/{len(SEED_PREFIXES)})"
            )
        else:
            return (
                "QUEUE EMPTY and all seed families searched.\n"
                "Try: ncbi_search('uncharacterized protein human', db='gene', max_results=5)\n"
                "Or: ncbi_search('hypothetical protein homo sapiens', db='gene', max_results=5)"
            )

    # Pop the first gene
    gene_entry = q["queue"].pop(0)
    q["in_progress"] = {
        "gene": gene_entry["gene"],
        "started": datetime.datetime.now().isoformat(),
        "steps_done": [],
        "source": gene_entry.get("source", "unknown"),
    }
    q["stats"]["genes_queued"] = len(q["queue"])
    _save_queue(q)

    gene = gene_entry["gene"]
    step = PIPELINE_STEPS[0]
    return (
        f"NEW GENE: {gene}\n"
        f"Source: {gene_entry.get('source', 'unknown')}\n"
        f"Priority: {gene_entry.get('priority', 'normal')}\n"
        f"Queue remaining: {len(q['queue'])}\n\n"
        f"START PIPELINE — Step 1: {step}\n"
        f"{_step_instructions(step, gene)}"
    )


def add_to_queue(*args, **kwargs) -> str:
    """
    Add a gene to the research queue.

    Args:
        gene: Gene name/symbol (e.g. 'C1orf87', 'FAM71A')
        source: How it was found (e.g. 'ncbi_search C1orf')
        priority: 'high', 'normal', or 'low'
    """
    gene = ""
    if args:
        gene = str(args[0]).strip()
    if not gene:
        for key in ("gene", "name", "target", "symbol"):
            if key in kwargs:
                gene = str(kwargs[key]).strip()
                break
    if not gene:
        return "[ERROR] Usage: add_to_queue('C1orf87', source='ncbi_search')"

    source = ""
    if len(args) >= 2:
        source = str(args[1])
    elif "source" in kwargs:
        source = str(kwargs["source"])

    priority = "normal"
    if len(args) >= 3:
        priority = str(args[2])
    elif "priority" in kwargs:
        priority = str(kwargs["priority"])

    q = _load_queue()

    # Check if already in queue, in progress, or completed
    all_genes = (
        {g["gene"] for g in q["queue"]} |
        {g["gene"] for g in q["completed"]} |
        {g["gene"] for g in q["skipped"]}
    )
    if q["in_progress"]:
        all_genes.add(q["in_progress"]["gene"])

    if gene.upper() in {g.upper() for g in all_genes}:
        return f"Gene '{gene}' already in queue/completed/skipped — skipping duplicate."

    q["queue"].append({
        "gene": gene,
        "source": source,
        "priority": priority,
        "added": datetime.datetime.now().isoformat(),
    })

    # Sort: high priority first
    priority_order = {"high": 0, "normal": 1, "low": 2}
    q["queue"].sort(key=lambda x: priority_order.get(x.get("priority", "normal"), 1))
    q["stats"]["genes_queued"] = len(q["queue"])
    _save_queue(q)

    return (
        f"Added '{gene}' to queue (priority: {priority}, source: {source}).\n"
        f"Queue size: {len(q['queue'])} genes waiting."
    )


def complete_step(*args, **kwargs) -> str:
    """
    Mark a pipeline step as done for the current gene.

    Args:
        step: Pipeline step name (discover/profile/analyze/translate/compare/annotate/hypothesize)
    """
    step = ""
    if args:
        step = str(args[0]).strip().lower()
    if not step:
        for key in ("step", "name", "phase"):
            if key in kwargs:
                step = str(kwargs[key]).strip().lower()
                break
    if not step:
        return f"[ERROR] Usage: complete_step('profile'). Valid steps: {', '.join(PIPELINE_STEPS)}"

    q = _load_queue()
    if not q["in_progress"]:
        return "[ERROR] No gene in progress. Call next_gene() first."

    gene = q["in_progress"]["gene"]
    done = q["in_progress"].setdefault("steps_done", [])

    if step not in PIPELINE_STEPS:
        # Qwen sometimes passes gene name instead of step name — auto-detect
        if q["in_progress"] and step == q["in_progress"]["gene"].lower():
            remaining = [s for s in PIPELINE_STEPS if s not in done]
            if remaining:
                step = remaining[0]  # auto-pick next undone step
            else:
                return f"All steps already done for {gene}. Call complete_gene()."
        else:
            # Try fuzzy match (e.g. "profiling" → "profile", "analysis" → "analyze")
            for ps in PIPELINE_STEPS:
                if ps.startswith(step[:4]) or step.startswith(ps[:4]):
                    step = ps
                    break
            else:
                return f"[ERROR] Unknown step '{step}'. Valid: {', '.join(PIPELINE_STEPS)}"

    if step not in done:
        done.append(step)

    remaining = [s for s in PIPELINE_STEPS if s not in done]
    _save_queue(q)

    if not remaining:
        return (
            f"ALL STEPS COMPLETE for {gene}! 🎉\n"
            f"Call complete_gene() to finalize and move to next gene."
        )

    next_step = remaining[0]
    return (
        f"Step '{step}' done for {gene}.\n"
        f"Progress: {len(done)}/{len(PIPELINE_STEPS)} steps\n"
        f"Done: {', '.join(done)}\n"
        f"Next: {next_step}\n"
        f"{_step_instructions(next_step, gene)}"
    )


def complete_gene(*args, **kwargs) -> str:
    """
    Finalize the current gene and move it to completed list.
    Call this after all pipeline steps are done (or to skip remaining steps).
    """
    q = _load_queue()
    if not q["in_progress"]:
        return "[ERROR] No gene in progress."

    gene_data = q["in_progress"]
    gene_data["finished"] = datetime.datetime.now().isoformat()
    q["completed"].append(gene_data)
    q["in_progress"] = None
    q["stats"]["genes_completed"] = len(q["completed"])
    _save_queue(q)

    return (
        f"Gene '{gene_data['gene']}' COMPLETED.\n"
        f"Steps done: {', '.join(gene_data.get('steps_done', []))}\n"
        f"Total genes completed: {len(q['completed'])}\n"
        f"Queue remaining: {len(q['queue'])}\n\n"
        f"Call next_gene() to start the next one!"
    )


def skip_gene(*args, **kwargs) -> str:
    """
    Skip the current gene (e.g. well-studied, not human, database error).

    Args:
        reason: Why it's being skipped
    """
    reason = ""
    if args:
        reason = str(args[0])
    if not reason:
        for key in ("reason", "why", "note"):
            if key in kwargs:
                reason = str(kwargs[key])
                break

    q = _load_queue()
    if not q["in_progress"]:
        return "[ERROR] No gene in progress."

    gene = q["in_progress"]["gene"]
    q["skipped"].append({
        "gene": gene,
        "reason": reason,
        "skipped_at": datetime.datetime.now().isoformat(),
    })
    q["in_progress"] = None
    q["stats"]["genes_skipped"] = len(q["skipped"])
    _save_queue(q)

    return (
        f"Gene '{gene}' SKIPPED: {reason}\n"
        f"Call next_gene() for the next one."
    )


def advance_seed(*args, **kwargs) -> str:
    """
    Move to the next seed prefix family for gene discovery.
    Call this after searching a seed prefix and adding results to queue.
    """
    q = _load_queue()
    idx = q.get("seed_index", 0)
    q["seed_index"] = idx + 1
    _save_queue(q)

    if idx + 1 < len(SEED_PREFIXES):
        next_prefix = SEED_PREFIXES[idx + 1]
        return (
            f"Seed advanced: {SEED_PREFIXES[idx]} → {next_prefix}\n"
            f"Progress: {idx + 1}/{len(SEED_PREFIXES)} seed families searched.\n"
            f"Next: ncbi_search('{next_prefix}', db='gene', max_results=5)"
        )
    return f"All {len(SEED_PREFIXES)} seed families searched!"


def queue_status(*args, **kwargs) -> str:
    """Show the current state of the gene research queue and pipeline."""
    q = _load_queue()

    lines = ["═══ GENE QUEUE STATUS ═══"]

    # Current gene
    if q["in_progress"]:
        gene = q["in_progress"]["gene"]
        done = q["in_progress"].get("steps_done", [])
        remaining = [s for s in PIPELINE_STEPS if s not in done]
        progress_bar = "".join(["█" if s in done else "░" for s in PIPELINE_STEPS])
        lines.append(f"\n🔬 Current: {gene} [{progress_bar}] {len(done)}/{len(PIPELINE_STEPS)}")
        lines.append(f"   Done: {', '.join(done) if done else 'none'}")
        if remaining:
            lines.append(f"   Next: {remaining[0]}")
    else:
        lines.append("\n⏸️  No gene in progress")

    # Queue
    lines.append(f"\n📋 Queue: {len(q['queue'])} genes waiting")
    for entry in q["queue"][:10]:
        lines.append(f"   • {entry['gene']} ({entry.get('priority', 'normal')})")
    if len(q["queue"]) > 10:
        lines.append(f"   ... and {len(q['queue']) - 10} more")

    # Stats
    lines.append(f"\n📊 Stats:")
    lines.append(f"   Completed: {len(q['completed'])}")
    lines.append(f"   Skipped: {len(q['skipped'])}")
    lines.append(f"   Seed progress: {q.get('seed_index', 0)}/{len(SEED_PREFIXES)} families")

    # Last 5 completed
    if q["completed"]:
        lines.append(f"\n✅ Recently completed:")
        for g in q["completed"][-5:]:
            lines.append(f"   • {g['gene']} ({len(g.get('steps_done', []))} steps)")

    return "\n".join(lines)


def hypothesize(*args, **kwargs) -> str:
    """
    Generate and save a function hypothesis for the current gene.
    This is the final pipeline step — synthesize everything you learned
    into a hypothesis about what this gene does.

    Args:
        hypothesis: Your hypothesis about the gene's function
        evidence: Key evidence supporting it (BLAST hits, domains, motifs...)
        confidence: low / medium / high
    """
    from tools.findings import save_finding

    hypothesis = ""
    if args:
        hypothesis = str(args[0]).strip()
    if not hypothesis:
        for key in ("hypothesis", "description", "text", "title"):
            if key in kwargs:
                hypothesis = str(kwargs[key]).strip()
                break

    evidence = ""
    if len(args) >= 2:
        evidence = str(args[1]).strip()
    elif "evidence" in kwargs:
        evidence = str(kwargs["evidence"]).strip()

    confidence = "medium"
    if len(args) >= 3:
        confidence = str(args[2]).strip().lower()
    elif "confidence" in kwargs:
        confidence = str(kwargs["confidence"]).strip().lower()

    # Get current gene from queue
    q = _load_queue()
    gene = "unknown"
    if q["in_progress"]:
        gene = q["in_progress"]["gene"]

    if not hypothesis:
        return (
            f"[ERROR] Usage: hypothesize('This gene likely functions as a membrane transporter', "
            f"evidence='BLAST hits to SLC family, 7 TM domains found', confidence='medium')\n"
            f"Current gene: {gene}"
        )

    # Save as a finding with hypothesis tag
    title = f"{gene} - Function Hypothesis [{confidence}]"
    description = f"HYPOTHESIS: {hypothesis}"
    result = save_finding(title=title, description=description, evidence=evidence)

    # Also mark hypothesize step as done
    complete_step("hypothesize")

    return f"{result}\nHypothesis recorded for {gene} (confidence: {confidence}).\nCall complete_gene() or next_gene() to continue."


def _step_instructions(step: str, gene: str) -> str:
    """Return concrete tool call examples for each pipeline step."""
    instructions = {
        "discover": (
            f"→ DISCOVER: Confirm {gene} is understudied.\n"
            f"  TOOL: gene_info('{gene}')\n"
            f"  If well-studied, call skip_gene('well-studied gene')."
        ),
        "profile": (
            f"→ PROFILE: Fetch the mRNA/protein sequence.\n"
            f"  TOOL: ncbi_search('{gene}', db='nucleotide', max_results=3)\n"
            f"  Then: ncbi_fetch('NM_XXXXXX', db='nucleotide')\n"
            f"  After: complete_step('profile')"
        ),
        "analyze": (
            f"→ ANALYZE: Examine the sequence composition.\n"
            f"  TOOL: analyze_sequence('{gene}')\n"
            f"  After: complete_step('analyze')"
        ),
        "translate": (
            f"→ TRANSLATE: Get the protein sequence.\n"
            f"  TOOL: translate_sequence('{gene}')\n"
            f"  Or: uniprot_fetch('{gene}')\n"
            f"  After: complete_step('translate')"
        ),
        "compare": (
            f"→ COMPARE: Find homologs via BLAST.\n"
            f"  TOOL: blast_search('{gene}', db='nt', evalue=0.01)\n"
            f"  After: complete_step('compare')"
        ),
        "annotate": (
            f"→ ANNOTATE: Check UniProt for known domains/functions.\n"
            f"  TOOL: uniprot_search('{gene}')\n"
            f"  Then: save_finding(title='{gene} - Analysis', description='...', evidence='...')\n"
            f"  After: complete_step('annotate')"
        ),
        "hypothesize": (
            f"→ HYPOTHESIZE: What does this gene do? Synthesize all evidence.\n"
            f"  TOOL: hypothesize('This gene likely functions as...', evidence='BLAST hits, domains, motifs...', confidence='medium')\n"
            f"  This will auto-save the finding and complete the step."
        ),
    }
    return instructions.get(step, f"→ {step} for {gene}")
