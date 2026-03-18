"""
LLM client — 4-tier provider system with automatic failover.

Tier 1: Ollama qwen3.5:cloud       — large cloud model via Ollama, best quality
Tier 2: Cerebras Qwen 3 235B       — cloud, free, 1M tokens/day, fast
Tier 3: Groq Llama 4 Scout         — cloud, free, 30K TPM (rate-limited)
Tier 4: Ollama qwen3.5:4b          — small local model, always available

In hybrid mode (default), the system cascades down tiers on failure.
Zero downtime.
"""

import logging
import re
import time
import requests

from config import (
    OLLAMA_URL, OLLAMA_MODEL_PRIMARY, OLLAMA_MODEL_FALLBACK,
    CEREBRAS_URL, CEREBRAS_API_KEY, CEREBRAS_MODEL,
    GROQ_URL, GROQ_API_KEY, GROQ_MODEL,
    LLM_PROVIDER,
)
from orchestrator.providers import (
    _chat_openai_compatible, _recovery_openai_compatible,
)

def _ui_log(level, msg):
    """Lazy import to avoid circular dependency."""
    try:
        from agent.ui import log as _log
        _log(level, msg)
    except ImportError:
        print(f"  [{level}] {msg}")

# Regex to extract Qwen <think>...</think> blocks
_THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)

log = logging.getLogger("genoresearch.llm")

# Runtime provider override (set by main.py --provider)
_provider_override = None

from config import (
    GROQ_MIN_INTERVAL as _GROQ_MIN_INTERVAL_CFG,
    FAILOVER_MAX_WAIT as _FAILOVER_MAX_WAIT_CFG,
    RECOVERY_MAX_TOKENS as _RECOVERY_MAX_TOKENS,
    LLM_CONTEXT_WINDOW as _LLM_CONTEXT_WINDOW,
)

# Groq rate limiter
_GROQ_MIN_INTERVAL = _GROQ_MIN_INTERVAL_CFG
_groq_last_request = 0.0

# ─── Failover state ─────────────────────────────────────────────────────────

_cerebras_available_at = 0.0     # timestamp when Cerebras cooldown ends
_cerebras_failover_count = 0     # how many times Cerebras has failed over
# Moonshot removed — abandoned due to excessive rate-limiting delays
_groq_available_at = 0.0         # timestamp when Groq cooldown ends
_groq_failover_count = 0         # how many times we've failed over this session
_ollama_primary_down = False     # True if primary Ollama model failed
_ollama_primary_retry_at = 0.0   # when to try primary again
_FAILOVER_MAX_WAIT = _FAILOVER_MAX_WAIT_CFG


def _parse_groq_reset(reset_str: str) -> float:
    """Parse Groq reset time like '11m31.2s' or '500ms' into seconds."""
    total = 0.0
    m = re.search(r"(\d+)m", reset_str)
    if m:
        total += int(m.group(1)) * 60
    s = re.search(r"([\d.]+)s", reset_str)
    if s:
        total += float(s.group(1))
    ms = re.search(r"(\d+)ms", reset_str)
    if ms and not s:
        total += int(ms.group(1)) / 1000
    return total if total > 0 else 30


def _groq_throttle():
    """Wait if needed to stay under Groq rate limits."""
    global _groq_last_request
    now = time.time()
    elapsed = now - _groq_last_request
    if elapsed < _GROQ_MIN_INTERVAL:
        time.sleep(_GROQ_MIN_INTERVAL - elapsed)
    _groq_last_request = time.time()


def _groq_is_available() -> bool:
    return time.time() >= _groq_available_at


def _groq_set_cooldown(seconds: float):
    global _groq_available_at, _groq_failover_count
    _groq_available_at = time.time() + seconds
    _groq_failover_count += 1
    log.warning("Groq rate limited — cooldown %.0fs — failover #%d", seconds, _groq_failover_count)


def _get_groq_wait(resp) -> float:
    reset = resp.headers.get("x-ratelimit-reset-tokens", "")
    retry_after = _parse_groq_reset(reset) if reset else 30
    retry_after = max(retry_after, float(resp.headers.get("retry-after", 5)))
    return retry_after


