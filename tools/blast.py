"""
BLAST tool — sequence similarity search via NCBI BLAST API.
Note: BLAST searches are async — submit, poll, then fetch results.
"""

import time
import logging
import requests

from config import NCBI_BLAST_URL, NCBI_API_KEY

log = logging.getLogger("genoresearch.blast")

MAX_WAIT_SECONDS = 300  # 5 min max wait for BLAST results
POLL_INTERVAL = 15      # check every 15 seconds


def blast_search(sequence: str, db: str = "nt", program: str = "blastn",
                 evalue: float = 0.01, max_hits: int = 10) -> str:
    """
    Run BLAST search against NCBI.

    Args:
        sequence: Nucleotide or protein sequence (raw, no header)
        db: Database — nt (nucleotide), nr (protein), refseq_rna, etc.
        program: blastn, blastp, blastx, tblastn, tblastx
        evalue: E-value threshold
        max_hits: Max alignments to return
    """
    if len(sequence) < 10:
        return "[ERROR] Sequence too short for BLAST (min 10 characters)"

    # Auto-detect program if needed
    if _looks_like_protein(sequence) and program == "blastn":
        program = "blastp"
        db = "nr"
        log.info("Auto-switched to blastp/nr for protein sequence")

    # Step 1: Submit
    put_params = {
        "CMD": "Put",
        "PROGRAM": program,
        "DATABASE": db,
        "QUERY": sequence[:10000],  # limit length
        "EXPECT": str(evalue),
        "HITLIST_SIZE": str(max_hits),
        "FORMAT_TYPE": "Text",
    }
    if NCBI_API_KEY:
        put_params["API_KEY"] = NCBI_API_KEY

    try:
        resp = requests.post(NCBI_BLAST_URL, data=put_params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return f"[ERROR] BLAST submission failed: {e}"

    # Extract RID
    rid = _extract_rid(resp.text)
    if not rid:
        return "[ERROR] Could not get BLAST request ID from response"

    log.info("BLAST submitted — RID: %s, waiting for results...", rid)

    # Step 2: Poll for completion
    result_text = _poll_results(rid)
    if result_text.startswith("[ERROR]"):
        return result_text

    # Step 3: Parse and summarize
    return _summarize_blast(result_text, max_hits)


def _looks_like_protein(seq: str) -> bool:
    """Heuristic: protein seqs have letters beyond ATCGN."""
    cleaned = seq.upper().replace(" ", "").replace("\n", "")
    non_dna = set(cleaned) - set("ATCGNU\n ")
    return len(non_dna) > 2


def _extract_rid(html: str) -> str:
    """Extract Request ID from BLAST submission response."""
    for line in html.split("\n"):
        if "RID = " in line:
            return line.split("RID = ")[1].strip()
    return ""


def _poll_results(rid: str) -> str:
    """Poll BLAST for results until ready or timeout."""
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        params = {
            "CMD": "Get",
            "RID": rid,
            "FORMAT_TYPE": "Text",
            "FORMAT_OBJECT": "Alignment",
        }

        try:
            resp = requests.get(NCBI_BLAST_URL, params=params, timeout=30)
            if "Status=WAITING" in resp.text:
                log.info("BLAST still running... (%ds elapsed)", elapsed)
                continue
            if "Status=FAILED" in resp.text:
                return "[ERROR] BLAST search failed on server"
            if "Status=UNKNOWN" in resp.text:
                return "[ERROR] BLAST RID expired or unknown"
            # Results ready
            return resp.text
        except Exception as e:
            log.warning("Poll error: %s", e)

    return f"[ERROR] BLAST timed out after {MAX_WAIT_SECONDS}s"


def _summarize_blast(raw_text: str, max_hits: int) -> str:
    """Extract key info from BLAST text output."""
    lines = raw_text.split("\n")
    summary_lines = []
    in_descriptions = False
    hit_count = 0

    for line in lines:
        if "Sequences producing significant alignments" in line:
            in_descriptions = True
            summary_lines.append("=== BLAST Hits ===")
            continue
        if in_descriptions and line.strip() and hit_count < max_hits:
            if line.startswith(">") or line.startswith(" "):
                summary_lines.append(line.rstrip()[:200])
                hit_count += 1
            if line.strip() == "":
                in_descriptions = False

        if "No significant similarity found" in line:
            return "BLAST: No significant similarity found."

    if not summary_lines:
        # Fallback — return first meaningful chunk
        meaningful = [l for l in lines if l.strip() and not l.startswith("<!")]
        return "BLAST results (raw):\n" + "\n".join(meaningful[:20])

    return "\n".join(summary_lines)
