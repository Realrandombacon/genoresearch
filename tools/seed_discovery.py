"""
Seed discovery — seed prefix families and seed advancement for gene discovery.
"""

# Seed families — systematic starting points for dark gene discovery
# These are known to contain many uncharacterized genes
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


def advance_seed(*args, **kwargs) -> str:
    """Move to the next seed prefix family for gene discovery."""
    from tools.gene_queue import _load_queue, _save_queue

    q = _load_queue()
    idx = q.get("seed_index", 0)
    q["seed_index"] = idx + 1
    _save_queue(q)

    if idx + 1 < len(SEED_PREFIXES):
        next_prefix = SEED_PREFIXES[idx + 1]
        return (
            f"Seed advanced: {SEED_PREFIXES[idx]} -> {next_prefix}\n"
            f"Progress: {idx + 1}/{len(SEED_PREFIXES)} seed families searched.\n"
            f"Next: ncbi_search('{next_prefix}', db='gene', max_results=5)"
        )
    return f"All {len(SEED_PREFIXES)} seed families searched!"
