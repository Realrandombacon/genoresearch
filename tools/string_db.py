"""
STRING-DB tools — protein-protein interaction network queries.
Uses the STRING REST API to find interaction partners.
"""

import logging
import requests

log = logging.getLogger("genoresearch.string_db")

STRING_BASE = "https://string-db.org/api"


def string_interactions(*args, protein: str = "", species: int = 9606, **kwargs) -> str:
    """
    Get protein-protein interactions from STRING-DB.

    Args:
        protein: Gene name or protein ID (e.g. "TP53", "BRCA1", "C2orf69")
        species: NCBI taxonomy ID (default 9606 = human)
    """
    if not protein and args:
        protein = str(args[0])
    if not protein:
        for key in ("protein", "gene", "query", "name", "gene_name", "id"):
            if key in kwargs:
                protein = str(kwargs[key])
                break
    if not protein:
        return "[ERROR] Usage: string_interactions('TP53')"

    protein = protein.strip()

    # First resolve the protein name to STRING ID
    try:
        resolve_url = f"{STRING_BASE}/json/get_string_ids"
        params = {
            "identifiers": protein,
            "species": species,
            "limit": 1,
            "caller_identity": "genoresearch",
        }
        resp = requests.get(resolve_url, params=params, timeout=30)
        resp.raise_for_status()
        ids = resp.json()
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        return f"[ERROR] STRING-DB resolve failed for '{protein}': {e}"

    if not ids:
        return f"STRING-DB: No protein found for '{protein}' in species {species}"

    string_id = ids[0].get("stringId", "")
    preferred_name = ids[0].get("preferredName", protein)

    # Get interactions
    try:
        interact_url = f"{STRING_BASE}/json/network"
        params = {
            "identifiers": string_id,
            "species": species,
            "limit": 10,
            "caller_identity": "genoresearch",
        }
        resp = requests.get(interact_url, params=params, timeout=30)
        resp.raise_for_status()
        interactions = resp.json()
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        return f"[ERROR] STRING-DB interaction query failed: {e}"

    if not interactions:
        return f"STRING-DB: No interactions found for {preferred_name} ({string_id}). This protein may be poorly studied or not interact with known proteins."

    lines = [f"STRING-DB interactions for {preferred_name}:"]

    # Deduplicate and sort by score
    seen = set()
    partners = []
    for inter in interactions:
        name_a = inter.get("preferredName_A", "?")
        name_b = inter.get("preferredName_B", "?")
        score = inter.get("score", 0)
        partner = name_b if name_a == preferred_name else name_a
        if partner not in seen:
            seen.add(partner)
            partners.append((partner, score))

    partners.sort(key=lambda x: x[1], reverse=True)

    for partner, score in partners[:10]:
        confidence = "high" if score > 0.7 else "medium" if score > 0.4 else "low"
        lines.append(f"  {partner} — score: {score:.3f} ({confidence} confidence)")

    lines.append(f"\nTotal interactions found: {len(partners)}")
    return "\n".join(lines)


def string_enrichment(*args, proteins: str = "", species: int = 9606, **kwargs) -> str:
    """
    Get functional enrichment for a protein (GO terms, KEGG pathways).

    Args:
        proteins: Comma-separated gene names (e.g. "TP53,BRCA1,MDM2")
        species: NCBI taxonomy ID (default 9606 = human)
    """
    if not proteins and args:
        proteins = str(args[0])
    if not proteins:
        for key in ("proteins", "protein", "genes", "gene", "query", "list"):
            if key in kwargs:
                proteins = str(kwargs[key])
                break
    if not proteins:
        return "[ERROR] Usage: string_enrichment('TP53,BRCA1')"

    try:
        url = f"{STRING_BASE}/json/enrichment"
        params = {
            "identifiers": proteins.replace(",", "\r"),
            "species": species,
            "caller_identity": "genoresearch",
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        return f"[ERROR] STRING enrichment failed: {e}"

    if not data:
        return f"STRING-DB: No enrichment results for '{proteins}'"

    lines = [f"STRING-DB functional enrichment for {proteins}:"]
    categories_seen = {}

    for item in data:
        cat = item.get("category", "?")
        term = item.get("term", "?")
        desc = item.get("description", "?")
        pvalue = item.get("p_value", 1.0)

        if cat not in categories_seen:
            categories_seen[cat] = 0
        if categories_seen[cat] >= 3:  # Max 3 per category
            continue
        categories_seen[cat] += 1

        lines.append(f"  [{cat}] {desc} ({term}) — p={pvalue:.2e}")

    return "\n".join(lines)
