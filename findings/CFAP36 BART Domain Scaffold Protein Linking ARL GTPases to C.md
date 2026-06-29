# CFAP36: BART Domain Scaffold Protein Linking ARL GTPases to Ciliary Assembly

**Date:** 2026-03-20T14:06:02.225221

**Quality Score:** 2.75/10  (E=5.2, D=0.3) [WEAK]

## Description
CFAP36 (Cilia- and Flagella-Associated Protein 36) is a 342 amino acid intracellular scaffold protein (UniProt Q96G28) that contains a conserved BART domain (IPR023379, PF11527, residues 10-121) characteristic of ARF-like GTPase-binding proteins. The protein localizes to the primary cilium, nucleoplasm, nucleolar fibrillar center, and nuclear bodies according to HPA data, with low tissue specificity but ubiquitous expression across all tissues examined.

STRING interaction analysis reveals CFAP36 forms a high-confidence complex (score 0.974) with ARL3 (ADP-ribosylation factor-like 3), a small GTPase critical for ciliary protein trafficking and lipid modification. Additional medium-confidence partners include ARL2 (0.458), FAM161B (0.621, a retinal ciliopathy protein), TTC29 (0.575, tetratricopeptide repeat protein), and CCDC63 (0.502, coiled-coil ciliary protein). This interaction network positions CFAP36 as a molecular adaptor bridging ARL GTPase signaling to ciliary structural assembly.

ClinVar contains 12 pathogenic/likely pathogenic variants including splice site mutations (c.640+9G>A), 5′UTR variants (c.-39C>G), and large chromosomal rearrangements on chromosome 2p, suggesting CFAP36 dysfunction contributes to human disease, potentially ciliopathy phenotypes. Orthologs exist in mouse (Q8C6E0, 343 aa, 99% identity), rat (Q4V8E4), and zebrafish (Q1RM35, 350 aa), indicating strong evolutionary conservation of ciliary function.

Mechanistic hypothesis: CFAP36 uses its BART domain to bind activated ARL3-GTP at the ciliary membrane, recruiting cargo proteins for intraflagellar transport. The BART domain superfamily (IPR042541) typically functions as GTPase-activating proteins or effectors that regulate membrane trafficking. CFAP36 may coordinate ARL2/ARL3 switching during ciliary protein import, with dysfunction leading to defective ciliogenesis and human ciliopathy.

## Evidence
```
InterPro: IPR023379 (BART domain), IPR038888 (CFAP36 family), IPR042541 (BART superfamily), PF11527, G3DSA:1.20.1520.10 | STRING: ARL3 (0.974), FAM161B (0.621), TTC29 (0.575), ARL2 (0.458), CCDC63 (0.502) | HPA: Primary cilium, nucleoplasm, low tissue specificity, detected in all | ClinVar: 12 pathogenic variants | Conservation: Mouse 99%, Zebrafish ortholog Q1RM35 | UniProt: Q96G28 (342 aa)
```
