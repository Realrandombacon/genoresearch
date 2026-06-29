# ZNF703: Oncogenic C2H2 Zinc Finger Transcriptional Repressor in 8p11 Amplification

**Date:** 2026-03-23T03:46:33.599647

**Quality Score:** 3.05/10  (E=5.1, D=1.0) [WEAK]

## Description
ZNF703 (Q9H7S9) encodes a 590-amino acid transcriptional repressor belonging to the Elbow/Noc zinc finger family (IPR051520). The protein architecture features a central NocA-like repression domain (IPR022129/PF12402, residues 311-365) and a C-terminal C2H2 zinc finger DNA-binding motif (IPR013087/G3DSA:3.30.160.60, residues 456-489). AlphaFold prediction yields a global pLDDT of 50.2, indicating a structured DNA-binding C-terminus coupled with an intrinsically disordered N-terminal repression region, characteristic of dynamic transcriptional regulators.

STRING interaction analysis identifies 10 partners, highlighting three functional axes: (1) Transcriptional corepression via TRIM28 (0.508, KAP1) and DCAF7 (0.726, WD40 scaffold); (2) 8p11 amplicon co-amplification partners including FGFR1 (0.684) and ERLIN2 (0.639), reflecting genomic linkage in luminal B breast cancer; (3) Developmental patterning factors MSX2 (0.517) and HOXA1 (0.512), suggesting roles in hindbrain rhombomere specification conserved from zebrafish (znf703, 589 aa) and mouse (Znf703, 594 aa, ~95% identity).

HPA data shows tissue-enhanced expression peaking in skeletal muscle (104.7 nTPM) with nuclear matrix localization. The gene acts as a molecular repressor of differentiation programs, specifically blocking mammary epithelial cell differentiation while promoting proliferation.

ClinVar lists 56 pathogenic/likely pathogenic variants, predominantly large copy number gains (amplifications) spanning 8p11.23-q11.23. These amplifications are hallmark drivers of luminal B breast cancer, where ZNF703 overexpression correlates with poor prognosis and endocrine resistance.

FUNCTIONAL HYPOTHESIS: ZNF703 functions as a lineage-specific transcriptional silencer that maintains progenitor states in mammary epithelium. The disordered N-terminal domain recruits the TRIM28/SETDB1 histone methyltransferase complex via DCAF7 scaffolding to deposit H3K9me3 repressive marks at differentiation loci (e.g., GATA3 targets). The C2H2 finger anchors the complex to GC-rich promoter elements. In luminal B breast cancer, 8p11 amplification drives ZNF703 overexpression, locking cells in a proliferative, undifferentiated state and conferring resistance to estrogen receptor signaling modulators. Interaction with FGFR1 (co-amplified) may create a feed-forward loop enhancing MAPK signaling to further stabilize the repressor complex.

## Evidence
```
InterPro: IPR051520/Elbow-Noc(20-590), IPR022129/PF12402/NocA(311-365), IPR013087/C2H2(456-489), G3DSA:3.30.160.60 | STRING: DCAF7(0.726), FGFR1(0.684), ERLIN2(0.639), TRIM28(0.508), MSX2(0.517), HOXA1(0.512) | HPA: Nuclear matrix, Skeletal muscle 104.7 nTPM, Repressor | ClinVar: 56 pathogenic variants (amplicons) | UniProt: Q9H7S9, 590aa | AlphaFold: pLDDT 50.2 (disordered N-term, structured C-term) | Conservation: Mouse Znf703 (594aa), Zebrafish znf703 (589aa)
```
