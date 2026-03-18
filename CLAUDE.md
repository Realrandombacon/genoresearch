# GenoResearch — Instructions pour Claude

Tu es Claude, assistant IA. Ce fichier contient les instructions architecturales permanentes pour le projet GenoResearch. Lis-le au debut de chaque session.

---

## 1. CONTEXTE DU PROJET

GenoResearch est un agent de recherche genomique autonome qui caracterise des "dark genes" (genes humains non etudies). Un orchestrateur Python fait tourner Qwen 3.5 en boucle continue. A chaque cycle, Qwen decide quels outils appeler (NCBI, UniProt, InterPro, STRING, HPA, ClinVar, AlphaFold), synthetise les resultats, et produit un "finding" (fichier .md) avec un score de qualite 0-10.

**Stack:** Python, Qwen 3.5 via Ollama Cloud, APIs bioinformatiques publiques, Flask dashboard.
**Owner:** Un seul developpeur. Pas de CI/CD. Pas de team.
**Etat:** Production — l'agent tourne 24/7 et produit des findings. La stabilite est prioritaire.

---

## 2. ARCHITECTURE — NE PAS VIOLER

```
config.py                  # Constantes, chemins, API keys — LEAF (aucun import interne)
  |
agent/                     # Couche agent (memoire, UI, planning)
  ├── memory.py            # JSON-backed persistent memory — importe seulement config
  ├── ui.py                # Terminal ANSI output — importe seulement config
  ├── planner.py           # Planification de recherche via LLM
  └── evaluator.py         # Evaluation de resultats (peu utilise)
  |
tools/                     # Couche outils (30+ fonctions genomiques)
  ├── registry.py          # Dispatch dynamique des outils
  ├── gene_queue.py        # Gestion de la queue de genes + pipeline
  ├── findings.py          # Sauvegarde + scoring des findings
  ├── ncbi.py              # NCBI E-utilities
  ├── uniprot.py           # UniProt API
  ├── interpro.py          # InterPro domains
  ├── string_db.py         # STRING interactions
  ├── hpa.py               # Human Protein Atlas
  ├── clinvar.py           # ClinVar variants
  ├── alphafold.py         # AlphaFold structures
  ├── blast.py             # BLAST local/remote
  ├── sequence.py          # Analyse de sequences locale
  ├── memory_tools.py      # Outils de memoire pour l'agent
  └── file_tools.py        # I/O fichiers
  |
orchestrator/              # Couche orchestration (boucle principale)
  ├── core.py              # Boucle think->act->observe, parsing, compression
  ├── llm.py               # Providers LLM (4-tier failover hybrid)
  └── dashboard.py         # Status writer pour Flask
  |
dashboard.py               # Flask web UI — monitoring temps reel
main.py                    # CLI entry point
```

### Regles d'import STRICTES

```
config.py        peut etre importe par:  TOUT
agent/*          peut importer:          config seulement
tools/*          peut importer:          config, agent/memory
orchestrator/*   peut importer:          config, agent/*, tools/registry
dashboard.py     peut importer:          config seulement
main.py          peut importer:          tout
```

