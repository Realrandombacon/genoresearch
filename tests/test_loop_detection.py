"""
Tests for orchestrator/loop_detection.py — loop detection and breaking.
"""

from unittest.mock import patch

from orchestrator.loop_detection import is_looping, suggest_next_step


class TestIsLooping:

    def test_no_loop_empty(self):
        assert is_looping([], loop_threshold=2) is False

    def test_consecutive_identical(self):
        assert is_looping(["A", "A"], loop_threshold=2) is True

    def test_no_loop_different(self):
        assert is_looping(["A", "B"], loop_threshold=2) is False

    def test_spread_loop(self):
        """Same call 3+ times in last 10 triggers spread-out loop detection."""
        calls = ["A", "B", "A", "B", "A"]
        assert is_looping(calls, loop_threshold=2) is True

    def test_no_tool_loop(self):
        """__NO_TOOL__ repeated should trigger consecutive check but not spread check."""
        # With threshold=2, consecutive identical triggers
        assert is_looping(["__NO_TOOL__", "__NO_TOOL__"], loop_threshold=2) is True


class TestSuggestNextStep:

    def test_no_tool_suggestion(self):
        result = suggest_next_step("__NO_TOOL__")
        assert "must call a tool" in result.lower()

    def test_ncbi_search_suggestion(self):
        result = suggest_next_step("ncbi_search('BRCA1')")
        assert "ncbi_fetch" in result.lower() or "gene_info" in result.lower()

    def test_save_finding_suggestion(self):
        result = suggest_next_step("save_finding('title', 'desc', 'ev')")
        assert "next_gene" in result.lower()

    def test_generic_fallback(self):
        result = suggest_next_step("some_unknown_tool('x')")
        assert "different tool" in result.lower()
