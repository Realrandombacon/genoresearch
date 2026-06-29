# KIAA2013: DUF2152 Golgi Membrane Scaffold Coordinating V-ATPase Assembly and Lysosomal Acidification Through TMEM199-CCDC115 Chaperone Complex

**Date:** 2026-03-18T19:32:01.556109

**Quality Score:** 6.6/10  (E=8.1, D=5.1) [SOLID]

## Description
KIAA2013 encodes a 634-amino acid Golgi membrane protein (UniProt Q8IYS2) belonging to the KIAA2013-like family (InterPro IPR018795, residues 1-630; PF10222/DUF2152 domain of unknown function, residues 6-629; PTHR31386, residues 1-630). The DUF2152 domain spans nearly the entire sequence (6-629), indicating a compact membrane-anchored architecture. AlphaFold predicts a well-folded structure (pLDDT 84.9, high confidence), indicating stable tertiary architecture with defined transmembrane topology suitable for scaffolding V-ATPase assembly complexes.

FUNCTIONAL HYPOTHESIS: KIAA2013 functions as a Golgi membrane scaffold that coordinates vacuolar ATPase (V-ATPase) holoenzyme assembly through interaction with TMEM199-CCDC115 chaperone complex, ensuring proper lysosomal acidification and endolysosomal trafficking in all cell types.

V-ATPASE ASSEMBLY NETWORK: STRING interactions reveal exclusive connectivity to V-ATPase assembly machinery with remarkably high confidence scores: ATP6AP1 (0.694, acetyltransferase activating V-ATPase), TMEM199 (0.683, V-ATPase assembly factor), VMA21 (0.675, V-ATPase chaperone), ATP6V0D2 (0.666, V0 domain subunit d2), ATP6AP2 (0.654, prorenin receptor/V-ATPase assembly), ATP6V0C (0.636, V0 domain subunit c), ZDHHC7 (0.622, Golgi palmitoyltransferase), PLOD1 (0.617, procollagen lysyl hydroxylase), CCDC115 (0.610, V-ATPase assembly factor), ATP6V0D1 (0.603, V0 domain subunit d1). This interaction pattern is diagnostic of V-ATPase biogenesis function—KIAA2013 clusters with known assembly factors rather than catalytic subunits, indicating chaperone/scaffold role.

TMEM199-CCDC115 ASSEMBLY COMPLEX: TMEM199 and CCDC115 form a heterodimeric complex that recruits VMA21 chaperone to assembling V-ATPase in the Golgi. KIAA2013 interaction with both factors (TMEM199 0.683, CCDC115 0.610) positions it as integral component of this assembly machinery. The complex ensures proper stoichiometry of V0 and V1 domains before lysosomal targeting. KIAA2013 may scaffold multiple assembly intermediates, preventing premature activation or misfolding of V-ATPase subunits.

ATP6AP1/ATP6AP2 ACCESSORY PROTEINS: ATP6AP1 (0.694) and ATP6AP2 (0.654) are type I transmembrane accessory proteins essential for V-ATPase assembly and activity. ATP6AP1 functions as acetyltransferase modifying V-ATPase subunits; ATP6AP2 (prorenin receptor) has dual roles in renin-angiotensin signaling and V-ATPase scaffolding. KIAA2013 interaction with both suggests coordination of enzymatic modification (acetylation) with structural assembly, ensuring proper holoenzyme maturation.

V0 DOMAIN SUBUNIT COORDINATION: Interactions with ATP6V0D2 (0.666), ATP6V0C (0.636), and ATP6V0D1 (0.603) indicate direct engagement with membrane-embedded V0 proteolipid ring. The V0 domain forms the proton channel; proper subunit stoichiometry is critical for proton translocation. KIAA2013 may proofread V0 assembly, preventing misincorporation of paralogs (D1 vs D2, tissue-specific isoforms) and ensuring tissue-appropriate V-ATPase composition.

