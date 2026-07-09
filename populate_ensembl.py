"""Save the 47k genes we already found — just re-run the 2 working queries."""
import requests
import time
import datetime
from tools.gene_queue import _load_queue, _save_queue
from tools.gene_filters import _is_pseudogene, _get_known_genes

q = _load_queue()
known = _get_known_genes(q)
known.update(g["gene"].upper() for g in q.get("queue", []))
print(f"Already known: {len(known)}")
print(f"Current queue size: {len(q['queue'])}")

today = datetime.date.today().isoformat()
new_genes = []

# Query 1: protein_coding, no GO
print("\n=== BioMart: protein_coding, no GO ===")
xml1 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query virtualSchemaName="default" formatter="TSV" header="1" uniqueRows="1" count="" datasetConfigVersion="0.6">
<Dataset name="hsapiens_gene_ensembl" interface="default">
<Filter name="biotype" value="protein_coding"/>
<Filter name="with_go" excluded="1"/>
<Attribute name="ensembl_gene_id"/>
<Attribute name="hgnc_symbol"/>
<Attribute name="description"/>
</Dataset>
</Query>'''

try:
    r1 = requests.post("http://www.ensembl.org/biomart/martservice", data={"query": xml1}, timeout=300)
    lines1 = r1.text.strip().split("\n")[1:]
    print(f"Got {len(lines1)} protein_coding genes with no GO")
    added1 = 0
    for line in lines1:
        cols = line.split("\t")
        ensembl_id = cols[0].strip()
        symbol = cols[1].strip() if len(cols) > 1 else ""
        desc = cols[2].strip() if len(cols) > 2 else ""
        gene_id = symbol if symbol else ensembl_id
        if not gene_id or gene_id.upper() in known:
            continue
        if _is_pseudogene(gene_id, desc):
            continue
        new_genes.append({"gene": gene_id, "source": "ensembl_biomart_pc_no_go", "priority": "normal", "added_at": today, "ensembl_id": ensembl_id})
        known.add(gene_id.upper())
        added1 += 1
    print(f"  {added1} new")
except Exception as e:
    print(f"  Error: {e}")

# Save incrementally after first query
if new_genes:
    for entry in new_genes:
        q["queue"].append(entry)
    q["stats"]["genes_queued"] = len(q["queue"])
    _save_queue(q)
    print(f"  [SAVED] Queue now: {len(q['queue'])} genes")

time.sleep(2)

# Query 2: lncRNA, no GO
print("\n=== BioMart: lncRNA, no GO ===")
xml2 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query virtualSchemaName="default" formatter="TSV" header="1" uniqueRows="1" count="" datasetConfigVersion="0.6">
<Dataset name="hsapiens_gene_ensembl" interface="default">
<Filter name="biotype" value="lncRNA"/>
<Filter name="with_go" excluded="1"/>
<Attribute name="ensembl_gene_id"/>
<Attribute name="hgnc_symbol"/>
<Attribute name="description"/>
</Dataset>
</Query>'''

new_genes2 = []
try:
    r2 = requests.post("http://www.ensembl.org/biomart/martservice", data={"query": xml2}, timeout=300)
    lines2 = r2.text.strip().split("\n")[1:]
    print(f"Got {len(lines2)} lncRNA genes with no GO")
    added2 = 0
    for line in lines2:
        cols = line.split("\t")
        ensembl_id = cols[0].strip()
        symbol = cols[1].strip() if len(cols) > 1 else ""
        desc = cols[2].strip() if len(cols) > 2 else ""
        gene_id = symbol if symbol else ensembl_id
        if not gene_id or gene_id.upper() in known:
            continue
        if _is_pseudogene(gene_id, desc):
            continue
        new_genes2.append({"gene": gene_id, "source": "ensembl_biomart_lncrna_no_go", "priority": "low", "added_at": today, "ensembl_id": ensembl_id})
        known.add(gene_id.upper())
        added2 += 1
    print(f"  {added2} new")
except Exception as e:
    print(f"  Error: {e}")

# Save second batch
if new_genes2:
    q = _load_queue()  # re-load in case first save was on different state
    for entry in new_genes2:
        q["queue"].append(entry)
    q["stats"]["genes_queued"] = len(q["queue"])
    _save_queue(q)
    print(f"  [SAVED] Queue now: {len(q['queue'])} genes")

print(f"\n=== TOTAL: {len(new_genes)} pc + {len(new_genes2)} lncRNA = {len(new_genes)+len(new_genes2)} new genes ===")