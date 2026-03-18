"""
Gene filters — pseudogene detection, finding checks, and known gene tracking.
"""

import os
import re


def _is_pseudogene(gene_name: str, description: str = "") -> bool:
    """Check if a gene is a pseudogene, withdrawn, or otherwise non-protein-coding.

    Detects:
    - Names ending in P, P1, P2... (e.g. C19orf48P, C11orf58P1)
    - Names ending in B then P (e.g. C10orf88B -> pseudogene in description)
    - Description containing 'pseudogene' or 'withdrawn'
    """
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
    # Match ALL gene families the project investigates, not just CXorf/LOC
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
