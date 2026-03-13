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
        from tools.ncbi import ncbi_search, ncbi_fetch
        from tools.blast import blast_search
        from tools.uniprot import uniprot_search, uniprot_fetch
        from tools.sequence import analyze_sequence, compare_sequences
        from tools.findings import save_finding, list_findings
        from tools.memory_tools import query_memory, my_stats, list_unexplored
        from tools.lab_tools import lab_train, lab_status

        self.register("ncbi_search", ncbi_search)
        self.register("ncbi_fetch", ncbi_fetch)
        self.register("blast_search", blast_search)
        self.register("uniprot_search", uniprot_search)
        self.register("uniprot_fetch", uniprot_fetch)
        self.register("analyze_sequence", analyze_sequence)
        self.register("compare_sequences", compare_sequences)
        self.register("save_finding", save_finding)
        self.register("list_findings", list_findings)
        self.register("query_memory", query_memory)
        self.register("my_stats", my_stats)
        self.register("list_unexplored", list_unexplored)
        self.register("lab_train", lab_train)
        self.register("lab_status", lab_status)

        log.info("Registered %d tools", len(self._tools))