def _ollama_primary_available() -> bool:
    global _ollama_primary_down
    if not _ollama_primary_down:
        return True
    if time.time() >= _ollama_primary_retry_at:
        _ollama_primary_down = False
        log.info("Retrying primary Ollama model...")
        return True
    return False


def _ollama_primary_set_down(seconds: float = 30):
    global _ollama_primary_down, _ollama_primary_retry_at
    _ollama_primary_down = True
    _ollama_primary_retry_at = time.time() + seconds
    log.warning("Primary Ollama model unavailable — retry in %.0fs", seconds)


# ─── Provider management ────────────────────────────────────────────────────

def set_provider(provider: str):
    """Override the active LLM provider at runtime."""
    global _provider_override
    _provider_override = provider.lower()
    log.info("LLM provider set to: %s", _provider_override)


def get_provider() -> str:
    """Get the configured LLM provider."""
    return _provider_override or LLM_PROVIDER


def get_active_tier() -> str:
    """Get which tier is currently active.

    Returns: 'tier1'–'tier4'
    """
    configured = get_provider()

    if configured == "hybrid":
        if _ollama_primary_available():
            return "tier1"
        if CEREBRAS_API_KEY and _cerebras_is_available():
            return "tier2"
        if GROQ_API_KEY and _groq_is_available():
            return "tier3"
        return "tier4"

    if configured == "cerebras":
        if _cerebras_is_available():
            return "tier2"
        return "tier4"

    if configured == "groq":
        if _groq_is_available():
            return "tier3"
        return "tier4"

    return "tier1"  # ollama-only mode


def get_model() -> str:
    """Get the default model for the currently active tier."""
    tier = get_active_tier()
    if tier == "tier1":
        return OLLAMA_MODEL_PRIMARY
    if tier == "tier2":
        return CEREBRAS_MODEL
    if tier == "tier3":
        return GROQ_MODEL
    return OLLAMA_MODEL_FALLBACK


def get_provider_status() -> str:
    """Human-readable provider status for UI/banner."""
    configured = get_provider()
    tier = get_active_tier()

    if configured == "hybrid":
        parts = []
        if tier == "tier1":
            parts.append(f">>> T1: {OLLAMA_MODEL_PRIMARY} (active)")
        else:
            reason = "down" if _ollama_primary_down else ""
            parts.append(f"    T1: {OLLAMA_MODEL_PRIMARY} ({reason})")

        if tier == "tier2":
            parts.append(f">>> T2: cerebras/{CEREBRAS_MODEL} (active)")
        elif _cerebras_is_available():
            parts.append("    T2: cerebras (ready)")
        else:
            remaining = max(0, _cerebras_available_at - time.time())
            parts.append(f"    T2: cerebras (cooldown {remaining:.0f}s)")

        if tier == "tier3":
            parts.append(f">>> T3: groq/{GROQ_MODEL.split('/')[-1]} (active)")
        elif _groq_is_available():
            parts.append("    T3: groq (ready)")
        else:
            remaining = max(0, _groq_available_at - time.time())
            parts.append(f"    T3: groq (cooldown {remaining:.0f}s)")

        if tier == "tier4":
            parts.append(f">>> T4: {OLLAMA_MODEL_FALLBACK} (active)")
        else:
            parts.append(f"    T4: {OLLAMA_MODEL_FALLBACK} (standby)")

        return "hybrid | " + " | ".join(parts)

    if configured == "cerebras":
        if _cerebras_is_available():
            return f"cerebras ({CEREBRAS_MODEL})"
        return f"ollama/{OLLAMA_MODEL_FALLBACK} [cerebras cooldown]"

    if configured == "groq":
        if _groq_is_available():
            return f"groq ({GROQ_MODEL.split('/')[-1]})"
        return f"ollama/{OLLAMA_MODEL_FALLBACK} [groq cooldown]"

    return f"ollama ({OLLAMA_MODEL_PRIMARY})"


# ─── Ollama engine ───────────────────────────────────────────────────────────

