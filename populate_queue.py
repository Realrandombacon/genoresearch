"""
Bulk populate the gene queue from multiple sources:
  1. Pharos/TCRD Tdark proteins (NIH Illuminating the Druggable Genome)
  2. NCBI uncharacterized/hypothetical gene searches
"""
import requests
import time
import re
import datetime
from tools.gene_queue import _load_queue, _save_queue
from tools.gene_filters import _is_pseudogene, _get_known_genes

q = _load_queue()
known = _get_known_genes(q)
# Also exclude genes already in the queue
known.update(g["gene"].upper() for g in q.get("queue", []))
print(f"Already known (completed/queued/skipped): {len(known)}")
print(f"Current queue size: {len(q['queue'])}")

today = datetime.date.today().isoformat()
new_genes = []


# ──────────────────────────────────────────────────────────────
# SOURCE 1: Pharos Tdark proteins (~5,500 understudied proteins)
# ──────────────────────────────────────────────────────────────
print("\n=== SOURCE 1: Pharos Tdark (NIH IDG) ===")
PHAROS_URL = "https://pharos-api.ncats.io/graphql"
BATCH_SIZE = 500

try:
    # Get total count
    count_query = '{ targets(filter: { facets: [{ facet: "Target Development Level", values: ["Tdark"] }] }) { count } }'
    r = requests.post(PHAROS_URL, json={"query": count_query}, timeout=30)
    total_tdark = r.json()["data"]["targets"]["count"]
    print(f"  Total Tdark in Pharos: {total_tdark}")

    pharos_added = 0
    for skip in range(0, total_tdark, BATCH_SIZE):
        query = (
            '{ targets(filter: { facets: [{ facet: "Target Development Level", values: ["Tdark"] }] }) '
            f'{{ targets(top: {BATCH_SIZE}, skip: {skip}) {{ sym uniprot tdl fam novelty description }} }} }}'
        )
        try:
            r = requests.post(PHAROS_URL, json={"query": query}, timeout=60)
            targets = r.json()["data"]["targets"]["targets"]
            for t in targets:
                sym = (t.get("sym") or "").strip()
                if not sym:
                    continue
                if sym.upper() in known:
                    continue
                desc = t.get("description") or ""
                if _is_pseudogene(sym, desc):
                    continue
                new_genes.append(sym)
                known.add(sym.upper())
                pharos_added += 1
        except Exception as e:
            print(f"  Pharos batch error at skip={skip}: {e}")
        time.sleep(0.3)
        if (skip // BATCH_SIZE) % 4 == 0:
            print(f"  Pharos: {skip}/{total_tdark} fetched, {pharos_added} new...")

    print(f"  Pharos done: {pharos_added} new Tdark genes added")

except Exception as e:
    print(f"  Pharos API error: {e}")
    pharos_added = 0


# ──────────────────────────────────────────────────────────────
# SOURCE 2: NCBI uncharacterized/hypothetical searches
# ──────────────────────────────────────────────────────────────
print("\n=== SOURCE 2: NCBI gene searches ===")
url_search = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
url_summary = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

queries = [
    ('"uncharacterized" AND "Homo sapiens"[Organism] AND alive[prop]', 5000),
    ('"hypothetical protein" AND "Homo sapiens"[Organism] AND alive[prop]', 2000),
    ('"family with sequence similarity" AND "Homo sapiens"[Organism] AND alive[prop]', 1000),
    ('"coiled-coil domain containing" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
    ('"transmembrane protein" AND "Homo sapiens"[Organism] AND alive[prop]', 1000),
    ('"zinc finger protein" AND "Homo sapiens"[Organism] AND alive[prop]', 1000),
    ('"leucine rich repeat" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
    ('"ankyrin repeat" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
    ('"spermatogenesis associated" AND "Homo sapiens"[Organism] AND alive[prop]', 200),
    ('"cilia and flagella" AND "Homo sapiens"[Organism] AND alive[prop]', 200),
    # New broader queries
    ('"WD repeat" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
    ('"RING finger" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
    ('"tetratricopeptide repeat" AND "Homo sapiens"[Organism] AND alive[prop]', 300),
    ('"EF-hand" AND "Homo sapiens"[Organism] AND alive[prop]', 300),
    ('"solute carrier" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
    ('"G protein-coupled receptor" AND "Homo sapiens"[Organism] AND alive[prop]', 500),
]

all_ids = set()
for query_str, retmax in queries:
    params = {"db": "gene", "term": query_str, "retmax": retmax, "retmode": "json"}
    try:
        resp = requests.get(url_search, params=params, timeout=60)
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        all_ids.update(ids)
        print(f"  {len(ids):>5} results: {query_str[:55]}...")
    except Exception as e:
        print(f"  Search error: {e}")
    time.sleep(0.4)

print(f"  Total unique NCBI IDs: {len(all_ids)}")

dark_patterns = re.compile(
    r"^(C\d+orf\d+|CXorf\d+|LOC\d+|FAM\d+[A-Z]?\d*|KIAA\d+|TMEM\d+[A-Z]?"
    r"|LINC\d+|FLJ\d+|CCDC\d+[A-Z]?|ANKRD\d+[A-Z]?|LRRC\d+[A-Z]?"
    r"|KLHL\d+|KBTBD\d+|SPATA\d+[A-Z]?|PRR\d+|PRAMEF\d+|ZNF\d+"
    r"|OR\d+[A-Z]\d*|CFAP\d+|ARMH\d+|TENT\d+|SMIM\d+|PLAC\d+"
    r"|DNAH\d+|DNAAF\d+|WDR\d+|KRTAP\d+|DRC\d+|TSPAN\d+"
    r"|GPR\d+|ABHD\d+|ADGR[A-Z]\d+|NBPF\d+|TEX\d+|RNF\d+|TRIM\d+"
    r"|SLC\d+[A-Z]\d*|PCDH[A-Z]?\d+|HIST\d+[A-Z]\d+|UGT\d+[A-Z]\d+"
    r"|CYP\d+[A-Z]\d+|KCNK?\d+|CACN[A-Z]\d+|SCN\d+[A-Z]?)$",
    re.IGNORECASE,
)

ncbi_added = 0
all_ids_list = list(all_ids)

for i in range(0, len(all_ids_list), 200):
    batch = all_ids_list[i : i + 200]
    params = {"db": "gene", "id": ",".join(batch), "retmode": "json"}
    try:
        resp = requests.get(url_summary, params=params, timeout=60)
        data = resp.json()
        for gene_id, info in data.get("result", {}).items():
            if gene_id == "uids":
                continue
            symbol = info.get("name", "").strip()
            desc = info.get("description", "")
            organism = info.get("organism", {}).get("scientificname", "")
            if not symbol or organism != "Homo sapiens":
                continue
            if symbol.upper() in known:
                continue
            if _is_pseudogene(symbol, desc):
                continue
            is_dark = bool(dark_patterns.match(symbol))
            is_unchar = any(
                w in desc.lower()
                for w in [
                    "uncharacterized",
                    "hypothetical",
                    "unknown function",
                    "open reading frame",
                ]
            )
            if is_dark or is_unchar:
                new_genes.append(symbol)
                known.add(symbol.upper())
                ncbi_added += 1
    except Exception as e:
        print(f"  Batch error: {e}")
    time.sleep(0.4)
    if (i // 200) % 10 == 0:
        print(f"  NCBI: {i + 200}/{len(all_ids_list)}, {ncbi_added} new...")

print(f"  NCBI done: {ncbi_added} new genes added")


# ──────────────────────────────────────────────────────────────
# Add all new genes to queue
# ──────────────────────────────────────────────────────────────
print(f"\n=== TOTAL NEW GENES: {len(new_genes)} ===")
print(f"  From Pharos Tdark: {pharos_added}")
print(f"  From NCBI searches: {ncbi_added}")

for g in new_genes:
    source = "pharos_tdark" if new_genes.index(g) < pharos_added else "ncbi_bulk_v3"
    q["queue"].append(
        {"gene": g, "source": source, "priority": "normal", "added_at": today}
    )

q["stats"]["genes_queued"] = len(q["queue"])
_save_queue(q)

print(f"\nQueue total: {len(q['queue'])} genes")
print(f"First 20: {[g['gene'] for g in q['queue'][:20]]}")
print(f"Last 20:  {[g['gene'] for g in q['queue'][-20:]]}")
