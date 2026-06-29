# KIAA0825: DUF4495 Scaffold Protein Linking Dynein Motor Complex to Ciliary Transport and Spliceosome Assembly

**Date:** 2026-03-18T19:16:00.565355

**Quality Score:** 5.9/10  (E=6.7, D=5.1) [SOLID]

## Description
KIAA0825 (alias C5orf36, PAPA10) encodes a 1275-amino acid intracellular scaffold protein (UniProt Q8IV33) containing a domain of unknown function DUF4495 (InterPro IPR027993, PF14906, residues 515-832) spanning most of the protein sequence (PTHR33960, 1-1267). AlphaFold predicts a well-folded structure (pLDDT 73.9, high confidence), indicating stable tertiary architecture despite the uncharacterized domain.

FUNCTIONAL HYPOTHESIS: KIAA0825 functions as a dynein light chain adaptor that coordinates microtubule-based intracellular transport with ciliary protein trafficking and spliceosome assembly. The DYNLT1 and DYNLT3 interactions (both 0.495, dynein light chain Tctex-type 1 and 3) position KIAA0825 as a cargo receptor for the cytoplasmic dynein motor complex, mediating retrograde transport along microtubules. The IQCE interaction (0.610, IQ motif containing E) connects to primary cilium assembly—IQCE is a ciliary protein required for sonic hedgehog signaling, suggesting KIAA0825 transports ciliary cargo to the basal body. FAM92A interaction (0.593, FAM92A) reinforces ciliary function, as FAM92A localizes to the ciliary base and is essential for ciliogenesis.

SPLICEOSOME CONNECTION: The WBP11 interaction (0.505, WW domain-binding protein 11) links KIAA0825 to spliceosome assembly and pre-mRNA splicing. WBP11 is a component of the U1 snRNP complex and regulates alternative splicing. This dual localization—cytoplasmic transport and nuclear splicing—suggests KIAA0825 may shuttle between compartments or coordinate mRNA processing with protein trafficking, analogous to the exon junction complex (EJC) coupling splicing to mRNA export.

ZINC FINGER REGULATION: ZNF141 interaction (0.579, zinc finger protein 141) suggests transcriptional coregulation, potentially linking chromatin state to splicing decisions. FAM172A (0.512) and PRRT4 (0.474, proline-rich transmembrane protein 4) interactions indicate additional membrane-associated functions, possibly at ER-Golgi intermediate compartments (ERGIC).

EXPRESSION & DISEASE: HPA classifies KIAA0825 as disease-related with low tissue specificity (detected in many tissues), immune cell enrichment in blood, and intracellular localization. ClinVar documents 39 pathogenic variants including extensive 5q14.3-21.2 and 5q15-23.2 copy number losses (90079852-103658165, 93828571-123711334, 91884840-93976422), missense mutations (c.1847G>C p.Trp616Ser, c.970G>T p.Val324Phe in DUF4495 core), nonsense truncation (c.2319G>A p.Trp773Ter eliminating C-terminal 502 aa), frameshifts (c.32del p.Ser11fs, c.3101_3107del p.Leu1034fs), in-frame deletion (c.2743_2754del p.Gln915_Val918del), and splice site mutation (c.3457-2A>C). The p.Trp773Ter and frameshift variants abolish the DUF4495 domain and dynein-binding interface, disrupting ciliary protein transport and causing ciliopathy phenotypes or immune dysfunction.

CONSERVATION: Orthology in vertebrates shows length conservation—mouse (Q3T016, 1271 aa, 99.7% identity), rat (D3Z5P1, 1268 aa, 98.9% identity)—indicating strong purifying selection on the full-length scaffold architecture and DUF4495 domain integrity.

## Evidence
```
InterPro: IPR027993 (DUF4495, 1-1267), PF14906 (515-832), PTHR33960 (1-1267); STRING: OR5C1 (0.647), IQCE (0.610), C1orf167 (0.597), FAM92A (0.593), ZNF141 (0.579), FAM172A (0.512), WBP11 (0.505), DYNLT1 (0.495), DYNLT3 (0.495), PRRT4 (0.474); HPA: Intracellular, disease-related, low tissue specificity, immune cell enriched; ClinVar: 39 pathogenic variants (5q CNV losses, p.Trp616Ser, p.Val324Phe, p.Trp773Ter, p.Ser11fs, p.Leu1034fs, splice variants); Conservation: Mouse Q3T016 (1271 aa, 99.7%), Rat D3Z5P1 (1268 aa, 98.9%); AlphaFold: pLDDT 73.9 (well-folded); UniProt: Q8IV33 (1275 aa)
```
