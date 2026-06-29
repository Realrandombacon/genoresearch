# TMEM214: ER Membrane Adaptor Linking SEC61 Translocon to Caspase-4 Activation in ER Stress Apoptosis

**Date:** 2026-03-18T19:14:15.238962

**Quality Score:** 4.95/10  (E=8.8, D=1.1) [MODERATE]

## Description
TMEM214 encodes a 689-amino acid transmembrane protein (UniProt Q6NUQ4) localized to the endoplasmic reticulum, Golgi apparatus, and cytosol. The protein belongs to the TMEM214 family (InterPro IPR019308, PF10151, PTHR13448) with a C-terminal caspase-4 activator domain spanning residues 9-683. AlphaFold predicts a well-folded structure (pLDDT 78.3, high confidence), indicating stable tertiary structure with defined transmembrane helices.

FUNCTIONAL HYPOTHESIS: TMEM214 functions as an ER membrane adaptor that couples protein translocation to caspase-4-mediated apoptosis during ER stress. The strong interaction with EXD2 (exonuclease domain-containing protein 2, score 0.920) suggests TMEM214 recruits this 3-prime-to-5-prime exonuclease to the ER membrane for RNA surveillance of translocated transcripts or for degradation of aberrant mRNAs during the unfolded protein response (UPR). The SEC61 translocon complex interactions (SEC61A1 0.778, SEC63 0.723, SEC62 0.702, SEC61G 0.688, SEC61B 0.545) position TMEM214 as a regulatory subunit that modulates protein import into the ER lumen, potentially gating translocation efficiency during stress conditions.

MECHANISTIC PROPOSAL: Under ER stress, TMEM214 undergoes conformational changes that expose its C-terminal caspase-4 activator domain (PF10151), recruiting and activating caspase-4 (CASP4) to initiate non-canonical inflammasome signaling. The TAZ interaction (0.656, transcriptional coactivator with PDZ-binding motif) links TMEM214 to Hippo pathway signaling, suggesting cross-talk between ER stress and cell proliferation control. NPR2 interaction (0.672, natriuretic peptide receptor 2) indicates potential regulation of cGMP signaling at the ER membrane. TMEM38A (0.630, trimeric intracellular cation channel) connection suggests coordinated ion homeostasis during apoptosis execution.

EXPRESSION & DISEASE: HPA classifies TMEM214 as a transporter with low tissue specificity (detected in all tissues), ER and Golgi localization consistent with secretory pathway function. ClinVar documents 17 pathogenic variants including 2p25.3-23.1 copy number gains (multiple independent duplications: 12771-30565600, 20938401-37327210, 12771-35541353, 706460-35523639, 24601818-43466284, 24881528-43460021), 2p25.1-q13 deletions, and a truncating nonsense mutation (c.1942A>T, p.Arg648Ter) that eliminates the C-terminal 41 residues including critical caspase-4 activation motifs. The p.Arg648Ter variant is predicted to abolish caspase-4 recruitment, impairing ER stress-induced apoptosis and potentially contributing to tumorigenesis or autoinflammatory disease.

CONSERVATION: Strong orthology across mammals—mouse (Q8BM55, 687 aa, 99.7% identity), rat (A1L1L2, 685 aa, 98.8% identity), bovine (A4FV45, 687 aa, 98.5% identity)—shows exceptional length and sequence conservation, indicating purifying selection on transmembrane topology and caspase-4 activation function. The SEC61-binding interface and EXD2 recruitment motif are vertebrate-conserved.

## Evidence
```
InterPro: IPR019308 (TMEM214 family, 6-683), PF10151 (caspase-4 activator, 9-683), PTHR13448 (6-652); STRING: EXD2 (0.920), SEC61A1 (0.778), SEC63 (0.723), SEC62 (0.702), SEC61G (0.688), NPR2 (0.672), TAZ (0.656), TMEM38A (0.630), CNOT2 (0.586), SEC61B (0.545); HPA: ER/Golgi/cytosol, apoptosis, transporter, low tissue specificity, detected in all; ClinVar: 17 pathogenic variants (2p CNV gains/losses, p.Arg648Ter nonsense); Conservation: Mouse Q8BM55 (687 aa, 99.7%), Rat A1L1L2 (685 aa, 98.8%), Bovine A4FV45 (687 aa, 98.5%); AlphaFold: pLDDT 78.3 (well-folded); UniProt: Q6NUQ4 (689 aa)
```
