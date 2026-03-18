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


def _is_pseudogene(gene_name: str, description: str = "") -> bool:
    """Check if a gene is a pseudogene, withdrawn, or otherwise non-protein-coding.

    Detects:
    - Names ending in P, P1, P2... (e.g. C19orf48P, C11orf58P1)
    - Names ending in B then P (e.g. C10orf88B → pseudogene in description)
    - Description containing 'pseudogene' or 'withdrawn'
    """
    import re
    name = gene_name.strip().upper()

    # Name ends with P or P+digits (C19orf48P, C11orf98P1, C11orf98P2...)
    if re.search(r'P\d*$', name):
        # But NOT genes where P is part of the real name (e.g. TSBP1, VOPP1)
        # Pseudogene pattern: CXorfNNP, CXorfNNBP, FAMxxxP, etc.
        if re.search(r'(orf\d+|FAM\d+|LINC\d+)B?P\d*$', name, re.IGNORECASE):
            return True

    # Description says pseudogene or withdrawn
    desc_lower = description.lower()
    if 'pseudogene' in desc_lower or 'pseudo gene' in desc_lower:
        return True
    if 'withdrawn' in desc_lower or 'discontinued' in desc_lower:
        return True

    return False


def _has_finding_on_disk(gene_name: str) -> bool:
    """Check if a specific gene has at least one finding file on disk."""
    from config import FINDINGS_DIR
    if not os.path.isdir(FINDINGS_DIR):
        return False
    gene_upper = gene_name.strip().upper()
    for fname in os.listdir(FINDINGS_DIR):
        if fname.endswith(".md") and gene_upper in fname.upper():
            return True
    return False


def _get_known_genes(q: dict) -> set:
    """Get all genes already known (with findings on disk, skipped, queued, in_progress).

    IMPORTANT: We use findings on disk as the source of truth, NOT the completed list.
    This way, if a finding is deleted (cleanup), the gene becomes available again.
    """
    known = set()
    # Skipped genes stay skipped (they were explicitly marked as non-dark)
    known.update(g["gene"].upper() for g in q.get("skipped", []))
    # NOTE: queue is NOT included in known — genes in the queue are "to do", not "done".
    # Dedup for add_to_queue() is handled separately in that function.
    # Completed genes are known (prevent re-queueing)
    known.update(g["gene"].upper() for g in q.get("completed", []))
    if q.get("in_progress"):
        known.add(q["in_progress"]["gene"].upper())

    # Findings on disk = source of truth for completed genes
    from config import FINDINGS_DIR
    import re
    # Match ALL gene families the project investigates, not just CXorf/LOC
    # Includes: C1orf-C22orf, CXorf, LOC, FAM, KIAA, TMEM, LINC, CCDC,
    #           ANKRD, LRRC, KLHL, KBTBD, SPATA, PRR, PRAMEF, ZNF, OR, etc.
    gene_re = re.compile(
        r'(C\d+orf\d+|CXorf\d+|LOC\d+|'
        r'FAM\d+[A-Z]?|KIAA\d+|TMEM\d+[A-Z]?|LINC\d+|FLJ\d+|'
        r'CCDC\d+[A-Z]?|ANKRD\d+[A-Z]?|LRRC\d+[A-Z]?|KLHL\d+|KBTBD\d+|'
        r'SPATA\d+|PRR\d+|PRAMEF\d+|ZNF\d+|OR\d+[A-Z]\d*)',
        re.IGNORECASE
    )
    if os.path.isdir(FINDINGS_DIR):
        for fname in os.listdir(FINDINGS_DIR):
            if fname.endswith(".md"):
                # findall to catch ALL gene references (some files have 2+)
                for match in gene_re.findall(fname):
                    known.add(match.upper())
    return known


