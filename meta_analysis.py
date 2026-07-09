"""Meta-analysis of all GenoResearch findings — cross-gene pattern discovery."""
import os, re, json, sys
from itertools import combinations
from collections import Counter

FINDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "findings")

score_re = re.compile(r'\*\*Quality Score:\*\*\s*(\d+)/10')
ntpm_re = re.compile(r'(\d+\.?\d*)\s*ntpm', re.IGNORECASE)
aa_re = re.compile(r'(\d+)\s*(?:amino acid|aa)\b', re.IGNORECASE)
chrom_re = re.compile(r'chromosome\s+(\w+)', re.IGNORECASE)
duf_re = re.compile(r'(DUF\d+)', re.IGNORECASE)
plddt_re = re.compile(r'pLDDT[:\s]*(\d+\.?\d*)', re.IGNORECASE)

tissues = {
    'brain': r'brain.enriched|brain.specific|brain.enhanced',
    'testis': r'testis.enriched|testis.specific|spermat',
    'liver': r'liver.enriched|liver.specific|hepat',
    'kidney': r'kidney.enriched|kidney.specific|renal',
    'cancer': r'cancer.enriched|cancer.enhanced|tumor',
    'immune': r'immune|lymph|macrophage|t.cell|b.cell',
    'muscle': r'muscle|cardiac|heart',
    'ubiquitous': r'ubiquitous|housekeeping|broadly expressed',
}

features = {
    'transmembrane': r'transmembrane|membrane protein|single.pass|multi.pass',
    'disordered': r'intrinsically disordered|idr|low complexity',
    'secreted': r'secreted|extracellular|signal peptide',
    'nuclear': r'nuclear|nucleoplasm|nucleol|chromatin',
    'mitochondrial': r'mitochond',
    'ciliary': r'cilia|flagell|axoneme|basal body',
    'coiled_coil': r'coiled.coil|leucine zipper',
    'zinc_finger': r'zinc finger|c2h2|krab',
}

disease_kw = {
    'pathogenic_cnv': r'pathogenic.*?variant|clinvar.*?pathogenic',
    'dosage_sensitive': r'dosage.sensitive|haploinsuffici',
    'neurological': r'schizophren|alzheimer|parkinson|epilep|autism|intellectual disability',
    'fertility': r'infertil|azoosperm|oligosperm',
}

all_data = []
for fname in os.listdir(FINDINGS_DIR):
    if not fname.endswith('.md'):
        continue
    try:
        with open(os.path.join(FINDINGS_DIR, fname), 'r', encoding='utf-8') as f:
            content = f.read()
        text = content.lower()
        title = fname.replace('.md', '')

        m = score_re.search(content)
        score = int(m.group(1)) if m else 0

        aa_match = aa_re.search(content)
        size = int(aa_match.group(1)) if aa_match else 0

        plddt_match = plddt_re.search(content)
        plddt = float(plddt_match.group(1)) if plddt_match else -1

        dufs = list(set(d.upper() for d in duf_re.findall(content)))

        chrom_match = chrom_re.search(content)
        chrom = chrom_match.group(1) if chrom_match else ''

        tissue_hits = [t for t, p in tissues.items() if re.search(p, text)]
        feat_hits = [f for f, p in features.items() if re.search(p, text)]
        disease_hits = [d for d, p in disease_kw.items() if re.search(p, text)]

        ntpm_vals = [float(x) for x in ntpm_re.findall(content)]
        max_ntpm = max(ntpm_vals) if ntpm_vals else 0

        all_data.append({
            'title': title, 'score': score, 'size': size,
            'plddt': plddt, 'dufs': dufs, 'chrom': chrom,
            'tissues': tissue_hits, 'features': feat_hits,
            'diseases': disease_hits, 'max_ntpm': max_ntpm,
        })
    except Exception:
        pass

print("Extracted {} findings".format(len(all_data)))
print()

# === PATTERN 1: Tissue co-occurrence ===
print("=== PATTERN 1: TISSUE CO-OCCURRENCE ===")
tissue_pairs = Counter()
for d in all_data:
    for t1, t2 in combinations(sorted(d['tissues']), 2):
        tissue_pairs[t1 + " + " + t2] += 1
for k, v in tissue_pairs.most_common(15):
    print("  {:35s}: {:4d} findings".format(k, v))

# === PATTERN 2: Size vs disorder ===
print()
print("=== PATTERN 2: PROTEIN SIZE vs DISORDER ===")
bins = [('tiny (<100aa)', 0, 100), ('small (100-300)', 100, 300),
        ('medium (300-600)', 300, 600), ('large (600+)', 600, 99999)]
for label, lo, hi in bins:
    items = [d for d in all_data if lo <= d['size'] < hi and d['size'] > 0]
    if not items:
        continue
    disordered = sum(1 for i in items if 'disordered' in i['features'])
    pct = disordered / len(items) * 100
    avg_score = sum(i['score'] for i in items) / len(items)
    plddt_vals = [i['plddt'] for i in items if i['plddt'] > 0]
    avg_p = sum(plddt_vals) / len(plddt_vals) if plddt_vals else 0
    print("  {:20s}: {:4d} genes | {:.0f}% disordered | avg score {:.1f} | avg pLDDT {:.1f}".format(
        label, len(items), pct, avg_score, avg_p))

