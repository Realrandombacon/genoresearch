"""
BLAST tool — sequence similarity search.

Priority: local BLAST+ (instant, ~5-15s) → remote NCBI (slow, 1-5 min).
Local BLAST+ requires: blast+ installed + database files in data/blastdb/.
"""

import os
import shutil
import subprocess
import tempfile
import time
import logging
import requests

from config import (
    NCBI_BLAST_URL, NCBI_API_KEY, SEQUENCES_DIR,
    BLAST_BIN_DIR, BLAST_DB_DIR, BLAST_LOCAL_ENABLED,
)

log = logging.getLogger("genoresearch.blast")

# Remote NCBI settings
MAX_WAIT_SECONDS = 300
POLL_INTERVAL = 15

# Map program → local binary name
_PROGRAM_BIN = {
    "blastn": "blastn",
    "blastp": "blastp",
    "blastx": "blastx",
    "tblastn": "tblastn",
    "tblastx": "tblastx",
}

# Map generic db names → local db names (as downloaded by update_blastdb.pl)
_LOCAL_DB_MAP = {
    "nt": "nt",
    "nr": "nr",
    "refseq_rna": "refseq_rna",
    "swissprot": "swissprot",
    "refseq_select_rna": "refseq_select_rna",
    "refseq_protein": "refseq_protein",
}


# ─── Public API ──────────────────────────────────────────────────────────────

def blast_search(*args, sequence: str = "", db: str = "nt", program: str = "blastn",
                 evalue: float = 0.01, max_hits: int = 10, **kwargs) -> str:
    """
    Run BLAST search — uses local BLAST+ if available, else remote NCBI.

    Args:
        sequence: Raw sequence OR filepath to a .fasta file
        db: Database — nt, nr, swissprot, refseq_rna, etc.
        program: blastn, blastp, blastx, tblastn, tblastx
        evalue: E-value threshold
        max_hits: Max alignments to return
    """
    # Handle Qwen's creative kwarg names
    if not sequence and args:
        sequence = str(args[0])
    if not sequence:
        for key in ("query", "seq", "input", "fasta", "file", "filepath"):
            if key in kwargs:
                sequence = str(kwargs[key])
                break
    if "database" in kwargs:
        db = str(kwargs["database"])

    if not sequence:
        return "[ERROR] No sequence provided. Usage: blast_search('NM_007294.4.fasta', db='nt')"

    # Resolve filepath → raw sequence
    sequence = _resolve_sequence(sequence)
    if sequence.startswith("[ERROR]"):
        return sequence

    if len(sequence) < 10:
        return "[ERROR] Sequence too short for BLAST (min 10 characters)"

    # Auto-detect protein vs nucleotide
    if _looks_like_protein(sequence) and program == "blastn":
        program = "blastp"
        if db == "nt":
            db = "swissprot"
        log.info("Auto-switched to blastp/%s for protein sequence", db)

    # Redirect nr → local alternative when nr isn't available locally
    # Prefer swissprot (complete, small) over refseq_protein (may be incomplete)
    if db == "nr" and BLAST_LOCAL_ENABLED:
        if not _find_local_db("nr"):
            for alt in ("swissprot", "refseq_protein"):
                if _find_local_db(alt) and _db_is_usable(alt):
                    log.info("Redirecting db='nr' → '%s' (local, much faster)", alt)
                    db = alt
                    if program == "blastn":
                        program = "blastp"
                    break

    # Redirect nt → local alternative when nt isn't available locally
    if db == "nt" and BLAST_LOCAL_ENABLED:
        if not _find_local_db("nt") and _looks_like_protein(sequence):
            for alt in ("swissprot", "refseq_protein"):
                if _find_local_db(alt) and _db_is_usable(alt):
                    log.info("Redirecting protein query on db='nt' → '%s' (local)", alt)
                    db = alt
                    program = "blastp"
                    break

    # Try local BLAST first
    if BLAST_LOCAL_ENABLED:
        local_result = _blast_local(sequence, db, program, evalue, max_hits)
        if local_result is not None:
            return local_result
        log.info("Local BLAST not available for db=%s, falling back to remote NCBI", db)

    # Fallback: remote NCBI
    return _blast_remote(sequence, db, program, evalue, max_hits)


