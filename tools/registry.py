"""
Tool registry — maps tool names to callable functions.
The orchestrator dispatches TOOL: calls here.
Includes fuzzy matching so Qwen's invented tool names still resolve.
"""

import logging

log = logging.getLogger("genoresearch.tools")


class ToolRegistry:
    """Registry of all available tools. Auto-registers genomics tools on init."""

    def __init__(self):
        self._tools: dict[str, callable] = {}
        self._register_defaults()

    def register(self, name: str, func: callable):
        """Register a tool by name."""
        self._tools[name] = func
        log.debug("Registered tool: %s", name)

    def execute(self, name: str, *args, **kwargs) -> str:
        """Execute a tool by name. Tries fuzzy match if exact name not found."""
        func = self._tools.get(name)
        if not func:
            # Try fuzzy matching before giving up
            matched = self._fuzzy_match(name)
            if matched:
                log.info("Fuzzy matched '%s' → '%s'", name, matched)
                func = self._tools[matched]
                name = matched
            else:
                available = ", ".join(sorted(self._tools.keys()))
                return f"[ERROR] Unknown tool '{name}'. Available: {available}"
        try:
            result = func(*args, **kwargs)
            return str(result)
        except TypeError as e:
            # Catch unexpected keyword arguments and retry without them
            err_str = str(e)
            if "unexpected keyword argument" in err_str:
                # Strip the bad kwarg and retry
                bad_key = err_str.split("'")[1] if "'" in err_str else ""
                if bad_key and bad_key in kwargs:
                    log.warning("Stripping bad kwarg '%s' from %s call", bad_key, name)
                    clean_kwargs = {k: v for k, v in kwargs.items() if k != bad_key}
                    try:
                        result = func(*args, **clean_kwargs)
                        return str(result)
                    except Exception as e2:
                        log.error("Tool '%s' failed after kwarg strip: %s", name, e2)
                        return f"[ERROR] {name} failed: {e2}"
            # Suggest correct param name if "did you mean" is possible
            log.error("Tool '%s' failed: %s", name, e)
            hint = self._param_hint(name, err_str)
            return f"[ERROR] {name} failed: {e}{hint}"
        except Exception as e:
            log.error("Tool '%s' failed: %s", name, e)
            return f"[ERROR] {name} failed: {e}"

    def list_tools(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def _fuzzy_match(self, name: str) -> str:
        """Try to match an unknown tool name to a registered one."""
        name_lower = name.lower().replace("-", "_")

        # 1. Case-insensitive exact match
        for registered in self._tools:
            if registered.lower() == name_lower:
                return registered

        # 2. Check if name is a substring of a registered tool (or vice versa)
        for registered in self._tools:
            if name_lower in registered.lower() or registered.lower() in name_lower:
                return registered

        # 3. Strip common prefixes/suffixes Qwen adds
        stripped = name_lower
        for prefix in ("get_", "fetch_", "search_", "run_", "do_", "call_"):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
                break
        for suffix in ("_tool", "_search", "_query"):
            if stripped.endswith(suffix):
                stripped = stripped[:-len(suffix)]
                break
        # Try matching the stripped name
        for registered in self._tools:
            reg_lower = registered.lower()
            if stripped in reg_lower or reg_lower.startswith(stripped):
                return registered

        return ""

    def _param_hint(self, tool_name: str, error_str: str) -> str:
        """Generate a hint about correct parameter names."""
        # Known param corrections
        corrections = {
            "file_path": "filepath",
            "file_name": "filepath",
            "accession": "accession_id",
            "limit": "max_results",
            "gene": "gene_name",
            "query": "question (for query_memory)",
            "content": "description (for save_finding)",
            "sequence": "filepath (pass .fasta filename)",
        }
        for wrong, right in corrections.items():
            if f"'{wrong}'" in error_str:
                return f". Did you mean '{right}'?"
        return ""

    def _register_defaults(self):
        """Register all built-in genomics tools."""
        from tools.ncbi import ncbi_search, ncbi_fetch, pubmed_search, gene_info
        from tools.blast import blast_search
        from tools.uniprot import uniprot_search, uniprot_fetch
        from tools.sequence import analyze_sequence, compare_sequences, translate_sequence
        from tools.findings import save_finding, list_findings, read_finding, review_findings, list_sequences
        from tools.memory_tools import (
            query_memory, my_stats, list_unexplored,
            note, mark_explored, mark_done, dismiss,
        )
        from tools.lab_tools import lab_train, lab_status
        from tools.file_tools import read_file
        from tools.gene_queue import (
            next_gene, add_to_queue, complete_step, complete_gene,
            skip_gene, advance_seed, queue_status,
        )

        # Primary tool names
        self.register("ncbi_search", ncbi_search)
        self.register("ncbi_fetch", ncbi_fetch)
        self.register("blast_search", blast_search)
        self.register("uniprot_search", uniprot_search)
        self.register("uniprot_fetch", uniprot_fetch)
        self.register("analyze_sequence", analyze_sequence)
        self.register("compare_sequences", compare_sequences)
        self.register("save_finding", save_finding)
        self.register("list_findings", list_findings)
        self.register("read_finding", read_finding)
        self.register("review_findings", review_findings)
        self.register("list_sequences", list_sequences)
        self.register("query_memory", query_memory)
        self.register("my_stats", my_stats)
        self.register("list_unexplored", list_unexplored)
        self.register("note", note)
        self.register("mark_explored", mark_explored)
        self.register("mark_done", mark_done)
        self.register("dismiss", dismiss)
        self.register("lab_train", lab_train)
        self.register("lab_status", lab_status)
        self.register("translate_sequence", translate_sequence)
        self.register("pubmed_search", pubmed_search)
        self.register("gene_info", gene_info)
        self.register("read_file", read_file)
        self.register("next_gene", next_gene)
        self.register("add_to_queue", add_to_queue)
        self.register("complete_step", complete_step)
        self.register("complete_gene", complete_gene)
        self.register("skip_gene", skip_gene)
        self.register("advance_seed", advance_seed)
        self.register("queue_status", queue_status)

        # Aliases — Qwen-invented tool names that should resolve
        self.register("translate_sequences", translate_sequence)
        self.register("read", read_file)
        self.register("search_database", ncbi_search)
        self.register("search_ncbi", ncbi_search)
        self.register("fetch_nucleotide", ncbi_fetch)
        self.register("fetch_sequence", ncbi_fetch)
        self.register("fetch_protein", uniprot_fetch)
        self.register("blast_protein", blast_search)
        self.register("blastn", blast_search)
        self.register("blastp", blast_search)
        self.register("blastx", blast_search)
        self.register("save_findings", save_finding)
        self.register("save_analysis", save_finding)
        self.register("log_finding", save_finding)
        self.register("search_pubmed", pubmed_search)
        self.register("pubmed", pubmed_search)
        self.register("search_uniprot", uniprot_search)
        self.register("get_gene_info", gene_info)
        self.register("gene_search", gene_info)
        self.register("analyze", analyze_sequence)
        self.register("sequence_analysis", analyze_sequence)
        self.register("compare", compare_sequences)
        self.register("translate", translate_sequence)
        self.register("memory", query_memory)
        self.register("search_memory", query_memory)
        self.register("stats", my_stats)
        self.register("status", queue_status)
        self.register("cosmic_search", ncbi_search)  # Qwen invents this — redirect to ncbi
        self.register("analyse_sequence", analyze_sequence)  # British spelling
        self.register("blast_nucleotide", blast_search)
        self.register("blast_protein_search", blast_search)
        self.register("protein_search", uniprot_search)
        self.register("gene_query", gene_info)
        self.register("find_gene", gene_info)
        self.register("fetch_gene", ncbi_fetch)
        self.register("get_sequence", ncbi_fetch)
        self.register("download_sequence", ncbi_fetch)
        self.register("list_sequence", list_sequences)
        self.register("show_findings", list_findings)
        self.register("get_findings", list_findings)

        log.info("Registered %d tools (incl. aliases)", len(self._tools))
