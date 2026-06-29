# TMEM35B: Nuclear-Localized DoxX Family Membrane Protein with Disease-Associated Copy Number Variants

**Date:** 2026-03-20T08:42:07.173213

**Quality Score:** 3.4/10  (E=5.7, D=1.1) [WEAK]

## Description
TMEM35B encodes a 154 amino acid transmembrane protein (UniProt Q8NCS4) belonging to the DoxX family (InterPro IPR032808, PF07681, residues 5-102) and the transmembrane protein 35A/B family (IPR040399, residues 1-136). AlphaFold predicts a well-folded structure with high confidence (pLDDT 78.9), suggesting stable tertiary structure despite limited sequence homology to characterized proteins.

Expression profiling (HPA) reveals low tissue specificity with ubiquitous detection across all tissues, and subcellular localization to nucleoplasm and nucleoli—unexpected for a predicted membrane protein, suggesting potential dual localization or nucleic acid-binding function. This nuclear enrichment aligns with STRING interaction partners including ZMYM4 (0.448) and ZMYM6 (0.448), zinc finger MYM-type proteins involved in transcriptional regulation and chromatin remodeling.

ClinVar documents 9 pathogenic/likely pathogenic variants, predominantly large copy number alterations (deletions/duplications spanning 1p34.3), indicating dosage sensitivity and potential disease relevance. The paralog TMEM35A (STRING score 0.480) shares domain architecture, suggesting functional redundancy or heterodimerization. Additional interactions with GPN2 (0.570, GTPase involved in RNA polymerase II nuclear import) and TOMM20L (0.527, mitochondrial outer membrane) suggest potential roles in nucleocytoplasmic transport or organelle communication.

Conservation analysis reveals orthologs in mouse (Q3U0Y2, 150 aa, ~97% identity) and rat (D3ZYP5, 152 aa), indicating evolutionary constraint. The PANTHER family assignment (PTHR13163) to "Spinal Cord Expression Protein 4" suggests neural tissue relevance, though HPA shows ubiquitous expression.

HYPOTHESIS: TMEM35B functions as a nuclear membrane-associated scaffold protein that recruits zinc finger transcriptional regulators (ZMYM4/6) to chromatin, potentially modulating gene expression programs. Copy number variants disrupt this scaffolding function, leading to dosage-sensitive phenotypes. The DoxX domain may mediate protein-protein interactions rather than enzymatic activity, positioning TMEM35B as a regulatory hub in nuclear processes.

## Evidence
```
InterPro: IPR032808 (DoxX, aa 5-102), IPR040399 (TMEM35A/B, aa 1-136), PF07681, PTHR13163 | STRING: GPN2(0.570), TOMM20L(0.527), TMEM35A(0.480), CCDC18(0.478), DDX42(0.466), ZMYM4(0.448), ZMYM6(0.448), UROS(0.441) | HPA: Low tissue specificity, nucleoplasm/nucleoli, detected in all | ClinVar: 9 pathogenic CNVs | AlphaFold: pLDDT 78.9 (1-154 aa) | UniProt: Q8NCS4 (154 aa) | Conservation: Mouse Q3U0Y2 (150 aa, ~97%), Rat D3ZYP5 (152 aa)
```
