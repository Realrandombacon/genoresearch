# ZNF782: KRAB-C2H2 Zinc Finger Transcriptional Repressor with Widespread Expression and Clinical CNVs

**Date:** 2026-03-23T10:16:26.316913

**Quality Score:** 2.65/10  (E=5.0, D=0.3) [WEAK]

## Description
ZNF782 (Zinc Finger Protein 782) encodes a 699 amino acid Krüppel-associated box (KRAB) domain-containing zinc finger protein (UniProt Q6ZMW2) localized to chromosome 9q22.33. InterPro analysis reveals a canonical N-terminal KRAB repressor domain (IPR001909, PF01352, residues 7-79) followed by multiple C2H2-type zinc finger motifs (IPR013087, PF00096, residues 279-472) arranged in tandem arrays typical of sequence-specific DNA-binding transcription factors.

AlphaFold prediction yields moderate confidence (global pLDDT 60.7), reflecting the characteristic architecture of KRAB-ZFPs where structured zinc finger domains are connected by flexible linker regions. The HPA classifies ZNF782 as a transcription factor with ubiquitous expression across all tissues (low tissue specificity), localized primarily to the nucleoplasm with occasional mitochondrial detection.

STRING interactions identify 10 protein partners with medium confidence scores (0.409-0.593), notably including TRIM28 (score 0.522), the canonical co-repressor that recruits heterochromatin machinery to KRAB-ZFP target loci. Additional partners include GXYLT1, C11orf94, and various metabolic enzymes, suggesting potential roles in coordinating transcriptional programs with cellular metabolism.

ClinVar documents 34 pathogenic/likely pathogenic variants, predominantly large copy number variations (deletions, duplications, inversions) spanning 9q22-q34 regions, indicating dosage sensitivity and genomic instability at this locus.

FUNCTIONAL HYPOTHESIS: ZNF782 functions as a sequence-specific transcriptional repressor that binds GC-rich promoter/enhancer elements via its C2H2 zinc finger array and recruits the TRIM28/KAP1 co-repressor complex through its KRAB domain. This complex subsequently recruits SETDB1 histone methyltransferase and HP1 proteins to establish H3K9me3 heterochromatic marks, silencing target genes involved in cell cycle regulation, differentiation, or retrotransposon control. Dysregulation of ZNF782 expression or function may contribute to oncogenesis through derepression of proto-oncogenes or developmental disorders via altered neurodevelopmental gene programs.

## Evidence
```
InterPro: IPR001909/IPR013087/PF01352/PF00096 (KRAB + 3x C2H2 ZF) | STRING: TRIM28 (0.522), GXYLT1 (0.577), C11orf94 (0.543) | HPA: Ubiquitous, Nucleoplasm, Transcription factor | ClinVar: 34 pathogenic variants (CNVs, deletions) | AlphaFold: pLDDT 60.7 (Medium) | UniProt: Q6ZMW2 (699 aa) | Gene ID: 158431, 9q22.33
```
