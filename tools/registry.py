"""
Tool registry — maps tool names to callable functions.
The orchestrator dispatches TOOL: calls here.
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
        """Execute a tool by name. Returns result string or error."""
        func = self._tools.get(name)
        if not func:
            available = ", ".join(sorted(self._tools.keys()))
            return f"[ERROR] Unknown tool '{name}'. Available: {available}"
        try:
            result = func(*args, **kwargs)
            return str(result)
        except Exception as e:
            log.error("Tool '%s' failed: %s", name, e)
            return f"[ERROR] {name} failed: {e}"

    def list_tools(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

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
            skip_gene, advance_seed, queue_status, hypothesize,
        )
        from tools.interpro import interpro_scan, interpro_search
        from tools.string_db import string_interactions, string_enrichment
        from tools.hpa import hpa_expression
        from tools.alphafold import alphafold_structure
        from tools.clinvar import clinvar_search

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
        self.register("translate_sequences", translate_sequence)  # alias — Qwen uses plural
        self.register("pubmed_search", pubmed_search)
        self.register("gene_info", gene_info)
        self.register("read_file", read_file)
        self.register("read", read_file)  # alias — Qwen may use short form
        self.register("next_gene", next_gene)
        self.register("add_to_queue", add_to_queue)
        self.register("complete_step", complete_step)
        self.register("complete_gene", complete_gene)
        self.register("skip_gene", skip_gene)
        self.register("advance_seed", advance_seed)
        self.register("queue_status", queue_status)
        self.register("hypothesize", hypothesize)
        self.register("make_hypothesis", hypothesize)  # alias
        self.register("hypothesis", hypothesize)  # alias
        self.register("search_database", ncbi_search)  # alias — Qwen invents this name

        # New analysis tools — domains, interactions, expression, structure, clinical
        self.register("interpro_scan", interpro_scan)
        self.register("interpro_search", interpro_search)
        self.register("string_interactions", string_interactions)
        self.register("string_enrichment", string_enrichment)
        self.register("hpa_expression", hpa_expression)
        self.register("alphafold_structure", alphafold_structure)
        self.register("clinvar_search", clinvar_search)
        # Aliases — Qwen may use different names
        self.register("domain_search", interpro_scan)
        self.register("protein_interactions", string_interactions)
        self.register("tissue_expression", hpa_expression)
        self.register("protein_structure", alphafold_structure)
        self.register("clinical_variants", clinvar_search)

        log.info("Registered %d tools", len(self._tools))
