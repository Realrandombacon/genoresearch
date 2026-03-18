"""
AlphaFold tools — predicted protein structure data from AlphaFold DB.
Uses the AlphaFold REST API (EBI).
"""

import logging
import requests

log = logging.getLogger("genoresearch.alphafold")

AF_BASE = "https://alphafold.ebi.ac.uk/api"


def alphafold_structure(*args, accession_id: str = "", **kwargs) -> str:
    """
    Get AlphaFold predicted structure info for a UniProt accession.
    Returns confidence scores (pLDDT), structural summary, and download links.

    Args:
        accession_id: UniProt accession (e.g. "Q9H3H3", "P38398")
    """
    if not accession_id and args:
        accession_id = str(args[0])
    if not accession_id:
        for key in ("accession_id", "accession", "id", "acc", "uniprot", "protein"):
            if key in kwargs:
                accession_id = str(kwargs[key])
                break
    if not accession_id:
        return "[ERROR] Usage: alphafold_structure('Q9H3H3')"

    accession_id = accession_id.strip()

    # Get prediction metadata
    try:
        url = f"{AF_BASE}/prediction/{accession_id}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            return f"AlphaFold: No predicted structure for '{accession_id}'. Protein may not be in AlphaFold DB."
        return f"[ERROR] AlphaFold lookup failed for '{accession_id}': {e}"
    except Exception as e:
        return f"[ERROR] AlphaFold lookup failed for '{accession_id}': {e}"

    if isinstance(data, list):
        if not data:
            return f"AlphaFold: No structure for '{accession_id}'"
        data = data[0]

    lines = [f"AlphaFold predicted structure — {accession_id}:"]

    entry_id = data.get("entryId", "?")
    gene = data.get("gene", "?")
    organism = data.get("organismScientificName", "?")
    uniprot_desc = data.get("uniprotDescription", "?")
    uniprot_start = data.get("uniprotStart", "?")
    uniprot_end = data.get("uniprotEnd", "?")

    lines.append(f"  Entry: {entry_id}")
    lines.append(f"  Gene: {gene} | Organism: {organism}")
    lines.append(f"  Description: {uniprot_desc}")
    lines.append(f"  Modeled range: {uniprot_start}-{uniprot_end}")

    # Confidence info
    plddt = data.get("globalMetricValue", None)
    if plddt is not None:
        confidence = "Very high" if plddt > 90 else "High" if plddt > 70 else "Medium" if plddt > 50 else "Low"
        lines.append(f"  Global pLDDT: {plddt:.1f} ({confidence} confidence)")
        lines.append("    >90=very high, 70-90=confident, 50-70=low, <50=disordered")

    # Structural features from pLDDT distribution
    cif_url = data.get("cifUrl", "")
    pdb_url = data.get("pdbUrl", "")

    if pdb_url:
        lines.append(f"  PDB file: {pdb_url}")
    if cif_url:
        lines.append(f"  mmCIF file: {cif_url}")

    # Try to get per-residue pLDDT for structural insights
    try:
        summary_url = data.get("amAnnotationsUrl", "")
        if summary_url:
            ann_resp = requests.get(summary_url, timeout=15)
            if ann_resp.ok:
                ann_data = ann_resp.json()
                if ann_data:
                    lines.append(f"  Annotations available: {len(ann_data)} features")
    except Exception:
        pass  # Non-critical

    # Interpretation for dark genes
    if plddt is not None:
        lines.append("\n  Interpretation for dark gene research:")
        if plddt > 70:
            lines.append("    -> Well-folded protein — likely has stable 3D structure")
            lines.append("    -> Good candidate for structural comparison with known folds")
        elif plddt > 50:
            lines.append("    -> Partially structured — may have ordered domains + disordered regions")
            lines.append("    -> Could be an intrinsically disordered protein (IDP)")
        else:
            lines.append("    -> Mostly disordered — likely IDP or non-globular protein")
            lines.append("    -> May function through protein-protein interactions rather than enzymatic activity")

    return "\n".join(lines)
