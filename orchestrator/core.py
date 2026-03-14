"""
Orchestrator core — the main research loop.
LLM proposes actions → tools execute → results feed back → repeat.
"""

import re

from config import OLLAMA_MODEL
from orchestrator.llm import chat, build_system_prompt
from orchestrator.dashboard import write_status
from tools.registry import ToolRegistry
from agent.memory import load_memory, save_memory, update_memory, summarize_memory
from agent.ui import (
    C, log as ui_log, print_banner, print_cycle_header,
    print_cycle_summary, print_completion,
)

# Pattern: TOOL: function_name(...)
# Also catches Qwen markdown variants like **Tool Call:** func(), **TOOL:** func(), etc.
TOOL_START_PATTERN = re.compile(
    r"(?:\*{0,2}Tool(?:\s*Call)?:?\*{0,2}|TOOL:)\s*(\w+)\(", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Response deduplication (ported from auto-research)
# ---------------------------------------------------------------------------

def _deduplicate_response(response: str) -> tuple[str, bool]:
    """Detect and remove repeated blocks from Qwen output.

    When Qwen loops, it repeats THOUGHT blocks many times, consuming all
    num_predict tokens without ever emitting TOOL: lines. This detects
    that pattern and truncates.
    """
    lines = response.split("\n")

    # Count all non-empty line occurrences
    line_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 20:  # Only count substantial lines
            line_counts[stripped] = line_counts.get(stripped, 0) + 1

    # If any substantial line appears 3+ times, we have a repetition loop
    max_repeats = max(line_counts.values()) if line_counts else 0
    if max_repeats < 3:
        return response, False

    # Deduplicate: keep first occurrence of each line, always keep TOOL lines
    seen_lines: set[str] = set()
    deduped_lines = []
    repeated = False

    for line in lines:
        stripped = line.strip()
        # Always keep TOOL: lines (never deduplicate actions)
        if stripped.upper().startswith("TOOL:"):
            deduped_lines.append(line)
            continue
        # Keep short lines (empty, separators, etc.)
        if len(stripped) <= 20:
            deduped_lines.append(line)
            continue
        # Deduplicate substantial repeated lines
        if stripped in seen_lines:
            repeated = True
            continue
        seen_lines.add(stripped)
        deduped_lines.append(line)

    return "\n".join(deduped_lines), repeated


# ---------------------------------------------------------------------------
# Centralized parameter normalization (ported from auto-research)
# ---------------------------------------------------------------------------

# Common parameter aliases Qwen invents → correct name
_PARAM_ALIASES = {
    "file_path": "filepath",
    "file_name": "filepath",
    "filename": "filepath",
    "file": "filepath",
    "path": "filepath",
    "fasta": "filepath",
    "input": "filepath",
    "seq": "filepath",
    "accession": "accession_id",
    "acc": "accession_id",
    "seq_id": "accession_id",
    "protein_id": "accession_id",
    "limit": "max_results",
    "num_results": "max_results",
    "count": "max_results",
    "gene": "gene_name",
    "symbol": "gene_name",
    "gene_symbol": "gene_name",
    "database": "db",
    "content": "description",
    "details": "description",
    "result": "description",
    "body": "description",
    "source": "evidence",
    "reference": "evidence",
    "ref": "evidence",
    "question": "query",
    "term": "query",
    "search": "query",
    "q": "query",
    "text": "query",
}

# Per-tool overrides: for tools where the "canonical" name differs
# e.g. query_memory uses "question" not "query" as final name
_TOOL_PARAM_MAP = {
    "query_memory": {"query": "question"},
    "note": {"query": "text"},
    "save_finding": {"query": "title"},
    "analyze_sequence": {"query": "filepath"},
    "blast_search": {"filepath": "sequence"},
}


def _normalize_params(tool_name: str, args: list, kwargs: dict) -> tuple[list, dict]:
    """Normalize parameter names using central alias table."""
    normalized = {}
    for key, val in kwargs.items():
        # Apply global aliases
        canonical = _PARAM_ALIASES.get(key, key)
        # Apply per-tool overrides
        tool_map = _TOOL_PARAM_MAP.get(tool_name, {})
        canonical = tool_map.get(canonical, canonical)
        normalized[canonical] = val
    return args, normalized


class Orchestrator:
    """Main autonomous research loop."""

    def __init__(self, max_cycles: int = 10, model: str = None,
                 target: str = None):
        self.max_cycles = max_cycles
        self.model = model
        self.target = target
        self.tools = ToolRegistry()
        self.memory = load_memory()
        self.messages: list[dict] = []
        self.cycle = 0

    def run(self):
        """Execute the research loop."""
        model_name = self.model or OLLAMA_MODEL
        print_banner(model_name, self.memory, self.target)
        write_status(running=True, cycle=0, phase="init")

        # Build initial context
        context = summarize_memory(self.memory)
        if self.target:
            context += f"\nResearch target: {self.target}"

        self.messages = [build_system_prompt(context)]

        # Initial prompt — use "user" role (required by chat API) but frame as orchestrator
        if self.target:
            user_msg = f"[orchestrator] Research target: {self.target}"
        else:
            user_msg = "[orchestrator] Session started. Begin research."
        self.messages.append({"role": "user", "content": user_msg})

        while self._should_continue():
            self.cycle += 1
            self._run_cycle()

        write_status(running=False, cycle=self.cycle, phase="done")
        save_memory(self.memory)
        print_completion(self.cycle, self.memory)

    def _should_continue(self) -> bool:
        if self.max_cycles == 0:
            return True  # infinite mode
        return self.cycle < self.max_cycles

    def _run_cycle(self):
        """Single think → act → observe cycle."""
        print_cycle_header(self.cycle)
        write_status(running=True, cycle=self.cycle, phase="thinking")
        cycle_summary = []

        # 1. LLM thinks
        ui_log("INFO", "Waiting for LLM response...")
        response = chat(self.messages, model=self.model)

        # 1b. Deduplicate repeated blocks (Qwen loop detection)
        response, was_deduped = _deduplicate_response(response)
        if was_deduped:
            ui_log("WARN", "Repetition detected in response — deduplicated")

        self.messages.append({"role": "assistant", "content": response})

        # Show thought as compact block
        ui_log("THINK", response)

        # 2. Parse tool calls
        tool_calls = self._parse_all_tools(response)

        if tool_calls:
            # Execute each tool call (auto-research supports multiple per cycle)
            for name, args, kwargs in tool_calls:
                # 2b. Centralized param normalization
                args, kwargs = _normalize_params(name, args, kwargs)

                write_status(running=True, cycle=self.cycle,
                             phase="executing", current_tool=name)

                # Show tool call with args
                args_str = ", ".join([repr(a) for a in args] +
                                    [f"{k}={repr(v)}" for k, v in kwargs.items()])
                ui_log("TOOL", f"{name}|{name}({args_str})")

                # 3. Execute tool
                result = self.tools.execute(name, *args, **kwargs)
                result_str = str(result)[:3000]

                # Show result preview
                result_preview = result_str.replace("\n", " │ ")[:250]
                ui_log("RESULT", f"{name}|{result_preview}")
                cycle_summary.append(f"{name}: {result_preview[:80]}")

                # 4. Feed result back
                self.messages.append({
                    "role": "user",
                    "content": f"[orchestrator] {name} returned:\n{result_str}"
                })

                # 5. Update memory
                update_memory(self.memory, name, result_str)
        else:
            # No tool call — LLM is just thinking/summarizing
            ui_log("WARN", "No tool call detected — nudging agent")
            cycle_summary.append("No tool call — thinking only")
            self.messages.append({
                "role": "user",
                "content": (
                    "[orchestrator] No tool call detected. You MUST call a tool to proceed.\n"
                    "Format: TOOL: function_name(key=value, key2=value2)\n"
                    "Example: TOOL: ncbi_search(query='BRCA1', db='gene')\n"
                    "Example: TOOL: analyze_sequence(filepath='NM_007294.fasta')\n"
                    "Example: TOOL: next_gene()"
                )
            })

        print_cycle_summary(self.cycle, cycle_summary)

        # Trim conversation if it gets too long
        self._trim_messages()

    def _parse_all_tools(self, text: str) -> list[tuple]:
        """Extract ALL TOOL: name(args) from LLM response.

        Returns list of (name, args, kwargs) tuples.
        Unlike _parse_tool which only finds the first match,
        this finds all tool calls in the response.
        """
        results = []
        for match in TOOL_START_PATTERN.finditer(text):
            name = match.group(1)

            # Find the matching closing paren
            start = match.end()
            raw_args = _extract_balanced_args(text, start)
            if raw_args is None:
                raw_args = ""
            raw_args = raw_args.strip()

            if not raw_args:
                results.append((name, [], {}))
                continue

            args = []
            kwargs = {}
            for part in _split_args(raw_args):
                part = part.strip()
                if "=" in part and not part.startswith(("'", '"')):
                    key, val = part.split("=", 1)
                    kwargs[key.strip().lower()] = _cast(val.strip())
                else:
                    args.append(_cast(part))

            results.append((name, args, kwargs))

        return results

    def _trim_messages(self, max_messages: int = 80):
        """Keep conversation manageable — preserve system + last N messages.
        Only trim when significantly over limit to avoid trimming every cycle.
        """
        # Only trim when 20% over to avoid constant trimming
        if len(self.messages) <= int(max_messages * 1.2):
            return
        system = self.messages[0]
        recent = self.messages[-(max_messages - 1):]
        trimmed_count = len(self.messages) - len(recent) - 1
        self.messages = [system] + recent
        ui_log("INFO", f"Context trimmed: dropped {trimmed_count} old messages, keeping {len(self.messages)}")


def _extract_balanced_args(text: str, start: int) -> str:
    """Extract content between balanced parentheses, respecting quoted strings.

    `start` should point to the first char after the opening '('.
    Returns the content between parens, or None if no balanced close found.
    """
    depth = 1
    in_quote = None
    i = start
    while i < len(text):
        ch = text[i]
        if in_quote:
            if ch == in_quote and (i == 0 or text[i-1] != "\\"):
                in_quote = None
        else:
            if ch in ("'", '"'):
                in_quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return text[start:i]
        i += 1
    # No balanced close found — return everything we have
    return text[start:]


def _split_args(raw: str) -> list[str]:
    """Split comma-separated args, respecting quotes."""
    parts = []
    current = ""
    depth = 0
    in_quote = None
    for ch in raw:
        if ch in ("'", '"') and in_quote is None:
            in_quote = ch
        elif ch == in_quote:
            in_quote = None
        elif ch == "(" and in_quote is None:
            depth += 1
        elif ch == ")" and in_quote is None:
            depth -= 1
        elif ch == "," and depth == 0 and in_quote is None:
            parts.append(current)
            current = ""
            continue
        current += ch
    if current.strip():
        parts.append(current)
    return parts


def _cast(val: str):
    """Try to cast a string argument to int, float, or stripped string."""
    val = val.strip().strip("'\"")
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val
