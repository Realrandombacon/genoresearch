"""
Orchestrator core — the main research loop.
LLM proposes actions -> tools execute -> results feed back -> repeat.

Multi-turn inner loop: each cycle allows up to MAX_TURNS of
think -> act -> reflect before moving to the next cycle.
"""

from config import MAX_TURNS as _MAX_TURNS, SOFT_TURNS as _SOFT_TURNS, LOOP_THRESHOLD as _LOOP_THRESHOLD, MAX_RESULT_LENGTH
from orchestrator.llm import chat, recovery_reprompt, build_system_prompt, get_model, get_provider_status
from orchestrator.dashboard import write_status
from orchestrator.parsing import TOOL_START_PATTERN, parse_tool
from orchestrator.loop_detection import is_looping, break_loop, suggest_next_step
from orchestrator.prompts import _build_reflection_prompt, _auto_complete_step
from orchestrator.context import _deduplicate_response, _trim_messages
from tools.registry import ToolRegistry
from agent.memory import load_memory, save_memory, update_memory, summarize_memory
from agent.ui import (
    log as ui_log, print_banner, print_cycle_header,
    print_cycle_summary, print_completion,
)


class Orchestrator:
    """Main autonomous research loop with multi-turn inner loop."""

    # How many identical consecutive tool calls before we intervene
    LOOP_THRESHOLD = _LOOP_THRESHOLD
    # Soft target for turns per cycle — agent can go beyond if still working
    SOFT_TURNS = _SOFT_TURNS
    # Hard safety cap — prevent infinite loops
    MAX_TURNS = _MAX_TURNS

    def __init__(self, max_cycles: int = 10, model: str = None,
                 target: str = None):
        self.max_cycles = max_cycles
        self.model = model
        self.target = target
        self.tools = ToolRegistry()
        self.memory = load_memory()
        self.messages: list[dict] = []
        self.cycle = 0
        self._recent_tool_calls: list[str] = []  # track for loop detection

    def run(self):
        """Execute the research loop."""
        model_name = self.model or get_model()
        print_banner(model_name, self.memory, self.target, provider=get_provider_status())
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
            user_msg = (
                "[orchestrator] Session started. Call TOOL: next_gene() to begin."
            )
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
        """Multi-turn cycle: think -> act -> reflect -> act -> ... (up to MAX_TURNS).

        Each turn:
          1. LLM produces a response (possibly with a tool call)
          2. If tool call: execute, feed result back via reflection prompt
          3. If no tool call: attempt recovery reprompt, or end cycle
          4. Loop until no more tool calls or MAX_TURNS reached
        """
        print_cycle_header(self.cycle)
        write_status(running=True, cycle=self.cycle, phase="thinking")
        cycle_summary = []

        for turn in range(1, self.MAX_TURNS + 1):
            is_first_turn = (turn == 1)

            ui_log("INFO", f"── Turn {turn} ──")

            # --- Get LLM response ---
            if is_first_turn:
                ui_log("INFO", "Waiting for LLM response...")
                response = chat(self.messages, model=self.model)
            else:
                # Reflection turns — the reflection prompt was already
                # appended to self.messages by the previous iteration
                ui_log("INFO", "Reflecting on results...")
                write_status(running=True, cycle=self.cycle, phase="reflecting")
                response = chat(self.messages, model=self.model)

            # Deduplicate repeated thought blocks (Qwen bug)
            response, was_deduped = _deduplicate_response(response, TOOL_START_PATTERN)
            if was_deduped:
                ui_log("WARN", "Deduplicated repeated THOUGHT blocks in response")

            self.messages.append({"role": "assistant", "content": response})

            # Show thought
            ui_log("THINK", response)

            # --- Parse tool call ---
            tool_call = self._parse_tool(response)

            if tool_call:
                name, args, kwargs = tool_call

                # Build signature for loop detection
                args_str = ", ".join(
                    [repr(a) for a in args] +
                    [f"{k}={repr(v)}" for k, v in kwargs.items()]
                )
                call_sig = f"{name}({args_str})"

                # --- Loop detection ---
                self._recent_tool_calls.append(call_sig)
                if len(self._recent_tool_calls) > 10:
                    self._recent_tool_calls = self._recent_tool_calls[-10:]

                if is_looping(self._recent_tool_calls, self.LOOP_THRESHOLD):
                    ui_log("WARN", f"LOOP DETECTED: '{call_sig}' repeated {self.LOOP_THRESHOLD}+ times — breaking out")
                    cycle_summary.append(f"LOOP on {name} — redirecting")
                    break_loop(self.messages, self._recent_tool_calls, call_sig, self.LOOP_THRESHOLD)
                    break

                write_status(running=True, cycle=self.cycle,
                             phase="executing", current_tool=name)

                # Show tool call
                ui_log("TOOL", f"{name}|{name}({args_str})")

                # --- Execute tool ---
                result = self.tools.execute(name, *args, **kwargs)
                result_str = str(result)[:MAX_RESULT_LENGTH]

                # Show result preview
                result_preview = result_str.replace("\n", " | ")[:250]
                ui_log("RESULT", f"{name}|{result_preview}")
                cycle_summary.append(f"T{turn} {name}: {result_preview[:80]}")

                # Update memory
                update_memory(self.memory, name, result_str)

                # Auto-complete pipeline steps when the right tool is used
                _auto_complete_step(name, result_str)

                # --- Reflection: if not last turn, send reflection prompt ---
                if turn < self.MAX_TURNS:
                    reflection = _build_reflection_prompt(
                        name, result_str, turn, self.MAX_TURNS,
                        soft_turns=self.SOFT_TURNS
                    )
                    self.messages.append({
                        "role": "user",
                        "content": reflection,
                    })
                    # Continue to next turn — LLM will see the reflection
                    continue
                else:
                    # Last turn — just feed back the result normally
                    self.messages.append({
                        "role": "user",
                        "content": f"[orchestrator] {name} returned:\n{result_str}"
                    })
                    ui_log("INFO", f"Max turns ({self.MAX_TURNS}) reached — ending cycle")
                    break

            else:
                # No tool call detected
                # --- Recovery reprompt (not on the final turn) ---
                if turn < self.MAX_TURNS:
                    ui_log("WARN", f"No tool call in turn {turn} — attempting recovery reprompt")
                    recovered_response = recovery_reprompt(
                        response, model=self.model
                    )
                    if recovered_response:
                        recovered_call = self._parse_tool(recovered_response)
                        if recovered_call:
                            ui_log("OK", "Recovery reprompt yielded a tool call")
                            # Replace the last assistant message with the recovered one
                            self.messages[-1] = {
                                "role": "assistant",
                                "content": recovered_response,
                            }
                            # Re-parse and execute in-line (avoid extra turn cost)
                            rname, rargs, rkwargs = recovered_call
                            rargs_str = ", ".join(
                                [repr(a) for a in rargs] +
                                [f"{k}={repr(v)}" for k, v in rkwargs.items()]
                            )
                            ui_log("TOOL", f"{rname}|{rname}({rargs_str})")
                            result = self.tools.execute(rname, *rargs, **rkwargs)
                            result_str = str(result)[:MAX_RESULT_LENGTH]
                            result_preview = result_str.replace("\n", " | ")[:250]
                            ui_log("RESULT", f"{rname}|{result_preview}")
                            cycle_summary.append(f"T{turn}R {rname}: {result_preview[:80]}")
                            update_memory(self.memory, rname, result_str)

                            # Send reflection for recovered result
                            if turn < self.MAX_TURNS:
                                reflection = _build_reflection_prompt(
                                    rname, result_str, turn, self.MAX_TURNS,
                                    soft_turns=self.SOFT_TURNS
                                )
                                self.messages.append({
                                    "role": "user",
                                    "content": reflection,
                                })
                                continue
                            else:
                                self.messages.append({
                                    "role": "user",
                                    "content": f"[orchestrator] {rname} returned:\n{result_str}"
                                })
                                break

                    # Recovery failed or produced no tool call — nudge and end
                    ui_log("WARN", "Recovery failed — no tool call produced")

                # No tool call and either final turn or recovery failed
                cycle_summary.append(f"T{turn} no tool call — thinking only")

                self._recent_tool_calls.append("__NO_TOOL__")
                if len(self._recent_tool_calls) > 10:
                    self._recent_tool_calls = self._recent_tool_calls[-10:]

                if is_looping(self._recent_tool_calls, self.LOOP_THRESHOLD):
                    ui_log("WARN", "LOOP DETECTED: agent stuck thinking without acting — redirecting")
                    cycle_summary.append("LOOP — redirecting")
                    break_loop(self.messages, self._recent_tool_calls, "__NO_TOOL__", self.LOOP_THRESHOLD)
                    break

                # Nudge for next cycle (not a reflection — just a nudge)
                self.messages.append({
                    "role": "user",
                    "content": (
                        "[orchestrator] No tool call detected. You MUST call a tool now.\n"
                        "Pick ONE of these and call it:\n"
                        "  TOOL: next_gene()\n"
                        "  TOOL: ncbi_search('your_query', db='gene')\n"
                        "  TOOL: list_sequences()\n"
                        "  TOOL: list_findings()"
                    ),
                })
                break  # End cycle — next cycle will pick up with the nudge

        # --- End of turn loop ---
        total_turns = min(turn, self.MAX_TURNS)
        if total_turns > 1:
            ui_log("OK", f"Cycle {self.cycle} completed in {total_turns} turn(s)")

        print_cycle_summary(self.cycle, cycle_summary)

        # Save memory every 5 cycles
        if self.cycle % 5 == 0:
            save_memory(self.memory)

        # Smart context compression every cycle
        _trim_messages(self.messages, TOOL_START_PATTERN)

    def _parse_tool(self, text: str):
        """Extract TOOL: name(args) from LLM response. Returns (name, args, kwargs) or None."""
        return parse_tool(text)

    def _is_looping(self) -> bool:
        """Check if the agent is stuck in a loop."""
        return is_looping(self._recent_tool_calls, self.LOOP_THRESHOLD)

    def _break_loop(self, stuck_call: str):
        """Break out of a detected loop."""
        break_loop(self.messages, self._recent_tool_calls, stuck_call, self.LOOP_THRESHOLD)

    @staticmethod
    def _suggest_next_step(stuck_call: str) -> str:
        """Given the tool call that was looping, suggest what to do next."""
        return suggest_next_step(stuck_call)

    def _trim_messages(self, keep_recent: int = 20, hard_limit: int = 60):
        """Smart per-cycle context management."""
        _trim_messages(self.messages, TOOL_START_PATTERN, keep_recent, hard_limit)