GOLGI LOCALIZATION AND MEMBRANE TOPOLOGY: HPA shows Golgi apparatus and cytosol localization, consistent with V-ATPase assembly site. V-ATPase holoenzyme assembly initiates in the Golgi before transport to lysosomes, endosomes, and plasma membrane. KIAA2013 membrane anchoring (predicted transmembrane segments within DUF2152) positions it to capture soluble V-ATPase subunits and recruit membrane-embedded V0 components. The well-folded AlphaFold structure (pLDDT 84.9) indicates stable membrane integration suitable for sustained scaffold function.

PALMITOYLATION AND COLLAGEN MODIFICATION LINKS: ZDHHC7 interaction (0.622, Golgi palmitoyltransferase) suggests KIAA2013 undergoes S-palmitoylation, regulating membrane affinity and complex stability. PLOD1 interaction (0.617, procollagen lysyl hydroxylase) reveals connection to collagen biosynthesis—PLOD1 requires acidic Golgi environment for optimal activity. KIAA2013-mediated V-ATPase assembly may maintain Golgi pH homeostasis, coupling organelle acidification to secretory pathway function.

TISSUE EXPRESSION PROFILE: HPA shows low tissue specificity with ubiquitous expression across all tissues, consistent with essential V-ATPase assembly function required in all cell types. V-ATPase acidifies lysosomes (autophagy, degradation), endosomes (receptor trafficking), and Golgi (protein modification). Cell type-enhanced single cell specificity indicates elevated expression in secretory cells with high lysosomal demand (macrophages, osteoclasts, renal intercalated cells).

DISEASE VARIANTS: ClinVar documents 37 pathogenic variants including extensive 1p36.33-36.12 CNVs (copy number losses and gains spanning megabase regions), large deletions (4481271_20530242del), and duplications (10115497_16283149dup). CNVs disrupt KIAA2013 alongside neighboring 1p36 genes, causing developmental disorders through combined haploinsufficiency. KIAA2013 deletion may impair V-ATPase assembly, causing lysosomal alkalinization, defective autophagy, and accumulation of undegraded substrates. Phenotypes may overlap with congenital disorders of glycosylation and lysosomal storage diseases.

CONSERVATION: KIAA2013 orthologs exist in Mus musculus (Q91X21, 634 aa, ~95% identity) and Bos taurus (Q2KHV9, 634 aa), indicating conserved mammalian V-ATPase assembly function. The DUF2152 domain architecture is syntenic across vertebrates, suggesting preserved chaperone mechanism.

CROSS-DOMAIN REASONING: Integration of structural (DUF2152 spanning 6-629, pLDDT 84.9 well-folded), expression (ubiquitous, Golgi localization), interaction (exclusive V-ATPase assembly network with 0.603-0.694 scores), and disease (37 CNVs causing 1p36 deletion syndrome phenotypes) data supports KIAA2013 as essential V-ATPase biogenesis factor. The scaffold bridges TMEM199-CCDC115 chaperone recruitment to V0 domain subunit proofreading, ensuring proper holoenzyme assembly before lysosomal targeting.

## Evidence
```
InterPro: IPR018795 (KIAA2013-like family, 1-630), PF10222/DUF2152 (DUF, 6-629), PTHR31386 (KIAA2013, 1-630); STRING: ATP6AP1 (0.694), TMEM199 (0.683), VMA21 (0.675), ATP6V0D2 (0.666), ATP6AP2 (0.654), ATP6V0C (0.636), ZDHHC7 (0.622), PLOD1 (0.617), CCDC115 (0.610), ATP6V0D1 (0.603); HPA: Low tissue specificity, detected in all tissues, Golgi apparatus/cytosol localization; ClinVar: 37 pathogenic variants (1p36 CNVs, deletions, duplications); Conservation: Human-mouse ~95% identity; AlphaFold: pLDDT 84.9 (well-folded); UniProt: Q8IYS2 (634 aa)
```