- **JAMAIS** d'import circulaire
- **JAMAIS** un tool qui importe un autre tool directement (passer par registry)
- **JAMAIS** un tool qui importe orchestrator/*
- Si un import cree un cycle, utiliser un lazy import DOCUMENTE avec un commentaire `# lazy: avoid circular`

---

## 3. DATA FLOW — SOURCE DE VERITE

```
genes_todo.tsv   →  next_gene()  →  [6 outils deep]  →  save_finding()  →  findings/*.md
                                                                               ↑
                                                          gene_queue.json    SEULE SOURCE
                                                          (working state)    DE VERITE pour
                                                                             "est-ce fait?"
```

### Fichiers de donnees

| Fichier | Role | Format |
|---------|------|--------|
| `genes_todo.tsv` | Liste de reference de tous les genes | TSV: gene, status (TODO/DONE/SKIPPED) |
| `gene_queue.json` | Etat courant du pipeline | JSON: queue, in_progress, completed, skipped |
| `findings/*.md` | Un fichier par gene analyse | Markdown avec score |
| `findings.tsv` | Index consolide | TSV de tous les findings |
| `memory.json` | Memoire persistante de l'agent | JSON: explored, stats, notes |
| `research.log` | Log de l'orchestrateur | Texte |

### Regle critique: "Un finding sur disque = gene complete"
- `save_finding()` appelle `complete_gene()` automatiquement
- Pour verifier si un gene est fait: checker `findings/` sur disque
- `gene_queue.json` est un cache de travail, PAS la source de verite finale

---

## 4. REGLES DE CODE — TOUJOURS RESPECTER

### 4.1 Pas de magie automatique dans le pipeline de queue

**INTERDIT:** Ajouter du code qui modifie automatiquement la queue, complete des genes, skip des genes, ou avance des seeds SANS que l'agent LLM l'ait explicitement demande via un tool call.

**POURQUOI:** En mars 2026, une tentative d'automatisation du pipeline de queue a cause 8000 genes faussement marques comme completes et l'agent tournait en rond. La lecon: le LLM doit rester en controle du flow.

**EXCEPTION:** `save_finding()` peut appeler `complete_gene()` car c'est un side-effect direct et previsible.

### 4.2 Ecriture atomique pour les fichiers JSON

```python
# BON
import tempfile, os
def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomique sur le meme filesystem

# MAUVAIS
with open(path, "w") as f:
    json.dump(data, f)  # corruption si crash pendant l'ecriture
```

### 4.3 Gestion d'erreurs explicite

```python
# BON — catch specifique, log l'erreur
try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
except requests.Timeout:
    return f"[ERROR] Timeout after 30s for {url}"
except requests.HTTPError as e:
    return f"[ERROR] HTTP {resp.status_code} for {url}: {e}"

# MAUVAIS — cache tout, impossible a debugger
try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
except Exception:
    return "[ERROR] Something went wrong"
```

### 4.4 Taille des fichiers

- **MAX 400 lignes par fichier.** Si un fichier depasse 400 lignes, il faut le splitter.
- Fichiers actuellement en violation (dette technique acceptee):
  - `orchestrator/core.py` (887 lignes) — a refactorer en core.py + prompts.py + context.py
  - `tools/gene_queue.py` (848 lignes) — a refactorer en gene_queue.py + seeds.py
  - `orchestrator/llm.py` (812 lignes) — a refactorer avec un provider interface
  - `dashboard.py` (701 lignes) — a refactorer en routes + services
  - `tools/findings.py` (634 lignes) — a refactorer en findings.py + scoring.py
- **NE PAS aggraver** la dette — tout nouveau code doit respecter la limite de 400 lignes.

### 4.5 Constantes

Toutes les constantes (seuils, limites, timeouts) vont dans `config.py`. Pas de magic numbers dans le code.

```python
# BON
from config import MAX_TURNS, SOFT_TURNS, LOOP_THRESHOLD

# MAUVAIS
if turn > 20:  # pourquoi 20?
```

### 4.6 Pas de copier-coller

Si deux fonctions font la meme chose avec des parametres differents, extraire une fonction commune.

Exemple connu: `_chat_ollama()`, `_chat_cerebras()`, `_chat_groq()` dans llm.py sont quasi identiques. La bonne approche: un seul `_chat_openai_compatible(provider_config)`.

### 4.7 Tests pour les chemins critiques

Avant de merger un fix sur le pipeline de queue ou le scoring, ecrire un test dans `tests/`. Les chemins critiques:

- `next_gene()` — retourne le bon gene, skip les completes
- `save_finding()` — ecrit sur disque, complete le gene, pas de doublon
- `add_to_queue()` — rejette les doublons
- `_compute_score()` — scoring coherent
- `complete_gene()` — ne perd pas les genes en queue

---

## 5. PROMPTING DE L'AGENT — REGLES

Le system prompt de l'agent (dans `orchestrator/llm.py:build_system_prompt()`) suit ces principes:

### 5.1 Scoring = motivation
L'agent est evalue sur deux axes:
1. **Qualite des findings** (score 0-10 base sur coverage, depth, insight)
2. **Gestion de la queue** (pas de doublons, avancement des seeds, efficacite)

### 5.2 Le reflection prompt guide, ne force pas
Apres chaque tool call, l'agent recoit un reflection prompt qui:
- Resume le resultat
- Suggere la prochaine etape
- Rappelle les criteres de scoring
- **NE FORCE PAS** une action specifique

### 5.3 Informations gratuites
Quand `next_gene()` retourne "QUEUE EMPTY", inclure la liste des genes DEJA COMPLETES pour la famille seed courante. L'agent ne devrait jamais gaspiller un turn a essayer d'ajouter un gene deja fait.

---

## 6. CE QU'IL NE FAUT JAMAIS FAIRE

1. **Ne jamais auto-completer des genes en masse** — chaque gene doit passer par save_finding()
2. **Ne jamais modifier gene_queue.json manuellement** en dehors des fonctions dediees
3. **Ne jamais ajouter de provider LLM par copier-coller** — utiliser le pattern existant ou refactorer
4. **Ne jamais supprimer des findings sans demander** — les findings sont le produit final du projet
5. **Ne jamais casser le pipeline qui tourne** — si l'agent produit des findings, la stabilite prime sur la beaute du code
6. **Ne jamais ajouter de dependances sans justification** — le projet doit rester leger

---

## 7. REFACTORS PLANIFIES (pas urgents)

Ces refactors sont identifies mais NON prioritaires tant que le pipeline tourne:

1. **Queue simplifiee** — Le TSV devient seule source de verite (TODO/DONE/SKIPPED), gene_queue.json devient un simple pointeur "current gene"
2. **Provider interface** — Un seul `_chat_openai_compatible()` remplace les 3 fonctions copier-coller dans llm.py
3. **Split core.py** — Extraire prompts.py (reflection, system prompt) et context.py (compression, trimming)
4. **Split findings.py** — Extraire scoring.py
5. **SQLite findings DB** — Parser les .md en base structuree pour requetes interactives

**REGLE:** Ne faire ces refactors que quand l'utilisateur le demande explicitement. Ne jamais refactorer "au passage".

---

## 8. METRIQUES DE REFERENCE

Au 18 mars 2026:
- 734 findings, score moyen 8.00/10
- 290+ findings a 10/10
- 5 doublons mineurs restants
- Pipeline stable, ~15 genes/heure
- Donnees verifiees manuellement contre les APIs sources (5/5 exact)

---

*Ce fichier est la reference architecturale du projet. Toute modification doit etre approuvee par l'utilisateur.*
