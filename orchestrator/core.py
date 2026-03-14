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

# Pattern: TOOL: function_name(arg1, arg2, key=value)
TOOL_PATTERN = re.compile(
    r"TOOL:\s*(\w+)\(([^)]*)\)", re.IGNORECASE
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

        # Initial prompt
        if self.target:
            user_msg = f"Begin researching: {self.target}. Start by searching relevant databases."
        else:
            user_msg = "Review your memory and propose the next research direction."
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

        # Show full thought — split into paragraphs for readability
        for paragraph in response.split("\n"):
            line = paragraph.strip()
            if line:
                ui_log("THINK", line)

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
                "content": f"Tool result for {name}:\n{result_str}"
            })

            # 5. Update memory
            update_memory(self.memory, name, result_str)
        else:
            # No tool call — LLM is just thinking/summarizing
            ui_log("WARN", "No tool call detected — nudging agent")
            cycle_summary.append("No tool call — thinking only")
            self.messages.append({
                "role": "user",
                "content": "Continue. What's your next action?"
            })

        print_cycle_summary(self.cycle, cycle_summary)

        # Trim conversation if it gets too long
        self._trim_messages()

    def _parse_tool(self, text: str):
        """Extract TOOL: name(args) from LLM response. Returns (name, args, kwargs) or None."""
        match = TOOL_PATTERN.search(text)
        if not match:
            return None

        name = match.group(1)
        raw_args = match.group(2).strip()

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

    def _trim_messages(self, max_messages: int = 40):
        """Keep conversation manageable — preserve system + last N messages."""
        if len(self.messages) <= max_messages:
            return
        system = self.messages[0]
        recent = self.messages[-(max_messages - 1):]
        self.messages = [system] + recent
        ui_log("INFO", f"Trimmed conversation to {len(self.messages)} messages")


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
