"""
UniProt tools — search and fetch protein data from UniProt REST API.
"""

import os
import logging
import requests

from config import UNIPROT_BASE_URL, SEQUENCES_DIR

log = logging.getLogger("genoresearch.uniprot")


def uniprot_search(*args, query: str = "", max_results: int = 5, **kwargs) -> str:
    """
    Search UniProt for proteins.

    Args:
        query: Search terms (e.g. "BRCA1 human", "kinase cancer")
        max_results: Number of results (max 25)
    """
    # Handle Qwen's creative kwarg names
    if not query and args:
        query = str(args[0])
    if not query:
        for key in ("query", "term", "search", "q", "text", "protein", "gene", "name"):
            if key in kwargs:
                query = str(kwargs[key])
                break
    if not query:
        return "[ERROR] No query provided. Usage: uniprot_search('BRCA1 human')"
    max_results = min(max_results, 25)
    params = {
        "query": query,
        "format": "json",
        "size": max_results,
        "fields": "accession,protein_name,organism_name,length,gene_names",
    }

    try:
        resp = requests.get(f"{UNIPROT_BASE_URL}/uniprotkb/search",
                            params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] UniProt search failed: {e}"

    results = data.get("results", [])
    if not results:
        return f"No UniProt results for '{query}'"

    lines = [f"UniProt search: '{query}' — {len(results)} results"]
    for entry in results:
        acc = entry.get("primaryAccession", "?")
        name = _get_protein_name(entry)
        org = entry.get("organism", {}).get("scientificName", "?")
        length = entry.get("sequence", {}).get("length", "?")
        genes = entry.get("genes", [])
        gene_str = genes[0].get("geneName", {}).get("value", "") if genes else ""

        lines.append(f"  [{acc}] {name}")
        lines.append(f"    Organism: {org} | Gene: {gene_str} | Length: {length} aa")

    return "\n".join(lines)


def uniprot_fetch(*args, accession_id: str = "", **kwargs) -> str:
    """
    Fetch protein details and FASTA sequence from UniProt.

    Args:
        accession_id: UniProt accession (e.g. "P38398", "Q9Y6K1")
                      Also accepts NCBI protein accessions (NP_, XP_, WP_, YP_, AP_)
                      which are automatically redirected to ncbi_fetch.
    """
    # Handle Qwen's creative kwarg names
    if not accession_id and args:
        accession_id = str(args[0])
    if not accession_id:
        for key in ("accession_id", "accession", "id", "acc", "query", "protein_id"):
            if key in kwargs:
                accession_id = str(kwargs[key])
                break
    if not accession_id:
        return "[ERROR] No accession ID provided. Usage: uniprot_fetch('P38398')"
    accession_id = str(accession_id).strip()

    # Detect NCBI protein accessions and redirect
    ncbi_prefixes = ("NP_", "XP_", "WP_", "YP_", "AP_")
    if accession_id.upper().startswith(ncbi_prefixes):
        from tools.ncbi import ncbi_fetch
        return ncbi_fetch(accession_id, db="protein")

    # Detect NCBI nucleotide accessions sent here by mistake
    ncbi_nuc_prefixes = ("NM_", "NR_", "NC_", "XM_", "XR_")
    if accession_id.upper().startswith(ncbi_nuc_prefixes):
        from tools.ncbi import ncbi_fetch
        return ncbi_fetch(accession_id, db="nucleotide")

    # Fetch JSON details from UniProt
    try:
        resp = requests.get(f"{UNIPROT_BASE_URL}/uniprotkb/{accession_id}.json",
                            timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] UniProt fetch failed for '{accession_id}': {e}. Note: UniProt only accepts UniProt accessions (e.g. P38398, Q9Y6K1). For NCBI accessions (NP_, NM_), use ncbi_fetch instead."

    # Extract key info
    name = _get_protein_name(data)
    org = data.get("organism", {}).get("scientificName", "?")
    seq_info = data.get("sequence", {})
    seq_len = seq_info.get("length", "?")
    seq_val = seq_info.get("value", "")

    # Function annotations
    functions = []
    for comment in data.get("comments", []):
        if comment.get("commentType") == "FUNCTION":
            for text in comment.get("texts", []):
                functions.append(text.get("value", "")[:200])

    # Save FASTA
    fasta_path = ""
    if seq_val:
        fasta = f">{accession_id} {name} OS={org}\n"
        for i in range(0, len(seq_val), 80):
            fasta += seq_val[i:i+80] + "\n"
        fasta_path = os.path.join(SEQUENCES_DIR, f"{accession_id}.fasta")
        with open(fasta_path, "w", encoding="utf-8") as f:
            f.write(fasta)

    lines = [
        f"UniProt: {accession_id}",
        f"Name: {name}",
        f"Organism: {org}",
        f"Length: {seq_len} aa",
    ]
    if functions:
        lines.append(f"Function: {functions[0]}")
    if fasta_path:
        lines.append(f"FASTA saved: {fasta_path}")

    return "\n".join(lines)


def _get_protein_name(entry: dict) -> str:
    """Extract the recommended protein name from UniProt JSON."""
    prot = entry.get("proteinDescription", {})
    rec = prot.get("recommendedName", {})
    full = rec.get("fullName", {})
    return full.get("value", prot.get("submissionNames", [{}])[0]
                     .get("fullName", {}).get("value", "Unknown protein")
                     if prot.get("submissionNames") else "Unknown protein")
