"""
NCBI tools — search and fetch from GenBank, Gene, Nucleotide, Protein databases.
Uses NCBI E-utilities API (no API key required, but rate-limited to 3 req/sec).
"""

import os
import logging
import requests
import xml.etree.ElementTree as ET

from config import NCBI_BASE_URL, NCBI_API_KEY, SEQUENCES_DIR

log = logging.getLogger("genoresearch.ncbi")


def ncbi_search(query: str, db: str = "gene", max_results: int = 5) -> str:
    """
    Search NCBI database and return matching IDs with summaries.

    Args:
        query: Search terms (e.g. "BRCA1 human", "p53 mutation")
        db: Database — gene, nucleotide, protein, pubmed, etc.
        max_results: Number of results to return (max 20)
    """
    max_results = min(max_results, 20)

    # Smart query filters by database
    term = query
    if db == "gene" and "homo sapiens" not in query.lower() and "[orgn]" not in query.lower():
        term = f"({query}) AND Homo sapiens[Organism]"
    elif db == "nucleotide" and "[filter]" not in query.lower():
        # Auto-add refseq + mRNA + human filters to get useful NM_ accessions
        org_filter = "" if "homo sapiens" in query.lower() or "[orgn]" in query.lower() else " AND Homo sapiens[Organism]"
        term = f"({query}){org_filter} AND refseq[filter] AND mRNA[filter]"

    # Step 1: esearch — get IDs
    params = {
        "db": db,
        "term": term,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
        "usehistory": "y",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] NCBI search failed: {e}"

    result = data.get("esearchresult", {})
    ids = result.get("idlist", [])
    count = result.get("count", "0")

    if not ids:
        return f"No results found for '{query}' in {db} (total count: {count})"

    # Step 2: esummary — get details
    summaries = _fetch_summaries(ids, db)

    lines = [f"NCBI {db} search: '{query}' — {count} total, showing {len(ids)}"]
    lines.append("  (To fetch sequences: use NM_ accessions with ncbi_fetch('NM_XXXXX', db='nucleotide'). If no NM_ shown, search nucleotide db first.)")
    for s in summaries:
        acc_info = f" [accession: {s['accession']}]" if s.get("accession") else ""
        lines.append(f"  [{s['id']}] {s['title']}{acc_info}")
        if s.get("description"):
            lines.append(f"    {s['description'][:150]}")
    return "\n".join(lines)


def ncbi_fetch(accession_id: str, db: str = "nucleotide") -> str:
    """
    Fetch a sequence by accession ID and save as FASTA.

    Args:
        accession_id: NCBI accession (e.g. "NM_007294", "NP_000537")
        db: Database — nucleotide or protein
    """
    accession_id = str(accession_id)  # handle int IDs from parser
    params = {
        "db": db,
        "id": accession_id,
        "rettype": "fasta",
        "retmode": "text",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/efetch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        fasta = resp.text.strip()
    except Exception as e:
        return f"[ERROR] NCBI fetch failed: {e}"

    if not fasta or "Error" in fasta[:100]:
        return f"[ERROR] No sequence found for {accession_id} in {db}"

    # Save to file
    safe_name = accession_id.replace("/", "_").replace("\\", "_")
    filepath = os.path.join(SEQUENCES_DIR, f"{safe_name}.fasta")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(fasta)

    # Extract basic info from header
    header = fasta.split("\n")[0]
    seq_lines = [l for l in fasta.split("\n")[1:] if l.strip()]
    seq_len = sum(len(l.strip()) for l in seq_lines)

    return (
        f"Fetched {accession_id} from {db}\n"
        f"Header: {header[:200]}\n"
        f"Sequence length: {seq_len} bp/aa\n"
        f"Saved to: {filepath}"
    )


def _fetch_summaries(ids: list[str], db: str) -> list[dict]:
    """Fetch summary info for a list of NCBI IDs."""
    params = {
        "db": db,
        "id": ",".join(ids),
        "retmode": "json",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/esummary.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("esummary failed: %s", e)
        return [{"id": i, "title": "(summary unavailable)", "description": ""} for i in ids]

    results = []
    uids = data.get("result", {}).get("uids", ids)
    for uid in uids:
        info = data.get("result", {}).get(str(uid), {})

        if db in ("nucleotide", "protein"):
            # Nucleotide/protein esummary: accession in caption/accessionversion
            accession = info.get("accessionversion", info.get("caption", ""))
            title = info.get("title", str(uid))
            organism = info.get("organism", "")
            slen = info.get("slen", "")
            biomol = info.get("biomol", "")
            desc = f"Organism: {organism}" if organism else ""
            if slen:
                desc += f" | Length: {slen} {'bp' if biomol != 'peptide' else 'aa'}"
            results.append({
                "id": uid,
                "title": title,
                "description": desc,
                "accession": accession,
            })
        else:
            # Gene db: extract name, description, organism, mRNA accession
            name = info.get("name", info.get("title", str(uid)))
            desc = info.get("description", info.get("summary", ""))
            organism = info.get("organism", {}).get("scientificname", "") if isinstance(info.get("organism"), dict) else ""
            # Extract mRNA accession (NM_) — prefer over chromosome accession (NC_)
            accession = ""
            locationhist = info.get("locationhist", [])
            if locationhist and isinstance(locationhist, list):
                for loc in locationhist:
                    acc = loc.get("chraccver", "")
                    if acc.startswith("NM_") or acc.startswith("NR_"):
                        accession = acc
                        break
            if not accession:
                genomic = info.get("genomicinfo", [])
                if genomic and isinstance(genomic, list):
                    chr_acc = genomic[0].get("chraccver", "")
                    if chr_acc:
                        accession = f"{chr_acc} (chromosome)"
            results.append({
                "id": uid,
                "title": f"{name} — {desc}" if desc else name,
                "description": f"Organism: {organism}" if organism else "",
                "accession": accession,
            })
    return results
