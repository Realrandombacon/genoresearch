# ANKRD40: Brain-Enriched Ankyrin/UBL Scaffold Protein Coupling COPII Vesicle Trafficking to Nucleolar Function

**Date:** 2026-03-20T09:50:37.461355

**Quality Score:** 4.55/10  (E=7.1, D=2.0) [MODERATE]

## Description
ANKRD40 encodes a 368-amino acid intracellular scaffold protein (UniProt Q6AI12) with a bipartite domain architecture: N-terminal ankyrin repeat superfamily (IPR002110, IPR036770, PF13637, residues 1-110) providing protein-protein interaction capacity, and C-terminal ubiquitin-like domain (IPR060551, PF27687, residues 265-338) suggesting roles in ubiquitination or UBL conjugation pathways. AlphaFold predicts medium-confidence structure (pLDDT 68.5) consistent with flexible linker regions between structured domains.

STRING interaction network reveals striking enrichment for COPII vesicle trafficking machinery: SEC13 (0.808), SEC23A (0.639), SEC23B (0.636), SEC24A (0.606), SEC24B (0.607), SAR1A (0.654), SAR1B (0.577) - all components of ER-to-Golgi transport vesicles. The highest-confidence partner is AHCY (adenosylhomocysteinase, 0.828), linking methylation cycle metabolism to trafficking. Additional partners include SUPT20H (SAGA complex transcriptional coactivator, 0.590) and SUMF2 (sulfatase modifying factor, 0.489).

HPA expression profiling shows exceptional brain enrichment (196.0 nTPM - among highest for dark genes), detected ubiquitously across tissues, with subcellular localization to nucleoli fibrillar center, Golgi apparatus, and cytosol. This tri-compartmental localization (nucleolus-Golgi-cytosol) combined with COPII interactions suggests ANKRD40 functions as a nucleolar-Golgi shuttle coordinating ribosome biogenesis with secretory pathway flux.

ClinVar documents 12 pathogenic variants including splice donor mutations (c.134+2T>G), deletions, and chromosome 17q CNVs, indicating functional disruption causes disease despite no specific disease annotation yet.

FUNCTIONAL HYPOTHESIS: ANKRD40 operates as a COPII vesicle cargo adaptor that links nucleolar ribosome biogenesis to Golgi secretory trafficking in neurons. The ankyrin repeat domain scaffolds COPII coat components (SEC23/24 heterodimers) while the ubiquitin-like domain recruits ubiquitination machinery for cargo selection or quality control. High brain expression (196 nTPM) suggests specialized roles in neuronal protein secretion, potentially regulating neurotransmitter receptor trafficking or synaptic vesicle biogenesis. Interaction with AHCY couples S-adenosylhomocysteine metabolism (methylation cycle) to vesicle formation, possibly via methylation-dependent cargo sorting. Nucleolar localization indicates involvement in ribosomal subunit export or ribosome-associated quality control (RAQ) pathways. Pathogenic variants likely disrupt COPII cargo loading, causing defective neuronal protein secretion and nucleolar stress.

## Evidence
```
Evidence: InterPro IPR002110/IPR036770/PF13637 ankyrin repeats (aa 1-110), IPR060551/PF27687 UBL domain (aa 265-338); STRING partners: AHCY(0.828), SEC13(0.808), SAR1A(0.654), SEC23A(0.639), SEC23B(0.636), SEC24B(0.607), SEC24A(0.606), SUPT20H(0.590), SAR1B(0.577), SUMF2(0.489); HPA: brain 196.0 nTPM, nucleoli+Golgi+cytosol, tissue-enhanced; ClinVar: 12 pathogenic variants (splice, del, CNV); AlphaFold pLDDT 68.5; UniProt Q6AI12 368aa
```