# === PATTERN 3: DUF frequency ===
print()
print("=== PATTERN 3: MOST COMMON DUFs ===")
duf_count = Counter()
for d in all_data:
    for duf in d['dufs']:
        duf_count[duf] += 1
for k, v in duf_count.most_common(20):
    print("  {:12s}: {:3d} genes".format(k, v))

# === PATTERN 4: Feature x Tissue matrix ===
print()
print("=== PATTERN 4: FEATURE x TISSUE MATRIX ===")
t_list = ['brain', 'testis', 'cancer', 'immune', 'liver']
f_list = ['transmembrane', 'disordered', 'secreted', 'nuclear', 'mitochondrial', 'ciliary', 'coiled_coil', 'zinc_finger']
header = "{:20s}".format("") + "".join("{:>8s}".format(t) for t in t_list)
print(header)
for feat in f_list:
    row = "{:20s}".format(feat)
    for t in t_list:
        count = sum(1 for d in all_data if feat in d['features'] and t in d['tissues'])
        row += "{:8d}".format(count)
    print(row)

# === PATTERN 5: Disease hotspots ===
print()
print("=== PATTERN 5: DISEASE-ASSOCIATED DARK GENES BY CHROMOSOME ===")
chrom_disease = Counter()
chrom_total = Counter()
for d in all_data:
    c = d['chrom'][:2] if d['chrom'] else ''
    if not c:
        continue
    chrom_total[c] += 1
    if d['diseases']:
        chrom_disease[c] += 1
for k, v in chrom_disease.most_common(15):
    total = chrom_total[k]
    pct = v / total * 100 if total else 0
    print("  chr{:3s}: {:3d}/{:3d} disease-associated ({:.0f}%)".format(k, v, total, pct))

# === PATTERN 6: Brain+testis dual ===
print()
print("=== PATTERN 6: BRAIN+TESTIS DUAL EXPRESSION ===")
bt = [d for d in all_data if 'brain' in d['tissues'] and 'testis' in d['tissues']]
print("  {} genes expressed in BOTH brain and testis".format(len(bt)))
if bt:
    bt_dis = sum(1 for d in bt if 'disordered' in d['features'])
    bt_cilia = sum(1 for d in bt if 'ciliary' in d['features'])
    bt_disease = sum(1 for d in bt if d['diseases'])
    print("  {}% intrinsically disordered".format(round(bt_dis / len(bt) * 100)))
    print("  {}% ciliary-associated".format(round(bt_cilia / len(bt) * 100)))
    print("  {}% disease-associated".format(round(bt_disease / len(bt) * 100)))
    print("  Average score: {:.1f}".format(sum(d['score'] for d in bt) / len(bt)))
    print("  Examples:")
    for d in sorted(bt, key=lambda x: -x['score'])[:10]:
        print("    [{}/10] {}".format(d['score'], d['title'][:60]))

# === PATTERN 7: Disordered + disease ===
print()
print("=== PATTERN 7: DISORDER vs DISEASE ASSOCIATION ===")
has_struct = [d for d in all_data if d['plddt'] > 0]
if has_struct:
    ordered = [d for d in has_struct if d['plddt'] >= 70]
    disordered = [d for d in has_struct if d['plddt'] < 50]
    mid = [d for d in has_struct if 50 <= d['plddt'] < 70]
    for label, group in [('Ordered (pLDDT>=70)', ordered), ('Partial (50-70)', mid), ('Disordered (pLDDT<50)', disordered)]:
        if not group:
            continue
        dis_pct = sum(1 for d in group if d['diseases']) / len(group) * 100
        brain_pct = sum(1 for d in group if 'brain' in d['tissues']) / len(group) * 100
        testis_pct = sum(1 for d in group if 'testis' in d['tissues']) / len(group) * 100
        print("  {:25s}: {:4d} genes | {:.0f}% disease | {:.0f}% brain | {:.0f}% testis".format(
            label, len(group), dis_pct, brain_pct, testis_pct))

# === PATTERN 8: Small proteins (<150aa) cluster ===
print()
print("=== PATTERN 8: MICROPROTEINS (<150aa) ANALYSIS ===")
micro = [d for d in all_data if 0 < d['size'] < 150]
regular = [d for d in all_data if d['size'] >= 150]
if micro and regular:
    print("  Microproteins: {} genes".format(len(micro)))
    print("  Regular proteins: {} genes".format(len(regular)))
    for label, group in [('Micro (<150aa)', micro), ('Regular (150+)', regular)]:
        brain_pct = sum(1 for d in group if 'brain' in d['tissues']) / len(group) * 100
        membrane_pct = sum(1 for d in group if 'transmembrane' in d['features']) / len(group) * 100
        dis_pct = sum(1 for d in group if d['diseases']) / len(group) * 100
        secreted_pct = sum(1 for d in group if 'secreted' in d['features']) / len(group) * 100
        print("  {:20s}: {:.0f}% brain | {:.0f}% membrane | {:.0f}% secreted | {:.0f}% disease".format(
            label, brain_pct, membrane_pct, secreted_pct, dis_pct))