# ─── Local BLAST+ ────────────────────────────────────────────────────────────

def _find_blast_bin(program: str) -> str | None:
    """Find the BLAST+ binary — check PATH first, then configured BLAST_BIN_DIR."""
    bin_name = _PROGRAM_BIN.get(program, program)
    if os.name == "nt":
        bin_name += ".exe"

    # Check if it's on PATH
    found = shutil.which(bin_name)
    if found:
        return found

    # Check configured BLAST_BIN_DIR
    candidate = os.path.join(BLAST_BIN_DIR, bin_name)
    if os.path.isfile(candidate):
        return candidate

    return None


def _find_local_db(db: str) -> str | None:
    """Check if a local BLAST database exists in BLAST_DB_DIR."""
    local_name = _LOCAL_DB_MAP.get(db, db)
    db_path = os.path.join(BLAST_DB_DIR, local_name)

    # BLAST databases consist of multiple files — check for at least one index file
    # For nucleotide: .ndb, .nhr, .nin, .njs, .not, .nsq, .ntf, .nto
    # For protein: .pdb, .phr, .pin, .pjs, .pot, .psq, .ptf, .pto
    for ext in [".nhr", ".phr", ".nsq", ".psq", ".nin", ".pin", ".ndb", ".pdb"]:
        if os.path.isfile(db_path + ext):
            return db_path

    # Also check subdirectories (some databases have volume files)
    for f in os.listdir(BLAST_DB_DIR) if os.path.isdir(BLAST_DB_DIR) else []:
        if f.startswith(local_name + ".") and any(f.endswith(e) for e in [".nhr", ".phr", ".nsq", ".psq"]):
            return db_path

    return None


def _db_is_usable(db: str) -> bool:
    """Quick check: can BLAST actually use this database?
    Multi-volume databases (e.g. refseq_protein) need an alias file (.pal/.nal)
    or a single-volume set of index files.
    """
    local_name = _LOCAL_DB_MAP.get(db, db)
    db_path = os.path.join(BLAST_DB_DIR, local_name)

    # Single-volume: has .pin or .nin directly (e.g. swissprot.pin)
    if os.path.isfile(db_path + ".pin") or os.path.isfile(db_path + ".nin"):
        return True

    # Multi-volume: needs an alias file (.pal for protein, .nal for nucleotide)
    if os.path.isfile(db_path + ".pal") or os.path.isfile(db_path + ".nal"):
        return True

    return False


def _blast_local(sequence: str, db: str, program: str, evalue: float,
                 max_hits: int) -> str | None:
    """Run BLAST locally. Returns result string or None if not available."""
    blast_bin = _find_blast_bin(program)
    if not blast_bin:
        log.debug("BLAST+ binary '%s' not found", program)
        return None

    local_db = _find_local_db(db)
    if not local_db:
        log.debug("Local BLAST database '%s' not found in %s", db, BLAST_DB_DIR)
        return None

    # Write sequence to temp FASTA file
    tmp_query = None
    tmp_out = None
    try:
        tmp_query = tempfile.NamedTemporaryFile(
            mode="w", suffix=".fasta", delete=False, dir=tempfile.gettempdir()
        )
        tmp_query.write(f">query\n{sequence}\n")
        tmp_query.close()

        tmp_out = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, dir=tempfile.gettempdir()
        )
        tmp_out.close()

        # Run BLAST with tabular output for easy parsing
        # outfmt 6: qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore
        # Also get outfmt 7 (tabular with comments) for readability
        cmd = [
            blast_bin,
            "-query", tmp_query.name,
            "-db", local_db,
            "-evalue", str(evalue),
            "-max_target_seqs", str(max_hits),
            "-outfmt", "7 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle",
            "-out", tmp_out.name,
            "-num_threads", "4",
        ]

        log.info("Running local BLAST: %s -db %s (%d bp/aa query)",
                 program, db, len(sequence))
        t0 = time.time()

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            env={**os.environ, "BLASTDB": BLAST_DB_DIR}
        )

        elapsed = time.time() - t0
        log.info("Local BLAST completed in %.1fs", elapsed)

        if result.returncode != 0:
            stderr = result.stderr.strip()
            log.error("Local BLAST failed: %s", stderr[:500])
            return f"[ERROR] Local BLAST failed: {stderr[:200]}"

        # Read results
        with open(tmp_out.name, "r", encoding="utf-8") as f:
            output = f.read().strip()

        if not output:
            return "BLAST: No significant similarity found."

        return _format_local_results(output, elapsed)

    except subprocess.TimeoutExpired:
        log.error("Local BLAST timed out after 120s")
        return "[ERROR] Local BLAST timed out (120s)"
    except Exception as e:
        log.error("Local BLAST error: %s", e)
        return None  # fallback to remote
    finally:
        # Cleanup temp files
        for f in [tmp_query, tmp_out]:
            if f and os.path.isfile(f.name):
                try:
                    os.unlink(f.name)
                except OSError:
                    pass


