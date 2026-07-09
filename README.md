# GenoResearch

**Autonomous Genomics Research Agent** — An AI agent that autonomously explores the human genome, discovers understudied genes, and logs scientific findings using bioinformatics tools, database mining, and machine learning.

## The Mission

~20,000 protein-coding genes exist in the human genome, but only ~2,000 are well-studied. GenoResearch targets the other ~17,000 **"dark genes"** — systematically investigating them through sequence analysis, homology search, and database mining to generate functional hypotheses.

The agent runs autonomously in a **think → act → observe → learn** loop: it queries genomic databases, analyzes sequences, runs BLAST searches, and records novel findings — all without human intervention.

## Status (July 2026)

The **dark-genome sweep is complete** — every protein-coding gene without GO
annotation has been processed. The project is now a **multi-model bake-off**: the
same pipeline is re-run with different LLMs to measure how model choice affects the
quality of the hypotheses.

| Run | LLM | Findings | State |
|-----|-----|----------|-------|
| **qwen3.5** (this repo) | `qwen3.5:cloud` | **10,973** | ✅ complete — reference run |
| GLM-5.2 | `glm-5.2:cloud` | ~4,700 | ✅ complete |
| DeepSeek-V4-Pro | `deepseek-v4-pro:cloud` | — | 🟢 starting |

First finding: **March 12, 2026** (BRCA1). Dark-genome coverage: **~100%** of the
no-GO set. All runs share one reference gene list and one pipeline — only the LLM
changes, so the findings are directly comparable.

## Philosophy — honest orientation, not a high score

Findings are **hypotheses to orient a researcher**, never proven claims. As of the
June 2026 rewrite, the agent no longer optimizes a quality score — it writes for
*a researcher who has never heard of the gene*:

- **Separates established facts from inference** — "suggests" for a leap, never a bare assertion.
- **Calibrates confidence honestly** — thin or contradictory evidence is flagged LOW; *absence of data is itself a valid result*.
- **Flags literature noise** — gene-symbol homonyms (e.g. `NOL8`, `MOB2`) that pollute automated searches.
- **Ends on a testable step** — every finding names what would falsify or confirm it.
- **Values good triage** — correctly *skipping* a well-studied gene counts as much as a finding.

A numeric score (`tools/scoring.py`) is still computed, but it is **passive
bookkeeping**, not the agent's objective — it saturates and can be gamed, so it is
deliberately kept out of the agent's prompt. The real measure of quality is
**validation**: does the hypothesis match the gene's true function, and does it beat
a naive "guess-from-the-name" baseline?

## How It Works

1. **Orchestrator** sends a research prompt to a multi-tier LLM system (Ollama cloud/local + Cerebras + Groq)
2. The LLM reasons about what to investigate next and outputs a tool call
3. The orchestrator parses and executes the tool (NCBI, UniProt, InterPro, STRING, HPA, ClinVar, AlphaFold, etc.)
4. Results are fed back to the LLM, which decides the next step
5. Discoveries are saved as persistent findings with evidence and quality scores
6. Repeat — the agent runs for as many cycles as you want

## Quick Start

