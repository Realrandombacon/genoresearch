"""
Batch re-score findings with dual-axis (E + D) scoring.
Writes updated Quality Score lines back into each finding file.
"""
import os
import re
import sys
from collections import Counter

root = r'C:\Users\bacoo\OneDrive\Bureau\Genoresearch'
sys.path.insert(0, root)

from tools.scoring import compute_dual_score

FINDINGS_DIR = os.path.join(root, "findings")

# Regex to match old score line
OLD_SCORE_RE = re.compile(
    r'\*\*Quality Score:\*\*\s*\d+/10\s*\([^)]*\)',
    re.IGNORECASE
)


def rescore_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as fh:
        content = fh.read()

    # Extract title = first H1 line
    lines = content.split('\n')
    title = lines[0].lstrip('#').strip() if lines else ""
    if not title:
        title = os.path.basename(path).replace('.md', '')

    # Compute dual score
    result = compute_dual_score(title, content, evidence="")
    label = result['label']

    # Replace old score line or inject after first header block
    if OLD_SCORE_RE.search(content):
        new_content = OLD_SCORE_RE.sub(f'**Quality Score:** {label}', content, count=1)
    else:
        # Try to inject after "**Confidence:**" line or first blank line after title
        if '**Date:**' in content and '\n\n**Date:**' in content:
            # Replace everything between first blank line and ## Description
            # Just prepend the score after the header block
            parts = content.split('\n\n', 1)
            if len(parts) == 2:
                new_content = parts[0] + f'\n\n**Quality Score:** {label}\n\n' + parts[1]
            else:
                new_content = content
        else:
            new_content = content

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(new_content)

    return result


def main():
    all_files = sorted(
        [f for f in os.listdir(FINDINGS_DIR) if f.endswith('.md')],
        key=lambda x: os.path.getmtime(os.path.join(FINDINGS_DIR, x)),
        reverse=True
    )
    print(f"Total .md findings: {len(all_files)}")
    
    # Option: focus on last 200 for now, then scale
    TARGET = 200
    batch = all_files[:TARGET]
    print(f"Re-scoring last {len(batch)} files (most recent by mtime)...")

    tier_counts = Counter()
    composite_scores = []

    for i, fname in enumerate(batch, 1):
        path = os.path.join(FINDINGS_DIR, fname)
        try:
            result = rescore_file(path)
            tier_counts[result['tier']] += 1
            composite_scores.append(result['composite'])
            if i <= 5:
                print(f"  [{i}] {fname[:50]:50s} → {result['label']}")
        except Exception as e:
            print(f"  [{i}] ERROR {fname}: {e}")

    print("\n--- RESULTS ---")
    print(f"Processed: {len(composite_scores)}")
    print(f"Composite range: {min(composite_scores):.2f} to {max(composite_scores):.2f}")
    print(f"Avg composite: {sum(composite_scores)/len(composite_scores):.2f}")
    print("\nTier distribution:")
    total = sum(tier_counts.values())
    for tier in ['EXCEPTIONAL', 'STRONG', 'SOLID', 'MODERATE', 'WEAK', 'POOR']:
        count = tier_counts.get(tier, 0)
        pct = count / total * 100 if total else 0
        bar = '#' * int(round(pct / 2))
        print(f"  {tier:12s}: {count:4d} ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()