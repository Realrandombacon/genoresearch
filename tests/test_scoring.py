"""
Tests for tools/scoring.py — finding quality score computation.
"""

from tools.scoring import _compute_score


class TestComputeScore:

    def test_empty_finding(self):
        score = _compute_score("", "", "")
        assert score <= 2, f"Empty finding should score low, got {score}"

    def test_full_coverage(self):
        """Description mentioning InterPro, STRING, HPA, ClinVar, AlphaFold should score high coverage."""
        desc = (
            "InterPro domain IPR012345 identified. "
            "STRING interaction partners with score 0.95 include BRCA1. "
            "HPA tissue expression: 45.2 nTPM enriched in brain. "
            "ClinVar reports 3 pathogenic variants. "
            "AlphaFold pLDDT = 85.2 for the predicted structure."
        )
        score = _compute_score("GENE1 Analysis", desc, "evidence data")
        assert score >= 5, f"Full coverage should score high, got {score}"

    def test_depth_long_description(self):
        """800+ char description should get a depth bonus."""
        short_desc = "Short."
        long_desc = "A" * 800 + " detailed analysis of protein structure."
        score_short = _compute_score("GENE1", short_desc, "")
        score_long = _compute_score("GENE1", long_desc, "")
        assert score_long >= score_short, "Longer description should score >= shorter"

    def test_depth_quantitative_data(self):
        """Numbers with units (aa, kda, nTPM, %) should boost depth."""
        desc = (
            "Protein is 450 aa long, 52.3 kda molecular weight, "
            "expression is 12.5 nTPM, with 95% identity to mouse ortholog."
        )
        score = _compute_score("GENE1", desc, "")
        # Quantitative data adds depth
        score_empty = _compute_score("GENE1", "No data available.", "")
        assert score > score_empty

    def test_insight_hypothesis(self):
        """Functional hypothesis keywords should boost insight."""
        desc = (
            "This gene likely functions as a transporter in the signaling pathway. "
            "We suggest it may serve as a scaffold for protein assembly. "
            "It is potentially involved in membrane trafficking."
        )
        score = _compute_score("GENE1", desc, "evidence")
        assert score >= 2, f"Hypothesis-rich text should score well, got {score}"

    def test_insight_vacuous_penalty(self):
        """'unknown function', 'no data' should reduce insight."""
        vacuous = (
            "Unknown function. No data available. "
            "Could not determine the role of this gene. No evidence found."
        )
        good = (
            "This gene likely functions as a kinase regulator in the signaling pathway. "
            "Structural analysis suggests a transporter domain."
        )
        score_vacuous = _compute_score("GENE1", vacuous, "")
        score_good = _compute_score("GENE1", good, "evidence data")
        assert score_good > score_vacuous

    def test_thin_evidence_penalty(self):
        """Very short evidence should not boost the score much."""
        score_no_ev = _compute_score("GENE1", "A decent description here with enough text.", "")
        score_thin_ev = _compute_score("GENE1", "A decent description here with enough text.", "x")
        # Thin evidence should not substantially change score
        assert abs(score_thin_ev - score_no_ev) <= 2

    def test_perfect_10(self):
        """A comprehensive finding should be able to score 10."""
        title = "C1orf99 - Comprehensive Dark Gene Analysis"
        desc = (
            "C1orf99 encodes a 380 aa protein with a DUF4567 domain (IPR027891) "
            "spanning residues 45-210. STRING interaction analysis reveals high-confidence "
            "interactions (score 0.92) with BRCA1, TP53, and KRAS, suggesting involvement "
            "in DNA damage response signaling pathway. HPA tissue expression shows "
            "enrichment in brain (45.2 nTPM) and testis (32.1 nTPM), suggesting a role "
            "in neural development. AlphaFold pLDDT = 85.2 indicates a well-folded "
            "structure. ClinVar reports 5 pathogenic variants associated with cancer. "
            "BLAST analysis shows 78.5% identity to mouse ortholog, indicating strong "
            "evolutionary conservation. We hypothesize this protein functions as a "
            "scaffold in the DNA repair pathway, potentially regulating enzyme activity "
            "at the mitochondrial membrane. The presence of a kinase-like fold and "
            "its enriched expression in disease-relevant tissues implies clinical significance."
        )
        evidence = (
            "UniProt Q9BXY0, InterPro IPR027891, STRING 0.92 confidence, "
            "HPA 45.2 nTPM brain, AlphaFold pLDDT=85.2, ClinVar 5 pathogenic, "
            "BLAST 78.5% identity Mus musculus"
        )
        score = _compute_score(title, desc, evidence)
        assert score == 10, f"Comprehensive finding should score 10, got {score}"

    def test_minimum_score_zero(self):
        """Score should never go below 0."""
        score = _compute_score("", "", "")
        assert score >= 0

    def test_maximum_score_ten(self):
        """Score should never exceed 10."""
        # Stuff every possible keyword
        desc = (
            "IPR012345 PF00001 DUF1234 STRING interaction 0.99 partner "
            "45.2 nTPM enriched brain testis pLDDT=95 AlphaFold "
            "10 pathogenic ClinVar 99.9% identity conserved "
            "UniProt Q12345 suggests hypothesis likely scaffold "
            "transporter receptor enzyme kinase ligase "
            "pathway signaling metabolism trafficking assembly "
            "domain fold repeat helix transport signal catalytic bind regulate "
            "mitochondria golgi nucleus membrane cilia "
            "cancer disease syndrome " * 5
        )
        score = _compute_score("MEGA GENE", desc, desc)
        assert score <= 10, f"Score should be capped at 10, got {score}"