**Requirements:** Python 3.10+, [Ollama](https://ollama.com/)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the agent
python main.py
```

### Usage

```bash
python main.py                              # Interactive mode (infinite cycles)
python main.py --target "BRCA1 mutations"   # Focus on a specific gene/topic
python main.py --cycles 50                  # Run exactly 50 cycles
python main.py --plan                       # Planning mode — suggest directions only
python main.py --lab-status                 # Show ML lab experiment history
python main.py --model qwen3.5:cloud        # Override LLM model
```

### Dashboard

A real-time web dashboard monitors the agent's progress:

```bash
python dashboard.py              # http://localhost:5555
python dashboard.py --port 8080  # Custom port
```

Shows live research status, gene pipeline progress, tool usage distribution, error timeline, sequence inventory, findings log, and more — all updating in real time.

## Project Structure

```
main.py                 — Entry point
config.py               — Paths, API URLs, model config
dashboard.py            — Flask web dashboard entry point

orchestrator/
├── core.py             — Main think→act→observe loop
├── llm.py              — 4-tier LLM provider system with auto-failover
├── providers.py        — OpenAI-compatible provider pattern (Cerebras/Groq)
├── prompts.py          — System prompts and reflection prompts
├── context.py          — Message compression and context trimming
├── loop_detection.py   — Loop detection and breaking
├── parsing.py          — Tool call parsing
└── dashboard.py        — Status writer for Flask

agent/
├── memory.py           — Persistent research memory (JSON-backed)
├── planner.py          — Research direction planner
├── evaluator.py        — Finding quality assessment
└── ui.py               — Color-coded terminal output

tools/
├── registry.py         — Tool registry and dispatch
├── findings.py         — Finding management (save, list, review)
├── scoring.py          — Quality scoring v2 (CNV/SNV aware)
├── gene_queue.py       — Dark genome gene discovery pipeline
├── gene_filters.py     — Pseudogene and low-quality filters
├── seed_discovery.py   — Seed family management for queue
├── ncbi.py             — NCBI GenBank/Gene/PubMed search & fetch
├── uniprot.py          — UniProt protein database queries
├── interpro.py         — InterPro domain analysis
├── string_db.py        — STRING protein interactions
├── hpa.py              — Human Protein Atlas expression
├── clinvar.py           — ClinVar pathogenic variants
├── alphafold.py        — AlphaFold structure predictions
├── semantic_scholar.py — Academic literature search
├── blast.py            — BLAST local/remote sequence search
├── sequence.py         — Local sequence analysis
├── lab_tools.py        — ML experiment launcher
├── memory_tools.py     — Memory queries and stats
└── file_tools.py       — File I/O utilities

lab/
├── trainer.py          — Autonomous ML experiment runner
└── train_genomics.py   — Genomic sequence model

dashboard/
├── data_layer.py       — Data access layer
└── log_parser.py       — Log parsing utilities

data/
├── sequences/          — Downloaded FASTA files
├── alignments/         — BLAST results
├── runs/               — ML experiment logs
└── checkpoints/        — Saved model weights

findings/               — 10,900+ markdown findings (one per gene)
```

## Tools (30+ functions)

### Database Queries
| Tool | Description |
|------|-------------|
| `ncbi_search` | Search GenBank, Gene, Nucleotide, Protein, PubMed |
| `ncbi_fetch` | Download FASTA sequences by accession ID |
| `gene_info` | Detailed gene metadata |
| `pubmed_search` | Search biomedical literature |
| `uniprot_search` | Find proteins by name/function/organism |
| `uniprot_fetch` | Download protein sequences & annotations |
| `interpro_scan` | Protein domains and families |
| `string_interactions` | Protein-protein interaction partners |
| `hpa_expression` | Tissue expression and localization |
| `clinvar_search` | Pathogenic variants and diseases |
| `alphafold_structure` | Predicted 3D structures |
| `gene_literature` | Check literature coverage |
| `semantic_search` | Search academic papers |

### Sequence Analysis
| Tool | Description |
|------|-------------|
| `analyze_sequence` | Composition, GC content, motif scanning |
| `compare_sequences` | Pairwise identity & composition diff |
| `translate_sequence` | DNA → protein translation |
| `blast_search` | BLAST (blastn, blastp, blastx, etc.) |

### Research Management
| Tool | Description |
|------|-------------|
| `save_finding` | Log a discovery with quality score |
| `review_findings` | AI-assisted finding review |
| `query_memory` | Search past findings & notes |
| `note` | Save free-form observations |
| `my_stats` | Agent usage statistics |

### Dark Genome Pipeline
| Tool | Description |
|------|-------------|
| `next_gene` | Get next understudied gene from queue |
| `skip_gene` | Skip if not a dark gene |
| `advance_seed` | Move to next seed family |
| `queue_status` | Show pipeline progress |

## Gene Queue Pipeline

The **Dark Genome Mission** systematically investigates understudied gene families:

- **C1orf–C22orf** — Chromosome-specific open reading frames
- **FAM genes** — "Family with sequence similarity" genes
- **KIAA genes** — Large-scale cDNA project, many uncharacterized
- **TMEM genes** — Transmembrane proteins with unknown function
- **LINC genes** — Long intergenic non-coding RNAs

Each gene goes through deep analysis using 6+ bioinformatics sources before a finding is produced.

## LLM Providers

GenoResearch runs on a **4-tier hybrid system** with automatic failover. Any tier
can be swapped for another model — the T1 slot is just wherever you put your best
LLM.

| Tier | Provider | Model (default) | When |
|------|----------|-----------------|------|
| T1 | Ollama (cloud) | `qwen3.5:cloud` | Best quality |
| T2 | Cerebras | `qwen-3-235b` | Fast, free tier |
| T3 | Groq | `llama-4-scout` | Backup, fast |
| T4 | Ollama (local) | `qwen3.5:4b` | Always available |

Zero downtime — the cascade falls through to the next tier on any failure.

### Run it anywhere — quality scales with the model

Nothing requires the cloud. Set `LLM_PROVIDER=ollama` and point
`OLLAMA_MODEL_PRIMARY` at any local model to run the whole pipeline **100%
offline**. The tools, queue, and scoring are identical across every model — **the
only thing that changes is the quality of the reasoning**, which scales directly
with the LLM you give it. A 4B local model keeps the sweep running on a laptop; a
frontier model (`qwen3.5`, `glm-5.2`, `deepseek-v4-pro`) produces sharper,
better-calibrated hypotheses. Measuring that trade-off precisely is exactly what
the bake-off in **[Status](#status-july-2026)** is for.

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_MODEL_PRIMARY` | `qwen3.5:cloud` | Primary LLM |
| `OLLAMA_MODEL_FALLBACK` | `qwen3.5:4b` | Fallback local LLM |
| `LLM_PROVIDER` | `hybrid` | Provider mode |
| `NCBI_API_KEY` | *(env var)* | Optional — higher NCBI rate limits |

## Optional Dependencies

The core agent only requires `requests` and `flask`:

```bash
# ML Lab (autonomous training)
pip install torch

# Enhanced sequence analysis
pip install biopython
```

## License

MIT
