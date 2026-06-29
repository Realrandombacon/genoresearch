# TMEM67: Meckelin - Ciliary Transition Zone Scaffold Protein in MKS Complex

**Date:** 2026-03-20T09:14:37.410436

**Quality Score:** 3.35/10  (E=5.2, D=1.5) [WEAK]

## Description
TMEM67 encodes meckelin, a 995 amino acid type I transmembrane protein that serves as a critical scaffold component of the ciliary transition zone (TZ) and Meckel syndrome (MKS) protein complex. The protein contains an N-terminal growth factor receptor cysteine-rich domain superfamily (IPR009030, SSF57184, residues 46-197) followed by the meckelin family domain (IPR019170, PF09773, PTHR21274, residues 168-995) that mediates ciliary membrane protein sorting. AlphaFold predicts a well-folded structure with high confidence (pLDDT 84.7/100), indicating stable architecture for transition zone scaffolding.

Expression profiling (HPA) shows tissue-enhanced pattern with highest levels in heart muscle (20.8 nTPM), consistent with ciliary requirements in cardiomyocytes. STRING interactions reveal exclusive partnerships with ciliopathy proteins—all at high confidence: CC2D2A (0.998), CEP290 (0.997), MKS1 (0.993), TMEM216 (0.987), TCTN1 (0.984), B9D1 (0.929), TMEM231 (0.890), B9D2 (0.885), NPHP1 (0.837), TCTN2 (0.743). This interaction network defines the MKS complex that gates ciliary protein entry via the diffusion barrier at the ciliary base.

ClinVar documents 378 pathogenic/likely pathogenic variants including nonsense mutations (p.Gln558Ter), frameshifts (p.Tyr260fs, p.Ala7fs), and splice defects, causing Meckel syndrome type 3 (MKS3), Joubert syndrome type 6 (JBTS6), Bardet-Biedl syndrome, and nephronophthisis. The cysteine-rich domain likely mediates extracellular ligand binding or receptor dimerization, while the transmembrane/cytoplasmic regions recruit MKS complex components. Mechanistically, TMEM67 anchors the ciliary diffusion barrier by scaffolding MKS1-B9D1-B9D2 modules that filter membrane protein trafficking—defects cause mislocalization of ciliary receptors (GPCRs, RTKs), disrupting Hedgehog, Wnt, and GPCR signaling in developing neural tube, kidney, and retina.

## Evidence
```
InterPro: IPR009030/SSF57184 cysteine-rich domain (aa 46-197), IPR019170/PF09773/PTHR21274 meckelin (aa 168-995) | STRING: CC2D2A(0.998), CEP290(0.997), MKS1(0.993), TMEM216(0.987), TCTN1(0.984), B9D1(0.929), TMEM231(0.890), B9D2(0.885), NPHP1(0.837), TCTN2(0.743) | HPA: heart muscle 20.8 nTPM, tissue enhanced; Bardet-Biedl syndrome, ciliopathy, deafness | ClinVar: 378 pathogenic variants (nonsense, frameshift, splice) | AlphaFold: pLDDT 84.7 (high confidence) | UniProt: Q5HYA8 (995 aa) | Function: MKS complex transition zone scaffold for ciliary protein sorting
```
