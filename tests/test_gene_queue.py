"""
Tests for the gene queue pipeline.
Covers the bugs that were found and fixed in the March 2026 debugging session:
- Race conditions between add_to_queue and next_gene/complete_gene
- _get_known_genes self-blocking (queue genes treated as "done")
- Force-complete without finding
- Duplicate detection across all gene families
"""

import os
import pytest

# Patch config paths BEFORE importing gene_queue
import config

_original_base = config.BASE_DIR
_original_findings = config.FINDINGS_DIR


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path):
    """Redirect all file I/O to a temp directory for each test."""
    config.BASE_DIR = str(tmp_path)
    config.FINDINGS_DIR = str(tmp_path / "findings")
    config.FINDINGS_FILE = str(tmp_path / "findings.tsv")
    config.MEMORY_FILE = str(tmp_path / "memory.json")
    os.makedirs(config.FINDINGS_DIR, exist_ok=True)

    # Patch QUEUE_FILE in gene_queue module
    import tools.gene_queue as gq
    gq.QUEUE_FILE = str(tmp_path / "gene_queue.json")

    # Patch findings module's imported references
    import tools.findings as findings_mod
    findings_mod.FINDINGS_DIR = config.FINDINGS_DIR
    findings_mod.FINDINGS_FILE = config.FINDINGS_FILE

    yield tmp_path

    # Restore
    config.BASE_DIR = _original_base
    config.FINDINGS_DIR = _original_findings
    findings_mod.FINDINGS_DIR = _original_findings


def _create_finding(findings_dir, gene_name, title_suffix="Analysis"):
    """Helper: create a fake finding file on disk."""
    fname = f"{gene_name} - {title_suffix}.md"
    with open(os.path.join(findings_dir, fname), "w") as f:
        f.write(f"# {gene_name}\nTest finding\n")


# ─── _get_known_genes ─────────────────────────────────────────────

class TestGetKnownGenes:

    def test_queue_genes_not_in_known(self, tmp_path):
        """Genes in the queue should NOT be in known (they're 'to do', not 'done')."""
        from tools.gene_queue import _get_known_genes
        q = {
            "queue": [{"gene": "C1orf99"}],
            "completed": [],
            "skipped": [],
            "in_progress": None,
        }
        known = _get_known_genes(q)
        assert "C1ORF99" not in known

    def test_completed_genes_in_known(self, tmp_path):
        """Completed genes must be in known."""
        from tools.gene_queue import _get_known_genes
        q = {
            "queue": [],
            "completed": [{"gene": "C1orf50"}],
            "skipped": [],
            "in_progress": None,
        }
        known = _get_known_genes(q)
        assert "C1ORF50" in known

    def test_skipped_genes_in_known(self, tmp_path):
        """Skipped genes must be in known."""
        from tools.gene_queue import _get_known_genes
        q = {
            "queue": [],
            "completed": [],
            "skipped": [{"gene": "C2orf88"}],
            "in_progress": None,
        }
        known = _get_known_genes(q)
        assert "C2ORF88" in known

    def test_findings_on_disk_in_known(self, tmp_path):
        """Genes with finding files on disk must be in known."""
        from tools.gene_queue import _get_known_genes
        _create_finding(config.FINDINGS_DIR, "C5orf42")
        q = {"queue": [], "completed": [], "skipped": [], "in_progress": None}
        known = _get_known_genes(q)
        assert "C5ORF42" in known

    def test_all_gene_families_detected(self, tmp_path):
        """Findings for FAM, TMEM, CCDC, etc. must be detected, not just CXorf."""
        from tools.gene_queue import _get_known_genes
        for gene in ["FAM71A", "TMEM200A", "CCDC88B", "ANKRD36", "KIAA1549"]:
            _create_finding(config.FINDINGS_DIR, gene)
        q = {"queue": [], "completed": [], "skipped": [], "in_progress": None}
        known = _get_known_genes(q)
        for gene in ["FAM71A", "TMEM200A", "CCDC88B", "ANKRD36", "KIAA1549"]:
            assert gene.upper() in known, f"{gene} not detected in known"

    def test_in_progress_in_known(self, tmp_path):
        """The in_progress gene must be in known."""
        from tools.gene_queue import _get_known_genes
        q = {
            "queue": [],
            "completed": [],
            "skipped": [],
            "in_progress": {"gene": "C3orf85", "steps_done": []},
        }
        known = _get_known_genes(q)
        assert "C3ORF85" in known


