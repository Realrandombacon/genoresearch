"""
Finding scoring — compute quality scores for research findings.
v4: Rebuilt scoring with higher component ceilings, insight bonuses, depth bonuses,
    and proper 10/10 gating for SNV vs CNV-only.
    Backward compatible via _compute_score / _classify_clinvar.
"""
import re
import math


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _count_occurrences(text: str, keywords: list) -> int:
    return sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE))


def _extract_number(text: str, patterns: list) -> float:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except (ValueError, IndexError):
                continue
    return 0.0


def _classify_clinvar(text: str) -> str:
    """
    Classify ClinVar content: snv, cnv_only, both, generic, none
    Mixed SNV+CNV → 'snv' because gene-specific wins.
    """
    if not text:
        return "none"

    # Direct variant-type phrases
    # Negative phrases — text explicitly says there is NO ClinVar data
    neg_phrases = re.search(r"\bno\s+clinvar\b|\bno\s+clinvar\s+data\b|\bclinvar\s+not\s+found\b|\babsent\s+from\s+clinvar\b", text, re.IGNORECASE)
    if neg_phrases:
        return "none"

    direct_variant = re.search(
        r"(missense|nonsense|frameshift|stop.?gained|splice|silent|synonymous|intronic|deletion|duplication|insertion|inversion|translocation|copy.?number)",
        text,
        re.IGNORECASE,
    )
    if not direct_variant:
        # Check for generic ClinVar mentions
        generic_l = re.search(r"\bclinvar\b", text, re.IGNORECASE)
        if generic_l:
            return "generic"
        return "none"

    snv_l = re.search(
        r"\b(snv|single.?nucleotide|missense|nonsense|frameshift|splice|stop.?gained|pathogenic\s*variant)\b",
        text,
        re.IGNORECASE,
    )
    cnv_l = re.search(
        r"\b(cnv|copy.?number|microdeletion|microduplication|del(?:etion)?|dup(?:lication)?|gain|loss)\b",
        text,
        re.IGNORECASE,
    )

    if snv_l and cnv_l:
        return "snv"  # gene-specific wins
    if snv_l:
        return "snv"
    if cnv_l:
        return "cnv_only"
    return "generic"


def _has_orfam_penalty(text: str) -> bool:
    """Olfactory receptor / zinc-finger / KRAB families are over-studied, penalize insight."""
    return bool(re.search(r"\bOR\d+[A-Z]?\d*\b|\bolfactory\s+receptor\b|\b7TM\s+GPCR\b", text, re.IGNORECASE))


def _has_znf_penalty(text: str) -> bool:
    return bool(re.search(r"\bZNF\d+\b|\bKRAB\b|\bzinc\s+finger\b", text, re.IGNORECASE))


