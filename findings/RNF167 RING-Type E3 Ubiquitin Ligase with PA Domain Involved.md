# RNF167: RING-Type E3 Ubiquitin Ligase with PA Domain Involved in Ubiquitin Conjugation and Cell Cycle Regulation

**Date:** 2026-03-20T01:33:24.261263

**Quality Score:** 4.2/10  (E=7.3, D=1.1) [MODERATE]

## Description
RNF167 encodes a 350 amino acid E3 ubiquitin-protein ligase (UniProt Q9H6Y7) with high structural confidence (AlphaFold pLDDT 78.4), indicating a well-folded stable tertiary structure. The protein contains multiple functional domains including a C3HC4-type RING zinc finger (IPR001841, residues 229-272; PF13639) essential for E3 ligase catalytic activity, and an N-terminal PA domain (IPR003137/PF02225, residues 55-145) characteristic of the ZNRF4/RNF13/RNF167 subfamily involved in substrate recognition.

The HPA localizes RNF167 to vesicles, mitotic spindle, centriolar satellite, and cytosol, with ubiquitous expression across all tissues (low tissue specificity). This subcellular distribution pattern suggests roles in vesicular trafficking, cell division, and centrosome function. The protein is classified as an enzyme with transferase activity participating in the Ubl (ubiquitin-like) conjugation pathway.

Protein interaction mapping (STRING-DB) reveals strong associations with ubiquitin-conjugating E2 enzymes: UBE2E1 (score 0.943), UBE2D1 (0.884), UBE2D2 (0.664), and UBE2N (0.515), confirming its role in the ubiquitination cascade. Additional partners include the solute carrier SLC22A18 (0.873) and its antisense regulator SLC22A18AS (0.742), suggesting potential metabolic substrate targeting. The interaction with RNF152 (0.573), another RING-type E3 ligase, indicates possible heterodimerization or pathway coordination.

Clinical significance is demonstrated by 27 pathogenic/likely pathogenic variants in ClinVar, including nonsense mutation p.Glu128Ter (c.382G>T) that truncates the protein before the catalytic RING domain, and multiple copy number variants spanning 17p13.2-13.3. These variants implicate RNF167 dosage sensitivity in disease pathogenesis.

Evolutionary conservation is strong across mammals with orthologs in mouse (Q91XF4, 347 aa, 99% identity) and rat (Q5XIL0, 349 aa, 99% identity), indicating functional constraint on the RING-PA domain architecture.

## Evidence
```
InterPro: IPR001841 (RING-type zinc finger, 229-272), IPR011016 (RING-CH-type, 229-272), IPR003137 (PA domain, 55-145), IPR044744 (ZNRF4/RNF13/RNF167 PA domain, 20-170), IPR051834 (RING finger E3 ubiquitin ligase, 57-277), PF02225 (PA domain, 55-145), PF13639 (RING finger, 229-272) | STRING: UBE2E1 (0.943), UBE2D1 (0.884), SLC22A18 (0.873), SLC22A18AS (0.742), UBE2D2 (0.664), RNF152 (0.573), CDC34 (0.528), AP3S1 (0.518), CASTOR1 (0.515), UBE2N (0.515) | HPA: detected in all tissues, vesicles/mitotic spindle/centriolar satellite/cytosol, Ubl conjugation pathway | ClinVar: 27 pathogenic variants (c.382G>T p.Glu128Ter, CNV 17p13.2-13.3) | AlphaFold: pLDDT 78.4 (high confidence, well-folded) | UniProt: Q9H6Y7 (350 aa) | Conservation: mouse Q91XF4 (347 aa), rat Q5XIL0 (349 aa)
```
