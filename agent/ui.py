"""
Terminal UI — ANSI colors, tool styling, logging, banners, and cycle summaries.
Adapted from AstroResearch for genomics research.
"""

import json
import datetime

from config import RESEARCH_LOG


# ---------------------------------------------------------------------------
# ANSI color codes
# ---------------------------------------------------------------------------

class C:
    """ANSI color codes for rich terminal output."""
    RESET       = "\033[0m"
    BOLD        = "\033[1m"
    DIM         = "\033[2m"
    ITALIC      = "\033[3m"
    UNDERLINE   = "\033[4m"

    # Base log levels
    INFO        = "\033[94m"        # blue
    OK          = "\033[92m"        # green
    WARN        = "\033[93m"        # yellow
    ERROR       = "\033[91m"        # red
    FIND        = "\033[95m"        # magenta

    # Per-tool colors — each genomics tool gets a unique hue
    NCBI        = "\033[38;5;75m"   # steel blue      — NCBI queries
    BLAST       = "\033[38;5;214m"  # orange           — BLAST searches
    UNIPROT     = "\033[38;5;114m"  # soft green       — UniProt queries
    SEQUENCE    = "\033[38;5;51m"   # cyan             — sequence analysis
    COMPARE     = "\033[38;5;177m"  # lavender         — sequence comparison
    FINDINGS    = "\033[38;5;205m"  # hot pink         — findings logging
    MEMORY      = "\033[38;5;123m"  # aqua             — memory tools
    LAB         = "\033[38;5;220m"  # gold             — ML lab experiments

    # Thought styling
    THOUGHT     = "\033[38;5;183m"  # light purple     — LLM reasoning
    THOUGHT_BG  = "\033[48;5;236m"  # dark grey bg

    # Banners & separators
    BANNER      = "\033[38;5;39m"   # bright blue
    CYCLE_HDR   = "\033[38;5;45m"   # sky blue
    SEPARATOR   = "\033[38;5;240m"  # dark grey


# ---------------------------------------------------------------------------
# Tool styling — map tool names to (color, emoji)
# ---------------------------------------------------------------------------

TOOL_STYLE = {
    "ncbi_search":        (C.NCBI,     "🧬"),
    "ncbi_fetch":         (C.NCBI,     "📥"),
    "blast_search":       (C.BLAST,    "💥"),
    "uniprot_search":     (C.UNIPROT,  "🔬"),
    "uniprot_fetch":      (C.UNIPROT,  "📥"),
    "analyze_sequence":   (C.SEQUENCE, "🔍"),
    "compare_sequences":  (C.COMPARE,  "🔀"),
    "translate_sequence": (C.SEQUENCE, "🔄"),
    "translate_sequences":(C.SEQUENCE, "🔄"),
    "save_finding":       (C.FINDINGS, "⭐"),
    "list_findings":      (C.MEMORY,   "📋"),
    "read_finding":       (C.FINDINGS, "📖"),
    "review_findings":    (C.FINDINGS, "📖"),
    "list_sequences":     (C.SEQUENCE, "📂"),
    "query_memory":       (C.MEMORY,   "🧠"),
    "my_stats":           (C.MEMORY,   "📊"),
    "list_unexplored":    (C.MEMORY,   "🗺️"),
    "note":               (C.MEMORY,   "📝"),
    "mark_explored":      (C.MEMORY,   "✅"),
    "mark_done":          (C.MEMORY,   "🏁"),
    "dismiss":            (C.MEMORY,   "🚫"),
    "pubmed_search":      (C.NCBI,     "📚"),
    "gene_info":          (C.NCBI,     "🧬"),
    "lab_train":          (C.LAB,      "⚗️"),
    "lab_status":         (C.LAB,      "📈"),
}


