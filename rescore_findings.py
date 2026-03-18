"""
Batch re-score, deduplicate, and clean up findings.
Run once: python rescore_findings.py
"""
import os
import re
from collections import defaultdict

FINDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "findings")

# --- Scoring function (same as findings.py) ---
def compute_score(title, description, evidence=""):
    text = f"{title} {description} {evidence}".lower()
    score = 0
    if "clinvar" in text or "pathogenic" in text:
        score += 3
    if "interpro" in text or "pfam" in text or "duf" in text or "domain" in text:
        score += 2
    if "mouse" in text or "zebrafish" in text or "conserved" in text:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*identity", text)
        if m and float(m.group(1)) > 30:
            score += 2
        elif "conserved" in text:
            score += 1
    if "zero publications" in text or "0 pubmed" in text or "no publications" in text:
        score += 1
    if "string" in text or "interact" in text:
        score += 1
    if "hpa" in text or "tissue expression" in text or "protein atlas" in text:
        score += 1
    if "alphafold" in text or "plddt" in text:
        score += 1
    if "disease" in text or "cancer" in text or "syndrome" in text:
        score += 1
    if len(description) < 100:
        score = max(0, score - 2)
    return min(10, score)


GENE_PAT = re.compile(r"\b(LOC\d+|C\d+orf\d+|[A-Z][A-Z0-9]{1,10}(?:_[A-Z0-9]+)?)\b")

def extract_gene(title):
    m = GENE_PAT.search(title)
    if m:
        return m.group(1).upper()
    first = title.split()[0] if title.split() else ""
    if first.isupper() and 2 <= len(first) <= 15:
        return first
    return ""


def main():
    findings = []
    for fname in os.listdir(FINDINGS_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(FINDINGS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        title = fname.replace(".md", "")
        title_match = re.search(r"^#\s+(.+)", content)
        if title_match:
            title = title_match.group(1).strip()

        has_score = bool(re.search(r"\*\*Quality Score:\*\*", content))

        desc_match = re.search(r"## Description\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else content

        ev_match = re.search(r"## Evidence\n```\n(.*?)```", content, re.DOTALL)
        evidence = ev_match.group(1).strip() if ev_match else ""

        score = compute_score(title, description, evidence)
        gene = extract_gene(title)

        findings.append({
            "fname": fname,
            "fpath": fpath,
            "title": title,
            "gene": gene,
            "score": score,
            "has_score": has_score,
            "content": content,
            "description": description,
            "evidence": evidence,
            "size": len(content),
        })

    print(f"Total findings: {len(findings)}")

    # --- Deduplicate by gene (keep highest score, then longest) ---
    gene_groups = defaultdict(list)
    for f in findings:
        if f["gene"]:
            gene_groups[f["gene"]].append(f)

    dupes_removed = 0
    to_delete = set()
    for gene, group in gene_groups.items():
        if len(group) > 1:
            group.sort(key=lambda x: (x["score"], x["size"]), reverse=True)
            keeper = group[0]
            for dup in group[1:]:
                to_delete.add(dup["fpath"])
                dupes_removed += 1
                print(f"  DUPE: {dup['fname']} (score={dup['score']}) -> keeping {keeper['fname']} (score={keeper['score']})")

    # --- Score breakdown before cleanup ---
    active = [f for f in findings if f["fpath"] not in to_delete]
    excellent = sum(1 for f in active if f["score"] >= 8)
    good = sum(1 for f in active if 5 <= f["score"] < 8)
    moderate = sum(1 for f in active if 3 <= f["score"] < 5)
    low = sum(1 for f in active if f["score"] < 3)
    print("\nScore breakdown (after dedup, before LOW cleanup):")
    print(f"  EXCELLENT (8-10): {excellent}")
    print(f"  GOOD (5-7):       {good}")
    print(f"  MODERATE (3-4):   {moderate}")
    print(f"  LOW (0-2):        {low}")

    # --- Delete dupes and LOW quality ---
    low_removed = 0
    scored_count = 0
    for f in findings:
        if f["fpath"] in to_delete:
            os.remove(f["fpath"])
            print(f"  DELETED DUPE: {f['fname']}")
            continue

        if f["score"] < 3:
            os.remove(f["fpath"])
            low_removed += 1
            print(f"  LOW REMOVED: {f['fname']} (score={f['score']})")
            continue

        # --- Add score to unscored findings ---
        if not f["has_score"]:
            score_label = (
                "EXCELLENT" if f["score"] >= 8
                else "GOOD" if f["score"] >= 5
                else "MODERATE" if f["score"] >= 3
                else "LOW"
            )
            score_line = f"**Quality Score:** {f['score']}/10 ({score_label})\n\n"

            content = f["content"]
            date_match = re.search(r"(\*\*Date:\*\*.+?\n\n)", content)
            if date_match:
                pos = date_match.end()
                new_content = content[:pos] + score_line + content[pos:]
            else:
                heading_match = re.search(r"(#.+?\n\n)", content)
                if heading_match:
                    pos = heading_match.end()
                    new_content = content[:pos] + score_line + content[pos:]
                else:
                    new_content = score_line + content

            with open(f["fpath"], "w", encoding="utf-8") as fh:
                fh.write(new_content)
            scored_count += 1

    remaining = len(findings) - dupes_removed - low_removed
    print("\n--- SUMMARY ---")
    print(f"Duplicates removed: {dupes_removed}")
    print(f"LOW quality removed: {low_removed}")
    print(f"Newly scored: {scored_count}")
    print(f"Remaining findings: {remaining}")


if __name__ == "__main__":
    main()