def _chat_ollama(messages: list[dict], model: str = None, temperature: float = 0.1,
                 top_p: float = 0.85, max_tokens: int = 16384) -> str:
    """Send chat to Ollama (local)."""
    model = model or OLLAMA_MODEL_PRIMARY
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
            "num_ctx": _LLM_CONTEXT_WINDOW,
        },
    }

    # Try up to 2 times with short timeout before giving up
    max_attempts = 2 if model == OLLAMA_MODEL_PRIMARY else 1
    for attempt in range(max_attempts):
        try:
            timeout = 30 if model == OLLAMA_MODEL_PRIMARY else 180
            resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "").strip()

            thinking = ""
            msg = data.get("message", {})
            if msg.get("thinking"):
                thinking = msg["thinking"].strip()

            thinking_parts = _THINK_PATTERN.findall(content)
            visible = _THINK_PATTERN.sub("", content).strip()

            if thinking_parts:
                tag_thinking = "\n".join(t.strip() for t in thinking_parts if t.strip())
                thinking = f"{thinking}\n{tag_thinking}" if thinking else tag_thinking

            if thinking:
                return f"[Reasoning] {thinking}\n\n{visible}" if visible else f"[Reasoning] {thinking}"
            return content

        except requests.exceptions.ConnectionError:
            log.error("Cannot connect to Ollama at %s", OLLAMA_URL)
            return None  # signal failover
        except requests.exceptions.Timeout:
            if attempt < max_attempts - 1:
                log.warning("Ollama timeout (attempt %d/%d, model=%s) — retrying...",
                           attempt + 1, max_attempts, model)
                continue  # retry once
            log.error("Ollama request timed out after %d attempts (model=%s)", max_attempts, model)
            return None  # signal failover
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            if status == 429:
                log.warning("Ollama 429 rate limited — signaling failover")
                _ollama_primary_set_down(15)  # very short cooldown — retry soon
                return None  # signal failover to next tier
            if status == 404:
                log.error("Ollama model '%s' not found", model)
                return None
            log.error("Ollama HTTP error: %s", e)
            return None  # any HTTP error should trigger failover
        except (ValueError, KeyError) as e:
            log.error("Ollama call failed (parse error): %s", e)
            return None  # signal failover on unexpected errors too


def _recovery_ollama(thought_text: str, model: str = None,
                     temperature: float = 0.5) -> str:
    """Recovery reprompt via Ollama."""
    model = model or OLLAMA_MODEL_FALLBACK  # recovery uses small model for speed

    summary = thought_text
    if summary.startswith("[Reasoning]"):
        summary = summary[len("[Reasoning]"):].strip()
    summary = summary[:800]

    recovery_prompt = (
        f"You just analyzed data and concluded:\n{summary}\n\n"
        "NOW respond with ONLY a TOOL: line. No explanations. No THOUGHT blocks.\n"
        "Pick the most logical next step.\n\n"
        "Examples:\n"
        "TOOL: ncbi_search('BRCA1', db='gene')\n"
        "TOOL: save_finding('title', 'description', 'evidence')\n"
        "TOOL: next_gene()\n"
        "TOOL: save_finding('gene - title', 'description', 'evidence')\n"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a genomics research agent. Respond with ONLY a TOOL: line. No other text."},
            {"role": "user", "content": recovery_prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": _RECOVERY_MAX_TOKENS,
            "num_ctx": 4000,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "").strip()
        if not content:
            return ""
        log.info("Recovery response (%s): %d chars", model, len(content))
        return content
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError) as e:
        log.error("Recovery reprompt failed: %s", e)
        return ""


# ─── Cerebras state helpers ──────────────────────────────────────────────────

def _cerebras_is_available() -> bool:
    return time.time() >= _cerebras_available_at


def _cerebras_set_cooldown(seconds: float):
    global _cerebras_available_at, _cerebras_failover_count
    _cerebras_available_at = time.time() + seconds
    _cerebras_failover_count += 1
    log.warning("Cerebras rate limited — cooldown %.0fs — failover #%d",
                seconds, _cerebras_failover_count)


# ─── Cerebras engine ────────────────────────────────────────────────────────

