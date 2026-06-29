# ZNF451: E3 SUMO Ligase with C2H2 Zinc Finger Array Regulating Transcription and DNA Topology

**Date:** 2026-03-20T12:28:01.331493

**Quality Score:** 2.65/10  (E=5.0, D=0.3) [WEAK]

## Description
ZNF451 encodes a 1061 amino acid E3 SUMO-protein ligase (UniProt Q9Y4E5) with extensive C2H2 zinc finger architecture. InterPro analysis reveals 6+ C2H2-type zinc fingers (IPR013087, PF23101-PF23102) spanning residues 168-848, plus a C-terminal PIN-like nuclease domain (PF18479, residues 884-1001). AlphaFold predicts a partially structured conformation (pLDDT 68.9), consistent with modular DNA-binding zinc fingers linked by flexible regions.

STRING interactions identify ZNF451 within the SUMOylation machinery: high-confidence partners include SUMO2 (0.896), SUMO1 (0.729), and E2 conjugase UBE2I (0.504), plus chromatin regulators BEND6 (0.777), TDP2 (0.769), and topoisomerases TOP2A (0.738)/TOP2B (0.497). This interaction profile positions ZNF451 at the intersection of protein sumoylation and DNA topology management.

HPA shows ubiquitous expression with bone marrow enrichment (66.3 nTPM), nucleoplasmic localization, and classification as a transcription factor. ClinVar documents 10 pathogenic variants including copy number gains/losses on 6p12.1, suggesting dosage sensitivity.

FUNCTIONAL HYPOTHESIS: ZNF451 functions as a SUMO-dependent transcriptional corepressor that recruits SUMO2/1 conjugation machinery to chromatin via its zinc finger array, simultaneously regulating DNA supercoiling through TOP2A/B interactions. The PIN-like domain may provide nucleic acid binding or cleavage activity for resolving transcription-associated DNA structures.

MECHANISTIC PROPOSAL: ZNF451 binds specific DNA sequences via tandem C2H2 fingers, recruits UBE2I-SUMO2 complexes for substrate sumoylation, and coordinates with topoisomerases to relieve torsional stress during transcription repression. Disease-associated CNVs disrupt this multi-protein complex assembly.

## Evidence
```
InterPro: IPR013087 (C2H2 zinc finger), PF18479 (PIN-like domain), IPR041192, IPR058156-IPR058950 (ZNF451-specific domains) | STRING: SUMO2(0.896), BEND6(0.777), TDP2(0.769), TOP2A(0.738), SUMO1(0.729), GPATCH2L(0.725), PIAS1(0.698), RANBP2(0.664), UBE2I(0.504), TOP2B(0.497) | HPA: bone marrow 66.3 nTPM, nucleoplasm, tissue enhanced | ClinVar: 10 pathogenic variants (CNVs on 6p12.1) | AlphaFold: pLDDT 68.9, 1-1061 aa | UniProt: Q9Y4E5
```