# -----------------------------------------------------------------------------
# EVIDENCE SCORE (E) — 0–10  |  data richness + source diversity
# -----------------------------------------------------------------------------
def _evidence_score(text: str) -> float:
    score = 0.0
    text_l = text.lower()

    # 1. Literature & curation
    pubmed_count = _extract_number(text, [
        r"(\d+)\s*pubmed\s*(?:publication|reference)",
        r"(\d+)\s*publication",
    ])
    if "zero" in text_l or "0 publications" in text or "no literature" in text_l:
        pubmed_count = 0
    score += min(2.0, pubmed_count * 0.4)

    # 2. Functional annotation — domains
    domain_hits = _count_occurrences(text, ["interpro", "pfam", "domain", "repeat", "fold", "helix"])
    known_func = _count_occurrences(text, ["kinase", "transporter", "receptor", "enzyme", "scaffold", "ligase", "protease", "channel", "transcription factor"])
    score += min(2.0, domain_hits * 0.25 + known_func * 0.4)

    # 3. Protein-protein interactions
    string_count = _extract_number(text, [
        r"string.*?(\d+)\s*interact",
        r"(\d+)\s*protein.*interact",
        r"interactions.*?(\d+)",
    ])
    if "0 interactions" in text_l or "zero interactions" in text_l or "no interact" in text_l:
        string_count = 0
    score += min(2.0, string_count * 0.3)

    # 4. Expression data
    if re.search(r"hpa|protein atlas|tissue expression|ntpm", text, re.IGNORECASE):
        score += 1.0
        if re.search(r"testis.specific|brain.specific|liver.specific|tissue.enriched", text, re.IGNORECASE):
            score += 0.5

    # 5. Structural data — weighted by confidence
    if "alphafold" in text_l or "plddt" in text_l:
        plddt = _extract_number(text, [r"pLDDT[:\s=]+(\d+(?:\.\d+)?)", r"plddt[:\s=]+(\d+(?:\.\d+)?)"])
        if plddt >= 90:
            score += 2.5
        elif plddt >= 80:
            score += 2.0
        elif plddt >= 70:
            score += 1.5
        elif plddt >= 50:
            score += 0.8
        else:
            score += 0.3
    elif "predicted structure" in text_l:
        score += 0.4

    # 6. Model organism conservation
    if re.search(r"mouse|mus musculus|zebrafish|danio|rat|rattus", text, re.IGNORECASE):
        identity_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*identity", text, re.IGNORECASE)
        if identity_match:
            ident = float(identity_match.group(1))
            if ident > 80:
                score += 1.5
            elif ident > 50:
                score += 1.0
            elif ident > 30:
                score += 0.5
        else:
            score += 0.4

    # 7. Clinical evidence
    clinvar = _classify_clinvar(text)
    if clinvar == "snv":
        score += 3.0
    elif clinvar == "cnv_only":
        score += 1.5
    elif clinvar == "generic":
        score += 1.5

    # 8. Disease association
    disease_hits = _count_occurrences(text, ["disease", "cancer", "syndrome", "disorder", "pathology", "patients", "familial"])
    score += min(2.0, disease_hits * 0.4)

    # 9. GO / pathway annotation
    if re.search(r"gene ontology|go term|pathway|reactome|kegg|signaling|metabolism|trafficking|assembly", text, re.IGNORECASE):
        score += 1.0

    # 9b. Multi-source coverage bonus
    sources = ["interpro", "pfam", "string", "hpa", "alphafold", "clinvar", "blast", "uniprot", "pubmed", "gtex"]
    source_count = sum(1 for s in sources if s in text_l)
    if source_count >= 5:
        score += 2.0
    elif source_count >= 3:
        score += 1.0
    elif source_count >= 2:
        score += 0.5

    # 10. Quantitative data bonus
    quant_count = len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:aa|kda|ntpm|%|nm|mm|μm|residues|bp)\b", text, re.IGNORECASE))
    score += min(1.5, quant_count * 0.3)

    # 11. Depth bonus for long descriptions
    text_len = len(text)
    if text_len >= 800:
        score += 1.5
    elif text_len >= 500:
        score += 1.0
    elif text_len >= 300:
        score += 0.5

    # --- QUALITY DECAY ---
    # Very thin descriptions get penalized
    if text_len < 100:
        score *= 0.5
    elif text_len < 200:
        score *= 0.8

    # If every source is inferred/predicted with zero experimental data, cap
    all_predicted = bool(re.search(r"(?:no experimental|predicted only|computational|inferred|homology-based)", text, re.IGNORECASE))
    experimental = bool(re.search(r"(?:experimental|cryo.em|x.ray|nmr|co.ip|mass.spec|rna.seq|knockout|crispr)", text, re.IGNORECASE))
    if all_predicted and not experimental:
        score = min(score, 5.5)

    return round(max(0.0, min(10.0, score)), 2)


