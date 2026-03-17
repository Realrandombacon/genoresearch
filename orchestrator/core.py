"""
Orchestrator core — the main research loop.
LLM proposes actions → tools execute → results feed back → repeat.

Multi-turn inner loop: each cycle allows up to MAX_TURNS of
think → act → reflect before moving to the next cycle.
"""

import re

from orchestrator.llm import chat, recovery_reprompt, build_system_prompt, get_model, get_provider, get_provider_status
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
    """Main autonomous research loop with multi-turn inner loop."""

    # How many identical consecutive tool calls before we intervene
    LOOP_THRESHOLD = 2
    # Soft target for turns per cycle — agent can go beyond if still working
    SOFT_TURNS = 12
    # Hard safety cap — prevent infinite loops
    MAX_TURNS = 20

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
            response, was_deduped = _deduplicate_response(response)
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

                if self._is_looping():
                    ui_log("WARN", f"LOOP DETECTED: '{call_sig}' repeated {self.LOOP_THRESHOLD}+ times — breaking out")
                    cycle_summary.append(f"LOOP on {name} — redirecting")
                    self._break_loop(call_sig)
                    break

                write_status(running=True, cycle=self.cycle,
                             phase="executing", current_tool=name)

                # Show tool call
                ui_log("TOOL", f"{name}|{name}({args_str})")

                # --- Execute tool ---
                result = self.tools.execute(name, *args, **kwargs)
                result_str = str(result)[:3000]

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
                            result_str = str(result)[:3000]
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

                if self._is_looping():
                    ui_log("WARN", "LOOP DETECTED: agent stuck thinking without acting — redirecting")
                    cycle_summary.append("LOOP — redirecting")
                    self._break_loop("__NO_TOOL__")
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

    def _is_looping(self) -> bool:
        """Check if the agent is stuck in a loop.

        Two checks:
        1. Last N calls are strictly identical (immediate loop)
        2. Same call appears 3+ times in the last 10 calls (spread-out loop,
           e.g. search → nudge → search → nudge → search)
        """
        if len(self._recent_tool_calls) < self.LOOP_THRESHOLD:
            return False
        # Check 1: strictly consecutive identical calls
        last_n = self._recent_tool_calls[-self.LOOP_THRESHOLD:]
        if len(set(last_n)) == 1:
            return True
        # Check 2: same call appears 3+ times in last 10 (spread-out loop)
        from collections import Counter
        counts = Counter(self._recent_tool_calls[-10:])
        for call, count in counts.items():
            if call != "__NO_TOOL__" and count >= 3:
                return True
        return False

    def _break_loop(self, stuck_call: str):
        """Break out of a detected loop by trimming repeated context and
        suggesting the logical next step based on what tool was being repeated.

        Strategy:
        1. Keep system prompt + strip all the repeated messages
        2. Analyze the stuck tool call to suggest the right next action
        3. Inject a specific directive with the exact tool to call next
        4. Reset the tool call tracker
        """
        system = self.messages[0]

        # Keep only system + last 4 non-duplicate messages
        # (the loop fills context with identical copies — purge them)
        unique = []
        seen = set()
        for msg in reversed(self.messages[1:]):
            fp = msg.get("content", "")[:200]
            if fp not in seen:
                seen.add(fp)
                unique.append(msg)
            if len(unique) >= 4:
                break
        unique.reverse()
        self.messages = [system] + unique

        # Figure out what the next logical step is based on the stuck call
        hint = self._suggest_next_step(stuck_call)

        self.messages.append({
            "role": "user",
            "content": (
                f"[orchestrator] LOOP DETECTED: You repeated '{stuck_call}' "
                f"{self.LOOP_THRESHOLD}+ times without making progress. "
                f"You already have the results from that search.\n\n"
                f"DO SOMETHING DIFFERENT NOW. {hint}\n\n"
                "Pipeline reminder: discover → profile → analyze → translate → compare → annotate → hypothesize.\n"
                "If you are stuck on a gene, call skip_gene('reason') to move on."
            ),
        })

        # Reset loop tracker
        self._recent_tool_calls.clear()
        ui_log("INFO", f"Loop broken — suggested next step: {hint[:100]}")

    @staticmethod
    def _suggest_next_step(stuck_call: str) -> str:
        """Given the tool call that was looping, suggest what to do next."""
        call_lower = stuck_call.lower()

        if stuck_call == "__NO_TOOL__":
            return ("You must call a tool. Try: TOOL: next_gene() to get a target, "
                    "or TOOL: list_sequences() to see what data you have.")

        if "ncbi_search" in call_lower:
            return ("You already have search results. Now USE them: "
                    "pick an accession ID from the results and call "
                    "TOOL: ncbi_fetch('ACCESSION_ID', db='nucleotide') to download the sequence, "
                    "or TOOL: gene_info('GENE_NAME') to get detailed info.")

        if "ncbi_fetch" in call_lower:
            return ("You already fetched this sequence. Now analyze it: "
                    "TOOL: analyze_sequence('FILENAME.fasta') to check composition, "
                    "or TOOL: translate_sequence('FILENAME.fasta') for protein translation.")

        if "gene_info" in call_lower:
            return ("You already have gene info. Move to sequence analysis: "
                    "TOOL: ncbi_fetch('ACCESSION', db='nucleotide') to get the sequence, "
                    "or TOOL: uniprot_search('GENE_NAME') to find protein data.")

        if "analyze_sequence" in call_lower:
            return ("Analysis done. Next steps: "
                    "TOOL: translate_sequence('FILE') for protein translation, "
                    "TOOL: blast_search('FILE') for homology search, "
                    "or TOOL: save_finding('title', 'description', 'evidence') to record results.")

        if "uniprot" in call_lower:
            return ("You have UniProt results. Try: "
                    "TOOL: analyze_sequence('FILE') on a downloaded sequence, "
                    "or TOOL: save_finding('title', 'description', 'evidence') to record what you found.")

        if "blast" in call_lower:
            return ("BLAST is done. Record your findings: "
                    "TOOL: save_finding('title', 'description', 'evidence').")

        if "pubmed" in call_lower:
            return ("Literature search done. Use results to form hypotheses: "
                    "TOOL: save_finding('title', 'description', 'evidence'), "
                    "or search for a different angle with a new query.")

        if "save_finding" in call_lower:
            return ("Finding saved! Get your next target: "
                    "TOOL: next_gene()")

        # Generic fallback
        return ("Try a DIFFERENT tool than the one you were repeating. "
                "Options: gene_info(), ncbi_fetch(), analyze_sequence(), "
                "save_finding(), next_gene(), list_sequences().")

    def _trim_messages(self, keep_recent: int = 20, hard_limit: int = 60):
        """Smart per-cycle context management.

        Every cycle:
        1. Messages within the last `keep_recent` are kept in full detail.
        2. Older messages get compressed:
           - Tool results (user msgs with "[orchestrator] X returned:") → truncated to ~150 chars
           - Assistant thinking/reasoning → condensed to tool call + 1-line summary
           - Nudge messages → dropped entirely (they add no value to history)
        3. If total still exceeds `hard_limit`, oldest compressed messages are dropped.

        This prevents Qwen from losing coherence after ~30 cycles by keeping
        the context window focused on recent work while retaining a brief
        history of what was already done.
        """
        if len(self.messages) <= keep_recent + 1:  # +1 for system prompt
            return

        system = self.messages[0]
        # Split into old vs recent
        cutoff = len(self.messages) - keep_recent
        old_messages = self.messages[1:cutoff]
        recent_messages = self.messages[cutoff:]

        compressed = []
        compressed_count = 0

        i = 0
        while i < len(old_messages):
            msg = old_messages[i]
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Drop empty messages
            if not content.strip():
                i += 1
                continue

            # Drop nudge and reflection messages — they're noise in history
            if role == "user" and ("No tool call detected" in content
                                   or "— REFLECTION" in content):
                i += 1
                compressed_count += 1
                continue

            # Compress tool results — keep tool name + first ~150 chars
            if role == "user" and content.startswith("[orchestrator]") and "returned:" in content:
                # Extract tool name and truncate result
                lines = content.split("\n", 2)
                header = lines[0]  # "[orchestrator] tool_name returned:"
                # Get a brief snippet of the result
                result_text = content[len(header):].strip()
                snippet = result_text[:150].replace("\n", " ").strip()
                if len(result_text) > 150:
                    snippet += "..."
                compressed.append({
                    "role": "user",
                    "content": f"{header}\n{snippet}"
                })
                compressed_count += 1
                i += 1
                continue

            # Compress assistant messages — keep tool call line + brief summary
            if role == "assistant":
                # Check if it contains a tool call
                tool_match = TOOL_START_PATTERN.search(content)
                if tool_match:
                    # Extract just the tool call line
                    tool_line_start = content.rfind("\n", 0, tool_match.start())
                    tool_line_end = content.find("\n", tool_match.end())
                    if tool_line_end == -1:
                        tool_line_end = len(content)
                    tool_line = content[tool_line_start + 1:tool_line_end].strip()

                    # Also grab first non-reasoning line as summary
                    summary = ""
                    for line in content.split("\n"):
                        line = line.strip()
                        if (line and not line.startswith("[Reasoning]")
                                and not line.startswith("TOOL:")
                                and "Tool Call" not in line
                                and len(line) > 10):
                            summary = line[:120]
                            break

                    condensed = tool_line
                    if summary:
                        condensed = f"{summary}\n{tool_line}"
                    compressed.append({"role": "assistant", "content": condensed})
                    compressed_count += 1
                else:
                    # Thinking-only message (no tool call) — keep brief
                    brief = content[:200].replace("\n", " ").strip()
                    if len(content) > 200:
                        brief += "..."
                    compressed.append({"role": "assistant", "content": brief})
                    compressed_count += 1
                i += 1
                continue

            # Keep other messages (e.g., initial user prompt) as-is
            compressed.append(msg)
            i += 1

        # Deduplicate compressed messages — if the same tool call or result
        # appears multiple times (early loop that wasn't caught), keep only the last
        deduped = []
        seen_content = set()
        for msg in reversed(compressed):
            # Use a short fingerprint for dedup
            content = msg.get("content", "")
            fingerprint = content[:200]
            if fingerprint in seen_content:
                compressed_count += 1  # count as compressed/dropped
                continue
            seen_content.add(fingerprint)
            deduped.append(msg)
        deduped.reverse()
        compressed = deduped

        # Rebuild messages: system + compressed old + full recent
        self.messages = [system] + compressed + recent_messages

        # Hard limit: if still too many, drop oldest compressed messages
        if len(self.messages) > hard_limit:
            excess = len(self.messages) - hard_limit
            # Drop from position 1 (after system), keeping system + recent
            self.messages = [system] + self.messages[1 + excess:]
            compressed_count += excess

        if compressed_count > 0:
            ui_log("INFO", f"Context managed: compressed {compressed_count} old messages, total now {len(self.messages)}")


