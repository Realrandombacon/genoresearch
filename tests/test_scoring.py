"""
Tests for tools/scoring.py — finding quality score computation.
v2: Stricter scoring with CNV/SNV distinction and 10/10 gating.
"""

from tools.scoring import _compute_score, _classify_clinvar


class TestClassifyClinvar:

    def test_snv_detected(self):
        text = "ClinVar reports 5 missense variants and 2 frameshift mutations"
        assert _classify_clinvar(text) == 'snv'

    def test_cnv_only_detected(self):
        text = "Copy number loss at 7q22.3 chr7:104536649-109624996x1"
        assert _classify_clinvar(text) == 'cnv_only'

    def test_cnv_microdeletion(self):
        text = "20q11.22-13.12 microdeletion syndrome"
        assert _classify_clinvar(text) == 'cnv_only'

    def test_no_clinvar(self):
        text = "No ClinVar data available for this gene"
        assert _classify_clinvar(text) == 'none'

    def test_mixed_snv_and_cnv(self):
        """If both SNV and CNV present, classify as snv (gene-specific wins)."""
        text = "3 missense variants and copy number gain at chr1:238681812"
        assert _classify_clinvar(text) == 'snv'


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
        assert abs(score_thin_ev - score_no_ev) <= 2

    def test_perfect_10_requires_snv(self):
        """10/10 should require gene-specific ClinVar variants (SNV), not just CNVs."""
        title = "C1orf99 - Comprehensive Dark Gene Analysis"
        desc = (
            "C1orf99 encodes a 380 aa protein with a DUF4567 domain (IPR027891) "
            "spanning residues 45-210. STRING interaction analysis reveals high-confidence "
            "interactions (score 0.92) with BRCA1, TP53, and KRAS. HPA tissue expression shows "
            "enrichment in brain (45.2 nTPM) and testis (32.1 nTPM). AlphaFold pLDDT = 85.2. "
            "ClinVar reports 5 pathogenic copy number losses on chromosome 1. "
            "BLAST analysis shows 78.5% identity to mouse ortholog. "
            "We hypothesize this protein functions as a "
            "scaffold in the DNA repair pathway, potentially regulating enzyme activity "
            "at the mitochondrial membrane."
        )
        evidence = (
            "UniProt Q9BXY0, InterPro IPR027891, STRING 0.92 confidence, "
            "HPA 45.2 nTPM brain, AlphaFold pLDDT=85.2, ClinVar 5 pathogenic CNV, "
            "BLAST 78.5% identity Mus musculus"
        )
        score = _compute_score(title, desc, evidence)
        # CNV-only ClinVar should NOT allow 10/10
        assert score < 10, f"CNV-only ClinVar should not score 10, got {score}"

    def test_perfect_10_with_snv(self):
        """10/10 should be achievable with SNV ClinVar + deep analysis."""
        title = "C1orf99 - Comprehensive Dark Gene Analysis"
        desc = (
            "C1orf99 encodes a 380 aa protein with a DUF4567 domain (IPR027891) "
            "spanning residues 45-210. STRING interaction analysis reveals high-confidence "
            "interactions (score 0.92) with BRCA1, TP53, and KRAS, suggesting involvement "
            "in DNA damage response signaling pathway. HPA tissue expression shows "
            "enrichment in brain (45.2 nTPM) and testis (32.1 nTPM), suggesting a role "
            "in neural development. AlphaFold pLDDT = 85.2 indicates a well-folded "
            "structure. ClinVar reports 5 missense pathogenic variants and 2 frameshift "
            "mutations associated with cancer. "
            "BLAST analysis shows 78.5% identity to mouse ortholog, indicating strong "
            "evolutionary conservation. We hypothesize this protein functions as a "
            "scaffold in the DNA repair pathway, potentially regulating enzyme activity "
            "at the mitochondrial membrane. The presence of a kinase-like fold and "
            "its enriched expression in disease-relevant tissues implies clinical significance."
        )
        evidence = (
            "UniProt Q9BXY0, InterPro IPR027891, STRING 0.92 confidence, "
            "HPA 45.2 nTPM brain, AlphaFold pLDDT=85.2, "
            "ClinVar 5 missense + 2 frameshift pathogenic, "
            "BLAST 78.5% identity Mus musculus"
        )
        score = _compute_score(title, desc, evidence)
        assert score == 10, f"Comprehensive SNV finding should score 10, got {score}"

    def test_cnv_scores_lower_than_snv(self):
        """CNV-only ClinVar should not gate 10/10, but SNV should."""
        base = (
            "C1orf99 encodes a 380 aa protein with a DUF4567 domain (IPR027891) "
            "spanning residues 45-210. STRING interaction analysis reveals high-confidence "
            "interactions (score 0.92) with BRCA1, TP53, and KRAS. HPA tissue expression shows "
            "enrichment in brain (45.2 nTPM) and testis (32.1 nTPM). AlphaFold pLDDT = 85.2. "
            "We hypothesize this protein functions as a "
            "scaffold in the DNA repair pathway, potentially regulating enzyme activity "
            "at the mitochondrial membrane."
        )
        cnv_desc = base + " ClinVar reports 5 pathogenic copy number losses on chromosome 1."
        snv_desc = base + " ClinVar reports 5 missense pathogenic variants and 2 frameshift mutations."
        score_cnv = _compute_score("C1orf99", cnv_desc, "evidence")
        score_snv = _compute_score("C1orf99", snv_desc, "evidence")
        # The key property: CNV-only can never reach 10
        assert score_cnv < 10, f"CNV-only should not reach 10, got {score_cnv}"
        # SNV CAN reach 10 with sufficient evidence
        assert score_snv >= score_cnv, f"SNV ({score_snv}) should >= CNV ({score_cnv})"

    def test_redundant_or_family_penalty(self):
        """Olfactory receptor findings should get insight penalty."""
        or_title = "OR6K6 Olfactory Receptor GPCR"
        good_title = "C1orf99 Novel Dark Gene"
        desc = (
            "Gene encodes a 7TM GPCR. STRING shows GNAL interaction 0.69. "
            "HPA not detected. AlphaFold pLDDT 83. "
            "We hypothesize olfactory signal transduction via cAMP pathway."
        )
        score_or = _compute_score(or_title, desc, "evidence")
        score_good = _compute_score(good_title, desc, "evidence")
        assert score_good >= score_or, (
            f"Non-redundant ({score_good}) should >= OR ({score_or})"
        )

    def test_redundant_znf_family_penalty(self):
        """ZNF/KRAB findings should get insight penalty."""
        znf_title = "ZNF695 KRAB Zinc Finger Transcription Factor"
        good_title = "C1orf99 Novel Dark Gene"
        desc = (
            "Gene encodes KRAB domain + C2H2 zinc fingers. STRING shows KAT8 0.42. "
            "HPA cancer enhanced. AlphaFold pLDDT 69. "
            "We hypothesize transcriptional repression via KAP1 recruitment."
        )
        score_znf = _compute_score(znf_title, desc, "evidence")
        score_good = _compute_score(good_title, desc, "evidence")
        assert score_good >= score_znf, (
            f"Non-redundant ({score_good}) should >= ZNF ({score_znf})"
        )

    def test_minimum_score_zero(self):
        """Score should never go below 0."""
        score = _compute_score("", "", "")
        assert score >= 0

    def test_maximum_score_ten(self):
        """Score should never exceed 10."""
        desc = (
            "IPR012345 PF00001 DUF1234 STRING interaction 0.99 partner "
            "45.2 nTPM enriched brain testis pLDDT=95 AlphaFold "
            "10 missense pathogenic ClinVar 99.9% identity conserved "
            "UniProt Q12345 suggests hypothesis likely scaffold "
            "transporter receptor enzyme kinase ligase "
            "pathway signaling metabolism trafficking assembly "
            "domain fold repeat helix transport signal catalytic bind regulate "
            "mitochondria golgi nucleus membrane cilia "
            "cancer disease syndrome " * 5
        )
        score = _compute_score("MEGA GENE", desc, desc)
        assert score <= 10, f"Score should be capped at 10, got {score}"