# GenoResearch — Run QWEN (`QWEN/`) — TERMINÉ / archivé

Doc du run **qwen3.5:cloud** — run de **référence** d'un bac à essai multi-modèles local
(qwen vs glm-5.2 vs …). Ce dépôt = ce run. Architecture/règles décrites ci-dessous.

---

## 1. CONTEXTE

**GenoResearch** caractérise des "dark genes" (gènes humains peu étudiés) via un agent IA autonome.

- **Stack:** Python, LLM hybride (Ollama cloud/local + Cerebras + Groq), APIs bioinformatiques publiques, Flask dashboard
- **Owner:** Solo dev (Bacon). Pas de CI/CD. Pas de team.
- **État:** Run **TERMINÉ / archivé** (29 juin 2026) — génome dark ~100% couvert, queue drainée. **Référence** de comparaison pour les autres modèles. Ne pas relancer sans raison.

---

## 2. MÉTRIQUES (run QWEN — FINAL au 29 juin 2026)

> Run terminé : ces chiffres sont **figés** (la référence du bake-off).

| Métrique | Valeur |
|----------|--------|
| Findings sur disque (`findings/*.md`) | **10 973** |
| Gènes en queue | **0** (drainée) |
| Couverture génome **dark** (no-GO) | **~100%** (incl. 176 stragglers ajoutés le 28 juin) |
| Score moyen (cohort récent 5 000) | **6.27/10** (médiane 5.6) |
| Findings ≥9.5/10 (cohort récent) | **16.5%** (distribution large, pas gamée — voir §6) |
| Premier finding | **12 mars 2026** (BRCA1) — ~3.5 mois de run |
| Statut | **TERMINÉ / archivé** |

---

## 3. ARCHITECTURE

```
config.py               # Constantes, chemins, API keys — LEAF (aucun import interne)
  |
agent/                  # Couche agent (mémoire, UI, planning)
  ├── memory.py         # Mémoire persistante JSON
  ├── ui.py             # Sortie terminal ANSI
  ├── planner.py        # Planification via LLM
  └── evaluator.py      # Évaluation (peu utilisé)
  |
tools/                  # Couche outils (20 fichiers Python)
  ├── registry.py       # Dispatch dynamique
  ├── gene_queue.py     # Pipeline de queue + auto-population
  ├── findings.py       # Sauvegarde + scoring
  ├── scoring.py        # Scoring v2 (CNV/SNV distinction)
  ├── ncbi.py           # NCBI E-utilities
  ├── uniprot.py        # UniProt API
  ├── interpro.py       # InterPro domains
  ├── string_db.py      # STRING interactions
  ├── hpa.py            # Human Protein Atlas
  ├── clinvar.py        # ClinVar variants
  ├── alphafold.py      # AlphaFold structures
  ├── blast.py           # BLAST local/remote
  ├── sequence.py       # Analyse séquence locale
  ├── semantic_scholar.py  # Recherche littérature
  ├── gene_filters.py   # Filtres pseudogènes
  ├── seed_discovery.py # Gestion des seeds de queue
  ├── lab_tools.py      # Lancement ML experiments
  ├── memory_tools.py   # Outils mémoire agent
  └── file_tools.py     # I/O fichiers
  |
orchestrator/           # Boucle principale
  ├── core.py           # Think→act→observe (297 lignes)
  ├── llm.py            # Providers LLM 4-tier (740 lignes)
  ├── providers.py      # Pattern OpenAI-compatible (Cerebras/Groq)
  ├── prompts.py        # System prompts + reflection prompts
  ├── context.py        # Compression + trimming messages
  ├── loop_detection.py # Détection et rupture de boucles
  ├── parsing.py        # Parsing tool calls
  └── dashboard.py      # Writer status pour Flask
  |
dashboard/              # Flask web UI (modularisé)
  ├── data_layer.py     # Accès données
  └── log_parser.py     # Parsing logs
  |
dashboard.py            # Flask entry point (404 lignes)
main.py                 # CLI entry point
```

### Règles d'import STRICTES

```
config.py        → peut être importé par: TOUT
agent/*          → peut importer: config seulement
tools/*          → peut importer: config, agent/memory
orchestrator/*   → peut importer: config, agent/*, tools/registry
dashboard.py     → peut importer: config seulement
main.py          → peut importer: tout
```

