"""
Loop detection — detect and break agent loops in the research orchestrator.
"""

from collections import Counter

from agent.ui import log as ui_log


def is_looping(recent_tool_calls: list[str], loop_threshold: int) -> bool:
    """Check if the agent is stuck in a loop.

    Two checks:
    1. Last N calls are strictly identical (immediate loop)
    2. Same call appears 3+ times in the last 10 calls (spread-out loop,
       e.g. search -> nudge -> search -> nudge -> search)
    """
    if len(recent_tool_calls) < loop_threshold:
        return False
    # Check 1: strictly consecutive identical calls
    last_n = recent_tool_calls[-loop_threshold:]
    if len(set(last_n)) == 1:
        return True
    # Check 2: same call appears 3+ times in last 10 (spread-out loop)
    counts = Counter(recent_tool_calls[-10:])
    for call, count in counts.items():
        if call != "__NO_TOOL__" and count >= 3:
            return True
    return False


def break_loop(messages: list[dict], recent_tool_calls: list[str],
               stuck_call: str, loop_threshold: int):
    """Break out of a detected loop by trimming repeated context and
    suggesting the logical next step based on what tool was being repeated.

    Modifies messages in-place. Clears recent_tool_calls.
    """
    system = messages[0]

    # Keep only system + last 4 non-duplicate messages
    unique = []
    seen = set()
    for msg in reversed(messages[1:]):
        fp = msg.get("content", "")[:200]
        if fp not in seen:
            seen.add(fp)
            unique.append(msg)
        if len(unique) >= 4:
            break
    unique.reverse()
    messages.clear()
    messages.append(system)
    messages.extend(unique)

    # Figure out what the next logical step is based on the stuck call
    hint = suggest_next_step(stuck_call)

    messages.append({
        "role": "user",
        "content": (
            f"[orchestrator] LOOP DETECTED: You repeated '{stuck_call}' "
            f"{loop_threshold}+ times without making progress. "
            f"You already have the results from that search.\n\n"
            f"DO SOMETHING DIFFERENT NOW. {hint}\n\n"
            "Pipeline reminder: discover -> profile -> analyze -> translate -> compare -> annotate -> hypothesize.\n"
            "If you are stuck on a gene, call skip_gene('reason') to move on."
        ),
    })

    # Reset loop tracker
    recent_tool_calls.clear()
    ui_log("INFO", f"Loop broken -- suggested next step: {hint[:100]}")


def suggest_next_step(stuck_call: str) -> str:
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

    if "next_gene" in call_lower:
        return ("Queue is empty but the project is NOT complete — there are more seed families to search. "
                "You need to DISCOVER new genes. "
                "TOOL: ncbi_search('C5orf', db='gene', max_results=10) to find new dark genes, "
                "then TOOL: add_to_queue('GENE_NAME', source='ncbi_search') for each one. "
                "DO NOT save 'project complete' findings.")

    if "queue_status" in call_lower or "list_findings" in call_lower or "note" in call_lower:
        return ("Stop checking status and DO RESEARCH. "
                "TOOL: next_gene() to get a target, or "
                "TOOL: ncbi_search('uncharacterized protein human', db='gene') to discover new genes.")

    # Generic fallback
    return ("Try a DIFFERENT tool than the one you were repeating. "
            "Options: gene_info(), ncbi_fetch(), analyze_sequence(), "
            "save_finding(), next_gene(), list_sequences().")