# -----------------------------------------------------------------------------
# DISCOVERY POTENTIAL (D) — 0–10  |  novelty + dark-gene strategic value + insight
# -----------------------------------------------------------------------------
def _discovery_score(text: str) -> float:
    score = 0.0
    text_l = text.lower()

    # === INSIGHT BONUS (new in v4) ===
    # Base insight for any functional hypothesis or structural analysis
    insight_bonus = 0.0

    # Functional hypothesis keywords
    hypothesis_words = [
        "likely functions", "we suggest", "we hypothesize", "potentially",
        "may serve", "could act", "proposed role", "putative function",
        "involved in", "functions as", "acts as", "role in"
    ]
    has_hypothesis = any(w in text_l for w in hypothesis_words)
    if has_hypothesis:
        insight_bonus += 2.0

    # Evidence-supported insight
    evidence_support = [
        "structural analysis", "consistent with", "matches", "suggests",
        "predicted domain", "sequence analysis", "alignment shows",
        "phylogenetic analysis", "comparative analysis",
        "analysis reveals", "interaction analysis", "suggesting involvement",
        "bioinformatics", "in silico", "computational prediction",
        "fold recognition", "homology modeling", "identified", "reports"
    ]
    has_evidence_support = any(w in text_l for w in evidence_support)
    if has_evidence_support:
        insight_bonus += 1.5

    # Both hypothesis + evidence support → synergy bonus
    if has_hypothesis and has_evidence_support:
        insight_bonus += 1.0

    # Vacuous / empty penalty
    vacuous_phrases = [
        "unknown function", "no data available", "could not determine",
        "no evidence found", "no information", "function unknown",
        "not characterized", "unstudied", "no known function"
    ]
    vacuous_count = sum(1 for p in vacuous_phrases if p in text_l)
    if vacuous_count >= 2:
        insight_bonus = -1.5  # override: vacuous text gets negative
    elif vacuous_count >= 1:
        insight_bonus = max(insight_bonus - 1.0, -1.0)

    score += insight_bonus

    # 1. PURE DARKNESS bonus
    zero_pub = any(p in text_l for p in ["0 publications", "zero publications", "0 pubmed", "no publications", "no literature"])
    zero_domain = any(p in text_l for p in ["no domains", "zero domains", "no interpro", "no pfam"])
    zero_interact = any(p in text_l for p in ["0 interactions", "zero interactions", "no string interactions", "no interactors"])
    zero_expr = any(p in text_l for p in ["no expression", "not detected", "zero hpa", "no tissue data"])

    darkness_count = sum([zero_pub, zero_domain, zero_interact, zero_expr])
    if darkness_count >= 3:
        score += 3.5
    elif darkness_count == 2:
        score += 2.5
    elif darkness_count == 1:
        score += 1.2

    # 2. Uncharacterized / novelty language
    if re.search(r"uncharacterized|hypothetical|novel (?:gene|protein|orf)|putative|unknown function", text, re.IGNORECASE):
        score += 1.5
    if re.search(r"first structural|first report|orphan|dark gene|unstudied", text, re.IGNORECASE):
        score += 1.0

    # 3. Structural-before-function discovery signal
    plddt = _extract_number(text, [r"pLDDT[:\s=]+(\d+(?:\.\d+)?)", r"plddt[:\s=]+(\d+(?:\.\d+)?)"])
    high_plddt = plddt >= 80
    if high_plddt and zero_pub:
        score += 2.0
    elif high_plddt and darkness_count >= 2:
        score += 1.5
    elif "alphafold" in text_l and plddt >= 70:
        score += 0.8

    # 4. DUF / unknown function domain
    if re.search(r"\bduf\d+\b", text, re.IGNORECASE):
        score += 1.0
    if re.search(r"domain of unknown function", text, re.IGNORECASE):
        score += 1.0

    # 5. Tissue specificity in disease-relevant tissue
    tissue_bonus = 0.0
    if "testis" in text_l:
        tissue_bonus = 1.0
    elif any(t in text_l for t in ["brain", "neuron", "cardiac", "heart", "liver"]):
        tissue_bonus = 0.7
    elif "tissue-specific" in text_l or "enriched" in text_l:
        tissue_bonus = 0.5
    score += tissue_bonus

    # 6. Evolutionary novelty patterns
    if re.search(r"human-specific|primate-specific|hominid", text, re.IGNORECASE):
        score += 1.0
    if re.search(r"conserved in (?:\d+|all) (?!.*studied).*vertebrate", text, re.IGNORECASE):
        score += 0.8

    # 7. Potential unexplored disease territory
    has_disease_keyword = bool(re.search(r"disease|cancer|disorder|pathology", text, re.IGNORECASE))
    has_clinvar = _classify_clinvar(text) != "none"
    if has_disease_keyword and not has_clinvar:
        score += 1.2
    elif has_disease_keyword and has_clinvar:
        score += 0.3

    # 8. Microprotein / smORF novelty
    if re.search(r"microprotein|smorf|small orf|(?:\d+)\s*aa\s*(?:peptide|protein)", text, re.IGNORECASE):
        score += 1.0

    # 9. Source-coverage bonus — multiple distinct evidence sources
    sources = ["interpro", "pfam", "string", "hpa", "alphafold", "clinvar", "blast", "uniprot", "pubmed", "gtex"]
    source_count = sum(1 for s in sources if s in text_l)
    score += min(1.5, source_count * 0.3)

    # 10. Detailed analysis bonus — long text with multiple data modalities
    text_len = len(text)
    if text_len >= 800:
        score += 1.5
    elif text_len >= 500:
        score += 1.0
    elif text_len >= 300:
        score += 0.5

    # 11. Over-studied family penalty
    if _has_orfam_penalty(text):
        score -= 2.0
    if _has_znf_penalty(text):
        score -= 1.5

    # 12. Over-studied penalty — literature richness reduces discovery potential
    pubmed_count = _extract_number(text, [
        r"(\d+)\s*pubmed\s*(?:publication|reference)",
        r"(\d+)\s*publication",
    ])
    if "zero" in text_l or "0 publications" in text:
        pubmed_count = 0
    score -= min(2.0, pubmed_count / 20)

    # 13. Thin prediction penalty
    thin_prediction = bool(re.search(r"^.{0,300}$", text, re.DOTALL)) and bool(re.search(r"predicted|computational|in silico", text, re.IGNORECASE))
    if thin_prediction:
        score -= 1.0

    return round(max(0.0, min(10.0, score)), 2)