def _auto_populate_queue(q: dict, batch_size: int = 50):
    """Auto-populate the queue from dark_genes_reference.tsv ONLY.

    The TSV is the single source of truth for which genes to analyze.
    No NCBI search — that was adding non-dark genes (PIEZO2, TOMM40, etc.)
    """
    known = _get_known_genes(q)
    # Also exclude genes already in the queue
    known.update(g["gene"].upper() for g in q.get("queue", []))

    ref_file = os.path.join(os.path.dirname(QUEUE_FILE), "dark_genes_reference.tsv")
    if not os.path.exists(ref_file):
        log.warning("dark_genes_reference.tsv not found — cannot auto-populate")
        return

    try:
        import csv
        with open(ref_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            added = 0
            skipped_pseudo = 0
            for row in reader:
                gene = row.get("gene_name", "").strip()
                status = row.get("status", "").strip()
                desc = row.get("description", "").strip()
                if not gene or status == "DONE":
                    continue
                if gene.upper() in known:
                    continue
                # Skip pseudogenes and withdrawn annotations
                if _is_pseudogene(gene, desc):
                    skipped_pseudo += 1
                    log.info("Skipped pseudogene/withdrawn: %s (%s)", gene, desc[:50])
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
            if skipped_pseudo > 0:
                log.info("Filtered out %d pseudogenes/withdrawn from TSV", skipped_pseudo)
            if added > 0:
                q["stats"]["genes_queued"] = len(q["queue"])
                log.info("Auto-populated %d genes from dark_genes_reference.tsv", added)
    except Exception as e:
        log.warning("Failed to read dark_genes_reference.tsv: %s", e)


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
    """Save the gene queue to disk atomically (write-to-temp + rename).
    Prevents corruption if the process crashes mid-write."""
    tmp_path = QUEUE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, QUEUE_FILE)


