"""
Semantic Scholar tools — academic paper search for gene research.
Adds literature awareness to the research pipeline: check existing
publications, find related work, validate novelty of findings.

Uses Semantic Scholar API v1 (free tier with optional API key).
"""

import logging
import time

import requests

from config import API_TIMEOUT, SEMANTIC_SCHOLAR_API_KEY

log = logging.getLogger("genoresearch.semantic_scholar")

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1"

# Backoff schedule for HTTP 429 (seconds). 3 attempts max.
_RATE_LIMIT_BACKOFF = (5.0, 15.0, 45.0)


def _get_headers():
    """Build request headers, include API key if available."""
    headers = {"Accept": "application/json"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return headers


def _get_with_retry(url, params, headers, timeout, max_attempts=3):
    """GET with exponential backoff on HTTP 429. Honours Retry-After header if present.

    Returns the final Response object (may still be 429 if all attempts exhausted).
    """
    last_resp = None
    for attempt in range(max_attempts):
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code != 429:
            return resp
        last_resp = resp
        # 429 — backoff. Prefer server-supplied Retry-After, else use schedule.
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                wait = float(retry_after)
            except ValueError:
                wait = _RATE_LIMIT_BACKOFF[min(attempt, len(_RATE_LIMIT_BACKOFF) - 1)]
        else:
            wait = _RATE_LIMIT_BACKOFF[min(attempt, len(_RATE_LIMIT_BACKOFF) - 1)]
        log.warning("S2 429 — retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, max_attempts)
        time.sleep(wait)
    return last_resp


def semantic_search(*args, query: str = "", max_results: int = 5, **kwargs) -> str:
    """
    Search Semantic Scholar for academic papers related to a gene or topic.

    Usage:
      semantic_search('TP53 function dark gene')
      semantic_search(query='BRCA1 interaction pathway', max_results=10)

    Returns formatted results with titles, authors, year, citations, abstracts.
    """
    # Handle Qwen's flexible argument passing
    if not query and args:
        query = str(args[0])
    if not query:
        for key in ("query", "term", "search", "q", "text", "gene", "topic"):
            if key in kwargs:
                query = str(kwargs[key])
                break
    if not query:
        return "[ERROR] No query provided. Usage: semantic_search('kinase dark gene')"

    # Sanitize
    if isinstance(max_results, str):
        try:
            max_results = int(max_results)
        except ValueError:
            max_results = 5
    max_results = min(max(1, max_results), 20)

    try:
        resp = _get_with_retry(
            f"{SEMANTIC_SCHOLAR_URL}/paper/search",
            params={
                "query": query,
                "limit": max_results,
                "fields": "paperId,title,year,authors,abstract,citationCount,venue,openAccessPdf",
            },
            headers=_get_headers(),
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return f"[ERROR] Semantic Scholar timed out for '{query}'"
    except requests.ConnectionError:
        return "[ERROR] Could not connect to Semantic Scholar"
    except requests.HTTPError as e:
        return f"[ERROR] Semantic Scholar HTTP {resp.status_code}: {e}"
    except ValueError:
        return "[ERROR] Invalid response from Semantic Scholar"

    papers = data.get("data", [])
    total = data.get("total", 0)

    if not papers:
        return f"No papers found on Semantic Scholar for '{query}' (total: {total})"

    lines = [f"Semantic Scholar: '{query}' — {total} total results, showing {len(papers)}:\n"]
    for i, paper in enumerate(papers):
        title = paper.get("title", "?")
        year = paper.get("year", "?")
        authors = paper.get("authors", [])
        author_str = ", ".join([a.get("name", "?") for a in authors[:3]])
        if len(authors) > 3:
            author_str += f" +{len(authors) - 3} more"
        citations = paper.get("citationCount", 0)
        venue = paper.get("venue", "")
        paper_id = paper.get("paperId", "")

        lines.append(f"  [{i+1}] {title}")
        lines.append(f"      Authors: {author_str}")
        lines.append(f"      Year: {year} | Citations: {citations}" + (f" | Venue: {venue}" if venue else ""))

        abstract = paper.get("abstract", "")
        if abstract:
            short = abstract[:300].replace("\n", " ")
            lines.append(f"      Abstract: {short}...")

        lines.append(f"      ID: {paper_id}")
        lines.append("")

    return "\n".join(lines)


def gene_literature(*args, gene: str = "", **kwargs) -> str:
    """
    Search for literature specifically about a gene. Optimized query
    for finding publications about dark/uncharacterized genes.

    Usage:
      gene_literature('C1orf112')
      gene_literature(gene='FAM47A')
    """
    if not gene and args:
        gene = str(args[0])
    if not gene:
        for key in ("gene", "gene_name", "symbol", "name", "query"):
            if key in kwargs:
                gene = str(kwargs[key])
                break
    if not gene:
        return "[ERROR] No gene provided. Usage: gene_literature('C1orf112')"

    # Build a specific query — use exact gene symbol to avoid noise
    # Search with just the symbol first (most specific)
    query = f'"{gene}"'

    try:
        resp = _get_with_retry(
            f"{SEMANTIC_SCHOLAR_URL}/paper/search",
            params={
                "query": query,
                "limit": 10,
                "fields": "paperId,title,year,authors,abstract,citationCount,venue",
            },
            headers=_get_headers(),
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return f"[ERROR] Semantic Scholar timed out for gene '{gene}'"
    except requests.ConnectionError:
        return "[ERROR] Could not connect to Semantic Scholar"
    except requests.HTTPError as e:
        return f"[ERROR] Semantic Scholar HTTP {resp.status_code}: {e}"
    except ValueError:
        return f"[ERROR] Invalid response from Semantic Scholar for '{gene}'"

    papers = data.get("data", [])
    total = data.get("total", 0)

    if total == 0:
        return (
            f"No publications found for gene '{gene}' on Semantic Scholar.\n"
            f"This gene appears to be truly unstudied — a genuine dark gene.\n"
            f"This is valuable information for your finding."
        )

    # Classify how "dark" the gene is based on publication count
    if total <= 3:
        status = "VERY DARK — barely any publications"
    elif total <= 10:
        status = "DARK — few publications, poorly characterized"
    elif total <= 30:
        status = "PARTIALLY CHARACTERIZED — some literature exists"
    else:
        status = "WELL-STUDIED — consider skip_gene() if not a dark gene"

    lines = [
        f"Literature for gene '{gene}': {total} total papers. Status: {status}\n"
    ]

    # Filter for most relevant (those with gene symbol in title)
    gene_upper = gene.upper()
    relevant = [p for p in papers if gene_upper in (p.get("title", "") or "").upper()]
    others = [p for p in papers if p not in relevant]

    for label, subset in [("Directly about this gene:", relevant), ("Related papers:", others)]:
        if not subset:
            continue
        lines.append(f"  {label}")
        for paper in subset[:5]:
            title = paper.get("title", "?")
            year = paper.get("year", "?")
            citations = paper.get("citationCount", 0)
            lines.append(f"    - [{year}] {title} (cited {citations}x)")

            abstract = paper.get("abstract", "")
            if abstract:
                short = abstract[:200].replace("\n", " ")
                lines.append(f"      {short}...")
        lines.append("")

    return "\n".join(lines)


def semantic_fetch(*args, paper_id: str = "", **kwargs) -> str:
    """
    Fetch detailed information for a specific paper by Semantic Scholar ID.

    Usage:
      semantic_fetch('649def34...')
    """
    if not paper_id and args:
        paper_id = str(args[0])
    if not paper_id:
        for key in ("paper_id", "id", "paperId", "doi"):
            if key in kwargs:
                paper_id = str(kwargs[key])
                break
    if not paper_id:
        return "[ERROR] No paper ID provided. Usage: semantic_fetch('649def34...')"

    try:
        resp = requests.get(
            f"{SEMANTIC_SCHOLAR_URL}/paper/{paper_id}",
            params={
                "fields": "title,abstract,year,authors,citationCount,venue,references,tldr",
            },
            headers=_get_headers(),
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        paper = resp.json()
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError) as e:
        return f"[ERROR] Semantic Scholar fetch failed for '{paper_id}': {e}"

    lines = [f"Paper: {paper.get('title', '?')}"]
    lines.append(f"  Year: {paper.get('year', '?')}")
    lines.append(f"  Citations: {paper.get('citationCount', 0)}")

    venue = paper.get("venue", "")
    if venue:
        lines.append(f"  Venue: {venue}")

    authors = paper.get("authors", [])
    if authors:
        lines.append(f"  Authors: {', '.join(a.get('name', '?') for a in authors[:10])}")

    tldr = paper.get("tldr")
    if tldr and isinstance(tldr, dict):
        lines.append(f"  TL;DR: {tldr.get('text', '')}")

    abstract = paper.get("abstract", "")
    if abstract:
        lines.append(f"  Abstract: {abstract[:600]}")

    refs = paper.get("references", [])
    if refs:
        lines.append(f"  References: {len(refs)} papers cited")

    return "\n".join(lines)
