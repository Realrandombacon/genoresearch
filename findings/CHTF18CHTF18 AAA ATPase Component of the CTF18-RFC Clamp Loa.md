# CHTF18/CHTF18: AAA+ ATPase Component of the CTF18-RFC Clamp Loader Complex with Sister Chromatid Cohesion Function

**Date:** 2026-03-18T02:08:13.141742

**Quality Score:** 9/10 (EXCELLENT)

## Description
CHTF18 (chromosome transmission fidelity factor 18, 975 aa, UniProt Q8WVB6) encodes a specialized replication factor C-like clamp loader component that functions in sister chromatid cohesion during DNA replication. The protein contains a canonical AAA+ ATPase core domain (IPR003593, PF00004, aa 371-450) with Walker A/B motifs for ATP binding and hydrolysis, plus a C-terminal RFC lid domain (IPR047854, aa 515-575) that mediates complex assembly. STRING analysis reveals 10 high-confidence interaction partners forming the CTF18-RFC holoenzyme: DSCC1 (0.999), CHTF8 (0.999), RFC2-5 (0.662-0.999), plus DNA replication machinery including POLE (0.990), POLA1 (0.967), and cohesin acetyltransferase ESCO1 (0.964). HPA shows nucleoplasmic/cytosolic localization with expression in many tissues and immune cell enhancement. AlphaFold predicts a 975 aa structure with moderate confidence (pLDDT 64.1), suggesting flexible linkers between structured AAA+ and lid domains. ClinVar documents 53 pathogenic variants including missense (p.His645Pro, p.Leu676Arg) and structural variants, indicating disease relevance though specific phenotypes remain undefined. Conservation analysis shows the AAA+ module is deeply conserved across eukaryotes. FUNCTIONAL HYPOTHESIS: CHTF18 acts as a replication-coupled cohesion factor that loads the 9-1-1 checkpoint clamp (RAD9-RAD1-HUS1) at replication forks, coordinating DNA synthesis with sister chromatid tethering. The AAA+ ATPase cycle drives conformational changes that open/close the clamp ring around DNA, while the lid domain recruits DSCC1-CHTF8 effectors. MECHANISTIC PROPOSAL: During S-phase, CHTF18-RFC recognizes primer-template junctions, hydrolyzes ATP to load the 9-1-1 clamp, and simultaneously recruits ESCO1 to acetylate cohesin, ensuring replicated sisters remain paired until anaphase.

## Evidence
```
InterPro: IPR003593 (AAA+ ATPase), IPR047854 (RFC lid), IPR053016 (CTF18-RFC), PF00004 (AAA); STRING: DSCC1/CHTF8/RFC2-5/POLE/POLA1/ESCO1/WDHD1 (scores 0.662-0.999); HPA: nucleoplasm/cytosol, many tissues, immune cell enhanced; ClinVar: 53 pathogenic variants; AlphaFold: Q8WVB6 pLDDT 64.1, 975 aa
```
