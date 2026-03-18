"""
Shared test fixtures for GenoResearch test suite.
"""

import os
import pytest
import config


@pytest.fixture
def isolated_findings(tmp_path, monkeypatch):
    """Patch config.FINDINGS_DIR and config.FINDINGS_FILE to use tmp_path."""
    findings_dir = str(tmp_path / "findings")
    findings_file = str(tmp_path / "findings.tsv")
    os.makedirs(findings_dir, exist_ok=True)

    monkeypatch.setattr(config, "FINDINGS_DIR", findings_dir)
    monkeypatch.setattr(config, "FINDINGS_FILE", findings_file)

    # Also patch the module-level imports in tools.findings
    import tools.findings as findings_mod
    monkeypatch.setattr(findings_mod, "FINDINGS_DIR", findings_dir)
    monkeypatch.setattr(findings_mod, "FINDINGS_FILE", findings_file)

    return {"dir": findings_dir, "file": findings_file}


@pytest.fixture
def mock_memory(tmp_path, monkeypatch):
    """Patch config.MEMORY_FILE to use tmp_path."""
    memory_file = str(tmp_path / "memory.json")
    monkeypatch.setattr(config, "MEMORY_FILE", memory_file)

    # Also patch the module-level import in agent.memory
    import agent.memory as mem_mod
    monkeypatch.setattr(mem_mod, "MEMORY_FILE", memory_file)

    return memory_file
