"""
ClinVar tools — clinical variant significance data from NCBI ClinVar.
Uses NCBI E-utilities to query ClinVar for disease-associated variants.
"""

import logging
import requests
import xml.etree.ElementTree as ET

log = logging.getLogger("genoresearch.clinvar")

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def clinvar_search(*args, gene: str = "", **kwargs) -> str:
    """
    Search ClinVar for clinical variants associated with a gene.
    Returns pathogenic/likely pathogenic variants and disease associations.

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
        return "[ERROR] Usage: clinvar_search('TP53')"

    gene = gene.strip()

    # Search ClinVar for the gene
    try:
        search_url = f"{NCBI_BASE}/esearch.fcgi"
        params = {
            "db": "clinvar",
            "term": f"{gene}[gene] AND (pathogenic[clinsig] OR likely_pathogenic[clinsig])",
            "retmax": 20,
            "retmode": "json",
        }
        resp = requests.get(search_url, params=params, timeout=30)
        resp.raise_for_status()
        search_data = resp.json()
    except Exception as e:
        return f"[ERROR] ClinVar search failed for '{gene}': {e}"

    result = search_data.get("esearchresult", {})
    total = int(result.get("count", 0))
    id_list = result.get("idlist", [])

    if total == 0:
        # Try broader search without pathogenic filter
        try:
            params["term"] = f"{gene}[gene]"
            resp = requests.get(search_url, params=params, timeout=30)
            resp.raise_for_status()
            search_data = resp.json()
            result = search_data.get("esearchresult", {})
            total_all = int(result.get("count", 0))
            id_list = result.get("idlist", [])

            if total_all == 0:
                return f"ClinVar: No variants found for '{gene}'. Gene has no ClinVar entries — no known clinical significance."
            else:
                lines = [f"ClinVar: {total_all} total variants for {gene} (0 pathogenic/likely pathogenic)"]
                lines.append(f"  → No disease-causing variants known — gene may be tolerant to variation")
        except Exception:
            return f"ClinVar: No pathogenic variants found for '{gene}'"
    else:
        lines = [f"ClinVar: {total} pathogenic/likely pathogenic variants for {gene}"]

    if not id_list:
        return "\n".join(lines)

    # Fetch variant details via esummary
    try:
        summary_url = f"{NCBI_BASE}/esummary.fcgi"
        params = {
            "db": "clinvar",
            "id": ",".join(id_list[:10]),
            "retmode": "json",
        }
        resp = requests.get(summary_url, params=params, timeout=30)
        resp.raise_for_status()
        summary_data = resp.json()
    except Exception as e:
        lines.append(f"  (Could not fetch variant details: {e})")
        return "\n".join(lines)

    uid_results = summary_data.get("result", {})
    uids = uid_results.get("uids", [])

    diseases_seen = set()

    for uid in uids[:10]:
        entry = uid_results.get(uid, {})
        title = entry.get("title", "?")
        clinical_sig = entry.get("clinical_significance", {})
        sig_desc = clinical_sig.get("description", "?") if isinstance(clinical_sig, dict) else str(clinical_sig)

        # Get trait/disease associations
        trait_set = entry.get("trait_set", [])
        for trait in trait_set if isinstance(trait_set, list) else []:
            trait_name = trait.get("trait_name", "")
            if trait_name and trait_name not in diseases_seen:
                diseases_seen.add(trait_name)

        # Variation set info
        var_set = entry.get("variation_set", [])
        variant_type = ""
        for vs in var_set if isinstance(var_set, list) else []:
            variant_type = vs.get("variant_type", "")

        lines.append(f"  [{uid}] {title[:100]}")
        lines.append(f"    Significance: {sig_desc}")
        if variant_type:
            lines.append(f"    Type: {variant_type}")

    if diseases_seen:
        lines.append(f"\n  Disease associations:")
        for disease in sorted(diseases_seen):
            lines.append(f"    • {disease}")

    lines.append(f"\n  Summary: {total} pathogenic variants, {len(diseases_seen)} diseases associated")
    if total > 0:
        lines.append(f"  → This gene HAS clinical significance — variants cause disease")
    else:
        lines.append(f"  → No pathogenic variants — gene may be non-essential or redundant")

    return "\n".join(lines)
