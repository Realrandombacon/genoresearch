# CCDC122: Coiled-Coil Scaffold Protein in Innate Immunity with Leprosy Association and High-Confidence LACC1 Interaction

**Date:** 2026-03-20T08:43:08.910158

**Quality Score:** 3.1/10  (E=5.4, D=0.8) [WEAK]

## Description
CCDC122 encodes a 273 amino acid coiled-coil domain-containing protein (UniProt Q5T0U0) with a PFAM coiled-coil domain (PF28420, residues 53-262) and a CATH-Gene3D homologous superfamily (G3DSA:1.10.287.1490, residues 14-176). AlphaFold predicts a highly confident structure (pLDDT 88.9), indicating stable coiled-coil folding typical of protein-protein interaction scaffolds.

Expression profiling (HPA) shows low tissue specificity with detection in many tissues, and dual subcellular localization to nucleoplasm and vesicles—consistent with a shuttling scaffold protein that may traffic between nuclear and cytoplasmic compartments.

STRING interaction network reveals striking immune-related partnerships: LACC1 (0.949, very high confidence), TNFSF15 (0.728), NOD2 (0.699), LRRK2 (0.505), RIPK2 (0.434), and SLC11A1 (0.429). LACC1 (Lacerase) is a fatty acid hydroxylase strongly associated with leprosy susceptibility and macrophage function. NOD2 is a cytosolic pattern recognition receptor for bacterial peptidoglycan. RIPK2 is a kinase downstream of NOD2 signaling. SLC11A1 (NRAMP1) is a macrophage iron transporter linked to intracellular pathogen resistance.

ClinVar documents 52 pathogenic/likely pathogenic variants, predominantly copy number alterations on chromosome 13q. RefSeq explicitly notes natural mutations associated with leprosy, aligning with the LACC1 interaction and immune pathway enrichment.

Conservation analysis shows orthologs in mouse (Q8BVN0, 290 aa, ~95% identity) and other mammals, indicating evolutionary constraint on the coiled-coil architecture.

HYPOTHESIS: CCDC122 functions as a coiled-coil scaffold protein that nucleates innate immune signaling complexes, particularly in macrophages responding to mycobacterial infection. The high-confidence interaction with LACC1 suggests CCDC122 may recruit LACC1 to vesicular membranes (endosomes/phagosomes) where it hydroxylates fatty acids for antimicrobial activity. Coiled-coil domains mediate oligomerization, potentially forming higher-order scaffolds that concentrate NOD2-RIPK2 signaling components. Leprosy-associated variants disrupt this scaffolding function, impairing macrophage antimicrobial responses to Mycobacterium leprae.

## Evidence
```
InterPro: G3DSA:1.10.287.1490 (aa 14-176), PF28420 (aa 53-262) | STRING: LACC1(0.949), TNFSF15(0.728), NOD2(0.699), CFAP69(0.630), LRRK2(0.505), SPRYD7(0.489), RIPK2(0.434), SLC11A1(0.429), VIL1(0.425), PACRG(0.408) | HPA: Low tissue specificity, nucleoplasm/vesicles, detected in many | ClinVar: 52 pathogenic variants (leprosy-associated) | AlphaFold: pLDDT 88.9 (1-273 aa) | UniProt: Q5T0U0 (273 aa) | Conservation: Mouse Q8BVN0 (290 aa, ~95%)
```
