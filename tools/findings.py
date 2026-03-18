"""
Findings tool — log and retrieve research findings.
Writes to both memory and TSV file.
"""

import os
import csv
import re
import datetime
import logging

from config import FINDINGS_FILE, FINDINGS_DIR
from agent.memory import load_memory, save_memory, add_finding

log = logging.getLogger("genoresearch.findings")

# Common gene name patterns: LOC\d+, C\d+orf\d+, BRCA1, TP53, etc.
_GENE_PATTERN = re.compile(
    r'\b(LOC\d+|C\d+orf\d+|[A-Z][A-Z0-9]{1,10}(?:_[A-Z0-9]+)?)\b'
)


def _compute_score(title: str, description: str, evidence: str) -> int:
    """Compute a quality score (0-10) based on 3 dimensions:
    - COVERAGE (0-5): how many independent data sources were consulted
    - DEPTH (0-3): richness of actual data (not just keyword mentions)
    - INSIGHT (0-3): quality of reasoning, hypothesis, and interpretation

    A finding with 4+ sources, rich data, and a mechanistic hypothesis
    should naturally reach 9-10. Honest triage ("not a dark gene") is
    also valued — good science includes knowing what to skip.
    """
    text = f"{title} {description} {evidence}".lower()
    full_text = f"{title} {description} {evidence}"

    # ===== DIMENSION 1: COVERAGE (0-4) =====
    # Credit for each independent data source with ACTUAL data (not just mention)
    sources = 0

    # InterPro/Pfam — must have accession or domain description
    if re.search(r'IPR\d+|PF\d+|DUF\d+|UPF\d+', full_text):
        sources += 1
    elif re.search(r'(domain|repeat|fold)\s+(of|in|spanning|residue)', text):
        sources += 1

    # STRING — must have interaction partner name or score
    if re.search(r'(string|interact\w*).{0,80}(0\.\d+|\w{3,15}\s)', text):
        sources += 1

    # HPA/tissue expression — must have tissue name or nTPM value
    if re.search(r'\d+\.?\d*\s*ntpm|enriched|specific.{0,30}(brain|testis|liver|kidney|heart|lung|intestin|muscle|ovary|retina|fallopian|pituitary|adipose|spleen|thyroid|placenta|bone marrow)', text):
        sources += 1

    # AlphaFold — must have pLDDT score
    if re.search(r'plddt\s*[=:]?\s*\d+|alphafold.{0,40}\d+\.?\d*', text):
        sources += 1

    # ClinVar — must have variant count or specific classification
    clinvar_match = re.search(r'(\d+)\s*(pathogenic|clinvar|variant)', text)
    if clinvar_match and int(clinvar_match.group(1)) > 0:
        sources += 1

    # Conservation/BLAST — must have % identity or species comparison
    if re.search(r'\d+\.?\d*\s*%\s*(identity|identical|conserv)', text):
        sources += 1

    # UniProt — must have accession
    if re.search(r'[A-Z]\d[A-Z0-9]{3}\d|uniprot', text):
        sources += 0.5

    coverage = min(5.0, sources)

    # ===== DIMENSION 2: DEPTH (0-3) =====
    # How much actual data and detail is present
    depth = 0.0

    # Content length — count description + evidence (Qwen often puts data in evidence)
    total_content_len = len(description) + len(evidence)
    if total_content_len >= 800:
        depth += 1.0
    elif total_content_len >= 400:
        depth += 0.7
    elif total_content_len >= 200:
        depth += 0.4
    elif total_content_len >= 100:
        depth += 0.2

    # Quantitative data points (numbers in context = real data)
    numbers_in_context = re.findall(r'\d+\.?\d*\s*(?:aa|kda|ntpm|%|residue|variant|interaction|score)', text)
    depth += min(1.0, len(numbers_in_context) * 0.2)

    # Named protein/gene interactions (real biology, not just tool names)
    named_entities = re.findall(r'\b[A-Z][A-Z0-9]{2,10}\b', full_text)
    # Filter out tool names and common words
    tool_words = {'TOOL', 'INFO', 'WARN', 'ERROR', 'THE', 'AND', 'FOR', 'WITH',
                  'DARK', 'GENE', 'TRUE', 'NOT', 'HPA', 'STRING', 'BLAST',
                  'NCBI', 'INTERPRO', 'ALPHAFOLD', 'CLINVAR', 'UNIPROT',
                  'DUF', 'UPF', 'IPR', 'PFAM', 'DESCRIPTION', 'EVIDENCE',
                  'QUALITY', 'SCORE', 'DATE', 'MODERATE', 'EXCELLENT', 'GOOD', 'LOW'}
    bio_entities = [e for e in set(named_entities) if e not in tool_words and len(e) >= 3]
    depth += min(1.0, len(bio_entities) * 0.1)

    depth = min(3.0, depth)

    # ===== DIMENSION 3: INSIGHT (0-3) =====
    # Quality of reasoning and hypothesis
    insight = 0.0

    # Has a functional hypothesis or mechanistic proposal
    hypothesis_patterns = [
        r'suggest\w*|hypothes\w*|propos\w*|predict\w*|implic\w*',
        r'likely\s+\w+|may\s+function|could\s+serve|potentially',
        r'regulator|scaffold|transporter|receptor|enzyme|kinase|ligase',
        r'pathway|signaling|metabolism|trafficking|assembly',
    ]
    for pattern in hypothesis_patterns:
        if re.search(pattern, text):
            insight += 0.4

    # Correctly identifies gene status (dark vs characterized)
    if re.search(r'not\s+a\s+(true\s+)?dark\s+gene|well.?characteriz|resolved|renamed', text):
        insight += 0.8  # Honest assessment is valuable

    # Cross-domain reasoning (linking structure to function, expression to disease, etc.)
    domains_mentioned = set()
    for domain_type, patterns in {
        'structure': [r'domain|fold|repeat|helix|sheet|coil|disorder'],
        'function': [r'transport|signal|cataly|bind|regulat|modif'],
        'location': [r'mitochond|golgi|nucleus|membrane|cilia|vesicle|centrosome|cytoplasm'],
        'disease': [r'cancer|disease|syndrome|pathogen|clinical|dosage'],
        'expression': [r'enriched|specific|ubiquitous|expressed|ntpm'],
    }.items():
        for p in patterns:
            if re.search(p, text):
                domains_mentioned.add(domain_type)
                break
    if len(domains_mentioned) >= 3:
        insight += 0.5
    if len(domains_mentioned) >= 4:
        insight += 0.3

    # Penalize empty/vacuous findings
    vacuous_phrases = ['no data', 'no evidence', 'no information available',
                       'could not determine', 'unknown function']
    vacuous_count = sum(1 for p in vacuous_phrases if p in text)
    if vacuous_count >= 2:
        insight = max(0, insight - 0.5)

    insight = min(3.0, insight)

    # ===== FINAL SCORE =====
    raw = coverage + depth + insight
    # Round to nearest integer, clamp 0-10
    return max(0, min(10, round(raw)))