def _chat_cerebras(messages: list[dict], model: str = None, temperature: float = 0.1,
                   top_p: float = 0.85, max_tokens: int = 16384) -> str | None:
    """Send chat to Cerebras (OpenAI-compatible). Returns None to signal failover."""
    model = model or CEREBRAS_MODEL

    try:
        # First attempt
        try:
            return _chat_openai_compatible(
                CEREBRAS_URL, CEREBRAS_API_KEY, model, messages,
                temperature, top_p, min(max_tokens, 16384), timeout=120,
            )
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                retry_after = float(e.response.headers.get("retry-after", 60))
                if retry_after <= _FAILOVER_MAX_WAIT:
                    log.info("Cerebras rate limited — short wait %.0fs", retry_after)
                    time.sleep(retry_after)
                    # Retry once
                    try:
                        return _chat_openai_compatible(
                            CEREBRAS_URL, CEREBRAS_API_KEY, model, messages,
                            temperature, top_p, min(max_tokens, 16384), timeout=120,
                        )
                    except requests.exceptions.HTTPError as e2:
                        if hasattr(e2, 'response') and e2.response is not None and e2.response.status_code == 429:
                            retry_after = float(e2.response.headers.get("retry-after", 300))
                            _cerebras_set_cooldown(retry_after)
                            return None
                        raise
                else:
                    _cerebras_set_cooldown(retry_after)
                    return None
            raise

    except requests.exceptions.ConnectionError:
        log.error("Cannot connect to Cerebras API")
        _cerebras_set_cooldown(300)
        return None
    except requests.exceptions.Timeout:
        log.error("Cerebras timeout")
        _cerebras_set_cooldown(120)
        return None
    except (KeyError, requests.exceptions.HTTPError) as e:
        log.error("Cerebras call failed: %s", e)
        _cerebras_set_cooldown(120)
        return None


def _recovery_cerebras(thought_text: str, model: str = None,
                       temperature: float = 0.5) -> str | None:
    """Recovery reprompt via Cerebras. Returns None to signal failover."""
    model = model or CEREBRAS_MODEL

    try:
        return _recovery_openai_compatible(
            CEREBRAS_URL, CEREBRAS_API_KEY, model,
            thought_text, temperature, timeout=60,
        )
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            _cerebras_set_cooldown(float(e.response.headers.get("retry-after", 300)))
            return None
        log.error("Cerebras recovery failed: %s", e)
        return None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, KeyError) as e:
        log.error("Cerebras recovery failed: %s", e)
        return None



# ─── Groq engine ─────────────────────────────────────────────────────────────

def _trim_for_groq(messages: list[dict], max_messages: int = 8) -> list[dict]:
    """Trim message count for Groq TPM limits. Same prompt, fewer messages."""
    if len(messages) <= max_messages + 1:
        return messages

    system = messages[0]
    recent = messages[-(max_messages):]

    trimmed = [system]
    for msg in recent:
        content = msg.get("content", "")
        if len(content) > 600 and msg.get("role") == "user":
            content = content[:500] + "\n... (truncated)"
        trimmed.append({"role": msg["role"], "content": content})

    return trimmed


    # No special trimming for T3 — it gets the same full messages as GitHub version.
    # The 4B model runs with think=False and the same prompt as T1/T2.


def _chat_groq(messages: list[dict], model: str = None, temperature: float = 0.1,
               top_p: float = 0.85, max_tokens: int = 8192) -> str | None:
    """Send chat to Groq. Returns None to signal failover."""
    model = model or GROQ_MODEL
    max_tokens = min(max_tokens, 8192)
    trimmed_messages = _trim_for_groq(messages)

    try:
        _groq_throttle()
        try:
            return _chat_openai_compatible(
                GROQ_URL, GROQ_API_KEY, model, trimmed_messages,
                temperature, top_p, max_tokens, timeout=120,
            )
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                wait = _get_groq_wait(e.response)
                if wait <= _FAILOVER_MAX_WAIT:
                    log.info("Groq rate limited — short wait %.0fs", wait)
                    time.sleep(wait)
                    _groq_throttle()
                    try:
                        return _chat_openai_compatible(
                            GROQ_URL, GROQ_API_KEY, model, trimmed_messages,
                            temperature, top_p, max_tokens, timeout=120,
                        )
                    except requests.exceptions.HTTPError as e2:
                        if hasattr(e2, 'response') and e2.response is not None and e2.response.status_code == 429:
                            _groq_set_cooldown(_get_groq_wait(e2.response))
                            return None
                        raise
                else:
                    _groq_set_cooldown(wait)
                    return None
            raise

    except requests.exceptions.ConnectionError:
        log.error("Cannot connect to Groq API")
        _groq_set_cooldown(300)
        return None
    except requests.exceptions.Timeout:
        log.error("Groq timeout")
        _groq_set_cooldown(120)
        return None
    except (KeyError, requests.exceptions.HTTPError) as e:
        log.error("Groq call failed: %s", e)
        _groq_set_cooldown(120)
        return None