def next_gene(*args, **kwargs) -> str:
    """
    Get the next gene to study from the worklist.
    Returns the gene name and what pipeline steps to do.
    If the queue is empty, suggests a search to populate it.
    """
    q = _load_queue()

    # If there's a gene in progress, complete or skip it IN-PLACE
    # (no reload — avoids race condition where reload loses genes added by add_to_queue)
    if q["in_progress"]:
        prev_gene = q["in_progress"]["gene"]
        # Check if this gene has a FINDING FILE on disk (not just in known set,
        # which includes in_progress itself and would always be True)
        has_finding = _has_finding_on_disk(prev_gene)
        if has_finding:
            # Has a finding on disk — move to completed
            gene_data = q["in_progress"]
            gene_data["finished"] = datetime.datetime.now().isoformat()
            q["completed"].append(gene_data)
            q["in_progress"] = None
            q["stats"]["genes_completed"] = len(q["completed"])
            log.info("Auto-completed gene '%s' (finding exists on disk)", prev_gene)
        else:
            # No finding saved — mark as skipped
            log.warning("Gene '%s' abandoned without finding — marking as skipped", prev_gene)
            q["skipped"].append({
                "gene": prev_gene,
                "reason": "abandoned without finding (next_gene called before save_finding)",
                "skipped_at": datetime.datetime.now().isoformat(),
            })
            q["in_progress"] = None
            q["stats"]["genes_skipped"] = len(q["skipped"])
        _save_queue(q)  # save once, preserving any genes added by add_to_queue

    # Pick from queue — auto-populate if empty
    if not q["queue"]:
        _auto_populate_queue(q)
        _save_queue(q)

    if not q["queue"]:
        # Reference TSV exhausted — direct agent to seed-based discovery
        # DO NOT auto-advance seed_index here — only advance_seed() does that,
        # AFTER the agent actually searches and adds genes from the seed family.
        seed_idx = q.get("seed_index", 0)
        total_seeds = len(SEED_PREFIXES)
        total_completed = len(q.get("completed", []))

        if seed_idx < total_seeds:
            prefix = SEED_PREFIXES[seed_idx]

            # Tell the agent which genes from this family are ALREADY DONE
            # so it doesn't waste turns trying to add duplicates
            known = _get_known_genes(q)
            already_done = sorted([g for g in known if g.upper().startswith(prefix.upper())])
            if already_done:
                done_list = ", ".join(already_done[:30])
                done_note = f"\nALREADY COMPLETED for {prefix} family ({len(already_done)} genes): {done_list}\n"
                if len(already_done) > 30:
                    done_note += f"  ... and {len(already_done) - 30} more.\n"
                done_note += "Do NOT add any of these. Only add genes NOT in this list.\n"
            else:
                done_note = f"\nNo genes completed yet for {prefix} family — all results are fair game.\n"

            return (
                f"QUEUE EMPTY — discover new genes from seed family '{prefix}'!\n"
                f"Genes completed so far: {total_completed}\n"
                f"Seed progress: {seed_idx}/{total_seeds} families done\n"
                f"{done_note}\n"
                f"DO THIS NOW:\n"
                f"  1. TOOL: ncbi_search('chromosome {prefix.replace('C','').replace('orf','')} open reading frame', db='gene', max_results=10)\n"
                f"  2. Try add_to_queue('GENE_NAME') for 2-3 results that are NOT in the completed list above.\n"
                f"     If ALL are already completed → this family is DONE. Call advance_seed() then next_gene().\n"
                f"  3. As soon as ONE gene is accepted → call advance_seed() then next_gene() to START ANALYZING it.\n\n"
                f"RULE: Max 3 add_to_queue attempts per seed family. Then advance_seed().\n"
                f"DO NOT save 'project complete' findings — there are more genes to find."
            )
        else:
            # All seeds truly exhausted — suggest broader search
            from config import FINDINGS_DIR
            finding_count = len([f for f in os.listdir(FINDINGS_DIR) if f.endswith(".md")]) if os.path.isdir(FINDINGS_DIR) else 0
            return (
                f"All {total_seeds} seed families searched.\n"
                f"Total findings on disk: {finding_count}\n"
                f"Genes completed: {total_completed}\n\n"
                f"Search for more dark genes with broader queries:\n"
                f"  TOOL: ncbi_search('uncharacterized protein human', db='gene', max_results=10)\n"
                f"  TOOL: ncbi_search('hypothetical protein homo sapiens', db='gene', max_results=10)\n\n"
                f"Add any uncharacterized results with add_to_queue(), then call next_gene()."
            )

    # Pop the first gene — skip any that already have findings on disk
    known = _get_known_genes(q)
    gene_entry = None
    while q["queue"]:
        candidate = q["queue"].pop(0)
        gene_name = candidate["gene"]
        gene_desc = candidate.get("description", "")
        if gene_name.upper() in known:
            # Already done — silently skip (do NOT add to completed again)
            log.info("Auto-skipped '%s' (already has finding on disk)", gene_name)
            continue
        if _is_pseudogene(gene_name, gene_desc):
            # Pseudogene / withdrawn — skip silently
            q["skipped"].append({
                "gene": gene_name,
                "reason": "pseudogene/withdrawn — filtered automatically",
                "skipped_at": datetime.datetime.now().isoformat(),
            })
            log.info("Auto-skipped pseudogene '%s'", gene_name)
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
    return (
        f"ANALYZE: {gene}\n"
        f"Queue remaining: {len(q['queue'])}\n"
        f"Use your tools to build the best possible finding for this gene.\n"
        f"Your finding will be scored on COVERAGE, DEPTH, and INSIGHT (see scoring criteria).\n"
        f"When done, call save_finding(title, description, evidence) then next_gene()."
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

    # Reject pseudogenes and withdrawn annotations
    if _is_pseudogene(gene):
        return (
            f"[REJECTED] '{gene}' is a pseudogene or withdrawn annotation — not a protein-coding gene. "
            "Pseudogenes don't produce functional proteins. Skip it and find a real dark gene."
        )

    q = _load_queue()

    # Check if already in queue, in progress, completed, or has findings on disk
    known = _get_known_genes(q)
    # Also check current queue (not in _get_known_genes to avoid self-blocking in next_gene)
    queued_genes = {g["gene"].upper() for g in q.get("queue", [])}
    if gene.upper() in known or gene.upper() in queued_genes:
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
    Accepts an optional gene name for cases where save_finding triggers completion.
    """
    gene_name = args[0] if args else kwargs.get("gene", "")

    q = _load_queue()

    if q["in_progress"]:
        gene_data = q["in_progress"]
        gene_data["finished"] = datetime.datetime.now().isoformat()
        q["completed"].append(gene_data)
        q["in_progress"] = None
    elif gene_name:
        # Gene wasn't in queue (e.g. Qwen found it via ncbi_search)
        # Register it as completed so dashboard stays in sync
        already = {g["gene"].upper() for g in q.get("completed", [])}
        if gene_name.upper() not in already:
            q["completed"].append({
                "gene": gene_name,
                "finished": datetime.datetime.now().isoformat(),
                "steps_done": ["discover", "hypothesize"],
                "source": "auto-registered from save_finding",
            })
            gene_data = q["completed"][-1]
        else:
            return f"Gene '{gene_name}' already marked as completed."
    else:
        return "[ERROR] No gene in progress."

    q["stats"]["genes_completed"] = len(q["completed"])
    _save_queue(q)

    gene_info = gene_data if 'gene_data' in dir() else {"gene": gene_name, "steps_done": []}
    return (
        f"Gene '{gene_info.get('gene', gene_name)}' COMPLETED.\n"
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
    lines.append("\n📊 Stats:")
    lines.append(f"   Completed: {len(q['completed'])}")
    lines.append(f"   Skipped: {len(q['skipped'])}")
    lines.append(f"   Seed progress: {q.get('seed_index', 0)}/{len(SEED_PREFIXES)} families")

    # Last 5 completed
    if q["completed"]:
        lines.append("\n✅ Recently completed:")
        for g in q["completed"][-5:]:
            lines.append(f"   • {g['gene']} ({len(g.get('steps_done', []))} steps)")

    return "\n".join(lines)


def gene_status(*args, **kwargs) -> str:
    """
    Show comprehensive project status: how many genes are DONE vs TODO
    in dark_genes_reference.tsv, synced with actual findings on disk.
    Also auto-syncs the TSV status column with findings on disk.
    """
    import csv
    from config import FINDINGS_DIR

    ref_file = os.path.join(os.path.dirname(QUEUE_FILE), "dark_genes_reference.tsv")
    if not os.path.exists(ref_file):
        return "[ERROR] dark_genes_reference.tsv not found."

    # Get genes with findings on disk (source of truth)
    import re as _re
    gene_re = _re.compile(
        r'(C\d+orf\d+|CXorf\d+|LOC\d+|'
        r'FAM\d+[A-Z]?|KIAA\d+|TMEM\d+[A-Z]?|LINC\d+|FLJ\d+|'
        r'CCDC\d+[A-Z]?|ANKRD\d+[A-Z]?|LRRC\d+[A-Z]?|KLHL\d+|KBTBD\d+|'
        r'SPATA\d+|PRR\d+|PRAMEF\d+|ZNF\d+|OR\d+[A-Z]\d*)',
        _re.IGNORECASE
    )
    disk_genes = set()
    if os.path.isdir(FINDINGS_DIR):
        for fname in os.listdir(FINDINGS_DIR):
            if fname.endswith('.md'):
                for m in gene_re.findall(fname):
                    disk_genes.add(m.upper())

    # Read TSV and auto-sync status
    rows = []
    synced = 0
    with open(ref_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fieldnames = reader.fieldnames
        for row in reader:
            gene = row.get('gene_name', '').strip()
            if gene.upper() in disk_genes and row.get('status') == 'TODO':
                row['status'] = 'DONE'
                synced += 1
            rows.append(row)

    # Write back if anything changed
    if synced > 0:
        with open(ref_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

    done = [r for r in rows if r.get('status') == 'DONE']
    todo = [r for r in rows if r.get('status') == 'TODO']
    pseudo_todo = [r for r in todo if _is_pseudogene(r.get('gene_name', ''), r.get('description', ''))]
    real_todo = [r for r in todo if not _is_pseudogene(r.get('gene_name', ''), r.get('description', ''))]

    # Group TODO by chromosome
    chr_groups = {}
    for r in real_todo:
        chrom = r.get('chromosome', '?')
        chr_groups.setdefault(chrom, []).append(r.get('gene_name', ''))

    q = _load_queue()
    seed_idx = q.get("seed_index", 0)

    lines = [
        "PROJECT STATUS — dark_genes_reference.tsv",
        f"  DONE:  {len(done)}/{len(rows)} genes ({len(done)/len(rows)*100:.1f}%)",
        f"  TODO:  {len(real_todo)} real genes + {len(pseudo_todo)} pseudogenes (will be skipped)",
        f"  Findings on disk: {len(disk_genes)}",
        f"  Seed families: {seed_idx}/{len(SEED_PREFIXES)} searched",
    ]
    if synced > 0:
        lines.append(f"  (auto-synced {synced} genes from TODO->DONE)")

    # Show next 10 TODO genes
    lines.append(f"\n  NEXT TODO genes ({len(real_todo)} remaining):")
    for r in real_todo[:10]:
        lines.append(f"    - {r.get('gene_name')} ({r.get('chromosome', '?')}) {r.get('description', '')[:40]}")
    if len(real_todo) > 10:
        lines.append(f"    ... and {len(real_todo) - 10} more")

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
            "→ HYPOTHESIZE: What does this gene do? Synthesize all evidence.\n"
            "  TOOL: hypothesize('This gene likely functions as...', evidence='BLAST hits, domains, motifs...', confidence='medium')\n"
            "  This will auto-save the finding and complete the step."
        ),
    }
    return instructions.get(step, f"→ {step} for {gene}")
