"""
Context management — deduplication and message trimming for the orchestrator.
"""

import re


def _deduplicate_response(response: str, tool_start_pattern: re.Pattern) -> tuple[str, bool]:
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
        if tool_start_pattern.search(stripped) or stripped.upper().startswith("TOOL:"):
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


def _trim_messages(messages: list[dict], tool_start_pattern: re.Pattern,
                   keep_recent: int = 20, hard_limit: int = 60):
    """Smart per-cycle context management.

    Every cycle:
    1. Messages within the last `keep_recent` are kept in full detail.
    2. Older messages get compressed:
       - Tool results (user msgs with "[orchestrator] X returned:") -> truncated to ~150 chars
       - Assistant thinking/reasoning -> condensed to tool call + 1-line summary
       - Nudge messages -> dropped entirely (they add no value to history)
    3. If total still exceeds `hard_limit`, oldest compressed messages are dropped.

    Modifies messages list in-place.
    """
    from agent.ui import log as ui_log

    if len(messages) <= keep_recent + 1:  # +1 for system prompt
        return

    system = messages[0]
    # Split into old vs recent
    cutoff = len(messages) - keep_recent
    old_messages = messages[1:cutoff]
    recent_messages = messages[cutoff:]

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

        # Drop nudge messages and generic reflections — but KEEP
        # "FINDING SAVED" reflections (they contain the completed gene name
        # and prevent the agent from re-analyzing the same gene)
        if role == "user" and "No tool call detected" in content:
            i += 1
            compressed_count += 1
            continue
        if role == "user" and "— REFLECTION" in content:
            # Generic reflection — drop it
            i += 1
            compressed_count += 1
            continue
        if role == "user" and "— FINDING SAVED" in content:
            # Keep finding-saved reflections — they prevent re-analysis
            compressed.append(msg)
            i += 1
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
            tool_match = tool_start_pattern.search(content)
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

    # Rebuild messages in-place
    messages.clear()
    messages.append(system)
    messages.extend(compressed)
    messages.extend(recent_messages)

    # Hard limit: if still too many, drop oldest compressed messages
    if len(messages) > hard_limit:
        excess = len(messages) - hard_limit
        # Drop from position 1 (after system), keeping system + recent
        new_messages = [system] + messages[1 + excess:]
        messages.clear()
        messages.extend(new_messages)
        compressed_count += excess

    if compressed_count > 0:
        ui_log("INFO", f"Context managed: compressed {compressed_count} old messages, total now {len(messages)}")
