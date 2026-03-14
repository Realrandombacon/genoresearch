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
        log.error("Ollama request timed out after 120s")
        return "[ERROR] Ollama timeout."
    except Exception as e:
        log.error("LLM call failed: %s", e)
        return f"[ERROR] {e}"


def build_system_prompt(context: str = "") -> dict:
    """Build the system message for the genomics research agent."""
    base = (
        "You are an autonomous genomics research agent.\n\n"
        "MISSION: ~20,000 protein-coding genes exist in the human genome but only ~2,000\n"
        "are well-studied. Explore the other ~17,000 'dark genes' — find clues about\n"
        "what they do using sequence analysis, homology, and database mining.\n\n"
        "ARCHITECTURE: There is no human in the loop. All messages come from the\n"
        "orchestrator (a Python program). Tool results are automated API responses.\n"
        "You decide your own research strategy. Be creative and methodical.\n\n"
        "Available tools (call with TOOL: function_name(params)):\n"
        "  ncbi_search(query, db='gene', max_results=5)\n"
        "  ncbi_fetch(accession_id, db='nucleotide')\n"
        "  blast_search(sequence, db='nt', evalue=0.01)  # pass .fasta filename\n"
        "  uniprot_search(query, max_results=5)\n"
        "  uniprot_fetch(accession_id)\n"
        "  analyze_sequence(filepath)\n"
        "  compare_sequences(file1, file2)\n"
        "  translate_sequence(filepath)\n"
        "  pubmed_search(query, max_results=5)\n"
        "  gene_info(gene_name)\n"
        "  save_finding(title, description, evidence)\n"
        "  list_findings()\n"
        "  read_finding(number)\n"
        "  list_sequences()\n"
        "  read_file(filepath)\n"
        "  query_memory(question)\n"
        "  my_stats()\n"
        "  note(text)\n"
        "  next_gene()\n"
        "  add_to_queue(gene, source='...')\n"
        "  complete_step(step_name)\n"
        "  complete_gene()\n"
        "  skip_gene(reason)\n"
        "  advance_seed()\n"
        "  queue_status()\n"
        "  lab_train(config_name)\n"
        "  lab_status()\n\n"
        "Constraints:\n"
        "  - Only use accession IDs that appear in search results.\n"
        "  - For BLAST: pass the .fasta filename, not raw sequence.\n"
    )
    if context:
        base += f"\nCurrent research context:\n{context}\n"
    return {"role": "system", "content": base}
