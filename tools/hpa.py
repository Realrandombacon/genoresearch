"""
Human Protein Atlas tools -- tissue expression and subcellular localization.
Uses the HPA REST API (requires Ensembl ID resolution first).
"""

import logging
import requests

log = logging.getLogger("genoresearch.hpa")

HPA_BASE = "https://www.proteinatlas.org"


def _resolve_ensembl_id(gene: str) -> str:
    """Resolve gene symbol to Ensembl gene ID via MyGene.info."""
    try:
        url = f"https://mygene.info/v3/query?q=symbol:{gene}&species=human&fields=ensembl.gene&size=1"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if hits:
            ensembl = hits[0].get("ensembl", {})
            if isinstance(ensembl, list):
                ensembl = ensembl[0]
            return ensembl.get("gene", "")
    except Exception:
        pass
    return ""


def hpa_expression(*args, gene: str = "", **kwargs) -> str:
    """
    Get tissue expression and subcellular localization from Human Protein Atlas.

    Args:
        gene: Gene symbol (e.g. "TP53", "C2orf69", "BRCA1")
    """
    if not gene and args:
        gene = str(args[0])
    if not gene:
        for key in ("gene", "gene_name", "name", "query", "symbol", "protein"):
            if key in kwargs:
                gene = str(kwargs[key])
                break
    if not gene:
        return "[ERROR] Usage: hpa_expression('TP53')"

    gene = gene.strip().upper()

    # Resolve to Ensembl ID
    ensembl_id = _resolve_ensembl_id(gene)
    if not ensembl_id:
        return f"Human Protein Atlas: Could not resolve '{gene}' to Ensembl ID. Gene may not exist or have a different symbol."

    try:
        url = f"{HPA_BASE}/{ensembl_id}.json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError:
        return f"Human Protein Atlas: No data for '{gene}' ({ensembl_id}). Gene may not be in HPA database."
    except Exception as e:
        return f"[ERROR] HPA lookup failed for '{gene}': {e}"

    # Handle list response (HPA returns a list)
    if isinstance(data, list):
        if not data:
            return f"Human Protein Atlas: No data for '{gene}'"
        data = data[0]

    lines = [f"Human Protein Atlas -- {gene} ({ensembl_id}):"]

    # Gene summary
    gene_desc = data.get("Gene description", "")
    uniprot = data.get("Uniprot", "")
    protein_class = data.get("Protein class", "")
    biological_process = data.get("Biological process", "")
    molecular_function = data.get("Molecular function", "")
    disease_involvement = data.get("Disease involvement", "")
    subcell = data.get("Subcellular location", "")

    if gene_desc:
        lines.append(f"  Description: {gene_desc}")
    if uniprot:
        u = uniprot if isinstance(uniprot, str) else ", ".join(uniprot[:3])
        lines.append(f"  UniProt: {u}")
    if protein_class:
        pc = protein_class if isinstance(protein_class, str) else ", ".join(protein_class[:5])
        lines.append(f"  Protein class: {pc}")
    if biological_process:
        bp = biological_process if isinstance(biological_process, str) else ", ".join(biological_process[:5])
        lines.append(f"  Biological process: {bp}")
    if molecular_function:
        mf = molecular_function if isinstance(molecular_function, str) else ", ".join(molecular_function[:5])
        lines.append(f"  Molecular function: {mf}")
    if disease_involvement:
        di = disease_involvement if isinstance(disease_involvement, str) else ", ".join(disease_involvement[:5])
        lines.append(f"  Disease involvement: {di}")
    if subcell:
        sc = subcell if isinstance(subcell, str) else ", ".join(subcell[:5])
        lines.append(f"  Subcellular location: {sc}")

    # RNA tissue specificity
    rna_spec = data.get("RNA tissue specificity", "")
    rna_dist = data.get("RNA tissue distribution", "")
    if rna_spec:
        lines.append(f"  RNA tissue specificity: {rna_spec}")
    if rna_dist:
        lines.append(f"  RNA tissue distribution: {rna_dist}")

    # RNA tissue-specific nTPM (dict format)
    rna_ts = data.get("RNA tissue specific nTPM", None)
    if rna_ts and isinstance(rna_ts, dict):
        tissue_vals = sorted(rna_ts.items(), key=lambda x: float(x[1]) if x[1] else 0, reverse=True)
        if tissue_vals:
            lines.append("  Top tissue expression (nTPM):")
            for tissue, val in tissue_vals[:8]:
                lines.append(f"    {tissue}: {val}")

    # RNA cancer specificity
    cancer_spec = data.get("RNA cancer specificity", "")
    if cancer_spec:
        lines.append(f"  RNA cancer specificity: {cancer_spec}")

    # Blood cell specificity
    blood_spec = data.get("RNA blood cell specificity", "")
    if blood_spec:
        lines.append(f"  Blood cell specificity: {blood_spec}")

    # Single cell type specificity
    sc_spec = data.get("RNA single cell type specificity", "")
    if sc_spec:
        lines.append(f"  Single cell type specificity: {sc_spec}")

    if len(lines) <= 1:
        lines.append("  (Minimal data available -- gene may be poorly characterized)")

    return "\n".join(lines)
