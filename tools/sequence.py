"""
Sequence analysis tools — local analysis of FASTA files.
No external dependencies beyond stdlib (BioPython optional).
"""

import os
import logging
from collections import Counter

from config import SEQUENCES_DIR

log = logging.getLogger("genoresearch.sequence")


def analyze_sequence(filepath: str) -> str:
    """
    Analyze a FASTA sequence file — composition, length, GC content, motifs.

    Args:
        filepath: Path to .fasta file (relative to sequences dir if no sep)
    """
    filepath = _resolve_path(filepath)

    if not os.path.exists(filepath):
        return f"[ERROR] File not found: {filepath}"

    header, sequence = _read_fasta(filepath)
    if not sequence:
        return f"[ERROR] Empty or invalid FASTA: {filepath}"

    seq_type = _detect_type(sequence)
    length = len(sequence)
    composition = Counter(sequence)

    lines = [
        f"Sequence analysis: {os.path.basename(filepath)}",
        f"Header: {header[:150]}",
        f"Type: {seq_type}",
        f"Length: {length} {'bp' if seq_type == 'DNA' else 'aa'}",
        f"Composition: {dict(composition.most_common(10))}",
    ]

    if seq_type == "DNA":
        gc = (composition.get("G", 0) + composition.get("C", 0)) / max(length, 1)
        lines.append(f"GC content: {gc:.1%}")

        # Simple motif scan
        motifs = _scan_motifs_dna(sequence)
        if motifs:
            lines.append("Notable motifs found:")
            for m in motifs[:5]:
                lines.append(f"  - {m}")

    elif seq_type == "Protein":
        # Amino acid properties
        charged = sum(composition.get(aa, 0) for aa in "DEKRH")
        hydrophobic = sum(composition.get(aa, 0) for aa in "AVILMFYW")
        lines.append(f"Charged residues: {charged} ({charged/max(length,1):.1%})")
        lines.append(f"Hydrophobic residues: {hydrophobic} ({hydrophobic/max(length,1):.1%})")

    return "\n".join(lines)


def compare_sequences(file1: str, file2: str) -> str:
    """
    Compare two FASTA sequences — identity, length diff, composition diff.

    Args:
        file1: Path to first .fasta
        file2: Path to second .fasta
    """
    file1 = _resolve_path(file1)
    file2 = _resolve_path(file2)

    for fp in [file1, file2]:
        if not os.path.exists(fp):
            return f"[ERROR] File not found: {fp}"

    h1, s1 = _read_fasta(file1)
    h2, s2 = _read_fasta(file2)

    if not s1 or not s2:
        return "[ERROR] One or both sequences are empty"

    t1 = _detect_type(s1)
    t2 = _detect_type(s2)

    lines = [
        f"Comparing: {os.path.basename(file1)} vs {os.path.basename(file2)}",
        f"  Seq1: {len(s1)} {'bp' if t1 == 'DNA' else 'aa'} ({t1})",
        f"  Seq2: {len(s2)} {'bp' if t2 == 'DNA' else 'aa'} ({t2})",
        f"  Length ratio: {min(len(s1), len(s2)) / max(len(s1), len(s2)):.2%}",
    ]

    # Simple identity for same-length or aligned sequences
    if abs(len(s1) - len(s2)) / max(len(s1), len(s2)) < 0.1:
        min_len = min(len(s1), len(s2))
        matches = sum(1 for a, b in zip(s1[:min_len], s2[:min_len]) if a == b)
        identity = matches / min_len
        lines.append(f"  Pairwise identity (ungapped): {identity:.1%}")
    else:
        lines.append("  Sequences differ too much in length for simple alignment")

    # Composition comparison
    c1 = Counter(s1)
    c2 = Counter(s2)
    all_chars = sorted(set(c1.keys()) | set(c2.keys()))
    diffs = []
    for ch in all_chars:
        f1 = c1.get(ch, 0) / len(s1)
        f2 = c2.get(ch, 0) / len(s2)
        if abs(f1 - f2) > 0.02:
            diffs.append(f"{ch}: {f1:.1%} vs {f2:.1%}")
    if diffs:
        lines.append("  Composition differences (>2%):")
        for d in diffs[:8]:
            lines.append(f"    {d}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_path(filepath: str) -> str:
    """Resolve relative paths against sequences directory."""
    if os.path.sep not in filepath and "/" not in filepath:
        return os.path.join(SEQUENCES_DIR, filepath)
    return filepath


def _read_fasta(filepath: str) -> tuple[str, str]:
    """Read a FASTA file, return (header, sequence)."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header = ""
    seq_parts = []
    for line in lines:
        line = line.strip()
        if line.startswith(">"):
            header = line[1:]
        elif line:
            seq_parts.append(line.upper())
    return header, "".join(seq_parts)


def _detect_type(seq: str) -> str:
    """Detect if sequence is DNA, RNA, or Protein."""
    unique = set(seq.upper())
    if unique <= set("ATCGN"):
        return "DNA"
    if unique <= set("AUCGN"):
        return "RNA"
    return "Protein"


def _scan_motifs_dna(seq: str) -> list[str]:
    """Scan for common DNA motifs."""
    motifs_found = []
    known = {
        "TATAAA": "TATA box (promoter)",
        "AATAAA": "Polyadenylation signal",
        "CCAAT": "CCAAT box (promoter)",
        "GCCGCC": "Kozak-like (translation start context)",
        "GAATTC": "EcoRI restriction site",
        "GGATCC": "BamHI restriction site",
        "AAGCTT": "HindIII restriction site",
    }
    for motif, desc in known.items():
        count = seq.count(motif)
        if count > 0:
            motifs_found.append(f"{desc} ({motif}): {count}x")
    return motifs_found
