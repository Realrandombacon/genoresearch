"""
OpenAI-compatible provider helpers — shared HTTP logic for Cerebras and Groq.
"""

import re
import logging
import requests

log = logging.getLogger("genoresearch.llm")

# Regex to extract Qwen <think>...</think> blocks
_THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def _extract_thinking(content: str) -> str:
    """Extract and format <think> blocks from content."""
    thinking_parts = _THINK_PATTERN.findall(content)
    visible = _THINK_PATTERN.sub("", content).strip()

    if thinking_parts:
        thinking = "\n".join(t.strip() for t in thinking_parts if t.strip())
        if visible:
            return f"[Reasoning] {thinking}\n\n{visible}"
        return f"[Reasoning] {thinking}"
    return content


def _chat_openai_compatible(url: str, api_key: str, model: str,
                            messages: list[dict], temperature: float,
                            top_p: float, max_tokens: int, timeout: int,
                            extra_headers: dict = None,
                            extra_payload: dict = None) -> str:
    """Common HTTP POST + response extraction for OpenAI-compatible APIs."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    if extra_payload:
        payload.update(extra_payload)

    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    return _extract_thinking(content)


def _build_recovery_prompt(thought_text: str) -> str:
    """Build the shared recovery prompt template."""
    summary = thought_text
    if summary.startswith("[Reasoning]"):
        summary = summary[len("[Reasoning]"):].strip()
    summary = summary[:800]

    return (
        f"You just analyzed data and concluded:\n{summary}\n\n"
        "NOW respond with ONLY a TOOL: line. No explanations. No THOUGHT blocks.\n"
        "Pick the most logical next step.\n\n"
        "Examples:\n"
        "TOOL: ncbi_search('BRCA1', db='gene')\n"
        "TOOL: save_finding('title', 'description', 'evidence')\n"
        "TOOL: next_gene()\n"
        "TOOL: save_finding('gene - title', 'description', 'evidence')\n"
    )


def _recovery_openai_compatible(url: str, api_key: str, model: str,
                                thought_text: str, temperature: float,
                                timeout: int) -> str:
    """Common recovery logic for OpenAI-compatible APIs."""
    recovery_prompt = _build_recovery_prompt(thought_text)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a genomics research agent. Respond with ONLY a TOOL: line. No other text."},
            {"role": "user", "content": recovery_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 200,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    return content if content else ""
