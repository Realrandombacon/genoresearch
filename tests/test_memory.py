"""
Tests for agent/memory.py — persistent JSON-backed research memory.
"""

import os

from agent.memory import (
    load_memory,
    save_memory,
    update_memory,
    add_finding,
    summarize_memory,
)


class TestLoadMemory:

    def test_load_memory_default(self, mock_memory):
        """No file on disk should return default dict."""
        mem = load_memory()
        assert isinstance(mem, dict)
        assert "findings" in mem
        assert "explored" in mem
        assert "tool_stats" in mem
        # Fresh load from a non-existent file should have empty findings
        assert isinstance(mem["findings"], list)


class TestSaveAndLoad:

    def test_save_and_load(self, mock_memory):
        mem = load_memory()
        mem["notes"].append({"note": "test note", "timestamp": "2026-01-01"})
        save_memory(mem)

        reloaded = load_memory()
        assert len(reloaded["notes"]) == 1
        assert reloaded["notes"][0]["note"] == "test note"


class TestUpdateMemory:

    def test_update_memory(self, mock_memory):
        mem = load_memory()
        update_memory(mem, "ncbi_search", "Found BRCA1 gene results")
        assert mem["tool_stats"]["ncbi_search"] == 1

        update_memory(mem, "ncbi_search", "Another search result")
        assert mem["tool_stats"]["ncbi_search"] == 2


class TestAddFinding:

    def test_add_finding(self, mock_memory):
        mem = load_memory()
        initial_count = len(mem.get("findings", []))
        add_finding(mem, "BRCA1 Analysis", "Detailed description", "Evidence data")
        assert len(mem["findings"]) == initial_count + 1
        last = mem["findings"][-1]
        assert last["title"] == "BRCA1 Analysis"
        assert last["description"] == "Detailed description"
        assert last["evidence"] == "Evidence data"
        assert "timestamp" in last


class TestSummarizeMemory:

    def test_summarize_memory(self, mock_memory, tmp_path, monkeypatch):
        import config
        # Ensure FINDINGS_DIR and SEQUENCES_DIR point to tmp dirs
        findings_dir = str(tmp_path / "findings")
        sequences_dir = str(tmp_path / "sequences")
        os.makedirs(findings_dir, exist_ok=True)
        os.makedirs(sequences_dir, exist_ok=True)
        monkeypatch.setattr(config, "FINDINGS_DIR", findings_dir)
        monkeypatch.setattr(config, "SEQUENCES_DIR", sequences_dir)

        mem = load_memory()
        mem["session_count"] = 3
        mem["explored"] = [{"target": "BRCA1", "status": "complete", "timestamp": "2026-01-01"}]

        result = summarize_memory(mem)
        assert "Sessions: 3" in result
        assert "Targets explored: 1" in result
        assert isinstance(result, str)