# Map tools to the pipeline step they naturally complete
_TOOL_STEP_MAP = {
    "gene_info": "discover",
    "ncbi_fetch": "profile",
    "analyze_sequence": "analyze",
    "translate_sequence": "translate",
    "uniprot_fetch": "translate",
    "blast_search": "compare",
    "compare_sequences": "compare",
    "uniprot_search": "annotate",
    "hypothesize": "hypothesize",
    "save_finding": "hypothesize",
}

# Pattern to extract gene names from finding titles/results
_GENE_NAME_RE = re.compile(r'\b(C\d+orf\d+|LOC\d+|[A-Z][A-Z0-9]{1,10})\b')


def _auto_complete_step(tool_name: str, result_str: str):
    """Auto-mark pipeline steps done when the corresponding tool succeeds.

    Qwen often forgets to call complete_step() after using a tool.
    This silently marks the step so the pipeline tracks progress correctly.

    Special handling for save_finding: auto-completes the gene in the queue
    so Qwen doesn't revisit it. Also checks if the gene was being worked on
    outside the queue (direct analysis without add_to_queue) and registers it.
    """
    if "[ERROR]" in result_str or "[REJECTED]" in result_str:
        return

    step = _TOOL_STEP_MAP.get(tool_name)
    if not step:
        return

    try:
        from tools.gene_queue import (
            complete_step as _cs, complete_gene as _cg,
            _load_queue, _save_queue, add_to_queue
        )
        q = _load_queue()

        # --- Special: save_finding → auto-complete the gene entirely ---
        if tool_name == "save_finding":
            # Extract gene name from the result string
            gene_match = _GENE_NAME_RE.search(result_str)
            if gene_match:
                gene_name = gene_match.group(1)

                # If this gene is currently in_progress, complete it
                if q.get("in_progress") and q["in_progress"]["gene"].upper() == gene_name.upper():
                    _cg()
                    ui_log("INFO", f"Auto-completed gene '{gene_name}' (finding saved)")
                    return

                # If this gene was analyzed outside the queue, register it as completed
                # so it won't be re-queued later
                all_known = set()
                all_known.update(g["gene"].upper() for g in q.get("completed", []))
                all_known.update(g["gene"].upper() for g in q.get("skipped", []))
                all_known.update(g["gene"].upper() for g in q.get("queue", []))
                if q.get("in_progress"):
                    all_known.add(q["in_progress"]["gene"].upper())

                if gene_name.upper() not in all_known:
                    # Register as completed directly
                    import datetime
                    q["completed"].append({
                        "gene": gene_name,
                        "finished": datetime.datetime.now().isoformat(),
                        "steps_done": ["discover", "hypothesize"],
                        "source": "auto-registered from save_finding",
                    })
                    q["stats"]["genes_completed"] = len(q["completed"])
                    _save_queue(q)
                    ui_log("INFO", f"Auto-registered gene '{gene_name}' as completed (was outside queue)")
            return

        # --- Normal step completion ---
        if not q.get("in_progress"):
            return
        done = q["in_progress"].get("steps_done", [])
        if step not in done:
            _cs(step)
            ui_log("INFO", f"Auto-completed pipeline step '{step}' (from {tool_name})")
    except Exception:
        pass  # Don't crash the orchestrator for pipeline tracking


