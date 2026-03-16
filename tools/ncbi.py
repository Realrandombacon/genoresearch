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


def ncbi_search(*args, query: str = "", db: str = "gene", max_results: int = 5, **kwargs) -> str:
    """
    Search NCBI database and return matching IDs with summaries.

    Args:
        query: Search terms (e.g. "BRCA1 human", "p53 mutation")
        db: Database — gene, nucleotide, protein, pubmed, etc.
        max_results: Number of results to return (max 20)
    """
    # Handle Qwen's creative kwarg names
    if not query and args:
        query = str(args[0])
    if not query:
        for key in ("query", "term", "search", "q", "text", "gene", "name"):
            if key in kwargs:
                query = str(kwargs[key])
                break
    if not query:
        return "[ERROR] No query provided. Usage: ncbi_search('BRCA1', db='gene')"
    # Absorb database= alias
    if "database" in kwargs:
        db = str(kwargs["database"])
    # Absorb limit= alias for max_results
    if "limit" in kwargs:
        try:
            max_results = int(kwargs["limit"])
        except (ValueError, TypeError):
            pass

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


def ncbi_fetch(*args, accession_id: str = "", db: str = "nucleotide", **kwargs) -> str:
    """
    Fetch a sequence by accession ID and save as FASTA.

    Args:
        accession_id: NCBI accession (e.g. "NM_007294", "NP_000537")
        db: Database — nucleotide or protein
    """
    # Handle Qwen's creative kwarg names
    if not accession_id and args:
        accession_id = str(args[0])
    if not accession_id:
        for key in ("accession_id", "accession", "id", "acc", "query", "seq_id"):
            if key in kwargs:
                accession_id = str(kwargs[key])
                break
    if not accession_id:
        return "[ERROR] No accession ID provided. Usage: ncbi_fetch('NM_007294', db='nucleotide')"
    # Absorb database= alias
    if "database" in kwargs:
        db = str(kwargs["database"])
    accession_id = str(accession_id)  # handle int IDs from parser

    # Block chromosome-level accessions (NC_, AC_) — they are 100MB+ and will timeout
    prefix = accession_id.split("_")[0].upper() if "_" in accession_id else ""
    if prefix in ("NC", "AC", "NT", "NW"):
        return (
            f"[ERROR] {accession_id} is a chromosome/contig-level sequence (too large). "
            f"Use a transcript accession instead (NM_, XM_, NR_) or protein (NP_, XP_). "
            f"Search with ncbi_search() or gene_info() to find the right accession."
        )

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


def pubmed_search(*args, query: str = "", max_results: int = 5, **kwargs) -> str:
    """
    Search PubMed for scientific articles related to a genomics topic.
    Returns titles, authors, journal, year, and PMIDs.

    Args:
        query: Search terms (e.g. "BRCA1 cancer therapy", "TP53 mutation review")
        max_results: Number of papers to return (max 10)
    """
    # Handle Qwen's creative kwarg names
    if not query and args:
        query = str(args[0])
    if not query:
        for key in ("query", "term", "search", "q", "text", "topic"):
            if key in kwargs:
                query = str(kwargs[key])
                break
    if not query:
        return "[ERROR] No query provided. Usage: pubmed_search('BRCA1 cancer therapy')"
    # Absorb limit= alias for max_results
    if "limit" in kwargs:
        try:
            max_results = int(kwargs["limit"])
        except (ValueError, TypeError):
            pass
    max_results = min(max_results, 10)

    # Step 1: esearch on pubmed
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] PubMed search failed: {e}"

    ids = data.get("esearchresult", {}).get("idlist", [])
    total = data.get("esearchresult", {}).get("count", "0")
    if not ids:
        return f"No PubMed results for '{query}'"

    # Step 2: efetch XML to get title, authors, journal, year, abstract
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "rettype": "xml",
        "retmode": "xml",
    }
    if NCBI_API_KEY:
        fetch_params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/efetch.fcgi", params=fetch_params, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        return f"[ERROR] PubMed fetch failed: {e}"

    lines = [f"PubMed search: '{query}' — {total} total, showing {len(ids)}"]
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", "?")
        title = article.findtext(".//ArticleTitle", "?")
        journal = article.findtext(".//Journal/Title", "?")
        year = article.findtext(".//PubDate/Year",
                article.findtext(".//MedlineDate", "?"))

        # Authors — first 3
        authors = []
        for author in article.findall(".//Author")[:3]:
            last = author.findtext("LastName", "")
            init = author.findtext("Initials", "")
            if last:
                authors.append(f"{last} {init}".strip())
        total_authors = len(article.findall(".//Author"))
        author_str = ", ".join(authors)
        if total_authors > 3:
            author_str += f" et al. ({total_authors} authors)"

        # Abstract — first 200 chars
        abstract = article.findtext(".//AbstractText", "")
        abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract

        lines.append(f"\n  [PMID:{pmid}] {title}")
        lines.append(f"    {author_str} — {journal} ({year})")
        if abstract_preview:
            lines.append(f"    Abstract: {abstract_preview}")

    return "\n".join(lines)


