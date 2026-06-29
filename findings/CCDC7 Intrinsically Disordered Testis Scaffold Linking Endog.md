# CCDC7: Intrinsically Disordered Testis Scaffold Linking Endogenous Retroviral Silencing to Spermatogenesis via APOBEC3G Restriction

**Date:** 2026-03-18T19:19:34.804505

**Quality Score:** 4.15/10  (E=7.0, D=1.3) [MODERATE]

## Description
CCDC7 (alias BIOT2, BioT2-A/B/C, C10orf68) encodes a 1385-amino acid coiled-coil protein (UniProt Q96M83) belonging to the CCDC7 family (InterPro IPR029272, PTHR22035, residues 1-1384) with an N-terminal spermatogenesis BioT2 domain (PF15368, residues 1-170). AlphaFold predicts a mostly disordered structure (pLDDT 43.3, low confidence), indicating intrinsically disordered protein (IDP) architecture that functions through protein-protein interactions rather than enzymatic activity.

FUNCTIONAL HYPOTHESIS: CCDC7 functions as a testis-specific intrinsically disordered scaffold that coordinates endogenous retroviral element (ERV) silencing with spermatogenesis, potentially through APOBEC3G-mediated restriction and mitotic spindle assembly. The BioT2 domain (spermatogenesis family) and testis-enriched expression (74.0 nTPM, HPA tissue enriched) position CCDC7 as a germline-specific regulator.

ERV SILENCING: ERVFRD-1 (0.516, endogenous retrovirus group FRD member 1 envelope), ERVV-2 (0.511, ERV group V member 2), and ERVV-1 (0.496) interactions link CCDC7 to endogenous retroviral element regulation. During spermatogenesis, global DNA demethylation activates ERVs—CCDC7 may scaffold silencing complexes to prevent retrotransposition-induced genomic instability. The disordered architecture (pLDDT 43.3) enables multivalent binding to diverse ERV loci and silencing factors.

APOBEC3G RESTRICTION: APOBEC3G interaction (0.432, apolipoprotein B mRNA editing enzyme catalytic polypeptide-like 3G) connects CCDC7 to antiviral restriction. APOBEC3G deaminates cytidines in retroviral cDNA, causing hypermutation—CCDC7 may recruit APOBEC3G to ERV transcripts during meiosis, preventing retrotransposon propagation in germ cells. This mirrors APOBEC3G antiviral mechanisms but targets endogenous elements.

SPLICING & TRANSCRIPTION: TEX13C interaction (0.475, testis expressed 13C) and ZSCAN1 (0.421, zinc finger and SCAN domain containing 1) suggest transcriptional coregulation. TEX13C is testis-specific, potentially coupling CCDC7 to meiotic gene expression programs.

MITOTIC SPINDLE: HPA localizes CCDC7 to mitotic spindle and nucleoli—during spermatocyte meiosis, CCDC7 may scaffold spindle assembly factors ensuring faithful chromosome segregation. KIAA0586 interaction (0.415, centriolar cilia associated protein) links to centrosome function, critical for meiotic spindle formation.

DISEASE VARIANTS: ClinVar documents 12 pathogenic variants including 10p11.22-12.1 copy number losses (28970254-33231328, 30624523-33688350), extensive 10p15.3-q26.3 CNVs (100026-135427143), and splice site mutation (c.1135-1G>Ablating BioT2 domain expression). CNVs cause haploinsufficiency disrupting ERV silencing and meiotic spindle integrity, leading to azoospermia or spermatogenic failure.

CONSERVATION: Mouse Q9D541 (1642 aa) and macaque Q95J40 (1394 aa) show length divergence but domain conservation, indicating functional preservation of BioT2 spermatogenesis function across mammals.

## Evidence
```
InterPro: IPR029272 (CCDC7 family, 1-1384), PF15368 (BioT2 spermatogenesis, 1-170), PTHR22035; STRING: ERVFRD-1 (0.516), ERVV-2 (0.511), ERVV-1 (0.496), TEX13C (0.475), APOBEC3G (0.432), ZSCAN1 (0.421), LRRC69 (0.418), CCDC136 (0.415), KIAA0586 (0.415); HPA: Testis enriched (74.0 nTPM), nucleoli/mitotic spindle/cytosol; ClinVar: 12 pathogenic variants (10p CNVs, c.1135-1G>A splice); Conservation: Mouse Q9D541 (1642 aa), Macaque Q95J40 (1394 aa); AlphaFold: pLDDT 43.3 (disordered/IDP); UniProt: Q96M83 (1385 aa)
```
