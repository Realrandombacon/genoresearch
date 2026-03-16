# C21orf24: Phantom ORF - LINC00114 LncRNA Misannotation

**Date:** 2026-03-16T17:25:54.682885

**Quality Score:** 5/10 (GOOD)

## Description
C21orf24 represents a classic annotation artifact in the human genome - a 'phantom ORF' that likely does not encode a functional protein. Evidence chain: (1) UniProt search returned only one human entry (Q6XXX2, 140 aa) annotated as 'Putative uncharacterized protein encoded by LINC00114' - a long non-coding RNA locus, not a protein-coding gene. (2) STRING-DB returned 'No protein found' for C21orf24 in Homo sapiens, indicating no detectable protein-protein interactions. (3) Human Protein Atlas could not resolve C21ORF24 to any Ensembl ID, suggesting the gene lacks protein-coding evidence in major annotation pipelines. Chimpanzee entries exist (Q1MT15, 115 aa) but human orthology is uncertain. Mechanistic hypothesis: C21orf24 is a relic ORF within the LINC00114 lncRNA transcript that acquired an ORF annotation during automated genome annotation but lacks evolutionary conservation, ribosome profiling evidence, or detectable protein product. The 'gene' likely functions as non-coding RNA with regulatory roles (chromatin modulation, miRNA sponge) rather than encoding a 140 aa peptide. This represents ~500-1000 similar annotation artifacts inflating the 'dark proteome' count.

## Evidence
```
Evidence: UniProt Q6XXX2 (LINC00114-linked, 140 aa putative); STRING: no interactions detected; HPA: no Ensembl resolution; Cross-species: chimp C21orf24 entries (Q1MT15 115aa, Q1MT14 114aa) suggest annotation divergence; Classification: probable lncRNA misannotation
```
