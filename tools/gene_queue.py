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
# Estimated gene counts per family (for progress tracking)
SEED_PREFIXES = [
    # --- Phase 1: Chromosome ORFs (~250-300 genes) ---
    "C1orf", "C2orf", "C3orf", "C4orf", "C5orf", "C6orf", "C7orf",
    "C8orf", "C9orf", "C10orf", "C11orf", "C12orf", "C13orf", "C14orf",
    "C15orf", "C16orf", "C17orf", "C18orf", "C19orf", "C20orf", "C21orf",
    "C22orf", "CXorf",
    # --- Phase 2: Named dark gene families (~600 genes) ---
    "FAM",      # ~150-200 genes — family with sequence similarity
    "KIAA",     # ~20-30 genes — Kazusa cDNA project remnants
    "TMEM",     # ~200-250 genes — transmembrane proteins
    "LINC",     # ~2000-4000 genes — long intergenic non-coding RNA
    "FLJ",      # ~10 genes — full-length cDNA Japan remnants
    # --- Phase 3: Structural domain families (~400 genes) ---
    "CCDC",     # ~180 genes — coiled-coil domain containing
    "ANKRD",    # ~55 genes — ankyrin repeat domain
    "LRRC",     # ~65 genes — leucine rich repeat containing
    "KLHL",     # ~42 genes — kelch-like family
    "KBTBD",    # ~9 genes — kelch repeat and BTB domain
    # --- Phase 4: Functional dark families (~500 genes) ---
    "SPATA",    # ~50 genes — spermatogenesis associated
    "PRR",      # ~35 genes — proline rich
    "PRAMEF",   # ~23 genes — PRAME family
    "NKAPD",    # ~5 genes — NF-kB activating protein dark
    # --- Phase 5: Large understudied families (~1200 genes) ---
    "ZNF",      # ~718 genes — zinc finger (many dark despite size)
    "OR",       # ~400 functional genes — olfactory receptors
    # --- Phase 6: LOC genes — the biggest pool (~4000+ dark) ---
    "LOC1000",  # split LOC into sub-ranges to avoid overwhelming NCBI
    "LOC1001",
    "LOC1002",
    "LOC1003",
    "LOC1004",
    "LOC1005",
    "LOC1006",
    "LOC1007",
    "LOC1008",
    "LOC1009",
    "LOC101",
    "LOC102",
    "LOC103",
    "LOC104",
    "LOC105",
    "LOC106",
    "LOC107",
    "LOC108",
    "LOC109",
    "LOC110",
    "LOC111",
    "LOC112",
    "LOC124",
    "LOC125",
    "LOC126",
    "LOC127",
    "LOC128",
    "LOC129",
]


def _get_known_genes(q: dict) -> set:
    """Get all genes already known (with findings on disk, skipped, queued, in_progress).

    IMPORTANT: We use findings on disk as the source of truth, NOT the completed list.
    This way, if a finding is deleted (cleanup), the gene becomes available again.
    """
    known = set()
    # Skipped genes stay skipped (they were explicitly marked as non-dark)
    known.update(g["gene"].upper() for g in q.get("skipped", []))
    known.update(g["gene"].upper() for g in q.get("queue", []))
    if q.get("in_progress"):
        known.add(q["in_progress"]["gene"].upper())

    # Findings on disk = source of truth for completed genes
    from config import FINDINGS_DIR
    import re
    gene_re = re.compile(r'\b(C\d+orf\d+|CXorf\d+|LOC\d+)\b', re.IGNORECASE)
    if os.path.isdir(FINDINGS_DIR):
        for fname in os.listdir(FINDINGS_DIR):
            if fname.endswith(".md"):
                m = gene_re.search(fname)
                if m:
                    known.add(m.group(1).upper())
    return known


