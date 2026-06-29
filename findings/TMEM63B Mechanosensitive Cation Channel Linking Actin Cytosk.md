# TMEM63B: Mechanosensitive Cation Channel Linking Actin Cytoskeleton Remodeling to Golgi Trafficking and Synaptic Plasticity

**Date:** 2026-03-18T19:17:29.771855

**Quality Score:** 4.0/10  (E=6.2, D=1.8) [MODERATE]

## Description
TMEM63B encodes an 832-amino acid mechanosensitive cation channel (UniProt Q5T3F8) belonging to the OSCA1/CSC1 calcium-permeable stress-gated cation channel family (InterPro IPR045122, PTHR13018, residues 39-791). The protein contains three structural modules: an N-terminal transmembrane domain (IPR032880, PF13967, residues 120-224) for membrane anchoring, a cytosolic regulatory domain (IPR027815, PF14703, residues 240-422) for signal transduction, and a 7TM pore-forming region (IPR003864, PF02714, residues 433-705) characteristic of calcium-dependent channels. AlphaFold predicts a well-folded structure (pLDDT 72.6, high confidence), indicating stable tertiary architecture with defined transmembrane helices forming an ion-conducting pore.

FUNCTIONAL HYPOTHESIS: TMEM63B functions as a mechanosensitive calcium channel that couples plasma membrane tension to actin cytoskeleton remodeling, Golgi vesicle trafficking, and neuronal synaptic plasticity. The channel architecture (7TM pore + cytosolic domain) mirrors OSCA1/TMEM63A mechanotransduction mechanisms where membrane stretch induces conformational changes opening the pore for Ca2+ influx.

ACTIN CYTOSKELETON COUPLING: CYFIP2 interaction (0.569, cytoplasmic FMR1-interacting protein 2) positions TMEM63B at the interface between mechanotransduction and actin polymerization. CYFIP2 is part of the WAVE regulatory complex controlling Arp2/3-mediated actin branching—calcium influx through TMEM63B may activate CYFIP2-dependent actin remodeling, linking mechanical stimuli to cytoskeletal reorganization. This explains HPA localization to actin filaments and plasma membrane.

GOLGI EXOCYTOSIS: COG3 interaction (0.498, conserved oligomeric Golgi complex subunit 3) connects TMEM63B to retrograde Golgi trafficking and exocytosis. The COG complex mediates vesicle tethering at the Golgi—TMEM63B calcium signals may regulate COG3-dependent vesicle fusion, coordinating surfactant secretion (HPA annotation) and membrane protein trafficking. PF13967 (late exocytosis, Golgi transport) domain supports this function.

NEURONAL FUNCTION: GRIA3 interaction (0.463, glutamate ionotropic receptor AMPA type subunit 3) links TMEM63B to excitatory synaptic transmission. AMPA receptors mediate fast glutamatergic signaling—TMEM63B may modulate synaptic plasticity through calcium-dependent regulation of AMPA receptor trafficking or actin-based spine remodeling. XKR6 interaction (0.477, XK pseudorheumatoid factor 6) suggests apoptotic membrane scrambling coordination.

DISEASE VARIANTS: ClinVar documents 48 pathogenic variants including missense mutations mapping to functional domains: p.Arg507His (pore region, 433-705), p.His318Asp (cytosolic domain, 240-422), p.Tyr232His (N-terminal TM, 120-224), p.Ala54Val (N-terminal extension). These variants disrupt channel gating, calcium selectivity, or membrane trafficking, causing developmental and epileptic encephalopathy (DEE118 alias). Splice variants (c.1413+1G>A, c.2308-11T>C) abolish C-terminal pore formation.

CONSERVATION: Orthology shows strong length conservation—mouse Q3TWI9 (832 aa, 100% identity), rat D4A105 (832 aa), chicken A0A8V0ZB02 (816 aa, 97.6% identity)—indicating purifying selection on channel architecture and mechanotransduction function.

## Evidence
```
InterPro: IPR045122 (cation channel, 39-791), IPR003864 (7TM, 433-705), IPR027815 (cytosolic, 240-422), IPR032880 (N-TM, 120-224), PF02714, PF13967, PF14703, PTHR13018; STRING: CYFIP2 (0.569), COG3 (0.498), AZIN1 (0.488), XKR6 (0.477), GRIA3 (0.463), TMEM234 (0.440), UNC80 (0.432); HPA: Plasma membrane, actin filaments, low tissue specificity, detected in all; ClinVar: 48 pathogenic variants (p.Arg507His, p.His318Asp, p.Tyr232His, p.Ala54Val, splice sites); Conservation: Mouse Q3TWI9 (832 aa, 100%), Rat D4A105 (832 aa), Chicken A0A8V0ZB02 (816 aa, 97.6%); AlphaFold: pLDDT 72.6 (well-folded); UniProt: Q5T3F8 (832 aa)
```