def gene_info(*args, gene_name: str = "", **kwargs) -> str:
    """
    Get structured information about a gene from NCBI Gene database.
    Returns chromosome location, summary, aliases, associated diseases, and RefSeq accessions.

    Args:
        gene_name: Gene symbol or name (e.g. "BRCA1", "TP53", "EGFR")
    """
    # Handle Qwen's creative kwarg names
    if not gene_name and args:
        gene_name = str(args[0])
    if not gene_name:
        for key in ("gene_name", "gene", "name", "symbol", "query", "gene_symbol"):
            if key in kwargs:
                gene_name = str(kwargs[key])
                break
    if not gene_name:
        return "[ERROR] No gene name provided. Usage: gene_info('BRCA1')"
    # Step 1: Search gene database
    term = f"({gene_name}) AND Homo sapiens[Organism]"
    params = {
        "db": "gene",
        "term": term,
        "retmax": 1,
        "retmode": "json",
        "sort": "relevance",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] Gene search failed: {e}"

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return f"No gene found for '{gene_name}' in Homo sapiens"

    gene_id = ids[0]

    # Step 2: Fetch full gene record via efetch XML (docsum)
    fetch_params = {
        "db": "gene",
        "id": gene_id,
        "rettype": "docsum",
        "retmode": "json",
    }
    if NCBI_API_KEY:
        fetch_params["api_key"] = NCBI_API_KEY

    try:
        resp = requests.get(f"{NCBI_BASE_URL}/esummary.fcgi", params=fetch_params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] Gene info fetch failed: {e}"

    info = data.get("result", {}).get(str(gene_id), {})
    if not info:
        return f"[ERROR] Could not parse gene info for ID {gene_id}"

    name = info.get("name", gene_name)
    description = info.get("description", "")
    summary = info.get("summary", "")
    organism = info.get("organism", {})
    org_name = organism.get("scientificname", "Homo sapiens") if isinstance(organism, dict) else "Homo sapiens"

    # Chromosome & location
    chrom = info.get("chromosome", "?")
    maplocation = info.get("maplocation", "?")

    # Other names / aliases
    other_names = info.get("otheraliases", "")
    other_desig = info.get("otherdesignations", "")

    # Genomic info — get RefSeq accessions
    genomic = info.get("genomicinfo", [])
    refseq_accessions = []
    if genomic and isinstance(genomic, list):
        for g in genomic:
            chr_acc = g.get("chraccver", "")
            start = g.get("chrstart", "")
            stop = g.get("chrstop", "")
            if chr_acc:
                refseq_accessions.append(f"{chr_acc} ({start}-{stop})")

    # Location history — find mRNA accessions
    mrna_accessions = []
    locationhist = info.get("locationhist", [])
    if locationhist and isinstance(locationhist, list):
        for loc in locationhist:
            acc = loc.get("chraccver", "")
            if acc.startswith("NM_") or acc.startswith("NR_"):
                if acc not in mrna_accessions:
                    mrna_accessions.append(acc)

    lines = [
        f"Gene: {name} (Gene ID: {gene_id})",
        f"Full name: {description}",
        f"Organism: {org_name}",
        f"Chromosome: {chrom} ({maplocation})",
    ]
    if other_names:
        lines.append(f"Aliases: {other_names}")
    if summary:
        lines.append(f"Summary: {summary[:400]}{'...' if len(summary) > 400 else ''}")
    if mrna_accessions:
        lines.append(f"mRNA accessions: {', '.join(mrna_accessions[:5])}")
        lines.append(f"  → Fetch with: ncbi_fetch('{mrna_accessions[0]}', db='nucleotide')")
    if refseq_accessions:
        lines.append(f"Genomic location: {refseq_accessions[0]}")

    return "\n".join(lines)


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
