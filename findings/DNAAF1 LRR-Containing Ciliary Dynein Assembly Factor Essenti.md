# DNAAF1: LRR-Containing Ciliary Dynein Assembly Factor Essential for Axonemal Stability

**Date:** 2026-03-23T00:13:46.835013

**Quality Score:** 3.7/10  (E=6.4, D=1.0) [MODERATE]

## Description
DNAAF1 (Dynein Axonemal Assembly Factor 1, also known as LRRC50/ODA7) encodes a 725-amino acid cilium-specific protein (UniProt Q8NEP3) required for ciliary architecture stability and microtubule-based cilia regulation. The protein contains multiple leucine-rich repeat (LRR) domains (IPR001611, PF14580) spanning residues 130-299, forming a curved solenoid structure typical of protein-protein interaction scaffolds. InterPro identifies it as a ciliary and flagellar integrity-associated protein (IPR050576, PTHR45973, residues 78-406) with an outer arm dynein light chain-like fold (SSF52075).

STRING interaction analysis reveals DNAAF1 functions within a high-confidence dynein assembly complex, with strongest partners being DNAI2 (0.983), DNAI1 (0.946), DNAH11 (0.906), DNAAF3 (0.886), and DNAAF2 (0.799) - all established axonemal dynein components. Additional interactions with RSPH4A (0.771), RSPH9 (0.757), and NME8 (0.664) suggest roles in radial spoke head complex assembly. This interaction network positions DNAAF1 as a scaffold protein that stabilizes outer arm dynein pre-assembly in the cytoplasm before ciliary transport.

HPA expression shows tissue-enhanced RNA pattern with highest levels in testis (42.3 nTPM), choroid plexus (23.0 nTPM), and fallopian tube (21.4 nTPM) - tissues rich in motile cilia. This expression profile aligns with its role in ciliated epithelia. ClinVar documents 125 pathogenic/likely pathogenic variants including frameshifts (c.515del, c.285dup), nonsense mutations (p.Arg36Ter, p.Glu428Ter, p.Lys315Ter), and splice variants, all causing primary ciliary dyskinesia-13 (CILD13) with Kartagener syndrome features.

Conservation data from UniProt shows orthologs in mouse (Q9D2H9, 634 aa, ~87% identity), rat (Q6AYH9, 633 aa), and zebrafish (Q7ZV84, 555 aa, ~75% identity), indicating strong evolutionary constraint on ciliary function. AlphaFold structure prediction was unavailable (API error), but the LRR domain architecture suggests a concave binding surface for dynein intermediate chain interactions.

FUNCTIONAL HYPOTHESIS: DNAAF1 acts as a cytoplasmic chaperone/scaffold that binds nascent outer arm dynein heavy chains via its LRR domains, preventing aggregation and facilitating proper folding before intraflagellar transport. The LRR curvature creates a molecular cradle that positions dynein subunits for ATPase domain assembly. Loss of DNAAF1 destabilizes the dynein regulatory complex, leading to immotile cilia and defective mucociliary clearance.

## Evidence
```
Evidence: InterPro domains IPR001611/PF14580/IPR050576/PTHR45973/SSF52075 (LRR repeats, ciliary protein family); STRING partners DNAI2(0.983)/DNAI1(0.946)/DNAH11(0.906)/DNAAF3(0.886)/DNAAF2(0.799)/RSPH4A(0.771); HPA expression testis(42.3 nTPM)/choroid plexus(23.0)/fallopian tube(21.4); ClinVar 125 pathogenic variants causing PCD-13; UniProt Q8NEP3 (725 aa); Conservation: mouse ~87%, zebrafish ~75% identity
```
