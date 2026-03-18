"""
InterPro / Pfam tools — protein domain and family analysis.
Uses the InterPro REST API to find conserved domains in proteins.
"""

import logging
import requests

log = logging.getLogger("genoresearch.interpro")

INTERPRO_BASE = "https://www.ebi.ac.uk/interpro/api"


def interpro_scan(*args, accession_id: str = "", **kwargs) -> str:
    """
    Look up protein domains/families for a UniProt accession via InterPro.

    Args:
        accession_id: UniProt accession (e.g. "Q9H3H3", "P38398")
    """
    if not accession_id and args:
        accession_id = str(args[0])
    if not accession_id:
        for key in ("accession_id", "accession", "id", "acc", "protein", "uniprot"):
            if key in kwargs:
                accession_id = str(kwargs[key])
                break
    if not accession_id:
        return "[ERROR] Usage: interpro_scan('Q9H3H3')"

    accession_id = accession_id.strip()

    try:
        url = f"{INTERPRO_BASE}/protein/UniProt/{accession_id}?format=json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        resp.json()  # validate protein exists in InterPro
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        return f"[ERROR] InterPro lookup failed for '{accession_id}': {e}"

    # Get entry annotations (domains, families, etc.)
    try:
        url2 = f"{INTERPRO_BASE}/entry/all/protein/UniProt/{accession_id}?format=json"
        resp2 = requests.get(url2, timeout=30)
        resp2.raise_for_status()
        entries_data = resp2.json()
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        return f"[ERROR] InterPro entries lookup failed: {e}"

    results = entries_data.get("results", [])
    if not results:
        return f"InterPro: No domains or families found for {accession_id}. This protein has no recognized conserved domains — may be truly novel."

    lines = [f"InterPro domains/families for {accession_id}:"]

    for entry in results[:15]:  # Cap at 15 entries
        metadata = entry.get("metadata", {})
        entry_acc = metadata.get("accession", "?")
        entry_name = metadata.get("name", "?")
        entry_type = metadata.get("type", "?")
        source_db = metadata.get("source_database", "?")
        go_terms = metadata.get("go_terms", [])

        lines.append(f"  [{entry_acc}] {entry_name}")
        lines.append(f"    Type: {entry_type} | Source: {source_db}")

        # Show locations on the protein
        proteins = entry.get("proteins", [])
        for prot in proteins[:1]:
            locations = prot.get("entry_protein_locations", [])
            for loc in locations[:3]:
                frags = loc.get("fragments", [])
                for frag in frags:
                    start = frag.get("start", "?")
                    end = frag.get("end", "?")
                    lines.append(f"    Position: {start}-{end}")

        # Show GO terms if any
        if go_terms:
            go_strs = [f"{g.get('name', '?')} ({g.get('identifier', '?')})" for g in go_terms[:3]]
            lines.append(f"    GO terms: {', '.join(go_strs)}")

    return "\n".join(lines)


def interpro_search(*args, query: str = "", **kwargs) -> str:
    """
    Search InterPro for domain/family by name or keyword.

    Args:
        query: Search term (e.g. "kinase", "zinc finger", "DUF4709")
    """
    if not query and args:
        query = str(args[0])
    if not query:
        for key in ("query", "term", "search", "q", "text", "domain", "family"):
            if key in kwargs:
                query = str(kwargs[key])
                break
    if not query:
        return "[ERROR] Usage: interpro_search('kinase')"

    try:
        url = f"{INTERPRO_BASE}/entry/all?search={query}&format=json&page_size=10"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        return f"[ERROR] InterPro search failed: {e}"

    results = data.get("results", [])
    if not results:
        return f"No InterPro entries found for '{query}'"

    lines = [f"InterPro search: '{query}' — {len(results)} results"]
    for entry in results[:10]:
        metadata = entry.get("metadata", {})
        acc = metadata.get("accession", "?")
        name = metadata.get("name", "?")
        etype = metadata.get("type", "?")
        source = metadata.get("source_database", "?")
        count = metadata.get("counters", {}).get("proteins", "?")
        lines.append(f"  [{acc}] {name}")
        lines.append(f"    Type: {etype} | Source: {source} | Proteins: {count}")

    return "\n".join(lines)
