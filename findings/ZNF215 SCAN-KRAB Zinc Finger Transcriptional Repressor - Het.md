# ZNF215: SCAN-KRAB Zinc Finger Transcriptional Repressor - Heterochromatin Recruitment Factor

**Date:** 2026-03-20T09:18:44.301807

**Quality Score:** 3.42/10  (E=5.55, D=1.3) [WEAK]

## Description
ZNF215 encodes a 517 amino acid SCAN/KRAB family zinc finger transcription factor that functions as a sequence-specific DNA-binding repressor recruiting heterochromatin machinery. The protein contains an N-terminal SCAN oligomerization domain (IPR003309, IPR038269, residues 44-145) that mediates homo- and hetero-dimerization with paralogs, followed by a KRAB-A repression domain (IPR001909, IPR036051, residues 163-237) that recruits TRIM28/KAP1 corepressor complexes, and three C-terminal C2H2 zinc finger DNA-binding domains (IPR013087, residues 379-406, 407-434, 462-489) that recognize specific GC-rich promoter sequences.

AlphaFold predicts predominantly disordered conformation (pLDDT 49.3/100), characteristic of transcription factors with flexible linkers between structured DNA-binding zinc fingers and intrinsically disordered repression domains that facilitate dynamic chromatin interactions. Expression profiling (HPA) shows tissue-enhanced pattern with highest levels in lymphoid tissue (3.9 nTPM), consistent with immune cell transcriptional regulation roles. Subcellular localization spans nucleoplasm and vesicles, matching nuclear transcription factor function.

STRING interactions reveal partnerships with chromatin modifiers and SCAN-KRAB paralogs: BAZ2A (0.942), BAZ2B (0.942), BAZ1A (0.658), ZSCAN20 (0.592), BAZ1B (0.590), NAP1L4 (0.590), DYNC1I2 (0.543), NSD1 (0.538), IGF2 (0.528), TRIM28 (0.403). This network defines the SCAN-ZNF heterodimerization module where ZNF215 oligomerizes with BAZ2A/BAZ2B bromodomain proteins and recruits TRIM28 to deposit H3K9me3 heterochromatin marks via SETDB1 methyltransferase.

ClinVar documents 16 pathogenic copy number variants (all large 11p15 chromosomal rearrangements affecting multiple imprinted genes including IGF2, H19, CDKN1C), causing Beckwith-Wiedemann syndrome and Wilms tumor predisposition. ZNF215 resides in the imprinted 11p15.4 domain with tissue-specific parental expression (paternally expressed in testis). Mechanistically, ZNF215 SCAN domains mediate higher-order oligomerization on tandem zinc finger binding sites, while KRAB domains recruit KAP1-SETDB1 complexes to silence endogenous retroviral elements and developmental genes. Conservation spans primates (orangutan, 100% identity), bovine (98%), and vertebrates, indicating ancient transcriptional regulatory function.

## Evidence
```
InterPro: IPR003309/IPR038269 SCAN domain (aa 44-145), IPR001909/IPR036051 KRAB domain (aa 163-237), IPR013087 C2H2 zinc fingers (aa 379-406, 407-434, 462-489) | STRING: BAZ2A(0.942), BAZ2B(0.942), BAZ1A(0.658), ZSCAN20(0.592), BAZ1B(0.590), NAP1L4(0.590), DYNC1I2(0.543), NSD1(0.538), IGF2(0.528), TRIM28(0.403) | HPA: lymphoid tissue 3.9 nTPM; nucleoplasm/vesicles | ClinVar: 16 pathogenic CNVs (11p15 rearrangements) | AlphaFold: pLDDT 49.3 (disordered) | UniProt: Q9UL58 (517 aa) | Conservation: Primate/bovine orthologs | Function: SCAN-KRAB repressor recruiting heterochromatin machinery
```