def _extract_gene_from_title(title: str) -> str:
    """Extract the most likely gene name from a finding title.
    Returns empty string if no gene pattern found."""
    # Check common patterns
    m = _GENE_PATTERN.search(title)
    if m:
        return m.group(1).upper()
    # Fallback: first word if it looks gene-like (all caps, 2-15 chars)
    first_word = title.split()[0] if title.split() else ""
    if first_word.isupper() and 2 <= len(first_word) <= 15:
        return first_word
    return ""


def save_finding(*args, title: str = "", description: str = "",
                  evidence: str = "", **kwargs) -> str:
    """
    Log a research finding to memory and TSV.

    Args:
        title: Short title for the finding
        description: Detailed description
        evidence: Supporting evidence (tool output, accession IDs, etc.)
    """
    # Qwen sometimes passes: save_finding('filename.txt', title='...', description='...')
    # or save_finding('title', 'description', 'evidence') positionally.
    # Handle both gracefully.
    if args:
        if not title and len(args) >= 1:
            # First positional could be a filename (ignore) or the actual title
            candidate = str(args[0])
            if candidate.endswith(('.txt', '.md', '.json', '.csv')):
                # It's a filename — skip it, use kwargs
                pass
            else:
                title = candidate
        if not description and len(args) >= 2:
            description = str(args[1])
        if not evidence and len(args) >= 3:
            evidence = str(args[2])
    # Also absorb any unexpected kwargs Qwen invents (content=, query=, etc.)
    if not title:
        for key in ("query", "name", "finding", "topic", "subject", "text", "summary"):
            if key in kwargs:
                title = str(kwargs[key])
                break
    if not description:
        for key in ("content", "details", "result", "findings", "info", "data", "body"):
            if key in kwargs:
                description = str(kwargs[key])
                break
    if not evidence:
        for key in ("source", "reference", "ref", "pmid", "accession"):
            if key in kwargs:
                evidence = str(kwargs[key])
                break
    if not title:
        title = "Untitled Finding"

    # --- Quality guards ---

    title_lower = title.lower()

    # 0. Block meta/status findings: these are NOT research discoveries
    meta_phrases = [
        "project complete", "project termination", "terminal state",
        "mission accomplished", "mission complete", "no remaining",
        "queue exhausted", "all dark genes", "verified completion",
        "workflow summary", "session acknowledgment", "termination notice",
        "dark genome complete", "dark genome project",
        "termination certificate", "completion certificate",
        "completion summary", "final summary", "final state",
    ]
    for phrase in meta_phrases:
        if phrase in title_lower:
            return (
                f"[REJECTED] '{title}' is a status/meta message, not a research finding. "
                "Findings must be about SPECIFIC GENES — not project status. "
                "The project is NOT complete. Call next_gene() to continue research."
            )

    # 1. Block error-as-finding: operational errors are not discoveries
    error_phrases = ["file not found", "timed out", "error", "not found"]
    for phrase in error_phrases:
        if phrase in title_lower:
            return (
                f"[REJECTED] '{title}' looks like an operational error, not a research finding. "
                "Do not log errors as findings — fix the issue and retry the tool."
            )

    # 2. Minimum content check
    if not description or len(description.strip()) < 20:
        return (
            "[REJECTED] Finding description is too short (minimum 20 characters). "
            "Please provide a meaningful description of the discovery."
        )

    # 3. Gene-level consolidation: ONE finding per gene.
    #    If findings for the same gene already exist, DELETE ALL of them
    #    and replace with the new (presumably richer) version.
    existing_files_to_remove = []
    if os.path.isdir(FINDINGS_DIR):
        title_gene = _extract_gene_from_title(title)
        if title_gene:
            for fname in os.listdir(FINDINGS_DIR):
                if fname.endswith(".md"):
                    existing_gene = _extract_gene_from_title(fname.replace(".md", ""))
                    if existing_gene and existing_gene == title_gene:
                        existing_files_to_remove.append(
                            os.path.join(FINDINGS_DIR, fname)
                        )
            if existing_files_to_remove:
                log.info("Consolidating %s: removing %d old file(s)",
                         title_gene, len(existing_files_to_remove))

    # 4. Plausibility warning for low-identity claims between gene variants
    warning_prefix = ""
    identity_match = re.search(
        r'(\d+(?:\.\d+)?)\s*%?\s*identity', description.lower()
    )
    if identity_match:
        pct = float(identity_match.group(1))
        # Normalize: if value looks like a fraction (0.XX) treat as percentage
        if pct < 1.0:
            pct = pct * 100
        if pct < 40 and re.search(r'variant|transcript|isoform', description.lower()):
            warning_prefix = (
                "WARNING: This finding reports <40% identity between variants of "
                "the same gene. This is near random chance for nucleotides and "
                "likely a tool artifact (unaligned comparison). Verify with proper "
                "alignment before trusting this result.\n\n"
            )
            description = warning_prefix + description

    ts = datetime.datetime.now().isoformat()

    # Save to memory
    memory = load_memory()
    add_finding(memory, title, description, evidence)
    save_memory(memory)

    # Append to TSV
    file_exists = os.path.exists(FINDINGS_FILE)
    with open(FINDINGS_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        if not file_exists:
            writer.writerow(["timestamp", "title", "description", "evidence"])
        writer.writerow([ts, title, description[:500], evidence[:500]])

    # Remove ALL old finding files for the same gene (consolidation)
    for old_file in existing_files_to_remove:
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
                log.info("Removed old finding: %s", old_file)
            except Exception as e:
                log.warning("Could not remove old finding: %s", e)

    # Save detailed finding as individual file
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60]
    detail_path = os.path.join(FINDINGS_DIR, f"{safe_title}.md")
    # Auto-score the finding based on evidence richness
    score = _compute_score(title, description, evidence)
    score_label = (
        "EXCELLENT" if score >= 8 else
        "GOOD" if score >= 5 else
        "MODERATE" if score >= 3 else
        "LOW"
    )

    with open(detail_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Date:** {ts}\n\n")
        f.write(f"**Quality Score:** {score}/10 ({score_label})\n\n")
        f.write(f"## Description\n{description}\n\n")
        if evidence:
            f.write(f"## Evidence\n```\n{evidence}\n```\n")

    log.info("Finding saved: %s [score=%d/%d]", title, score, 10)

    # Auto-complete the gene in the queue so dashboard stays in sync
    # Done IN-PLACE to avoid race condition: complete_gene() reloads the file
    # which can overwrite genes added by add_to_queue() in the same cycle.
    gene_name = _extract_gene_from_title(title)
    try:
        from tools.gene_queue import _load_queue, _save_queue
        import datetime as _dt
        if gene_name:
            q = _load_queue()
            if q.get("in_progress") and q["in_progress"]["gene"].upper() == gene_name.upper():
                # Current gene — move to completed
                gene_data = q["in_progress"]
                gene_data["finished"] = _dt.datetime.now().isoformat()
                q["completed"].append(gene_data)
                q["in_progress"] = None
            else:
                # Gene analyzed outside queue — register as completed
                already = {g["gene"].upper() for g in q.get("completed", [])}
                if gene_name.upper() not in already:
                    q["completed"].append({
                        "gene": gene_name,
                        "finished": _dt.datetime.now().isoformat(),
                        "steps_done": ["discover", "hypothesize"],
                        "source": "auto-registered from save_finding",
                    })
            q["stats"]["genes_completed"] = len(q["completed"])
            _save_queue(q)
            log.info("Auto-completed gene: %s", gene_name)
    except Exception as e:
        log.warning("Failed to auto-complete gene: %s", e)

    # Auto-mark gene as DONE in dark_genes_reference.tsv
    if gene_name:
        try:
            from config import BASE_DIR
            ref_file = os.path.join(BASE_DIR, "dark_genes_reference.tsv")
            if os.path.exists(ref_file):
                import csv as _csv
                rows = []
                updated = False
                with open(ref_file, 'r', encoding='utf-8') as rf:
                    reader = _csv.DictReader(rf, delimiter='\t')
                    fieldnames = reader.fieldnames
                    for row in reader:
                        rg = row.get('gene_name', '').strip().upper()
                        if rg == gene_name.upper() and row.get('status') == 'TODO':
                            row['status'] = 'DONE'
                            updated = True
                        rows.append(row)
                if updated:
                    with open(ref_file, 'w', encoding='utf-8', newline='') as wf:
                        writer = _csv.DictWriter(wf, fieldnames=fieldnames, delimiter='\t')
                        writer.writeheader()
                        writer.writerows(rows)
                    log.info("Marked %s as DONE in dark_genes_reference.tsv", gene_name)
        except Exception as e:
            log.warning("Failed to update TSV for %s: %s", gene_name, e)

    consolidated = " (consolidated)" if existing_files_to_remove else ""
    return f"Finding logged{consolidated}: '{title}' [Score: {score}/10 {score_label}] — saved to {detail_path}"


def list_findings() -> str:
    """List all recorded findings with their index numbers.
    Use read_finding(number) to read the full content of a specific finding.
    """
    # List from actual finding files on disk (more reliable than memory)
    findings_from_files = []
    if os.path.isdir(FINDINGS_DIR):
        for fname in sorted(os.listdir(FINDINGS_DIR)):
            if fname.endswith(".md"):
                fpath = os.path.join(FINDINGS_DIR, fname)
                mtime = os.path.getmtime(fpath)
                findings_from_files.append({
                    "filename": fname,
                    "title": fname.replace(".md", ""),
                    "modified": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                })

    if not findings_from_files:
        return "No findings recorded yet. Use save_finding(title, description, evidence) to log discoveries."

    # Sort by modification time (newest first)
    findings_from_files.sort(key=lambda x: x["modified"], reverse=True)

    lines = [f"Total findings: {len(findings_from_files)}",
             "  (Use read_finding(number) to read full content)"]
    for i, f in enumerate(findings_from_files, 1):
        lines.append(f"  {i}. [{f['modified']}] {f['title']}")

    return "\n".join(lines)


def read_finding(*args, **kwargs) -> str:
    """
    Read the full content of a specific finding by number or title.

    Args:
        finding_id: Finding number (from list_findings) or partial title match
    """
    # Extract the identifier
    finding_id = ""
    if args:
        finding_id = str(args[0])
    if not finding_id:
        for key in ("finding_id", "id", "number", "index", "title", "name", "query"):
            if key in kwargs:
                finding_id = str(kwargs[key])
                break
    if not finding_id:
        return "[ERROR] No finding specified. Usage: read_finding(1) or read_finding('BRCA1')"

    # Get list of finding files
    if not os.path.isdir(FINDINGS_DIR):
        return "No findings directory found."

    files = sorted([f for f in os.listdir(FINDINGS_DIR) if f.endswith(".md")])
    if not files:
        return "No findings recorded yet."

    # Sort by modification time (newest first) to match list_findings order
    files.sort(key=lambda f: os.path.getmtime(os.path.join(FINDINGS_DIR, f)), reverse=True)

    # Try numeric index first
    try:
        idx = int(finding_id) - 1  # 1-indexed
        if 0 <= idx < len(files):
            fpath = os.path.join(FINDINGS_DIR, files[idx])
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            return f"[Finding #{idx + 1}: {files[idx]}]\n\n{content[:3000]}"
    except ValueError:
        pass

    # Try partial title match
    query = finding_id.lower()
    for fname in files:
        if query in fname.lower():
            fpath = os.path.join(FINDINGS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            return f"[Finding: {fname}]\n\n{content[:3000]}"

    return f"No finding matching '{finding_id}'. Use list_findings() to see available findings."


def review_findings(*args, **kwargs) -> str:
    """
    Read multiple findings at once. Supports ranges, keyword filtering, or both.

    Args:
        start: Start index (1-based), or keyword to filter by
        end: End index (optional, for range queries)
        focus: Keyword filter — only return findings matching this term
    """
    start = None
    end = None
    focus = ""

    # Parse positional args
    if args:
        first = args[0]
        if isinstance(first, (list, tuple)) and len(first) == 2:
            start, end = int(first[0]), int(first[1])
        elif isinstance(first, int) or (isinstance(first, str) and first.isdigit()):
            start = int(first)
        else:
            focus = str(first)
    if len(args) >= 2:
        second = args[1]
        if isinstance(second, int) or (isinstance(second, str) and second.isdigit()):
            end = int(second)
        else:
            focus = str(second)

    # Parse kwargs
    if "start" in kwargs:
        start = int(kwargs["start"])
    if "end" in kwargs:
        end = int(kwargs["end"])
    for key in ("focus", "filter", "keyword", "query", "search", "topic"):
        if key in kwargs:
            focus = str(kwargs[key])
            break
    if "findings_range" in kwargs:
        r = kwargs["findings_range"]
        if isinstance(r, (list, tuple)) and len(r) == 2:
            start, end = int(r[0]), int(r[1])

    # Get all findings
    if not os.path.isdir(FINDINGS_DIR):
        return "No findings directory."

    files = sorted(
        [f for f in os.listdir(FINDINGS_DIR) if f.endswith(".md")],
        key=lambda f: os.path.getmtime(os.path.join(FINDINGS_DIR, f)),
        reverse=True,
    )
    if not files:
        return "No findings yet."

    # Apply keyword filter
    if focus:
        focus_lower = focus.lower()
        filtered = []
        for fname in files:
            if focus_lower in fname.lower():
                filtered.append(fname)
                continue
            # Also check content
            try:
                fpath = os.path.join(FINDINGS_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read(2000)
                if focus_lower in content.lower():
                    filtered.append(fname)
            except Exception:
                pass
        files = filtered

    # Apply range
    if start is not None:
        s = max(0, start - 1)  # 1-indexed
        e = end if end else s + 1
        files = files[s:e]

    if not files:
        return f"No findings matched (focus='{focus}', range={start}-{end})."

    # Build summary
    results = []
    total_chars = 0
    for fname in files[:25]:  # cap at 25
        fpath = os.path.join(FINDINGS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read(500)  # first 500 chars each
            total_chars += len(content)
            results.append(f"--- {fname.replace('.md', '')} ---\n{content.strip()}")
        except Exception:
            results.append(f"--- {fname.replace('.md', '')} --- [read error]")
        if total_chars > 8000:
            results.append(f"... truncated ({len(files) - len(results)} more)")
            break

    header = f"Showing {len(results)} of {len(files)} findings"
    if focus:
        header += f" matching '{focus}'"
    return f"{header}\n\n" + "\n\n".join(results)


def list_sequences() -> str:
    """
    List all downloaded sequence files (.fasta) with their descriptions.
    Shows what's already been fetched so you don't re-download.
    """
    from config import SEQUENCES_DIR

    if not os.path.isdir(SEQUENCES_DIR):
        return "No sequences directory found."

    files = []
    for fname in os.listdir(SEQUENCES_DIR):
        if fname.lower().endswith((".fasta", ".fa", ".fna")):
            fpath = os.path.join(SEQUENCES_DIR, fname)
            size = os.path.getsize(fpath)
            # Read header line
            header = ""
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith(">"):
                        header = first_line[1:].strip()[:120]
            except Exception:
                pass
            files.append({
                "filename": fname,
                "size": size,
                "header": header,
            })

    if not files:
        return "No sequence files downloaded yet. Use ncbi_fetch() or uniprot_fetch() to download sequences."

    files.sort(key=lambda x: x["filename"])

    lines = [f"Downloaded sequences: {len(files)} files"]
    for f in files:
        size_str = f"{f['size']:,} bytes"
        if f['size'] > 1_000_000:
            size_str = f"{f['size'] / 1_000_000:.1f} MB"
        elif f['size'] > 1000:
            size_str = f"{f['size'] / 1000:.1f} KB"
        lines.append(f"  • {f['filename']} ({size_str})")
        if f['header']:
            lines.append(f"    {f['header']}")

    return "\n".join(lines)