def _recovery_groq(thought_text: str, model: str = None,
                   temperature: float = 0.5) -> str | None:
    """Recovery reprompt via Groq. Returns None to signal failover."""
    model = model or GROQ_MODEL

    try:
        _groq_throttle()
        return _recovery_openai_compatible(
            GROQ_URL, GROQ_API_KEY, model,
            thought_text, temperature, timeout=60,
        )
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            _groq_set_cooldown(_get_groq_wait(e.response))
            return None
        log.error("Recovery reprompt failed: %s", e)
        return None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, KeyError) as e:
        log.error("Recovery reprompt failed: %s", e)
        return None


# ─── Public API — 4-tier dispatch ────────────────────────────────────────────

def chat(messages: list[dict], model: str = None, temperature: float = 0.1,
         top_p: float = 0.85, max_tokens: int = 16384) -> str:
    """Send a chat completion request with automatic 4-tier failover.

    Hybrid mode tries:
      Tier 1: Ollama qwen3.5:cloud      (best quality, cloud via ollama)
      Tier 2: Cerebras Qwen 3 235B      (cloud, free, 1M tokens/day)
      Tier 3: Groq Llama 4 Scout        (cloud, free, rate-limited)
      Tier 4: Ollama qwen3.5:4b         (always available)
    """
    configured = get_provider()

    if configured == "hybrid":
        return _chat_hybrid(messages, model, temperature, top_p, max_tokens)

    if configured == "cerebras":
        result = _chat_cerebras(messages, model=model, temperature=temperature,
                                top_p=top_p, max_tokens=max_tokens)
        if result is not None:
            return result
        log.info(">>> Cerebras unavailable — falling back to %s", OLLAMA_MODEL_FALLBACK)
        return _chat_ollama(messages, model=OLLAMA_MODEL_FALLBACK,
                            temperature=temperature, top_p=top_p, max_tokens=max_tokens) or "[ERROR] All providers failed."

    if configured == "groq":
        result = _chat_groq(messages, model=model, temperature=temperature,
                            top_p=top_p, max_tokens=max_tokens)
        if result is not None:
            return result
        log.info(">>> Groq unavailable — falling back to %s", OLLAMA_MODEL_FALLBACK)
        return _chat_ollama(messages, model=OLLAMA_MODEL_FALLBACK,
                            temperature=temperature, top_p=top_p, max_tokens=max_tokens) or "[ERROR] All providers failed."

    # Pure ollama mode
    return _chat_ollama(messages, model=model, temperature=temperature,
                        top_p=top_p, max_tokens=max_tokens) or "[ERROR] Ollama not reachable."