- **JAMAIS** d'import circulaire
- **JAMAIS** un tool qui importe un autre tool directement (passer par registry)
- **JAMAIS** un tool qui importe orchestrator/*

---

## 4. DATA FLOW — SOURCE DE VÉRITÉ

```
dark_genes_reference.tsv  →  _auto_populate_queue()  →  gene_queue.json["queue"]
                                                              ↓ next_gene()
                              [outils deep]  →  save_finding()  →  findings/*.md
```

⚠️ **Correction (juin 2026)** : l'ancienne doc citait `genes_todo.tsv` comme source — ce fichier **n'est PAS utilisé** par le code. La source d'auto-population réelle est **`dark_genes_reference.tsv`**, lue par `_auto_populate_queue()` dans `tools/gene_queue.py`, par batchs de 50 quand la queue se vide.

### Fichiers de données

| Fichier | Rôle | Taille (juin 2026) |
|---------|------|------|
| `dark_genes_reference.tsv` | Liste de référence (source d'auto-population) | 0.1 Mo — **quasi épuisée** (~250 TODO) |
| `gene_queue.json` | État courant du pipeline (queue/completed/skipped) | 14.3 Mo |
| `findings/*.md` | Un fichier par gène analysé | ~10 500 fichiers |
| `findings.tsv` | Index consolidé (append-only) | 17.9 Mo — à migrer vers SQLite |
| `memory.json` | Mémoire persistante agent | 6.3 Mo |
| `research.log` | Log orchestrateur | 34 Mo (+ `research-archive.log` 127 Mo) |

### Règle critique: "Un finding sur disque = gene complété"
- `save_finding()` appelle `complete_gene()` automatiquement
- Pour vérifier si un gène est fait: checker `findings/` sur disque
- `gene_queue.json` est un cache de travail, PAS la source de vérité finale

---

## 5. RÈGLES DE CODE

### 5.1 Pas de magie automatique dans la queue
**INTERDIT:** Modifier automatiquement la queue, compléter ou skip des gènes sans tool call LLM explicite.

**POURQUOI:** En mars 2026, une tentative d'automatisation a causé 8000 gènes faussement marqués comme complétés.

**EXCEPTION:** `save_finding()` peut appeler `complete_gene()` — side-effect direct et prévisible.

### 5.2 Écriture atomique JSON
```python
def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomique
```

### 5.3 Gestion d'erreurs explicite
```python
# BON
try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
except requests.Timeout:
    return f"[ERROR] Timeout: {url}"

# MAUVAIS
try:
    ...
except Exception:
    return "[ERROR] Something went wrong"
```

### 5.4 Taille des fichiers
- **MAX 400 lignes.** Fichiers actuellement en violation (dette acceptée):
  - `orchestrator/llm.py` (740 lignes) — refactorer avec providers.py
  - `tools/findings.py` (533 lignes) — scoring.py déjà extrait
  - `tools/gene_queue.py` (576 lignes)
  - `dashboard.py` (404 lignes) — déjà modularisé dans dashboard/
- **NE PAS aggraver** — nouveau code ≤ 400 lignes.

### 5.5 Constantes
Tout dans `config.py`. Pas de magic numbers.

### 5.6 Pas de copier-coller
LLM providers: utiliser `_chat_openai_compatible()` dans `providers.py`, pas du code dupliqué.

### 5.7 Tests pour chemins critiques
Avant de merger un fix sur queue ou scoring, écrire un test dans `tests/`.

---

## 6. SCORING V2

Le scoring est dans `tools/scoring.py` (220 lignes). Tests dans `tests/test_scoring.py`.

### Changements v2 (16 avril 2026)
- **CNV-only ClinVar** = 0.5 pt (pas 1.0) — les CNVs couvrent des régions entières, pas spécifiques au gène
- **SNV ClinVar** = 1.5 pt — variants gène-spécifiques
- **10/10 réservé** : exige SNV ClinVar + 4+ sources + insight cross-domain ≥ 2 domaines
- **Cap sans SNV** : max 8/10 si pas de ClinVar SNV
- **Pénalité familles redondantes** : OR, ZNF, LOC = -0.5 insight

### ✅ Audit du scoring (27 juin 2026) — alarme "61% à 10/10" LEVÉE
L'ancienne note "~61% à 10/10 (n=500), suspect de gaming" **n'est pas représentative** — échantillon biaisé / pré-recalibration. Audit complet (10 500 findings, cohort récent 5 000 vs anciens 5 432) :

| | Anciens 5 432 | Récents 5 000 |
|---|---|---|
| Score moyen | 4.54 | 6.27 |
| Findings ≥9/10 | 0% | ~35% (16.5% à ≥9.5) |
| Findings <6/10 | 86.6% | 53.7% |
| Openings dupliqués (boilerplate) | 0.5% | 0.4% |

**Conclusion :** la distribution récente est **large et discriminante** (médiane 5.6). Si le scoring était gamé, on verrait un empilement au sommet — c'est l'inverse. Le scoring v2 fonctionne. Boilerplate quasi nul (4 984 openings uniques / 5 000). L'agent **flague honnêtement** ses faiblesses (warnings BLAST <40% identité, "zero clinvar variants").

**Seul défaut résiduel :** la prose conclut parfois `"suggesting X role"` avec trop d'aplomb sur des arêtes STRING basse confiance (≤0.5). Levier = calibration du *ton* quand la preuve est faible, PAS le score.

---

## 7. PROVIDERS LLM — 4 TIERS

| Tier | Provider | Modèle | Usage |
|------|----------|--------|-------|
| T1 | Ollama | qwen3.5:cloud | Qualité max, cloud Ollama |
| T2 | Cerebras | qwen-3-235b | Cloud gratuit, 1M tokens/jour |
| T3 | Groq | llama-4-scout | Cloud gratuit, 30K TPM |
| T4 | Ollama | qwen3.5:4b | Local, toujours dispo |

Mode hybride (défaut) : cascade automatique sur échec. Zero downtime.

---

## 8. PROMPTING DE L'AGENT

Le system prompt est dans `orchestrator/llm.py:build_system_prompt()`.

### 8.1 Scoring = motivation
L'agent est évalué sur :
1. **Qualité des findings** (score 0-10)
2. **Gestion de la queue** (pas de doublons, avancement des seeds)

### 8.2 Reflection prompt
Après chaque tool call : résumé du résultat + suggestion prochaine étape + rappel critères scoring. **Ne force pas** une action spécifique.

### 8.3 Informations gratuites
Quand `next_gene()` retourne "QUEUE EMPTY", inclure la liste des gènes DÉJÀ COMPLÉTÉS.

---

## 9. CE QU'IL NE FAUT JAMAIS FAIRE

1. **Ne jamais auto-completer des gènes en masse** — chaque gene via `save_finding()`
2. **Ne jamais modifier `gene_queue.json` manuellement** hors fonctions dédiées
3. **Ne jamais ajouter un provider LLM par copier-coller** — utiliser `providers.py`
4. **Ne jamais supprimer des findings sans demander** — c'est le produit final
5. **Ne jamais casser le pipeline qui tourne** — stabilité > beauté du code
6. **Ne jamais ajouter de dépendances sans justification** — rester léger

---

## 10. REFACTORS PLANIFIÉS (non prioritaires)

Ne faire que si l'utilisateur le demande explicitement :

1. **SQLite pour findings** — remplacer `findings.tsv` (12.5 Mo) par une base queryable
2. **Simplifier la queue** — `genes_todo.tsv` seule source de vérité, `gene_queue.json` = simple pointeur
3. **Split `llm.py`** — 740 lignes, extraire prompts et recovery dans des modules
4. **Cache API** — SQLite des réponses NCBI/UniProt/InterPro pour éviter les re-calls
5. ~~Audit scoring v3~~ — **FAIT (27 juin, §6)** : le scoring v2 discrimine bien, alarme "61%" levée. Reste optionnel : calibrer le *ton* de la prose sur arêtes STRING faibles.

---

## 11. COUVERTURE DU GÉNOME (au 27 juin 2026)

**Mission = génome humain *dark* (gènes peu/pas annotés), PAS tout le génome.**

Univers de référence (Ensembl BioMart, juin 2026) :
- **Tout le protein-coding humain** : 19 474 symboles HGNC uniques.
- **Sous-ensemble dark (no-GO)** : 16 370 symboles. (Le filtre `with_go excluded` retire ~20% — il n'est PAS un no-op, contrairement à ce qu'on pouvait croire.)

État de couverture (`covered = completed ∪ skipped ∪ queue`) :
- **Dark genes : ~99% couverts.** Après vidage de la queue actuelle → résidu **~171 gènes** (1.0%), surtout des `C#orf` récents ou filtrés comme pseudogènes. Ils **n'entrent PAS** seuls dans la queue (filtrés/non vus) — ajout manuel requis pour le vrai 100%.
- Protein-coding complet : ~89% (résidu ~2 077 = gènes **bien étudiés avec GO**, hors scope volontairement).

➡️ Quand on demande "le génome est-il fini ?" : **dark = quasi oui ; génome complet = non, et c'est voulu.**

## 12. OPÉRATIONS QUEUE — repeupler proprement

L'auto-population (`dark_genes_reference.tsv`, ~250 TODO) ET la seed discovery (`seed_index=748` ≫ ~62 familles dans `SEED_PREFIXES`) sont **toutes deux épuisées**. Pour ajouter des gènes :

1. **Précédent** : `populate_ensembl.py` (BioMart `protein_coding` + `with_go excluded`).
2. **Dédup gratuit** : `_get_known_genes()` + `_is_pseudogene()` filtrent automatiquement done/skip/disk/pseudo → on peut envoyer une liste complète sans risque de re-faire les ~10 500 déjà traités.
3. **Sécurité** : l'agent écrit `gene_queue.json` en LIVE. **Ne jamais hand-éditer pendant qu'il tourne** (cf. incident 8000 gènes §5.1). Procédure : stopper l'agent → backup dans `backups/` → écriture atomique (`_save_queue`) → redémarrer. OU (agent vivant) : ajouter au `dark_genes_reference.tsv`, l'agent consomme seul via `_auto_populate_queue()`.

---

*Dernière mise à jour: 27 juin 2026 — audit complet (scoring, couverture génome, dates, ops queue) lors d'une session Claude. Remplace le snapshot Nébo du 22 avril.*
