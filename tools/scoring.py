"""
Finding scoring — compute quality scores for research findings.
"""

import re


def _compute_score(title: str, description: str, evidence: str) -> int:
    """Compute a quality score (0-10) based on 3 dimensions:
    - COVERAGE (0-5): how many independent data sources were consulted
    - DEPTH (0-3): richness of actual data (not just keyword mentions)
    - INSIGHT (0-3): quality of reasoning, hypothesis, and interpretation
    """
    text = f"{title} {description} {evidence}".lower()
    full_text = f"{title} {description} {evidence}"

    # ===== DIMENSION 1: COVERAGE (0-4) =====
    sources = 0

    # InterPro/Pfam — must have accession or domain description
    if re.search(r'IPR\d+|PF\d+|DUF\d+|UPF\d+', full_text):
        sources += 1
    elif re.search(r'(domain|repeat|fold)\s+(of|in|spanning|residue)', text):
        sources += 1

    # STRING — must have interaction partner name or score
    if re.search(r'(string|interact\w*).{0,80}(0\.\d+|\w{3,15}\s)', text):
        sources += 1

    # HPA/tissue expression — must have tissue name or nTPM value
    if re.search(r'\d+\.?\d*\s*ntpm|enriched|specific.{0,30}(brain|testis|liver|kidney|heart|lung|intestin|muscle|ovary|retina|fallopian|pituitary|adipose|spleen|thyroid|placenta|bone marrow)', text):
        sources += 1

    # AlphaFold — must have pLDDT score
    if re.search(r'plddt\s*[=:]?\s*\d+|alphafold.{0,40}\d+\.?\d*', text):
        sources += 1

    # ClinVar — must have variant count or specific classification
    clinvar_match = re.search(r'(\d+)\s*(pathogenic|clinvar|variant)', text)
    if clinvar_match and int(clinvar_match.group(1)) > 0:
        sources += 1

    # Conservation/BLAST — must have % identity or species comparison
    if re.search(r'\d+\.?\d*\s*%\s*(identity|identical|conserv)', text):
        sources += 1

    # UniProt — must have accession
    if re.search(r'[A-Z]\d[A-Z0-9]{3}\d|uniprot', text):
        sources += 0.5

    coverage = min(5.0, sources)

    # ===== DIMENSION 2: DEPTH (0-3) =====
    depth = 0.0

    total_content_len = len(description) + len(evidence)
    if total_content_len >= 800:
        depth += 1.0
    elif total_content_len >= 400:
        depth += 0.7
    elif total_content_len >= 200:
        depth += 0.4
    elif total_content_len >= 100:
        depth += 0.2

    # Quantitative data points
    numbers_in_context = re.findall(r'\d+\.?\d*\s*(?:aa|kda|ntpm|%|residue|variant|interaction|score)', text)
    depth += min(1.0, len(numbers_in_context) * 0.2)

    # Named protein/gene interactions
    named_entities = re.findall(r'\b[A-Z][A-Z0-9]{2,10}\b', full_text)
    tool_words = {'TOOL', 'INFO', 'WARN', 'ERROR', 'THE', 'AND', 'FOR', 'WITH',
                  'DARK', 'GENE', 'TRUE', 'NOT', 'HPA', 'STRING', 'BLAST',
                  'NCBI', 'INTERPRO', 'ALPHAFOLD', 'CLINVAR', 'UNIPROT',
                  'DUF', 'UPF', 'IPR', 'PFAM', 'DESCRIPTION', 'EVIDENCE',
                  'QUALITY', 'SCORE', 'DATE', 'MODERATE', 'EXCELLENT', 'GOOD', 'LOW'}
    bio_entities = [e for e in set(named_entities) if e not in tool_words and len(e) >= 3]
    depth += min(1.0, len(bio_entities) * 0.1)

    depth = min(3.0, depth)

    # ===== DIMENSION 3: INSIGHT (0-3) =====
    insight = 0.0

    hypothesis_patterns = [
        r'suggest\w*|hypothes\w*|propos\w*|predict\w*|implic\w*',
        r'likely\s+\w+|may\s+function|could\s+serve|potentially',
        r'regulator|scaffold|transporter|receptor|enzyme|kinase|ligase',
        r'pathway|signaling|metabolism|trafficking|assembly',
    ]
    for pattern in hypothesis_patterns:
        if re.search(pattern, text):
            insight += 0.4

    # Correctly identifies gene status
    if re.search(r'not\s+a\s+(true\s+)?dark\s+gene|well.?characteriz|resolved|renamed', text):
        insight += 0.8

    # Cross-domain reasoning
    domains_mentioned = set()
    for domain_type, patterns in {
        'structure': [r'domain|fold|repeat|helix|sheet|coil|disorder'],
        'function': [r'transport|signal|cataly|bind|regulat|modif'],
        'location': [r'mitochond|golgi|nucleus|membrane|cilia|vesicle|centrosome|cytoplasm'],
        'disease': [r'cancer|disease|syndrome|pathogen|clinical|dosage'],
        'expression': [r'enriched|specific|ubiquitous|expressed|ntpm'],
    }.items():
        for p in patterns:
            if re.search(p, text):
                domains_mentioned.add(domain_type)
                break
    if len(domains_mentioned) >= 3:
        insight += 0.5
    if len(domains_mentioned) >= 4:
        insight += 0.3

    # Penalize empty/vacuous findings
    vacuous_phrases = ['no data', 'no evidence', 'no information available',
                       'could not determine', 'unknown function']
    vacuous_count = sum(1 for p in vacuous_phrases if p in text)
    if vacuous_count >= 2:
        insight = max(0, insight - 0.5)

    insight = min(3.0, insight)

    # ===== FINAL SCORE =====
    raw = coverage + depth + insight
    return max(0, min(10, round(raw)))