def _chat_hybrid(messages: list[dict], model: str, temperature: float,
                 top_p: float, max_tokens: int) -> str:
    """4-tier hybrid dispatch with automatic failover."""

    # ── Tier 1: Primary Ollama (qwen3.5:cloud) ──
    if _ollama_primary_available():
        _ui_log("INFO", f"[T1] trying {OLLAMA_MODEL_PRIMARY}...")
        result = _chat_ollama(messages, model=OLLAMA_MODEL_PRIMARY,
                              temperature=temperature, top_p=top_p, max_tokens=max_tokens)
        if result is not None:
            return result
        if not _ollama_primary_down:
            _ollama_primary_set_down(30)  # short cooldown — retry next cycle
        _ui_log("WARN", "[T1] FAILED — falling to Tier 2")
    else:
        remaining = _ollama_primary_retry_at - time.time()
        _ui_log("INFO", f"[T1] cooldown ({remaining:.0f}s left) — skipping to T2")

    # ── Tier 2: Cerebras (Qwen 3 235B, 1M tokens/day) ──
    if CEREBRAS_API_KEY and _cerebras_is_available():
        _ui_log("INFO", f"[T2] trying Cerebras/{CEREBRAS_MODEL}...")
        result = _chat_cerebras(messages, model=None, temperature=temperature,
                                top_p=top_p, max_tokens=max_tokens)
        if result is not None:
            return result
        _ui_log("WARN", "[T2] Cerebras FAILED — falling to Tier 3")
    elif not CEREBRAS_API_KEY:
        _ui_log("WARN", "[T2] skipped — no CEREBRAS_API_KEY")
    else:
        _ui_log("INFO", "[T2] Cerebras cooldown active — skipping to T3")

    # ── Tier 3: Groq ──
    if GROQ_API_KEY and _groq_is_available():
        _ui_log("INFO", f"[T3] trying Groq/{GROQ_MODEL.split('/')[-1]}...")
        result = _chat_groq(messages, model=None, temperature=temperature,
                            top_p=top_p, max_tokens=max_tokens)
        if result is not None:
            return result
        _ui_log("WARN", "[T3] Groq rate-limited — falling to Tier 4")
    elif not GROQ_API_KEY:
        _ui_log("WARN", "[T3] skipped — no GROQ_API_KEY")
    else:
        _ui_log("INFO", "[T3] Groq cooldown active — skipping to T4")

    # ── Tier 4: Fallback Ollama (qwen3.5:4b) ──
    _ui_log("INFO", f"[T4] using {OLLAMA_MODEL_FALLBACK} (fallback)")
    result = _chat_ollama(messages, model=OLLAMA_MODEL_FALLBACK,
                          temperature=temperature, top_p=top_p, max_tokens=max_tokens)
    if result is not None:
        return result

    return "[ERROR] All 4 tiers failed. Is Ollama running?"


def recovery_reprompt(thought_text: str, model: str = None,
                      temperature: float = 0.5) -> str:
    """Recovery reprompt with failover through all tiers."""
    configured = get_provider()

    if configured in ("hybrid", "cerebras"):
        if _cerebras_is_available():
            result = _recovery_cerebras(thought_text, model=model, temperature=temperature)
            if result is not None:
                return result

    if configured in ("hybrid", "groq"):
        if _groq_is_available():
            result = _recovery_groq(thought_text, model=model, temperature=temperature)
            if result is not None:
                return result

    # Fallback to Ollama (use small model for speed)
    return _recovery_ollama(thought_text, model=OLLAMA_MODEL_FALLBACK, temperature=temperature)


