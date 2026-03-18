"""
Tests for tools/findings.py — save_finding and helpers.
"""

import os

import pytest

from tools.findings import save_finding, list_findings, _extract_gene_from_title


class TestSaveFinding:

    def test_save_finding_creates_file(self, isolated_findings, mock_memory):
        result = save_finding(
            title="BRCA1 - Domain Analysis",
            description="This is a detailed test finding with enough text to pass validation checks.",
            evidence="InterPro IPR012345",
        )
        assert "Finding logged" in result
        md_files = [f for f in os.listdir(isolated_findings["dir"]) if f.endswith(".md")]
        assert len(md_files) == 1

    def test_save_finding_tsv_entry(self, isolated_findings, mock_memory):
        save_finding(
            title="TP53 - Expression Profile",
            description="Expression analysis shows enrichment in brain tissue with 45 nTPM measurements.",
            evidence="HPA data",
        )
        assert os.path.exists(isolated_findings["file"])
        with open(isolated_findings["file"], "r", encoding="utf-8") as f:
            content = f.read()
        assert "TP53" in content

    def test_save_finding_rejects_empty(self, isolated_findings, mock_memory):
        result = save_finding(title="Empty", description="", evidence="")
        assert "REJECTED" in result

    def test_save_finding_rejects_meta(self, isolated_findings, mock_memory):
        result = save_finding(
            title="Project Complete - All Done",
            description="The project has been completed successfully with all genes analyzed.",
            evidence="none",
        )
        assert "REJECTED" in result

    def test_save_finding_completes_gene(self, isolated_findings, mock_memory, tmp_path, monkeypatch):
        """save_finding should auto-complete the in-progress gene in the queue."""
        import tools.gene_queue as gq
        monkeypatch.setattr(gq, "QUEUE_FILE", str(tmp_path / "gene_queue.json"))
        gq._save_queue({
            "queue": [],
            "completed": [],
            "skipped": [],
            "in_progress": {"gene": "BRCA1", "started": "2026-01-01", "steps_done": []},
            "seed_index": 0,
            "stats": {"genes_queued": 0, "genes_completed": 0, "genes_skipped": 0},
        })

        save_finding(
            title="BRCA1 - Full Analysis",
            description="Comprehensive analysis of BRCA1 dark gene with multiple data sources.",
            evidence="evidence data",
        )

        q = gq._load_queue()
        assert q["in_progress"] is None
        completed_genes = [g["gene"] for g in q["completed"]]
        assert "BRCA1" in completed_genes


class TestExtractGeneFromTitle:

    def test_loc_pattern(self):
        assert _extract_gene_from_title("LOC123456 Analysis") == "LOC123456"

    def test_corf_pattern(self):
        assert _extract_gene_from_title("C5orf42 - Dark Gene") == "C5ORF42"

    def test_standard_gene(self):
        assert _extract_gene_from_title("BRCA1 Domain Structure") == "BRCA1"

    def test_no_gene(self):
        result = _extract_gene_from_title("a lowercase title with no gene")
        assert result == ""

    def test_gene_with_number(self):
        assert _extract_gene_from_title("TP53 mutations in cancer") == "TP53"


class TestListFindings:

    def test_list_findings_empty(self, isolated_findings):
        result = list_findings()
        assert "No findings" in result

    def test_list_findings_with_files(self, isolated_findings):
        # Create some fake finding files
        for name in ["BRCA1 Analysis.md", "TP53 Study.md"]:
            with open(os.path.join(isolated_findings["dir"], name), "w") as f:
                f.write(f"# {name}\nTest content\n")

        result = list_findings()
        assert "BRCA1" in result
        assert "TP53" in result
        assert "Total findings: 2" in result