def _auto_populate_queue(q: dict, batch_size: int = 10):
    """Auto-populate the queue when empty.

    Strategy:
    1. First, check dark_genes_reference.tsv for TODO genes (CXorf family)
    2. If that's exhausted, use NCBI search with wildcard for other families
    3. Always skip genes that already have findings on disk

    This prevents Qwen from having to search & add_to_queue manually,
    which it often forgets — causing it to re-analyze the same genes.
    """
    known = _get_known_genes(q)
    seed_idx = q.get("seed_index", 0)

    # --- Strategy 1: Use dark_genes_reference.tsv if available ---
    ref_file = os.path.join(os.path.dirname(QUEUE_FILE), "dark_genes_reference.tsv")
    if os.path.exists(ref_file):
        try:
            import csv
            with open(ref_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                added = 0
                for row in reader:
                    gene = row.get("gene_name", "").strip()
                    status = row.get("status", "").strip()
                    if not gene or status == "DONE":
                        continue
                    if gene.upper() in known:
                        continue
                    q["queue"].append({
                        "gene": gene,
                        "source": "dark_genes_reference.tsv",
                        "priority": "normal",
                        "added": datetime.datetime.now().isoformat(),
                    })
                    known.add(gene.upper())
                    added += 1
                    if added >= batch_size:
                        break
                if added > 0:
                    q["stats"]["genes_queued"] = len(q["queue"])
                    log.info("Auto-populated %d genes from dark_genes_reference.tsv", added)
                    return
        except Exception as e:
            log.warning("Failed to read dark_genes_reference.tsv: %s", e)

    # --- Strategy 2: NCBI search with wildcard for current seed prefix ---
    if seed_idx >= len(SEED_PREFIXES):
        return  # All seeds exhausted

    prefix = SEED_PREFIXES[seed_idx]
    try:
        from tools.ncbi import ncbi_search
        result = ncbi_search(f"{prefix}*[gene name]", db="gene", max_results=20)

        # Parse gene names — look for the original CXorf names in descriptions
        # or the current gene symbols
        import re
        # Match gene IDs and names from NCBI result format: [ID] SYMBOL — description
        symbol_pattern = re.compile(r'\[(\d+)\]\s+(\S+)\s+')
        found_genes = []
        for m in symbol_pattern.finditer(result):
            symbol = m.group(2)
            if symbol.upper() not in known:
                found_genes.append(symbol)

        added = 0
        for gene in found_genes:
            if gene.upper() in known:
                continue
            q["queue"].append({
                "gene": gene,
                "source": f"auto-populate seed {prefix}",
                "priority": "normal",
                "added": datetime.datetime.now().isoformat(),
            })
            known.add(gene.upper())
            added += 1
            if added >= batch_size:
                break

        q["seed_index"] = seed_idx + 1
        q["stats"]["genes_queued"] = len(q["queue"])
        log.info("Auto-populated %d genes from NCBI seed '%s'", added, prefix)

    except Exception as e:
        log.warning("Auto-populate NCBI failed for seed '%s': %s", prefix, e)
        q["seed_index"] = seed_idx + 1


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

    # Pick from queue — auto-populate if empty
    if not q["queue"]:
        _auto_populate_queue(q)
        _save_queue(q)

    if not q["queue"]:
        # Still empty after auto-populate — all seeds exhausted
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

    # Pop the first gene — skip any that already have findings on disk
    known = _get_known_genes(q)
    gene_entry = None
    while q["queue"]:
        candidate = q["queue"].pop(0)
        if candidate["gene"].upper() in known:
            # Already done — silently skip and move to completed
            candidate["finished"] = datetime.datetime.now().isoformat()
            candidate["steps_done"] = ["auto-skipped"]
            candidate["source"] = candidate.get("source", "unknown")
            q["completed"].append(candidate)
            log.info("Auto-skipped '%s' (already has finding on disk)", candidate["gene"])
            continue
        gene_entry = candidate
        break

    if not gene_entry:
        # All queue entries were already done — try auto-populate again
        _auto_populate_queue(q)
        _save_queue(q)
        if q["queue"]:
            gene_entry = q["queue"].pop(0)
        else:
            _save_queue(q)
            return "QUEUE EMPTY after filtering — all queued genes already completed."

    q["in_progress"] = {
        "gene": gene_entry["gene"],
        "started": datetime.datetime.now().isoformat(),
        "steps_done": [],
        "source": gene_entry.get("source", "unknown"),
    }
    q["stats"]["genes_queued"] = len(q["queue"])
    q["stats"]["genes_completed"] = len(q["completed"])
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

    # Check if already in queue, in progress, completed, or has findings on disk
    known = _get_known_genes(q)
    if gene.upper() in known:
        return f"Gene '{gene}' already in queue/completed/skipped/has findings — skipping duplicate."

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
        for key in ("step", "step_name", "name", "phase"):
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
