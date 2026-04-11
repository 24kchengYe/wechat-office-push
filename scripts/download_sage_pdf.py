"""
download_sage_pdf.py

Download SAGE-published paper PDFs via the sage.cnpereading.com mirror.

SAGE's official journals.sagepub.com PDFs are paywalled (HTTP 403 without
institutional access). The Chinese mirror at sage.cnpereading.com exposes a
direct download endpoint using just the DOI:

    https://sage.cnpereading.com/paragraph/download/?doi=<DOI>

Usage:
    python download_sage_pdf.py <doi> [--out <path>] [--name <filename>]
    python download_sage_pdf.py --doi-list dois.txt --out <dir>

Examples:
    python download_sage_pdf.py 10.1177/27541231261426518 \
        --out "D:/.../tus发表的论文" \
        --name "he-et-al-2026-shanghai.pdf"

    # batch mode (one DOI per line in dois.txt)
    python download_sage_pdf.py --doi-list dois.txt --out ./papers/

Exit codes:
    0 = all downloads succeeded
    1 = at least one download failed (invalid PDF header or HTTP error)
"""

import argparse
import pathlib
import re
import sys

import requests

MIRROR = "https://sage.cnpereading.com/paragraph/download/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
}


def slugify(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", doi).strip("-") + ".pdf"


def download_one(doi: str, out_dir: pathlib.Path, name: str | None = None) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = name or slugify(doi)
    target = out_dir / filename

    print(f"[download] DOI={doi}")
    try:
        resp = requests.get(MIRROR, params={"doi": doi}, headers=HEADERS,
                            stream=True, timeout=60)
    except requests.RequestException as e:
        print(f"  ✗ request failed: {e}")
        return False

    if resp.status_code != 200:
        print(f"  ✗ HTTP {resp.status_code}")
        return False

    content = resp.content
    if not content.startswith(b"%PDF-"):
        print(f"  ✗ response is not a PDF (got {content[:16]!r})")
        return False

    target.write_bytes(content)
    size_mb = len(content) / (1024 * 1024)
    print(f"  ✓ saved -> {target}  ({size_mb:.2f} MB)")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Download SAGE PDFs via cnpereading mirror")
    p.add_argument("doi", nargs="?", help="single DOI (e.g. 10.1177/xxx)")
    p.add_argument("--doi-list", type=pathlib.Path,
                   help="text file with one DOI per line")
    p.add_argument("--out", type=pathlib.Path, default=pathlib.Path("."),
                   help="output directory (default: current dir)")
    p.add_argument("--name", help="custom filename (single-DOI mode only)")
    args = p.parse_args()

    if not args.doi and not args.doi_list:
        p.error("provide a DOI or --doi-list")

    dois = []
    if args.doi:
        dois.append((args.doi, args.name))
    if args.doi_list:
        for line in args.doi_list.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                dois.append((line, None))

    failures = 0
    for doi, name in dois:
        if not download_one(doi, args.out, name):
            failures += 1

    print(f"\n[done] {len(dois) - failures}/{len(dois)} downloaded")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
