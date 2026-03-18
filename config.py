"""
Genoresearch — Shared configuration
Paths, directories, constants, and UTF-8 setup for Windows.
"""

import os
import sys

# Load .env file if present (API keys, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

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

# Tier 1 — primary: large local model (best quality)
OLLAMA_MODEL_PRIMARY = "qwen3.5:cloud"
# Tier 4 — fallback: small local model (always available)
OLLAMA_MODEL_FALLBACK = "qwen3.5:4b"
# Legacy alias (used by code that just needs "the ollama model")
OLLAMA_MODEL = OLLAMA_MODEL_PRIMARY

# Tier 2 — Cerebras cloud API (free tier, very fast, 1M tokens/day)
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "qwen-3-235b-a22b-instruct-2507"  # 1M tokens/day, 30 RPM

# Tier 3 — Groq cloud API (free tier, fast, backup)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # 30K TPM, fast

# Active provider: "ollama", "groq", "cerebras", or "hybrid" (recommended)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "hybrid")

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
UNIPROT_BASE_URL = "https://rest.uniprot.org"

# Optional — set in environment for higher NCBI rate limits
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")

# ---------------------------------------------------------------------------
# Local BLAST+ configuration
# ---------------------------------------------------------------------------

# Path to BLAST+ binaries (auto-detected if on PATH, else check default install)
BLAST_BIN_DIR = os.environ.get(
    "BLAST_BIN_DIR", r"C:\Program Files\NCBI\blast-2.17.0+\bin"
)
BLAST_DB_DIR = r"C:\blastdb"
# Use local BLAST when available, fallback to remote NCBI
BLAST_LOCAL_ENABLED = True

# ---------------------------------------------------------------------------
# Orchestrator limits
# ---------------------------------------------------------------------------

MAX_TURNS = 20
SOFT_TURNS = 12
LOOP_THRESHOLD = 2
MAX_RESULT_LENGTH = 3000

# ---------------------------------------------------------------------------
# LLM defaults
# ---------------------------------------------------------------------------

LLM_MAX_TOKENS = 16384
LLM_CONTEXT_WINDOW = 16000
RECOVERY_MAX_TOKENS = 500
GROQ_MIN_INTERVAL = 1.0
FAILOVER_MAX_WAIT = 60

# ---------------------------------------------------------------------------
# API timeouts
# ---------------------------------------------------------------------------

API_TIMEOUT = 30
BLAST_TIMEOUT = 120
DOWNLOAD_TIMEOUT = 3600

# ---------------------------------------------------------------------------
# Ensure required directories exist
# ---------------------------------------------------------------------------

for _d in [DATA_DIR, SEQUENCES_DIR, ALIGNMENTS_DIR, FINDINGS_DIR,
           REPORTS_DIR, LAB_RUNS_DIR, LAB_CHECKPOINTS_DIR, BLAST_DB_DIR]:
    os.makedirs(_d, exist_ok=True)