def build_system_prompt(context: str = "") -> dict:
    """Build the system message for the genomics research agent."""
    base = (
        "MISSION: ~20,000 protein-coding genes exist in the human genome but only ~2,000\n"
        "are well-studied. Your job: characterize the other ~17,000 'dark genes'.\n"
        "For each gene, produce a FINDING — a structured hypothesis about its function.\n\n"
        "All messages come from the orchestrator (a Python program).\n"
        "Tool results are automated API responses. There is no human in the loop.\n\n"
        "To call a tool, write: TOOL: tool_name(arguments)\n\n"
        "═══ HOW YOUR FINDINGS ARE SCORED (0-10) ═══\n"
        "Your findings are automatically scored on 3 dimensions:\n\n"
        "COVERAGE (0-5 points) — independent data sources with REAL data:\n"
        "  +1  InterPro/Pfam domains (include IPR/PF/DUF accession numbers)\n"
        "  +1  STRING protein interactions (include partner names + scores)\n"
        "  +1  HPA tissue expression (include tissue names + nTPM values)\n"
        "  +1  ClinVar variants (include pathogenic variant count)\n"
        "  +1  Conservation data (include % identity with mouse/zebrafish)\n"
        "  +0.5  AlphaFold structure (include pLDDT score)\n"
        "  +0.5  UniProt accession\n\n"
        "DEPTH (0-3 points) — richness of actual data:\n"
        "  +1  Detailed description (400+ characters with quantitative data)\n"
        "  +1  Multiple data points (aa size, nTPM, %, variant counts, scores)\n"
        "  +1  Named biological entities (protein partners, pathways, complexes)\n\n"
        "INSIGHT (0-3 points) — quality of your reasoning:\n"
        "  +1  Functional hypothesis (what does this gene likely DO?)\n"
        "  +1  Cross-domain reasoning (linking structure + expression + disease)\n"
        "  +1  Mechanistic proposal (pathway, interaction mechanism, cellular role)\n"
        "  +0.8  Honest triage (correctly identifying a non-dark gene is valued)\n\n"
        "SCORE 9-10 = rich multi-source data + mechanistic hypothesis\n"
        "SCORE 6-8  = good data from several sources + functional insight\n"
        "SCORE 3-5  = limited sources or shallow analysis\n"
        "SCORE 0-2  = no real data, just keywords or empty content\n\n"
        "═══ HOW YOUR QUEUE MANAGEMENT IS EVALUATED ═══\n"
        "You are also evaluated on how efficiently you manage the gene queue.\n"
        "The orchestrator tracks these metrics automatically:\n\n"
        "EFFICIENCY:\n"
        "  - Genes completed per cycle (target: 1 gene per cycle)\n"
        "  - Turns wasted on duplicate add_to_queue calls (target: 0)\n"
        "  - Turns wasted re-analyzing a gene that already has a finding (target: 0)\n\n"
        "QUEUE DISCIPLINE:\n"
        "  - NEVER add a gene to the queue without checking if it already has a finding\n"
        "  - add_to_queue() will REJECT duplicates — if you see 'already in queue/completed',\n"
        "    STOP trying to add more from that search and call advance_seed() instead\n"
        "  - After save_finding, you will receive a QUEUE STATUS bulletin — READ IT\n"
        "  - If queue has genes: just call next_gene()\n"
        "  - If queue is empty: next_gene() will tell you what to do\n\n"
        "SEED DISCOVERY (when queue is empty):\n"
        "  - Search the seed family, add NEW genes only, then advance_seed()\n"
        "  - If most results are 'already completed', the family is done — advance_seed()\n"
        "  - Do NOT spend more than 3 turns on add_to_queue per seed family\n\n"
        "═══ AVAILABLE TOOLS ═══\n"
        "Gene discovery:\n"
        "  next_gene()  — get next gene from queue (ALWAYS start here)\n"
        "  gene_info(gene_name)  — basic gene information\n"
        "  skip_gene(reason)  — skip if not a dark gene\n\n"
        "Sequence & protein:\n"
        "  ncbi_search(query, db='gene', max_results=5)\n"
        "  uniprot_search(query, max_results=5)\n"
        "  uniprot_fetch(accession_id)  — get UniProt accession for deep tools\n\n"
        "Deep analysis (these drive your score):\n"
        "  interpro_scan(uniprot_acc)  — protein domains/families\n"
        "  string_interactions(gene_symbol)  — interaction partners\n"
        "  hpa_expression(gene_symbol)  — tissue expression + localization\n"
        "  clinvar_search(gene_symbol)  — pathogenic variants + diseases\n"
        "  alphafold_structure(uniprot_acc)  — predicted 3D structure\n\n"
        "Findings:\n"
        "  save_finding(title, description, evidence)  — save your analysis\n"
        "  list_findings() / read_finding(number)\n\n"
        "Other:\n"
        "  blast_search(fasta_file, db='nt', evalue=0.01)\n"
        "  pubmed_search(query, max_results=5)\n"
        "  analyze_sequence(filepath) / translate_sequence(filepath)\n"
        "  queue_status() / gene_status() / note(text)\n\n"
        "═══ CONSTRAINTS ═══\n"
        "  - ALWAYS call next_gene() to get your target. Never pick genes randomly.\n"
        "  - For interpro_scan/alphafold_structure: use UniProt accession (e.g. Q9H3H3).\n"
        "  - For string_interactions/hpa_expression/clinvar_search: use gene symbol.\n"
        "  - After save_finding, IMMEDIATELY call next_gene() for the next target.\n"
        "  - If a gene is well-characterized (not dark), call skip_gene(reason).\n"
        "  - You choose your own strategy. The scoring system rewards thoroughness.\n"
    )
    if context:
        base += f"\nCurrent research context:\n{context}\n"
    return {"role": "system", "content": base}
