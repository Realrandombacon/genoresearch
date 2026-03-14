"""
File reading tool — lets the agent read any project file (sequences, findings, logs).
"""

import os
import logging

from config import BASE_DIR, SEQUENCES_DIR, FINDINGS_DIR, DATA_DIR

log = logging.getLogger("genoresearch.file_tools")

# Allowed root directories (security: don't let the agent read outside the project)
ALLOWED_ROOTS = [BASE_DIR]


def read_file(*args, **kwargs) -> str:
    """
    Read the contents of a file. Searches in sequences/, findings/, and project root.

    Args:
        filepath: Filename or relative path (e.g. 'NM_000041.4.fasta', 'findings/BRCA1.md')
    """
    filepath = ""
    if args:
        filepath = str(args[0])
    if not filepath:
        for key in ("filepath", "path", "file", "filename", "name"):
            if key in kwargs:
                filepath = str(kwargs[key])
                break
    if not filepath:
        return "[ERROR] No filepath specified. Usage: read_file('filename.fasta')"

    # Search order: exact path, sequences dir, findings dir, data dir, project root
    candidates = [
        filepath,
        os.path.join(SEQUENCES_DIR, filepath),
        os.path.join(FINDINGS_DIR, filepath),
        os.path.join(DATA_DIR, filepath),
        os.path.join(BASE_DIR, filepath),
    ]

    resolved = None
    for candidate in candidates:
        full = os.path.abspath(candidate)
        # Security check: must be within project
        if any(full.startswith(os.path.abspath(root)) for root in ALLOWED_ROOTS):
            if os.path.isfile(full):
                resolved = full
                break

    if not resolved:
        return f"[ERROR] File not found: '{filepath}'. Try list_sequences() to see available files."

    try:
        size = os.path.getsize(resolved)
        if size > 500_000:
            # For large files, read first + last portion
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                head = f.read(5000)
            return (
                f"[File: {os.path.basename(resolved)} — {size:,} bytes, showing first 5KB]\n\n"
                f"{head}\n\n[... truncated — file too large to display in full ...]"
            )

        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return f"[File: {os.path.basename(resolved)} — {size:,} bytes]\n\n{content}"

    except Exception as e:
        log.error("Failed to read file '%s': %s", resolved, e)
        return f"[ERROR] Could not read file: {e}"
