# CCDC40: Axonemal Dynein Regulatory Complex Scaffold - Coiled-Coil Molecular Ruler in Motile Cilia

**Date:** 2026-03-20T09:16:37.307873

**Quality Score:** 3.65/10  (E=6.5, D=0.8) [MODERATE]

## Description
CCDC40 encodes a 1142 amino acid coiled-coil domain protein that serves as an essential structural scaffold of the axonemal dynein regulatory complex (DRC) in motile cilia. The protein is dominated by an extended coiled-coil domain (IPR037386, PTHR16275, residues 31-1141) that spans nearly the entire sequence, forming an elongated molecular ruler that templates DRC assembly along the ciliary microtubule doublets. AlphaFold predicts a confident helical bundle structure (pLDDT 70.8/100), consistent with coiled-coil-mediated oligomerization required for axonemal scaffolding.

Expression profiling (HPA) shows tissue-enhanced pattern with highest levels in fallopian tube (14.0 nTPM) and choroid plexus (13.7 nTPM), matching tissues dependent on coordinated ciliary beating for oocyte transport and cerebrospinal fluid flow. Subcellular localization spans microtubules, primary cilium, cytokinetic bridge, and midpiece—consistent with axonemal incorporation. STRING interactions reveal exclusive partnerships with axonemal structural and assembly proteins: CCDC39 (0.995), DNAI2 (0.821), CCDC103 (0.821), LRRC6 (0.821), RSPH4A (0.780), DNAH5 (0.777), CCDC114 (0.738), CCDC65 (0.718), DRC1 (0.690), DNAAF1 (0.564). This network defines the DRC-inner dynein arm (IDA) assembly module where CCDC40 heterodimerizes with CCDC39 to anchor IDA rows and DRC linkers.

ClinVar documents 180 pathogenic/likely pathogenic variants including frameshifts (p.Leu752fs, p.Pro115fs), nonsense mutations (p.Gln319Ter, p.Glu518Ter), and splice defects, causing primary ciliary dyskinesia type 15 (PCD-15), Kartagener syndrome, and heterotaxy. The CCDC40-CCDC39 heterodimer forms a ~100nm coiled-coil ruler that positions IDA subspecies at 96nm axonemal repeats. Mechanistically, CCDC40 recruits IDA heavy chains (DNAH5) and intermediate chains (DNAI2) via CCDC103 adaptors, while DRC1 links the complex to nexin-dynein regulatory bridges that control microtubule sliding. Defects abolish ciliary beat frequency and waveform, causing mucociliary clearance failure, laterality defects (nodal cilia), and hydrocephalus (ependymal cilia).

## Evidence
```
InterPro: IPR037386/PTHR16275 coiled-coil domain (aa 31-1141) | STRING: CCDC39(0.995), DNAI2(0.821), CCDC103(0.821), LRRC6(0.821), RSPH4A(0.780), DNAH5(0.777), CCDC114(0.738), CCDC65(0.718), DRC1(0.690), DNAAF1(0.564) | HPA: fallopian tube 14.0 nTPM, choroid plexus 13.7 nTPM; ciliopathy, Kartagener syndrome, PCD; microtubules/cilium | ClinVar: 180 pathogenic variants (frameshift, nonsense, splice) | AlphaFold: pLDDT 70.8 (confident) | UniProt: Q4G0X9 (1142 aa) | Function: DRC-IDA scaffold for ciliary beat regulation
```
