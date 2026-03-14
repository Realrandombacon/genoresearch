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
        ui_log("INFO", f"Waiting for LLM response...")
        response = chat(self.messages, model=self.model)
        self.messages.append({"role": "assistant", "content": response})

        # Show thought as compact block
        ui_log("THINK", response)

        # 2. Parse tool call
        tool_call = self._parse_tool(response)

        if tool_call:
            name, args, kwargs = tool_call
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
                "content": "[orchestrator] No tool call detected. Call a tool to proceed."
            })

        print_cycle_summary(self.cycle, cycle_summary)

        # Trim conversation if it gets too long
        self._trim_messages()

    def _parse_tool(self, text: str):
        """Extract TOOL: name(args) from LLM response. Returns (name, args, kwargs) or None."""
        match = TOOL_START_PATTERN.search(text)
        if not match:
            return None

        name = match.group(1)

        # Find the matching closing paren, respecting quotes and nested parens
        start = match.end()  # position right after the opening '('
        raw_args = _extract_balanced_args(text, start)
        if raw_args is None:
            raw_args = ""

        raw_args = raw_args.strip()

        if not raw_args:
            return name, [], {}

        args = []
        kwargs = {}
        for part in _split_args(raw_args):
            part = part.strip()
            if "=" in part and not part.startswith(("'", '"')):
                key, val = part.split("=", 1)
                kwargs[key.strip()] = _cast(val.strip())
            else:
                args.append(_cast(part))

        return name, args, kwargs

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
