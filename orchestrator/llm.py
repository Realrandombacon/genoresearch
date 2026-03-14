"""
LLM client — talks to Ollama (local) or any OpenAI-compatible endpoint.
"""

import json
import logging
import re
import requests

from config import OLLAMA_URL, OLLAMA_MODEL

# Regex to extract Qwen <think>...</think> blocks
_THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)

log = logging.getLogger("genoresearch.llm")


def chat(messages: list[dict], model: str = None, temperature: float = 0.3,
         top_p: float = 0.9, max_tokens: int = 4096) -> str:
    """Send a chat completion request to Ollama and return the response text."""
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,  # Disable thinking — saves tokens, forces direct output
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
            "num_ctx": 16000,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "").strip()

        # Qwen 3.5 puts reasoning in <think>...</think> tags inside content,
        # OR Ollama may return it in a separate "thinking" field.
        thinking = ""

        # Check for separate thinking field (Ollama >=0.9)
        msg = data.get("message", {})
        if msg.get("thinking"):
            thinking = msg["thinking"].strip()

        # Also check for <think> tags inside content itself
        thinking_parts = _THINK_PATTERN.findall(content)
        visible = _THINK_PATTERN.sub("", content).strip()

        if thinking_parts:
            tag_thinking = "\n".join(t.strip() for t in thinking_parts if t.strip())
            thinking = f"{thinking}\n{tag_thinking}" if thinking else tag_thinking

        if thinking:
            # Return thinking + visible content so the UI can display reasoning
            return f"[Reasoning] {thinking}\n\n{visible}" if visible else f"[Reasoning] {thinking}"

        return content
    except requests.exceptions.ConnectionError:
        log.error("Cannot connect to Ollama at %s — is it running?", OLLAMA_URL)
        return "[ERROR] Ollama not reachable."
    except requests.exceptions.Timeout:
        log.error("Ollama request timed out after 300s")
        return "[ERROR] Ollama timeout."
    except Exception as e:
        log.error("LLM call failed: %s", e)
        return f"[ERROR] {e}"


def build_system_prompt(context: str = "") -> dict:
    """Build the system message for the genomics research agent."""
    base = """MISSION: ~20,000 protein-coding genes exist in the human genome but only ~2,000
are well-studied. Explore the other ~17,000 'dark genes' — find clues about
what they do using sequence analysis, homology, and database mining.

All messages come from the orchestrator (a Python program).
Tool results are automated API responses. There is no human in the loop.
Decide your own research strategy. Be creative and methodical.

Available tools (ALWAYS use key=value format for parameters):

  Database search:
  - ncbi_search(query='BRCA1', db='gene', max_results=5)
  - ncbi_fetch(accession_id='NM_007294', db='nucleotide')
  - uniprot_search(query='BRCA1 human', max_results=5)
  - uniprot_fetch(accession_id='P38398')
  - pubmed_search(query='BRCA1 cancer therapy', max_results=5)
  - gene_info(gene_name='BRCA1')

  Sequence analysis:
  - analyze_sequence(filepath='NM_007294.fasta')
  - compare_sequences(file1='seq1.fasta', file2='seq2.fasta')
  - translate_sequence(filepath='NM_007294.fasta')
  - blast_search(sequence='NM_007294.fasta', db='nt', evalue=0.01)

  Research tracking:
  - save_finding(title='Discovery X', description='Details...', evidence='NM_007294')
  - list_findings()
  - read_finding(finding_id=1)
  - review_findings(start=1, end=5, focus='keyword')
  - list_sequences()
  - read_file(filepath='filename')

  Memory & progress:
  - query_memory(question='What genes have I studied?')
  - my_stats()
  - note(text='Observation about gene X')
  - mark_explored(target='GENE1')
  - mark_done(target='GENE1')
  - dismiss(target='GENE1', reason='Not a dark gene')
  - list_unexplored()

  Gene queue:
  - next_gene()
  - add_to_queue(gene='LOC12345', source='NCBI search')
  - complete_step(step='sequence_analysis')
  - complete_gene()
  - skip_gene(reason='Withdrawn from NCBI')
  - advance_seed()
  - queue_status()

  ML lab:
  - lab_train(config_name='default')
  - lab_status()

How to investigate a gene — example workflow:

  Cycle 1 — Get gene info:
    TOOL: gene_info(gene_name='LOC12345')
    TOOL: ncbi_search(query='LOC12345', db='nucleotide')

  Cycle 2 — Fetch and analyze sequence:
    TOOL: ncbi_fetch(accession_id='NM_XXXXX', db='nucleotide')

  Cycle 3 — Analyze:
    TOOL: analyze_sequence(filepath='NM_XXXXX.fasta')
    TOOL: translate_sequence(filepath='NM_XXXXX.fasta')

  Cycle 4 — Homology search:
    TOOL: blast_search(sequence='NM_XXXXX.fasta', db='nt')
    TOOL: uniprot_search(query='LOC12345 human')

  Cycle 5 — Record findings:
    TOOL: save_finding(title='LOC12345 analysis', description='Found X...', evidence='NM_XXXXX')
    TOOL: complete_gene()

Format (MUST use parentheses and key=value):
  TOOL: ncbi_search(query='TP53', db='gene')
  TOOL: analyze_sequence(filepath='NM_007294.fasta')
  TOOL: save_finding(title='Discovery', description='Details', evidence='Source')

Constraints:
  - ALWAYS use key=value format: TOOL: func(key='value', key2='value2')
  - Only use accession IDs that appear in search results.
  - For BLAST: pass the .fasta filename, not raw sequence.
  - For analyze_sequence: just pass the filename (e.g. 'NM_007294.fasta'), not the full path.
  - Call ONE tool per TOOL: line. You can call multiple tools per response.
"""
    if context:
        base += f"\nCurrent research context:\n{context}\n"
    return {"role": "system", "content": base}
