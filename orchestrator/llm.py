"""
LLM client — talks to Ollama (local) or any OpenAI-compatible endpoint.
"""

import json
import logging
import requests

from config import OLLAMA_URL, OLLAMA_MODEL

log = logging.getLogger("genoresearch.llm")


def chat(messages: list[dict], model: str = None, temperature: float = 0.1,
         top_p: float = 0.85, max_tokens: int = 4096) -> str:
    """Send a chat completion request to Ollama and return the response text."""
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        log.error("Cannot connect to Ollama at %s — is it running?", OLLAMA_URL)
        return "[ERROR] Ollama not reachable."
    except requests.exceptions.Timeout:
        log.error("Ollama request timed out after 120s")
        return "[ERROR] Ollama timeout."
    except Exception as e:
        log.error("LLM call failed: %s", e)
        return f"[ERROR] {e}"


def build_system_prompt(context: str = "") -> dict:
    """Build the system message for the genomics research agent."""
    base = (
        "You are GenoResearch, an autonomous genomics research agent.\n"
        "Your goal: discover novel patterns in genomic data by querying databases,\n"
        "analyzing sequences, and running ML experiments.\n\n"
        "Available tools (call with TOOL: function_name(params)):\n"
        "  - ncbi_search(query, db='gene', max_results=5)\n"
        "  - ncbi_fetch(accession_id, db='nucleotide')\n"
        "  - blast_search(sequence, db='nt', evalue=0.01)\n"
        "  - uniprot_search(query, max_results=5)\n"
        "  - uniprot_fetch(accession_id)\n"
        "  - analyze_sequence(filepath)\n"
        "  - compare_sequences(file1, file2)\n"
        "  - lab_train(config_name)\n"
        "  - lab_status()\n"
        "  - save_finding(title, description, evidence)\n"
        "  - query_memory(question)\n"
        "  - list_findings()\n"
        "  - my_stats()\n"
        "  - list_unexplored()\n\n"
        "Rules:\n"
        "  1. Always explain your reasoning before calling a tool.\n"
        "  2. One TOOL call per response.\n"
        "  3. After receiving results, analyze them before the next action.\n"
        "  4. Log any novel or unexpected finding immediately.\n"
        "  5. Be systematic — don't repeat queries you've already done.\n"
        "  6. IMPORTANT — fetching sequences:\n"
        "     - To get a gene's mRNA: ncbi_search('GENE_NAME', db='nucleotide') → returns NM_ accessions.\n"
        "     - Then fetch: TOOL: ncbi_fetch('NM_XXXXX', db='nucleotide')\n"
        "     - Gene db results show chromosome accessions (NC_) — do NOT fetch those.\n"
        "     - NEVER invent accession numbers. Only use accessions shown in search results.\n"
    )
    if context:
        base += f"\nCurrent research context:\n{context}\n"
    return {"role": "system", "content": base}
