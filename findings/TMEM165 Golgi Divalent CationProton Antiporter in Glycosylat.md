# TMEM165: Golgi Divalent Cation/Proton Antiporter in Glycosylation

**Date:** 2026-03-18T19:03:10.956218

**Quality Score:** 2.75/10  (E=4.4, D=1.1) [WEAK]

## Description
TMEM165 encodes a 324-amino acid transmembrane protein (UniProt Q9HC07) localized to the Golgi apparatus. The protein belongs to the GDT1-like family (InterPro IPR001727, PF01169) and functions as a divalent cation/proton antiporter (GO:0046873). AlphaFold predicts a well-folded structure with confident scores (pLDDT 76.2).

FUNCTIONAL HYPOTHESIS: TMEM165 acts as a Golgi membrane antiporter that exchanges divalent cations (Ca2+, Mn2+) for protons, maintaining Golgi ion homeostasis required for proper protein glycosylation. This mechanistic role explains its disease association: loss-of-function mutations cause congenital disorder of glycosylation type IIk (CDG2K), characterized by defective terminal Golgi glycosylation and decreased sialylation. The antiporter activity likely regulates Golgi pH and metal ion concentrations necessary for glycosyltransferase enzyme function.

INTERACTION NETWORK: TMEM165 shows high-confidence interaction with ATP2C1 (STRING score 0.718), another Golgi Ca2+/Mn2+ ATPase, suggesting coordinated ion homeostasis. Additional partners include TM9SF2 (0.625, lysosomal transporter), ALG2 (0.590, ER-Golgi trafficking), SLC10A7 (0.562, Golgi transporter), UNC50 (0.554, Golgi membrane protein), SRD5A3 (0.551, glycosylation enzyme), GOLIM4 (0.534, Golgi integral membrane), and PIGO (0.447, GPI anchor biosynthesis). This network positions TMEM165 within the Golgi glycosylation and trafficking machinery.

EXPRESSION & DISEASE: HPA shows ubiquitous expression across all tissues with low tissue specificity, classified as a transporter and disease-related gene. Subcellular location is Golgi apparatus. ClinVar documents 28 pathogenic/likely pathogenic variants including copy number losses/gains on chromosome 4q12 and truncating mutations (e.g., p.Trp249Ter), confirming dosage sensitivity and loss-of-function pathomechanism.

CONSERVATION: Orthologs identified in mouse (323 aa, P52875) and rat (323 aa, Q4V899) with high sequence conservation. The GDT1/UPF0016 family (IPR001727) is conserved across eukaryotes, indicating ancient ion transport function.

## Evidence
```
InterPro: IPR001727, IPR049555, PF01169, PS01214, PTHR12608 (GDT1-like divalent cation/proton antiporter, residues 17-318); STRING: ATP2C1 (0.718), TM9SF2 (0.625), ALG2 (0.590), SLC10A7 (0.562), UNC50 (0.554), SRD5A3 (0.551), GOLIM4 (0.534), TPTEP2-CSNK1E (0.519), PIGO (0.447), GOSR1 (0.420); HPA: Golgi apparatus, detected in all tissues, low specificity, transporter, disease-related (CDG2K); ClinVar: 28 pathogenic variants (4q12 CNVs, truncating mutations); Conservation: Mouse 323aa (P52875), Rat 323aa (Q4V899), GDT1 family conserved across eukaryotes; AlphaFold: pLDDT 76.2 (confident); UniProt: Q9HC07 (324 aa)
```
