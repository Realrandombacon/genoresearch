"""
Sequence analysis tools — local analysis of FASTA files.
No external dependencies beyond stdlib (BioPython optional).
"""

import os
import logging
from collections import Counter

from config import SEQUENCES_DIR

log = logging.getLogger("genoresearch.sequence")


def analyze_sequence(*args, filepath: str = "", **kwargs) -> str:
    """
    Analyze a FASTA sequence file — composition, length, GC content, motifs.

    Args:
        filepath: Path to .fasta file (relative to sequences dir if no sep)
    """
    # Handle Qwen's creative kwarg names
    if not filepath and args:
        filepath = str(args[0])
    if not filepath:
        for key in ("filepath", "file", "path", "fasta", "sequence", "input", "filename"):
            if key in kwargs:
                filepath = str(kwargs[key])
                break
    if not filepath:
        return "[ERROR] No filepath provided. Usage: analyze_sequence('NM_007294.4.fasta')"
    filepath = _resolve_path(filepath)

    if not os.path.exists(filepath):
        return f"[ERROR] File not found: {filepath}"

    # Guard against huge files (e.g. entire chromosomes)
    file_size = os.path.getsize(filepath)
    if file_size > 50_000_000:  # 50 MB
        return (
            f"[ERROR] File too large ({file_size / 1_000_000:.0f} MB): {os.path.basename(filepath)}\n"
            "This looks like an entire chromosome. Fetch the specific gene's mRNA instead:\n"
            "  1. Search: ncbi_search('GENE_NAME', db='nucleotide')\n"
            "  2. Fetch: ncbi_fetch('NM_XXXXX', db='nucleotide')"
        )

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


def compare_sequences(*args, file1: str = "", file2: str = "", **kwargs) -> str:
    """
    Compare two FASTA sequences — identity, length diff, composition diff.

    Args:
        file1: Path to first .fasta
        file2: Path to second .fasta
    """
    # Handle Qwen's creative kwarg names
    if args:
        if len(args) >= 2:
            file1, file2 = str(args[0]), str(args[1])
        elif len(args) == 1:
            file1 = str(args[0])
    if not file1:
        for key in ("file1", "seq1", "sequence1", "first", "input1"):
            if key in kwargs:
                file1 = str(kwargs[key])
                break
    if not file2:
        for key in ("file2", "seq2", "sequence2", "second", "input2"):
            if key in kwargs:
                file2 = str(kwargs[key])
                break
    if not file1 or not file2:
        return "[ERROR] Two filepaths required. Usage: compare_sequences('file1.fasta', 'file2.fasta')"
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
    # Sample first 10k chars for efficiency on large sequences
    sample = seq[:10000].upper()
    unique = set(sample)
    if unique <= set("ATCGN"):
        return "DNA"
    if unique <= set("AUCGN"):
        return "RNA"
    return "Protein"


def translate_sequence(*args, **kwargs) -> str:
    """
    Translate a DNA/RNA sequence to protein using the standard genetic code.
    Reads a FASTA file, translates all 3 reading frames, picks the longest ORF,
    and saves the protein as a new .protein.fasta file.
    Can translate multiple files if given file1=, file2=, etc.

    Args:
        filepath: Path to .fasta file containing DNA or RNA sequence
    """
    # Collect all filepaths from args and kwargs (Qwen sends file1=, file2=, etc.)
    filepaths = list(args)
    for key in sorted(kwargs.keys()):
        val = str(kwargs[key])
        if val.strip():
            filepaths.append(val)

    if not filepaths:
        return "[ERROR] No filepath provided. Usage: translate_sequence('file.fasta')"

    # If multiple files, translate each and combine results
    if len(filepaths) > 1:
        results = []
        for fp in filepaths:
            results.append(_translate_single(fp))
        return "\n\n---\n\n".join(results)

    return _translate_single(filepaths[0])


def _translate_single(filepath: str) -> str:
    """Translate a single FASTA file to protein."""
    filepath = _resolve_path(str(filepath).strip())

    if not os.path.exists(filepath):
        return f"[ERROR] File not found: {filepath}"

    header, sequence = _read_fasta(filepath)
    if not sequence:
        return f"[ERROR] Empty or invalid FASTA: {filepath}"

    seq_type = _detect_type(sequence)
    if seq_type == "Protein":
        return f"[ERROR] {os.path.basename(filepath)} is already a protein sequence — nothing to translate."

    # Convert RNA to DNA for uniform codon table
    dna = sequence.replace("U", "T")

    # Translate all 3 forward reading frames
    frames = {}
    for frame in range(3):
        protein = _translate_dna(dna[frame:])
        frames[frame] = protein

    # Find the longest ORF (M...* or M...end) in any frame
    best_orf = ""
    best_frame = 0
    for frame, protein in frames.items():
        orfs = _extract_orfs(protein)
        for orf in orfs:
            if len(orf) > len(best_orf):
                best_orf = orf
                best_frame = frame

    # If no ORF with M found, use frame 0 full translation
    if not best_orf:
        best_orf = frames[0].replace("*", "")
        best_frame = 0

    # Save translated protein
    base = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(SEQUENCES_DIR, f"{base}.protein.fasta")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f">{base} translated frame={best_frame} len={len(best_orf)}aa src={header[:80]}\n")
        for i in range(0, len(best_orf), 80):
            f.write(best_orf[i:i+80] + "\n")

    lines = [
        f"Translation: {os.path.basename(filepath)}",
        f"Source: {seq_type}, {len(dna)} bp",
        f"Best ORF: frame +{best_frame}, {len(best_orf)} aa",
        f"Frame translations: {', '.join(f'+{f}: {len(p.replace(chr(42), str()))} aa' for f, p in frames.items())}",
        f"Protein saved: {out_path}",
    ]

    # Quick protein composition
    if best_orf:
        comp = Counter(best_orf)
        charged = sum(comp.get(aa, 0) for aa in "DEKRH")
        hydrophobic = sum(comp.get(aa, 0) for aa in "AVILMFYW")
        lines.append(f"Charged: {charged} ({charged/max(len(best_orf),1):.1%}), Hydrophobic: {hydrophobic} ({hydrophobic/max(len(best_orf),1):.1%})")

    return "\n".join(lines)


# Standard genetic code
_CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def _translate_dna(dna: str) -> str:
    """Translate a DNA string to protein using standard genetic code."""
    protein = []
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i+3]
        if len(codon) == 3:
            protein.append(_CODON_TABLE.get(codon, "X"))
    return "".join(protein)


def _extract_orfs(protein: str) -> list[str]:
    """Extract all ORFs (M to stop or end) from a translated protein string."""
    orfs = []
    i = 0
    while i < len(protein):
        if protein[i] == "M":
            # Find next stop codon
            stop = protein.find("*", i)
            if stop == -1:
                orfs.append(protein[i:])
            else:
                orfs.append(protein[i:stop])
            i = (stop + 1) if stop != -1 else len(protein)
        else:
            i += 1
    return orfs


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
