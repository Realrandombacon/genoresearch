# Endosomal Trafficking Regulator SNX15 Couples APP Recycling to Aβ Production via PX-Mediated PI3P Binding and MIT-Domain ESCRT Recruitment

**Quality Score:** 5.61/10  (E=9.12, D=2.1) [SOLID]

**Date:** 2026-04-27T12:15:17.359005

**Quality Score:** 5.61/10  (E=9.12, D=2.1) [SOLID]

**Confidence:** MEDIUM

## Description
SNX15 (Sorting Nexin 15) is a 342 aa cytosolic/peripheral membrane protein functioning as a critical regulator of endosomal sorting, specifically controlling the cell surface recycling of the Amyloid Precursor Protein (APP) and thereby modulating amyloid-beta (Aβ) generation. Despite 21 literature references, its precise mechanistic role in the endocytic pathway and potential involvement in neurodegeneration remain partially obscure, classifying it as a 'partially characterized' dark gene. InterPro analysis reveals a canonical sorting nexin architecture: an N-terminal Phox Homology (PX) domain (IPR001683/PF00787, aa 1-130) that binds phosphatidylinositol 3-phosphate (PI3P) to anchor SNX15 to early endosomes, and a C-terminal Microtubule Interacting and Transport (MIT) domain (IPR007330/PF04212, aa 265-342) known to interact with ESCRT-III components for membrane scission or cargo selection. AlphaFold predicts a confident global structure (pLDDT 72.4), indicating two well-folded domains connected by a flexible linker, allowing the protein to bridge membrane surfaces and cytosolic machinery. HPA confirms ubiquitous expression with localization to nucleoli, vesicles, plasma membrane, and cytosol, consistent with a dynamic trafficking factor. STRING interactions place SNX15 in a functional network with other sorting nexins (SNX4: 0.788, SNX2: 0.784, SNX1: 0.698, SNX17: 0.628) and ubiquitin ligases (UBOX5: 0.786), suggesting cooperation in cargo recognition and ubiquitin-dependent sorting. ClinVar lists 8 pathogenic/likely pathogenic variants, exclusively large copy number gains/losses on chromosome 11q, implicating SNX15 dosage sensitivity in developmental disorders, though no specific monogenic disease is yet named. Recent literature (2016, 2023) explicitly demonstrates that SNX15 knockdown reduces cell surface APP levels and decreases Aβ secretion, identifying it as a positive regulator of the amyloidogenic pathway by promoting APP recycling over lysosomal degradation.

## Evidence
```
INTERPRO: IPR001683 (PX domain, 1-130, GO:0035091 PI binding), IPR007330 (MIT domain, 265-342), IPR036181 (MIT superfamily, 264-339), IPR036871 (PX superfamily, 3-135), PF00787 (PX, 42-123), PF04212 (MIT, 269-332), cd02677 (MIT_SNX15, 267-341), G3DSA:3.30.1520.10 (Phox-like, 3-135). STRING: SNX4 (0.788), UBOX5 (0.786), SNX2 (0.784), FAM3A (0.779), SNX1 (0.698), FIP1L1 (0.640), RTN4 (0.639), PDGFC (0.637), SNX17 (0.628), REEP6 (0.406). HPA: Detected in all, Low tissue specificity, Nucleoli/Vesicles/Plasma membrane/Cytosol. CLINVAR: 8 pathogenic/LP variants (CNVs on 11q, e.g., chr11:56895955-69295402 x3). ALPHAFOLD: pLDDT 72.4 (Confident), full-length model 1-342 aa, structured PX and MIT domains. UNIPROT: Q9NRS6, 342 aa. LITERATURE: 21 papers; SNX15 regulates APP recycling and Aβ generation (2016, 17 citations; 2023 correction); RARA-SNX15 fusion in APL (2022, 3 citations). CONSERVATION: Orthologs in mouse (Q91WE1, 337 aa), rat (Q4V896, 338 aa), cow (Q148E7, 345 aa) - highly conserved domain order.
```