def _format_local_results(output: str, elapsed: float) -> str:
    """Format tabular BLAST output into readable summary."""
    lines = output.strip().split("\n")
    hits = []

    for line in lines:
        if line.startswith("#"):
            # Check for "0 hits found"
            if "0 hits found" in line:
                return f"BLAST (local, {elapsed:.1f}s): No significant similarity found."
            continue

        parts = line.split("\t")
        if len(parts) >= 13:
            hits.append({
                "subject": parts[1],
                "identity": float(parts[2]),
                "length": int(parts[3]),
                "evalue": parts[10],
                "bitscore": parts[11],
                "title": parts[12] if len(parts) > 12 else parts[1],
            })

    if not hits:
        return f"BLAST (local, {elapsed:.1f}s): No significant similarity found."

    result_lines = [f"=== BLAST Hits (local, {elapsed:.1f}s) ==="]
    for i, h in enumerate(hits, 1):
        result_lines.append(
            f"  {i}. {h['title'][:120]}"
        )
        result_lines.append(
            f"     Identity: {h['identity']:.1f}% | Length: {h['length']} | "
            f"E-value: {h['evalue']} | Score: {h['bitscore']}"
        )

    result_lines.append(f"\n{len(hits)} hits found.")
    return "\n".join(result_lines)


# ─── Remote NCBI BLAST (fallback) ────────────────────────────────────────────