# ─── add_to_queue ─────────────────────────────────────────────────

class TestAddToQueue:

    def test_add_new_gene(self, tmp_path):
        from tools.gene_queue import add_to_queue, _load_queue
        result = add_to_queue("C1orf99", source="test")
        assert "Added" in result
        q = _load_queue()
        assert any(g["gene"] == "C1orf99" for g in q["queue"])

    def test_reject_duplicate_in_queue(self, tmp_path):
        from tools.gene_queue import add_to_queue
        add_to_queue("C1orf99", source="test")
        result = add_to_queue("C1orf99", source="test")
        assert "already" in result.lower()

    def test_reject_completed_gene(self, tmp_path):
        """A gene in completed[] must be rejected."""
        from tools.gene_queue import add_to_queue, _save_queue
        _save_queue({
            "queue": [], "completed": [{"gene": "C1orf50"}],
            "skipped": [], "in_progress": None,
            "seed_index": 0, "stats": {"genes_queued": 0, "genes_completed": 1, "genes_skipped": 0},
        })
        result = add_to_queue("C1orf50", source="test")
        assert "already" in result.lower()

    def test_reject_gene_with_finding_on_disk(self, tmp_path):
        """A gene with a finding file must be rejected."""
        from tools.gene_queue import add_to_queue, _save_queue
        _save_queue({
            "queue": [], "completed": [], "skipped": [], "in_progress": None,
            "seed_index": 0, "stats": {"genes_queued": 0, "genes_completed": 0, "genes_skipped": 0},
        })
        _create_finding(config.FINDINGS_DIR, "C5orf42")
        result = add_to_queue("C5orf42", source="test")
        assert "already" in result.lower()

    def test_reject_pseudogene(self, tmp_path):
        from tools.gene_queue import add_to_queue
        result = add_to_queue("C1orf50P1", source="test")
        assert "REJECTED" in result


# ─── next_gene ────────────────────────────────────────────────────

class TestNextGene:

    def _seed_queue(self, tmp_path, genes):
        from tools.gene_queue import _save_queue
        _save_queue({
            "queue": [{"gene": g, "source": "test", "priority": "normal"} for g in genes],
            "completed": [], "skipped": [], "in_progress": None,
            "seed_index": 0, "stats": {"genes_queued": len(genes), "genes_completed": 0, "genes_skipped": 0},
        })

    def test_serves_gene_from_queue(self, tmp_path):
        from tools.gene_queue import next_gene
        self._seed_queue(tmp_path, ["C1orf99", "C2orf88"])
        result = next_gene()
        assert "C1orf99" in result
        assert "ANALYZE" in result

    def test_skips_gene_with_finding(self, tmp_path):
        """A gene with a finding on disk must be skipped, serve the next one."""
        from tools.gene_queue import next_gene
        self._seed_queue(tmp_path, ["C1orf50", "C2orf88"])
        _create_finding(config.FINDINGS_DIR, "C1orf50")
        result = next_gene()
        assert "C2orf88" in result

    def test_queue_not_lost_after_completion(self, tmp_path):
        """Genes added to queue must survive the next_gene() in-place completion."""
        from tools.gene_queue import next_gene, _save_queue
        # Set up: gene in progress, another gene in queue
        _save_queue({
            "queue": [{"gene": "C2orf88", "source": "test", "priority": "normal"}],
            "completed": [], "skipped": [],
            "in_progress": {"gene": "C1orf50", "started": "2026-01-01", "steps_done": []},
            "seed_index": 0, "stats": {"genes_queued": 1, "genes_completed": 0, "genes_skipped": 0},
        })
        # C1orf50 has a finding → should be completed, then C2orf88 served
        _create_finding(config.FINDINGS_DIR, "C1orf50")
        result = next_gene()
        assert "C2orf88" in result, f"C2orf88 was lost! Got: {result}"

    def test_abandoned_gene_skipped_not_completed(self, tmp_path):
        """A gene in_progress WITHOUT a finding must be skipped, not completed."""
        from tools.gene_queue import next_gene, _load_queue, _save_queue
        self._seed_queue(tmp_path, ["C2orf88"])
        # Manually set in_progress WITHOUT creating a finding
        q = _load_queue()
        q["in_progress"] = {"gene": "ABANDONED1", "started": "2026-01-01", "steps_done": []}
        _save_queue(q)

        result = next_gene()
        q = _load_queue()
        # ABANDONED1 should be in skipped, NOT in completed
        skipped_genes = [g["gene"] for g in q["skipped"]]
        completed_genes = [g["gene"] for g in q["completed"]]
        assert "ABANDONED1" in skipped_genes
        assert "ABANDONED1" not in completed_genes


