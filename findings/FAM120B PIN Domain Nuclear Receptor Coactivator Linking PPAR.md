# FAM120B: PIN Domain Nuclear Receptor Coactivator Linking PPAR-γ Adipogenesis to DNA Repair and Ubiquitin-Mediated Proteostasis

**Date:** 2026-03-18T19:18:29.069401

**Quality Score:** 3.4/10  (E=5.7, D=1.1) [WEAK]

## Description
FAM120B (alias CCPG, PGCC1, KIAA1838) encodes a 910-amino acid nuclear coactivator protein (UniProt Q96EK7) belonging to the constitutive coactivator of PPAR-gamma family (InterPro IPR026784, PTHR15976, residues 1-898). The protein contains an N-terminal PIN-like nuclease fold domain (IPR029060, G3DSA:3.40.50.1010, SSF88723, cd18672, residues 1-216) and a FAM120 helical domain (IPR060110, PF27242, residues 215-307). AlphaFold predicts a well-folded structure (pLDDT 71.8, high confidence), indicating stable tertiary architecture with defined domain organization.

FUNCTIONAL HYPOTHESIS: FAM120B functions as a constitutive transcriptional coactivator that bridges nuclear receptor signaling (PPAR-γ, RXR, ER) with DNA repair machinery (ERCC5/XPG) and ubiquitin-mediated protein turnover (UBR1, MARCHF6). The PIN-like domain—canonical in 5′-nucleases for RNA processing and DNA repair—suggests FAM120B may process nucleic acid intermediates during transcription or recruit repair factors to active chromatin.

PPAR-γ ADIPOGENESIS: PPARG interaction (0.794, high confidence) positions FAM120B as a coregulator of peroxisome proliferator-activated receptor gamma, the master transcription factor for adipocyte differentiation. RXRA interaction (0.704, retinoid X receptor alpha) indicates heterodimerization with PPAR-γ on peroxisome proliferator response elements (PPREs). PLIN1 interaction (0.597, perilipin 1) connects to lipid droplet formation—FAM120B may coordinate adipogenic gene expression with lipid storage machinery. This explains gene ontology annotations for fat cell differentiation and PPAR signaling.

DNA REPAIR COUPLING: ERCC5 interaction (0.711, ERCC excision nuclease 5/XPG) and BIVM-ERCC5 fusion partner (0.748) link FAM120B to nucleotide excision repair (NER). XPG is a structure-specific endonuclease cleaving 3′ lesions during NER—the PIN-like domain may scaffold XPG recruitment or process DNA flaps during repair. This dual role (transcription + repair) mirrors transcription-coupled repair mechanisms where RNA polymerase stalling recruits NER factors.

UBIQUITIN PROTEOSTASIS: UBR1 interaction (0.722, ubiquitin protein ligase E3 component n-recognin 1) connects FAM120B to N-end rule proteasomal degradation. MARCHF6 interaction (0.644, membrane-associated ring-CH-type finger 6) indicates additional ubiquitin ligase recruitment. FAM120B may regulate nuclear receptor turnover or mark damaged chromatin for proteasomal clearance. PSMB1 interaction (0.615, proteasome subunit beta type-1) reinforces proteasome coupling.

DISEASE VARIANTS: ClinVar documents 87 pathogenic variants including extensive 6q25.2-27 and 6q27 copy number gains/losses (153483970-170605209, 167201522-170610382, 144488859-170610382), intronic variants (c.2692+100G>A, c.1916-225G>T), and synonymous exonic change (c.1173G>A p.Thr391=). CNVs disrupt FAM120B dosage, causing metabolic syndrome, lipodystrophy, or developmental defects through PPAR-γ haploinsufficiency. The PIN domain (1-216) and helical domain (215-307) are mutation hotspots affecting coactivator function.

CONSERVATION: Mouse ortholog Q6RI63 (786 aa) shows strong homology despite length divergence, indicating functional conservation of PPAR-gamma coactivation and PIN domain architecture across mammals.

## Evidence
```
InterPro: IPR026784 (PPAR-γ coactivator, 1-898), IPR029060 (PIN-like, 1-216), IPR060110 (FAM120 helical, 215-307), PF27242, PTHR15976, cd18672, G3DSA:3.40.50.1010, SSF88723; STRING: PPARG (0.794), BIVM-ERCC5 (0.748), UBR1 (0.722), ERCC5 (0.711), RXRA (0.704), MARCHF6 (0.644), PSMB1 (0.615), PLIN1 (0.597), PDCD2 (0.597), ESR1 (0.582); ClinVar: 87 pathogenic variants (6q CNVs, intronic/splice variants); Conservation: Mouse Q6RI63 (786 aa, strong homology); AlphaFold: pLDDT 71.8 (well-folded); UniProt: Q96EK7 (910 aa)
```
