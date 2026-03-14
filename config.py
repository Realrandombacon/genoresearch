"""
Genoresearch — Shared configuration
Paths, directories, constants, and UTF-8 setup for Windows.
"""

import os
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEQUENCES_DIR = os.path.join(DATA_DIR, "sequences")
ALIGNMENTS_DIR = os.path.join(DATA_DIR, "alignments")
FINDINGS_DIR = os.path.join(BASE_DIR, "findings")
FINDINGS_FILE = os.path.join(BASE_DIR, "findings.tsv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
RESEARCH_LOG = os.path.join(BASE_DIR, "research.log")
DASHBOARD_STATUS = os.path.join(BASE_DIR, "dashboard_status.json")
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")

# ---------------------------------------------------------------------------
# Lab (ML training) paths
# ---------------------------------------------------------------------------

LAB_DIR = os.path.join(BASE_DIR, "lab")
LAB_RUNS_DIR = os.path.join(DATA_DIR, "runs")
LAB_CHECKPOINTS_DIR = os.path.join(DATA_DIR, "checkpoints")

# ---------------------------------------------------------------------------
# External APIs
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3.5:4b"

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
UNIPROT_BASE_URL = "https://rest.uniprot.org"

# Optional — set in environment for higher NCBI rate limits
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")

# ---------------------------------------------------------------------------
# Ensure required directories exist
# ---------------------------------------------------------------------------

for _d in [DATA_DIR, SEQUENCES_DIR, ALIGNMENTS_DIR, FINDINGS_DIR,
           REPORTS_DIR, LAB_RUNS_DIR, LAB_CHECKPOINTS_DIR]:
    os.makedirs(_d, exist_ok=True)