def _blast_remote(sequence: str, db: str, program: str, evalue: float,
                  max_hits: int) -> str:
    """Submit BLAST to NCBI web API (slow, 1-5 min)."""
    log.info("Using remote NCBI BLAST (this may take 1-5 minutes)...")

    put_params = {
        "CMD": "Put",
        "PROGRAM": program,
        "DATABASE": db,
        "QUERY": sequence[:10000],
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

    rid = _extract_rid(resp.text)
    if not rid:
        return "[ERROR] Could not get BLAST request ID from response"

    log.info("BLAST submitted — RID: %s, waiting for results...", rid)

    result_text = _poll_results(rid)
    if result_text.startswith("[ERROR]"):
        return result_text

    return _summarize_remote(result_text, max_hits)


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
            return resp.text
        except Exception as e:
            log.warning("Poll error: %s", e)

    return f"[ERROR] BLAST timed out after {MAX_WAIT_SECONDS}s"


def _summarize_remote(raw_text: str, max_hits: int) -> str:
    """Extract key info from BLAST text output."""
    lines = raw_text.split("\n")
    summary_lines = []
    in_descriptions = False
    hit_count = 0

    for line in lines:
        if "Sequences producing significant alignments" in line:
            in_descriptions = True
            summary_lines.append("=== BLAST Hits (remote NCBI) ===")
            continue
        if in_descriptions and line.strip() and hit_count < max_hits:
            if line.startswith(">") or line.startswith(" "):
                summary_lines.append(line.rstrip()[:200])
                hit_count += 1
            if line.strip() == "":
                in_descriptions = False

        if "No significant similarity found" in line:
            return "BLAST (remote): No significant similarity found."

    if not summary_lines:
        meaningful = [l for l in lines if l.strip() and not l.startswith("<!")]
        return "BLAST results (raw):\n" + "\n".join(meaningful[:20])

    return "\n".join(summary_lines)


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _resolve_sequence(sequence: str) -> str:
    """If sequence is a filepath or filename, read the FASTA and return raw sequence."""
    sequence = sequence.strip()

    is_path = (
        os.sep in sequence
        or "/" in sequence
        or sequence.endswith(".fasta")
        or sequence.endswith(".fa")
    )
    if not is_path:
        return sequence

    candidates = [sequence]
    if not os.path.isabs(sequence):
        candidates.append(os.path.join(SEQUENCES_DIR, sequence))
        candidates.append(os.path.join(SEQUENCES_DIR, os.path.basename(sequence)))

    filepath = None
    for c in candidates:
        if os.path.isfile(c):
            filepath = c
            break

    if not filepath:
        return f"[ERROR] FASTA file not found: {sequence} (looked in {SEQUENCES_DIR})"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"[ERROR] Could not read {filepath}: {e}"

    seq_lines = [l.strip() for l in lines if l.strip() and not l.startswith(">")]
    raw = "".join(seq_lines)

    if len(raw) < 10:
        return f"[ERROR] Sequence in {os.path.basename(filepath)} too short ({len(raw)} chars)"

    log.info("Resolved BLAST sequence from file: %s (%d bp/aa)", filepath, len(raw))
    return raw


def _looks_like_protein(seq: str) -> bool:
    """Heuristic: protein seqs have letters beyond ATCGN."""
    cleaned = seq.upper().replace(" ", "").replace("\n", "")
    non_dna = set(cleaned) - set("ATCGNU\n ")
    return len(non_dna) > 2


# ─── Database management utility ─────────────────────────────────────────────

def download_blast_db(db_name: str = "swissprot") -> str:
    """
    Download a BLAST database using update_blastdb.pl.
    Call this once to set up local databases.

    Small databases (good for genomics research):
      - swissprot (~250 MB) — curated protein sequences
      - refseq_select_rna (~2 GB) — curated RefSeq RNA
      - refseq_protein (~30 GB) — all RefSeq proteins

    Large databases (comprehensive but huge):
      - nt (~100 GB) — all nucleotide sequences
      - nr (~100 GB) — all non-redundant protein sequences
    """
    update_script = os.path.join(BLAST_BIN_DIR, "update_blastdb.pl")

    # Check if perl is available
    perl = shutil.which("perl")
    if not perl:
        return (
            f"[ERROR] Perl not found. To download databases manually:\n"
            f"1. Go to https://ftp.ncbi.nlm.nih.gov/blast/db/\n"
            f"2. Download {db_name}.*.tar.gz files\n"
            f"3. Extract them into {BLAST_DB_DIR}"
        )

    if not os.path.isfile(update_script):
        return (
            f"[ERROR] update_blastdb.pl not found at {update_script}\n"
            f"Install BLAST+ first: https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/"
        )

    cmd = [
        perl, update_script,
        "--passive", "--decompress",
        "--blastdb_version", "5",
        db_name,
    ]

    log.info("Downloading BLAST database '%s' to %s ...", db_name, BLAST_DB_DIR)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=BLAST_DB_DIR, timeout=3600,  # 1 hour max
        )
        if result.returncode == 0:
            log.info("Database '%s' downloaded successfully", db_name)
            return f"Database '{db_name}' downloaded to {BLAST_DB_DIR}"
        else:
            return f"[ERROR] Download failed: {result.stderr[:500]}"
    except subprocess.TimeoutExpired:
        return "[ERROR] Database download timed out (1 hour)"
    except Exception as e:
        return f"[ERROR] Download failed: {e}"
