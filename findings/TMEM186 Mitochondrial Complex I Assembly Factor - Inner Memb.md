# TMEM186: Mitochondrial Complex I Assembly Factor - Inner Membrane Chaperone in Respiratory Chain Biogenesis

**Date:** 2026-03-20T09:15:29.184448

**Quality Score:** 3.6/10  (E=6.9, D=0.3) [MODERATE]

## Description
TMEM186 encodes a 213 amino acid mitochondrial inner membrane protein that functions as an assembly chaperone for NADH-ubiquinone oxidoreductase (Complex I) of the electron transport chain. The protein belongs to the TMEM70/TMEM186/TMEM223 family (IPR045325, PF06979, residues 98-207) with a TMEM186-specific domain (IPR026571, residues 1-211) that anchors it to the inner mitochondrial membrane. AlphaFold predicts a partially structured conformation (pLDDT 60.5/100), consistent with intrinsically disordered chaperone regions that facilitate dynamic protein-protein interactions during Complex I assembly.

Expression profiling (HPA) shows ubiquitous expression across all tissues with low tissue specificity and cell junction enhancement, matching the universal requirement for oxidative phosphorylation. STRING interactions reveal exclusive partnerships with mitochondrial respiratory chain assembly factors—all at high-to-medium confidence: TMEM126B (0.949), MT-ND3 (0.934), TIMMDC1 (0.830), COA1 (0.794), NDUFAF6 (0.757), NDUFAF4 (0.746), NDUFAF1 (0.737), ACAD9 (0.682), ECSIT (0.630), NDUFAF3 (0.577). This interaction network defines the Complex I assembly module where TMEM186 likely stabilizes early membrane arm intermediates containing MT-ND3 and recruits peripheral assembly factors (NDUFAFs).

ClinVar documents 27 pathogenic/likely pathogenic variants including copy number variations (deletions, duplications on 16p13) and splice defects (c.4-3C>T), implicating TMEM186 in mitochondrial disease phenotypes. The TMEM70/TMEM186/TMEM223 family shares topological features with known ATP synthase assembly factors (TMEM70 causes neonatal encephalocardiomyopathy). Mechanistically, TMEM186 likely acts as a membrane-embedded chaperone that stabilizes nascent Complex I membrane arm subunits (MT-ND3, MT-ND4L, MT-ND6) during co-translational insertion, preventing aggregation and facilitating module integration with nuclear-encoded assembly factors (TIMMDC1, NDUFAFs). Defects cause Complex I deficiency, impairing NADH oxidation and ATP synthesis in high-energy tissues.

## Evidence
```
InterPro: IPR026571 TMEM186 (aa 1-211), IPR045325/PF06979/PTHR13603 TMEM70/TMEM186/TMEM223 family (aa 98-207) | STRING: TMEM126B(0.949), MT-ND3(0.934), TIMMDC1(0.830), COA1(0.794), NDUFAF6(0.757), NDUFAF4(0.746), NDUFAF1(0.737), ACAD9(0.682), ECSIT(0.630), NDUFAF3(0.577) | HPA: ubiquitous expression, low tissue specificity, cell junctions | ClinVar: 27 pathogenic variants (CNVs, splice) | AlphaFold: pLDDT 60.5 (medium confidence) | UniProt: Q96B77 (213 aa) | Function: Complex I membrane arm assembly chaperone
```
