# PAGE1: Cancer/Testis Antigen with Undefined Molecular Function Despite GAGE Domain Architecture

**Date:** 2026-06-27T23:49:26.159940

**Quality Score:** 7/10 (GOOD)

**Confidence:** MEDIUM

## Description
PAGE1 (UniProt O75459) encodes a 146-amino acid P antigen family member classified as a cancer/testis (CT) antigen—expressed in various tumors but restricted to testis in normal tissues. InterPro analysis reveals tandem GAGE domains (IPR031320, aa 1-98 and 99-146; PF05831, aa 1-98) within the G/X antigen family (IPR008625, aa 1-96), characteristic of the PAGE/GAGE protein family. AlphaFold predicts a partially structured protein (pLDDT: 60.9), consistent with small CT antigens that may function through protein-protein interactions rather than enzymatic activity.\n\nSTRING interactions confirm PAGE1's membership in the CT antigen network: strongest link to PAGE2 (0.946), with moderate connections to KLK3 (0.556), EFNA5 (0.541), GAGE12F (0.512), and MAGE family members (MAGEB2, MAGEA12, MAGEA1, MAGEC2: 0.413-0.470). HPA data shows testis-restricted expression (17.0 nTPM) with cancer-enhanced patterns across multiple tumor types, and subcellular localization to nucleoplasm, nucleoli fibrillar center, and mitochondria.\n\nCritically, despite 154 papers in the literature search, most are false positives (unrelated studies containing 'PAGE1' in titles like diabetes trials). The RefSeq summary explicitly states 'Nothing is presently known about the function of this protein.' Unlike related GAGE proteins that encode antigenic peptides recognized by cytotoxic T cells, PAGE1 does not produce known antigenic epitopes. ClinVar contains 156 pathogenic variants including deletions and copy number variations at Xp11.23. This positions PAGE1 as a genuine dark gene—a CT antigen with confirmed tumor expression but completely undefined molecular mechanism, representing an unexplored target for cancer immunotherapy.

## Evidence
```
InterPro: IPR008625, IPR031320, PF05831 | STRING: PAGE2 (0.946), KLK3 (0.556), GAGE12F (0.512), MAGE family | HPA: Testis 17.0 nTPM, Cancer enhanced | ClinVar: 156 pathogenic variants | AlphaFold pLDDT: 60.9 | UniProt: O75459 | Literature: 154 papers but mostly false positives—RefSeq states 'function unknown'; does not encode antigenic peptide unlike GAGE relatives
```