def _build_reflection_prompt(tool_name: str, result_str: str,
                             turn: int, max_turns: int,
                             soft_turns: int = 12) -> str:
    """Build a lightweight reflection prompt after a tool execution.

    Sent as a user message so Qwen sees the result and decides what to do next
    within the same cycle (multi-turn inner loop).
    """
    # Truncate result for the reflection prompt (keep it focused)
    result_preview = result_str[:1500]
    if len(result_str) > 1500:
        result_preview += "\n... (truncated)"

    # After save_finding, direct Qwen to move to next gene
    if tool_name == "save_finding":
        return (
            f"[orchestrator] Turn {turn} — REFLECTION\n\n"
            f"Finding saved successfully.\n\n"
            "GOOD WORK! Now move to the next gene:\n"
            "TOOL: next_gene()\n\n"
            "Do NOT re-analyze the same gene. The queue will give you a new target."
        )

    # Dynamic pacing — no pressure early, gentle nudge after soft cap
    if turn < soft_turns:
        pacing = "Take your time — explore all relevant sources before saving."
    elif turn < max_turns - 2:
        pacing = "You've done thorough research. When ready, save your finding."
    else:
        pacing = "Wrap up and save your finding now."

    return (
        f"[orchestrator] Turn {turn} — REFLECTION\n\n"
        f"Tool result from {tool_name}:\n{result_preview}\n\n"
        "Before your next action, REFLECT briefly:\n"
        "1. EVALUATE: What useful data did this tool give me? What's still missing?\n"
        "2. TOOL REVIEW: Which sources have I already queried? Which scoring dimensions am I missing?\n"
        f"3. PLAN: {pacing}\n\n"
        "Scoring reminders:\n"
        "  COVERAGE: InterPro domains, STRING interactions, HPA expression, ClinVar, conservation, AlphaFold\n"
        "  DEPTH: 400+ char description, quantitative data, named entities\n"
        "  INSIGHT: functional hypothesis, cross-domain reasoning, mechanistic proposal\n\n"
        "Now call your next tool using TOOL: format."
    )