# -----------------------------------------------------------------------------
# COMPOSITE & LABELING
# -----------------------------------------------------------------------------
def compute_dual_score(title: str, description: str = "", evidence: str = "") -> dict:
    """
    Returns {"E": float, "D": float, "composite": float, "label": str, "tier": str}
    """
    text = f"{title} {description} {evidence}".strip()
    E = _evidence_score(text)
    D = _discovery_score(text)

    # === 10/10 GATING ===
    clinvar = _classify_clinvar(text)
    # CNV-only ClinVar can never reach 10/10 regardless of evidence
    if clinvar == "cnv_only":
        composite = round(min((E + D) / 2, 9.49), 2)
    else:
        composite = round((E + D) / 2, 2)

    # Tier labels based on composite
    if composite >= 8.5:
        tier = "EXCEPTIONAL"
    elif composite >= 7.0:
        tier = "STRONG"
    elif composite >= 5.0:
        tier = "SOLID"
    elif composite >= 3.5:
        tier = "MODERATE"
    elif composite >= 2.0:
        tier = "WEAK"
    else:
        tier = "POOR"

    label = f"{composite}/10  (E={E}, D={D}) [{tier}]"
    return {
        "E": E,
        "D": D,
        "composite": composite,
        "label": label,
        "tier": tier,
    }


def _compute_score(title: str, description: str = "", evidence: str = "") -> int:
    """
    BACKWARD COMPATIBLE: returns composite integer (0-10) matching old API.
    """
    return int(round(compute_dual_score(title, description, evidence)["composite"]))


# -----------------------------------------------------------------------------
# Quick self-test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    samples = [
        (
            "SEPTIN12 Spermatogenesis Defects and Male Infertility",
            "SEPTIN12 variants (missense, nonsense) linked to male infertility via spermatogenesis defects. 12 PubMed publications. STRING: 8 interactions. InterPro: GTPase domain. AlphaFold pLDDT: 91.2. ClinVar: 4 pathogenic SNVs. Testis-enriched expression.",
            "",
        ),
        (
            "ENSG00000289760 Uncharacterized 23 Amino Acid Micropeptide",
            "ENSG00000289760: Uncharacterized 23 amino acid micropeptide (A0A8V8TNB9) with no domains, no interactions, no expression data, and zero literature. AlphaFold pLDDT: 78.4. DUF1120-containing. Predicted testis-specific. No ClinVar data.",
            "",
        ),
        (
            "DUF1120 Chromosome 1q21.1 Neurodevelopmental Copy Number Driver",
            "DUF1120 domain-containing genes at 1q21.1 show CNV association with neurodevelopmental disorders and microcephaly. 45 PubMed publications. STRING: 3 interactions. InterPro: DUF1120. ClinVar: pathogenic CNVs. AlphaFold pLDDT: 65.2. Brain expression.",
            "",
        ),
    ]

    for t, d, e in samples:
        r = compute_dual_score(t, d, e)
        print(f"{t[:50]:50s}  →  {r['label']}")