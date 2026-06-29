# LRCH1: Cytoskeletal Scaffold Negatively Regulating T Cell Migration via DOCK8-Cdc42 Antagonism

**Date:** 2026-04-17T03:10:29.928204

**Quality Score:** 2.5/10  (E=5.0, D=0.0) [WEAK]

**Confidence:** MEDIUM

## Description
LRCH1 (UniProt Q9Y2L9) encodes a 728 amino acid intracellular scaffold protein characterized by an N-terminal leucine-rich repeat (LRR) domain (residues 62-292, IPR001611, PF13855) and a C-terminal calponin homology (CH) domain (residues 576-692, IPR001715, PF00307). The LRR region likely mediates protein-protein interactions, while the CH domain suggests actin-binding or cytoskeletal regulatory capacity. HPA data indicates ubiquitous expression with localization to nucleoli, actin filaments, and cytosol. STRING interactions reveal a high-confidence partnership with DOCK8 (score 0.935), a guanine nucleotide exchange factor (GEF) for Cdc42, as well as connections to other LRCH family members (LRCH3, LRCH4) and DOCK proteins (DOCK6, DOCK7). Literature (31 papers) defines LRCH1 as a critical negative regulator of T cell migration: it physically interacts with DOCK8 to inhibit its GEF activity toward Cdc42, thereby suppressing actin polymerization and directional migration of CD4+ and CD8+ T cells. This mechanism ameliorates experimental autoimmune encephalomyelitis (EMS) and limits tumor infiltration; conversely, LRCH1 deficiency enhances LAT signalosome formation and boosts anti-tumor immunity. ClinVar lists 27 pathogenic/likely pathogenic variants, predominantly large copy number losses/gains at 13q14, suggesting dosage sensitivity may impact immune regulation or development, though no specific monogenic syndrome is named. AlphaFold structure (pLDDT 62.8) predicts medium confidence, consistent with a modular architecture containing structured LRR/CH domains connected by flexible linkers. FUNCTIONAL HYPOTHESIS: LRCH1 acts as a molecular brake on T cell motility by sequestering or allosterically inhibiting DOCK8, preventing excessive Cdc42 activation and stabilizing the immunological synapse or limiting tissue extravasation. MECHANISTIC PROPOSAL: Upon TCR engagement or chemokine signaling, LRCH1 recruits to the leading edge via its CH domain binding F-actin, where its LRR domain binds the DHR-2 domain of DOCK8, sterically blocking Cdc42 loading; loss of LRCH1 unleashes DOCK8-driven Cdc42-GTP bursts, hyper-accelerating migration but potentially destabilizing sustained synaptic contacts required for effective killing.

## Evidence
```
Evidence: UniProt Q9Y2L9 (728 aa); InterPro: IPR001611 (LRR), IPR001715 (CH domain), PF00307; STRING: DOCK8 (0.935), LRCH3 (0.800), DOCK6 (0.769); HPA: Detected in all tissues, localized to actin filaments/cytosol/nucleoli; ClinVar: 27 pathogenic variants (CNVs at 13q14); AlphaFold: pLDDT 62.8; Literature: 31 papers (DOCK8 inhibition, EAE suppression, T cell migration control).
```
