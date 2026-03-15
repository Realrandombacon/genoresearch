"""
Download BLAST databases from NCBI FTP.

Usage:
    python download_blastdb.py refseq_protein          # Download refseq_protein (~50 GB)
    python download_blastdb.py nt --dest G:\blastdb     # Download nt to G: drive (~300 GB)
    python download_blastdb.py nr --dest G:\blastdb     # Download nr (~250 GB)
    python download_blastdb.py --list                   # Show available databases
"""

import os
import sys
import time
import subprocess
import argparse
import urllib.request
import re

NCBI_FTP = "https://ftp.ncbi.nlm.nih.gov/blast/db"
DEFAULT_DEST = r"C:\blastdb"


def get_volume_list(db_name: str) -> list[str]:
    """Fetch list of volume files for a database from NCBI FTP."""
    print(f"  Fetching file list for '{db_name}' from NCBI FTP...")
    url = f"{NCBI_FTP}/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GenoResearch/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  [ERROR] Cannot fetch FTP listing: {e}")
        return []

    # Match files like: refseq_protein.00.tar.gz, nr.142.tar.gz, etc.
    pattern = rf'{re.escape(db_name)}\.\d+\.tar\.gz'
    files = sorted(set(re.findall(pattern, html)))

    if not files:
        # Try single file (like swissprot.tar.gz)
        single = f"{db_name}.tar.gz"
        if single in html:
            files = [single]

    return files


def download_and_extract(filename: str, dest_dir: str) -> bool:
    """Download a single volume file and extract it."""
    url = f"{NCBI_FTP}/{filename}"
    filepath = os.path.join(dest_dir, filename)

    # Check if already extracted (look for extracted files matching this volume)
    # Volume files extract to files like refseq_protein.00.phr, etc.
    base = filename.replace(".tar.gz", "")
    already_done = any(
        f.startswith(base + ".") and not f.endswith(".tar.gz")
        for f in os.listdir(dest_dir)
        if os.path.isfile(os.path.join(dest_dir, f))
    )
    if already_done:
        print(f"  [SKIP] {filename} — already extracted")
        return True

    # Download
    try:
        print(f"  Downloading {filename}...", end=" ", flush=True)
        t0 = time.time()

        # Use curl for progress display
        result = subprocess.run(
            ["curl", "-L", "-o", filepath, url, "--progress-bar", "--fail"],
            capture_output=False, timeout=3600,
        )
        if result.returncode != 0:
            print(f"FAILED (curl exit {result.returncode})")
            return False

        elapsed = time.time() - t0
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"OK ({size_mb:.0f} MB in {elapsed:.0f}s)")

    except Exception as e:
        print(f"FAILED: {e}")
        return False

    # Extract
    try:
        print(f"  Extracting {filename}...", end=" ", flush=True)
        result = subprocess.run(
            ["tar", "-xzf", filepath],
            cwd=dest_dir, capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            print(f"FAILED: {result.stderr[:200]}")
            return False
        print("OK")

    except Exception as e:
        print(f"FAILED: {e}")
        return False

    # Cleanup tar.gz
    try:
        os.remove(filepath)
    except OSError:
        pass

    return True


def download_database(db_name: str, dest_dir: str):
    """Download a complete BLAST database."""
    os.makedirs(dest_dir, exist_ok=True)

    files = get_volume_list(db_name)
    if not files:
        print(f"[ERROR] No files found for database '{db_name}'")
        print("Use --list to see available databases.")
        return

    total = len(files)
    print(f"\n{'='*60}")
    print(f"  Database: {db_name}")
    print(f"  Volumes:  {total} files")
    print(f"  Dest:     {dest_dir}")
    print(f"{'='*60}\n")

    success = 0
    failed = []

    for i, filename in enumerate(files, 1):
        print(f"\n[{i}/{total}] {filename}")
        if download_and_extract(filename, dest_dir):
            success += 1
        else:
            failed.append(filename)

    print(f"\n{'='*60}")
    print(f"  Done! {success}/{total} volumes downloaded.")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
        print(f"\n  Re-run to retry failed downloads.")
    print(f"{'='*60}")


def list_databases():
    """Show popular BLAST databases with sizes."""
    print("""
Available BLAST databases (NCBI):

  Small (good for testing):
    swissprot          ~250 MB    Curated protein sequences (~570K)

  Medium (recommended for research):
    refseq_protein     ~50 GB     All RefSeq protein sequences
    refseq_select_rna  ~2 GB      Curated RefSeq RNA transcripts
    refseq_rna         ~15 GB     All RefSeq RNA transcripts

  Large (comprehensive):
    nt                 ~300 GB    All nucleotide sequences
    nr                 ~250 GB    All non-redundant protein sequences

  Usage:
    python download_blastdb.py refseq_protein
    python download_blastdb.py nt --dest G:\\blastdb
""")


def main():
    parser = argparse.ArgumentParser(description="Download BLAST databases from NCBI")
    parser.add_argument("database", nargs="?", help="Database name (e.g. refseq_protein, nt, nr)")
    parser.add_argument("--dest", default=DEFAULT_DEST, help=f"Destination directory (default: {DEFAULT_DEST})")
    parser.add_argument("--list", action="store_true", help="List available databases")
    args = parser.parse_args()

    if args.list or not args.database:
        list_databases()
        return

    download_database(args.database, args.dest)


if __name__ == "__main__":
    main()