# ─── save_finding integration ─────────────────────────────────────

class TestSaveFindingIntegration:

    def test_save_finding_returns_success(self, tmp_path):
        """save_finding must return a success string (not crash on undefined var)."""
        from tools.findings import save_finding
        result = save_finding(
            title="C1orf99 - Test Finding",
            description="This is a test finding with enough characters to pass the minimum.",
            evidence="test evidence data",
        )
        assert "Finding logged" in result
        assert "Score:" in result

    def test_consolidation_replaces_old_finding(self, tmp_path):
        """Saving a finding for the same gene should remove old files."""
        from tools.findings import save_finding
        save_finding(
            title="C1orf99 - Old Analysis",
            description="This is the old finding with enough text to pass validation.",
            evidence="old evidence",
        )
        # Check file exists
        files_before = os.listdir(config.FINDINGS_DIR)
        assert any("C1orf99" in f for f in files_before)

        save_finding(
            title="C1orf99 - New Analysis",
            description="This is the new finding that should replace the old one completely.",
            evidence="new evidence",
        )
        files_after = os.listdir(config.FINDINGS_DIR)
        c1orf99_files = [f for f in files_after if "C1orf99" in f]
        assert len(c1orf99_files) == 1, f"Expected 1 file for C1orf99, got {len(c1orf99_files)}: {c1orf99_files}"

    def test_save_finding_completes_gene_in_queue(self, tmp_path):
        """save_finding should move the in_progress gene to completed."""
        from tools.gene_queue import _save_queue, _load_queue
        _save_queue({
            "queue": [], "completed": [], "skipped": [],
            "in_progress": {"gene": "C1orf99", "started": "2026-01-01", "steps_done": []},
            "seed_index": 0, "stats": {"genes_queued": 0, "genes_completed": 0, "genes_skipped": 0},
        })

        from tools.findings import save_finding
        save_finding(
            title="C1orf99 - Deep Analysis",
            description="Multi-source analysis of this dark gene with enough detail to pass.",
            evidence="InterPro, STRING, HPA data",
        )

        q = _load_queue()
        assert q["in_progress"] is None
        completed_genes = [g["gene"] for g in q["completed"]]
        assert "C1orf99" in completed_genes


# ─── pseudogene detection ─────────────────────────────────────────

class TestPseudogeneDetection:

    def test_detects_orf_pseudogene(self):
        from tools.gene_queue import _is_pseudogene
        assert _is_pseudogene("C19orf48P") is True
        assert _is_pseudogene("C11orf58P1") is True

    def test_real_gene_not_pseudogene(self):
        from tools.gene_queue import _is_pseudogene
        assert _is_pseudogene("C1orf116") is False
        assert _is_pseudogene("TSBP1") is False

    def test_description_pseudogene(self):
        from tools.gene_queue import _is_pseudogene
        assert _is_pseudogene("GENE1", "this is a pseudogene") is True
        assert _is_pseudogene("GENE1", "withdrawn from database") is True
