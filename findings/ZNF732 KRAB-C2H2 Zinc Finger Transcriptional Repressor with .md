# ZNF732: KRAB-C2H2 Zinc Finger Transcriptional Repressor with Cancer-Enriched Expression

**Date:** 2026-03-23T00:14:35.166706

**Quality Score:** 4.6/10  (E=8.4, D=0.8) [MODERATE]

## Description
ZNF732 (Zinc Finger Protein 732) encodes a 585-amino acid Krüppel-associated box (KRAB) domain-containing C2H2 zinc finger transcription factor (UniProt B4DXR9) located on chromosome 4p16.3. The protein architecture features an N-terminal KRAB repressor domain (IPR001909, PF01352, PS50805, residues 4-75) followed by multiple C-terminal C2H2-type zinc finger DNA-binding domains (IPR013087, PF00096, PF13912, PS00028, PS50157) spanning residues 167-440 with at least 16 finger repeats identified. This domain organization is characteristic of the KRAB-ZFP family, the largest group of mammalian transcriptional repressors.

STRING interaction analysis identifies TRIM28 (KAP1/TIF1β) as the primary interaction partner (score: 0.651), which is the canonical co-receptor for KRAB domains that recruits heterochromatin protein 1 (HP1) and histone methyltransferases (SETDB1) to establish H3K9me3 repressive chromatin marks. Additional partners include ANKS4B (0.530), TRAPPC12 (0.451), SUSD1 (0.427), and SNTG2 (0.407), suggesting potential roles in vesicular trafficking and membrane organization. The TRIM28 interaction confirms ZNF732 functions through the canonical KRAB-KAP1 silencing machinery.

HPA expression profiling shows low tissue specificity with detection in some tissues, but cancer-enriched RNA expression pattern, indicating potential upregulation in neoplastic contexts. The protein is classified as a transcription factor with DNA-binding molecular function and transcription regulation biological process. No immune cell expression is detected.

ClinVar documents 138 pathogenic/likely pathogenic variants, predominantly copy number variations (CNVs) including deletions (chr4:68454-12774004x1, chr4:49556-3910769x1) and duplications (chr4:68454-4013853x3) spanning the 4p16.3 region. These large structural variants likely disrupt ZNF732 alongside neighboring genes, contributing to 4p16.3 deletion/duplication syndromes. No single nucleotide pathogenic variants are catalogued, suggesting haploinsufficiency rather than dominant-negative mechanisms.

Conservation analysis from UniProt shows orthologs in gorilla (G3SAS8, 583 aa, ~95% identity), chimpanzee (H2RG74, 585 aa, ~98% identity), and vervet monkey (A0A0D9RRI6, 585 aa, ~93% identity), indicating strong primate conservation. AlphaFold structure prediction was unavailable (API error), but the canonical C2H2 zinc finger fold (ββα motif with Zn²⁺ coordination by Cys2His2 residues) is well-established.

FUNCTIONAL HYPOTHESIS: ZNF732 functions as a sequence-specific transcriptional repressor that binds GC-rich promoter/enhancer elements via its tandem C2H2 zinc finger array. Upon DNA binding, the KRAB domain recruits TRIM28/KAP1, which oligomerizes and recruits SETDB1 histone methyltransferase to deposit H3K9me3 marks, establishing facultative heterochromatin. The cancer-enriched expression suggests ZNF732 may silence tumor suppressor loci or developmental regulators in neoplastic cells. The 16-finger array potentially recognizes a 24-32bp DNA target sequence, providing high specificity for gene regulatory elements controlling cell proliferation or differentiation pathways.

## Evidence
```
Evidence: InterPro domains IPR001909/PF01352/PS50805 (KRAB box), IPR013087/PF00096/PF13912/PS00028/PS50157 (C2H2 zinc fingers); STRING partners TRIM28(0.651)/ANKS4B(0.530)/TRAPPC12(0.451)/SUSD1(0.427); HPA expression: cancer enriched, low tissue specificity, transcription factor class; ClinVar 138 pathogenic CNV variants on 4p16.3; UniProt B4DXR9 (585 aa); Conservation: chimpanzee ~98%, gorilla ~95%, vervet ~93% identity
```