def _tool_color(tool_name):
    """Get (color, emoji) for a tool, with fallback."""
    return TOOL_STYLE.get(tool_name, ("\033[96m", "🔧"))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(level, message, **extra):
    """Write a log entry to file and console with rich colors."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    ts_str = f"\033[38;5;114m{timestamp}{C.RESET}"

    level_colors = {
        "INFO":   C.INFO,
        "OK":     C.OK,
        "WARN":   C.WARN,
        "ERROR":  C.ERROR,
        "TOOL":   "\033[96m",
        "RESULT": "\033[38;5;141m",
        "FIND":   C.FIND,
        "THINK":  C.THOUGHT,
    }
    lc = level_colors.get(level, "")

    # Special rendering for thoughts — full display
    if level == "THINK":
        thought_lines = [l for l in message.split("\n") if l.strip()]
        if not thought_lines:
            thought_lines = ["(thinking...)"]
        prefix = f"{C.THOUGHT}{C.ITALIC}💭{C.RESET}"
        # First line with timestamp
        console_msg = f"  {ts_str} {prefix} {C.THOUGHT}{C.ITALIC}{thought_lines[0].strip()}{C.RESET}"
        # Remaining lines indented
        for line in thought_lines[1:]:
            console_msg += f"\n  {'':>8}   {C.THOUGHT}{C.ITALIC}{line.strip()}{C.RESET}"

    # Special rendering for tool calls
    elif level == "TOOL" and "|" in message:
        parts = message.split("|", 1)
        tool_name = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        color, emoji = _tool_color(tool_name)
        prefix = f"{color}{C.BOLD}{emoji} {tool_name}{C.RESET}"
        console_msg = f"  {ts_str} {prefix} {C.DIM}{rest}{C.RESET}"
    elif level == "TOOL":
        console_msg = f"  {ts_str} {lc}{C.BOLD}🔧 {level}{C.RESET} {message}"

    # Special rendering for tool results
    elif level == "RESULT" and "|" in message:
        parts = message.split("|", 1)
        tool_name = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        color, emoji = _tool_color(tool_name)
        prefix = f"{color}{emoji} {tool_name}{C.RESET}"
        console_msg = f"  {ts_str} {prefix} {C.DIM}→ {rest}{C.RESET}"

    elif level == "OK":
        console_msg = f"  {ts_str} {C.OK}{C.BOLD}✅ {level}{C.RESET} {C.OK}{message}{C.RESET}"
    elif level == "WARN":
        console_msg = f"  {ts_str} {C.WARN}{C.BOLD}⚠️  {level}{C.RESET} {C.WARN}{message}{C.RESET}"
    elif level == "ERROR":
        console_msg = f"  {ts_str} {C.ERROR}{C.BOLD}❌ {level}{C.RESET} {C.ERROR}{message}{C.RESET}"
    elif level == "FIND":
        console_msg = f"  {ts_str} {C.FIND}{C.BOLD}🌟 DISCOVERY{C.RESET} {C.FIND}{message}{C.RESET}"
    else:
        console_msg = f"  {ts_str} {lc}{level}{C.RESET} {message}"

    if extra:
        extra_str = ", ".join(f"{C.DIM}{k}={v}{C.RESET}" for k, v in extra.items())
        console_msg += f" {extra_str}"
    print(console_msg)

    # File log (plain text, no ANSI)
    full_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(RESEARCH_LOG, "a", encoding="utf-8") as f:
            if level == "THINK":
                # Log full thought as multi-line block but single entry
                f.write(f"[{full_ts}] [THINK] --- BEGIN THOUGHT ---\n")
                for tl in message.split("\n"):
                    if tl.strip():
                        f.write(f"  {tl.strip()}\n")
                f.write(f"[{full_ts}] [THINK] --- END THOUGHT ---\n")
            else:
                f.write(f"[{full_ts}] [{level}] {message}")
                if extra:
                    f.write(f" | {json.dumps(extra, default=str)}")
                f.write("\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Banners & summaries
# ---------------------------------------------------------------------------

def print_banner(model, memory, target=None, provider=None):
    """Print a colorful startup banner."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_findings = len(memory.get("findings", []))
    n_explored = len(memory.get("explored", []))
    n_sessions = memory.get("session_count", 0)
    prov = (provider or "ollama").upper()

    print(f"""
{C.BANNER}{C.BOLD}╔══════════════════════════════════════════════════════════╗
║  🧬  GenoResearch — Autonomous Genomics Agent  🧬       ║
╠══════════════════════════════════════════════════════════╣{C.RESET}
{C.BANNER}║{C.RESET}  Provider  : {C.BOLD}{prov}{C.RESET}
{C.BANNER}║{C.RESET}  Model     : {C.BOLD}{model}{C.RESET}
{C.BANNER}║{C.RESET}  Started   : {now}
{C.BANNER}║{C.RESET}  Memory    : {C.BOLD}{n_findings}{C.RESET} findings │ {C.BOLD}{n_explored}{C.RESET} targets │ {C.BOLD}{n_sessions}{C.RESET} session(s)""")
    if target:
        print(f"{C.BANNER}║{C.RESET}  Target    : {C.BOLD}{C.OK}{target}{C.RESET}")
    print(f"""{C.BANNER}{C.BOLD}╚══════════════════════════════════════════════════════════╝{C.RESET}
""")


def print_cycle_header(cycle_num):
    """Print a colorful cycle separator."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"""
{C.SEPARATOR}{'─' * 60}{C.RESET}
  {C.CYCLE_HDR}{C.BOLD}🔬 Research Cycle {cycle_num}{C.RESET}  {C.DIM}@ {now}{C.RESET}
{C.SEPARATOR}{'─' * 60}{C.RESET}""")


def print_cycle_summary(cycle_num, summary_parts):
    """Print a colorful end-of-cycle summary."""
    if not summary_parts:
        return
    print(f"\n  {C.DIM}{'─' * 50}{C.RESET}")
    print(f"  {C.OK}{C.BOLD}📊 Cycle {cycle_num} Summary:{C.RESET}")
    for part in summary_parts:
        # Try to match a tool name from the summary
        matched_tool = None
        for tool_name in TOOL_STYLE:
            if part.startswith(tool_name) or tool_name in part.lower():
                matched_tool = tool_name
                break

        if "ERROR" in part:
            print(f"    ❌ {C.ERROR}{part}{C.RESET}")
        elif "WAITING" in part or "POLLING" in part:
            print(f"    ⏳ {C.WARN}{part}{C.RESET}")
        elif matched_tool:
            color, emoji = _tool_color(matched_tool)
            print(f"    {emoji} {color}{part}{C.RESET}")
        else:
            print(f"    • {C.DIM}{part}{C.RESET}")
    print(f"  {C.DIM}{'─' * 50}{C.RESET}")


def print_completion(cycle_num, memory):
    """Print the final completion banner."""
    n_findings = len(memory.get("findings", []))
    n_explored = len(memory.get("explored", []))

    print(f"""
{C.BANNER}{C.BOLD}╔══════════════════════════════════════════════════════════╗
║  🏁  Research Complete                                   ║
╠══════════════════════════════════════════════════════════╣{C.RESET}
{C.BANNER}║{C.RESET}  Cycles     : {C.BOLD}{cycle_num}{C.RESET}
{C.BANNER}║{C.RESET}  Findings   : {C.BOLD}{C.FIND}{n_findings}{C.RESET}
{C.BANNER}║{C.RESET}  Explored   : {C.BOLD}{n_explored}{C.RESET} targets
{C.BANNER}║{C.RESET}  Log        : {C.DIM}{RESEARCH_LOG}{C.RESET}
{C.BANNER}{C.BOLD}╚══════════════════════════════════════════════════════════╝{C.RESET}
""")