def _deduplicate_response(response: str) -> tuple[str, bool]:
    """Detect and remove repeated THOUGHT blocks or repeated substantial lines.

    Qwen sometimes repeats the same reasoning block multiple times in a single
    response, consuming tokens without producing useful output. This detects
    that pattern and keeps only the first occurrence of each substantial line,
    while always preserving TOOL: lines.

    Returns (cleaned_response, was_deduplicated).
    """
    lines = response.split("\n")

    # Count occurrences of substantial lines
    line_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 20:
            line_counts[stripped] = line_counts.get(stripped, 0) + 1

    # If no substantial line appears 3+ times, no dedup needed
    max_repeats = max(line_counts.values()) if line_counts else 0
    if max_repeats < 3:
        return response, False

    # Deduplicate: keep first occurrence, always keep TOOL: lines
    seen: set[str] = set()
    deduped: list[str] = []
    was_deduped = False

    for line in lines:
        stripped = line.strip()
        # Always keep TOOL: lines
        if TOOL_START_PATTERN.search(stripped) or stripped.upper().startswith("TOOL:"):
            deduped.append(line)
            continue
        # Keep short/empty lines
        if len(stripped) <= 20:
            deduped.append(line)
            continue
        # Deduplicate substantial repeated lines
        if stripped in seen:
            was_deduped = True
            continue
        seen.add(stripped)
        deduped.append(line)

    return "\n".join(deduped), was_deduped


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
