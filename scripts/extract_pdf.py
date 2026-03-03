#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_pdf.py - Extract metadata and key page images from academic paper PDFs.

Usage:
    python extract_pdf.py <pdf_path> <output_dir> [--max-images N]

Outputs:
    - metadata.json: title, authors, abstract, journal, doi
    - page_*.jpg: key page images (title page + figure/table pages)

Dependencies: PyMuPDF (fitz)
    pip install PyMuPDF
"""

import sys
import os
import re
import json
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF is required. Install with: pip install PyMuPDF", file=sys.stderr)
    sys.exit(1)


def extract_text_from_pdf(pdf_path):
    """Extract full text from all pages."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return pages_text


def extract_pdf_metadata(pdf_path):
    """Extract metadata from PDF file properties."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    doc.close()
    return meta or {}


def extract_doi_from_text(full_text):
    """Try to extract DOI from PDF text."""
    patterns = [
        r'(?:doi|DOI)\s*[:\s]\s*(10\.\d{4,}/[^\s,;]+)',
        r'https?://doi\.org/(10\.\d{4,}/[^\s,;]+)',
        r'https?://dx\.doi\.org/(10\.\d{4,}/[^\s,;]+)',
        r'(10\.\d{4,}/[^\s,;]{3,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            doi = match.group(1).rstrip('.')
            return doi
    return None


def extract_title_from_first_page(first_page_text, pdf_meta=None):
    """Extract paper title using PDF metadata first, then text heuristics."""
    # Try PDF metadata first
    if pdf_meta and pdf_meta.get('title'):
        title = pdf_meta['title'].strip()
        if len(title) > 10 and not title.lower().startswith(('untitled', 'microsoft')):
            return title

    lines = first_page_text.strip().split('\n')
    lines = [l.strip() for l in lines if l.strip()]

    # Strategy: find text between header/journal info and "Abstract"
    abstract_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^Abstract\b', line, re.IGNORECASE):
            abstract_idx = i
            break

    # Skip patterns for non-title lines
    skip_patterns = [
        r'^(vol|volume|issue|page|pp\.|doi|http|www|received|accepted|published)',
        r'^\d{4}',  # year
        r'^(original|research|review|article|paper|letter|short|data\s+visualization)\s*(article|paper|communication)?$',
        r'^[A-Z]{2,}\s*$',
        r'^\d+[–\-]\d+$',  # page ranges like "1-10"
        r'^©|^Article reuse',
        r'^Check for updates',
        r'sagepub\.com|springer\.com|elsevier\.com|wiley\.com',
        r'^(Corresponding|Email|College|University|School|Department|Key Laboratory)',
        r'ORCID|orcid',
        r'journals?\.',
    ]

    # Also skip lines that look like journal names
    journal_keywords = ['journal', 'review', 'letters', 'proceedings', 'transactions',
                        'studies', 'science', 'nature', 'lancet', 'cities', 'technology']

    search_end = abstract_idx if abstract_idx > 0 else min(20, len(lines))
    candidate_lines = []

    for i, line in enumerate(lines[:search_end]):
        skip = False
        for pat in skip_patterns:
            if re.search(pat, line, re.IGNORECASE):
                skip = True
                break
        # Skip short lines that match journal keywords
        if not skip and len(line) < 60:
            line_lower = line.lower()
            if any(kw in line_lower for kw in journal_keywords):
                skip = True
        # Skip very short lines (likely headers/labels)
        if not skip and len(line) < 10:
            skip = True
        if not skip:
            candidate_lines.append((i, line))

    if not candidate_lines:
        return None

    # The title is typically the longest block of text before "Abstract"
    # and before author names. Look for the largest font text or longest lines.
    # Combine consecutive candidate lines that form the title
    best_title = None
    best_score = 0

    for start_idx in range(len(candidate_lines)):
        for end_idx in range(start_idx, min(start_idx + 4, len(candidate_lines))):
            # Check lines are roughly consecutive (within 2 lines gap)
            if end_idx > start_idx:
                if candidate_lines[end_idx][0] - candidate_lines[end_idx - 1][0] > 2:
                    break
            combined = ' '.join(c[1] for c in candidate_lines[start_idx:end_idx + 1])
            # Score: prefer longer titles that appear early
            score = len(combined) - candidate_lines[start_idx][0] * 2
            # Boost if it contains typical title words
            if ':' in combined or '–' in combined or '-' in combined:
                score += 10
            if score > best_score and len(combined) > 15:
                best_score = score
                best_title = combined

    return best_title


def extract_corresponding_author(full_text):
    """Extract corresponding author name from PDF text.

    Looks for patterns like:
    - "Corresponding author: Name"
    - "* Corresponding author"
    - "Email: name@..." near author names
    - "Correspondence: Name"
    """
    patterns = [
        r'[Cc]orrespond(?:ing|ence)\s*(?:author)?[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'\*\s*[Cc]orrespond(?:ing|ence)\s*(?:author)?[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'[Cc]orrespond(?:ing|ence)\s*(?:author)?[:\s]*\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?:E-?mail|Contact)\s*:\s*(\S+@\S+)',  # Capture email for later matching
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1).strip()

    return None


def extract_authors_from_first_page(first_page_text, title=None, pdf_meta=None):
    """Extract authors using PDF metadata first, then text heuristics."""
    # Try PDF metadata first
    if pdf_meta and pdf_meta.get('author'):
        author = pdf_meta['author'].strip()
        if author and len(author) > 2:
            return author

    lines = first_page_text.strip().split('\n')
    lines = [l.strip() for l in lines if l.strip()]

    # Find the title position
    title_idx = -1
    if title:
        title_start = title[:30].lower()
        for i, line in enumerate(lines):
            if title_start in line.lower():
                title_idx = i
                break

    # Find abstract position
    abstract_idx = len(lines)
    for i, line in enumerate(lines):
        if re.match(r'^Abstract\b', line, re.IGNORECASE):
            abstract_idx = i
            break

    # Authors are between title and abstract
    search_start = max(0, title_idx + 1) if title_idx >= 0 else 3
    search_end = abstract_idx

    for i in range(search_start, min(search_end, search_start + 8)):
        if i >= len(lines):
            break
        line = lines[i]
        # Clean superscripts and symbols
        cleaned = re.sub(r'[\d*†‡§¶∥⊥#,\s]+$', '', line)
        cleaned = re.sub(r'[\u00b9\u00b2\u00b3\u2070-\u209f]', '', cleaned)  # Unicode superscripts

        # Check for author-like patterns:
        # "Name1, Name2, and Name3" or "Name1 Name2 Name3"
        # Authors often have "and" between last two names
        if re.search(r'\b(and|&)\b', cleaned) and re.match(r'^[A-Z]', cleaned):
            # Likely an author line
            return cleaned.strip()

        # Pattern: "FirstName LastName,1,2 FirstName LastName1"
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+', cleaned) and len(cleaned) > 10:
            # Check it's not a sentence (no verb-like patterns)
            if not re.search(r'\b(is|are|was|were|has|have|the|this|that|in|of|for)\b', cleaned.lower()):
                return cleaned.strip()

    return None


def extract_abstract(full_text):
    """Extract abstract from PDF text."""
    patterns = [
        r'(?:^|\n)\s*Abstract\s*\n(.+?)(?:\n\s*(?:Keywords?|Key\s*words?|Introduction|1[\s\.]|INTRODUCTION)\b)',
        r'(?:^|\n)\s*ABSTRACT\s*\n(.+?)(?:\n\s*(?:KEY\s*WORDS?|KEYWORDS?|INTRODUCTION|1[\s\.])\b)',
        r'(?:^|\n)\s*Abstract\s*[:\.]\s*\n?(.+?)(?:\n\s*(?:Keywords?|Key\s*words?|Introduction|1[\s\.])\b)',
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            abstract = re.sub(r'\s+', ' ', abstract)
            if len(abstract) > 50:
                return abstract

    return None


def extract_journal(full_text, pdf_meta=None):
    """Extract journal name from PDF text or metadata."""
    # Try PDF metadata subject or other fields
    if pdf_meta:
        for key in ['subject', 'keywords']:
            val = pdf_meta.get(key, '')
            if val and any(kw in val.lower() for kw in ['journal', 'review', 'transactions', 'cities', 'letters']):
                return val.strip()

    lines = full_text.strip().split('\n')
    journal_keywords = ['journal', 'review', 'letters', 'proceedings', 'transactions',
                        'cities', 'studies', 'research', 'science', 'nature', 'lancet',
                        'technology', 'planning', 'geography', 'urban']

    # Check first few lines and last few lines
    for line in lines[:8] + lines[-5:]:
        line = line.strip()
        if len(line) < 5 or len(line) > 80:
            continue
        line_lower = line.lower()
        if any(kw in line_lower for kw in journal_keywords):
            # Filter out URLs and metadata
            if not re.search(r'(http|doi|©|@|\.com|\.org)', line_lower):
                return line

    return None


def score_page_importance(page, page_num, total_pages):
    """Score a page's importance for inclusion in the article preview."""
    score = 0
    text = page.get_text()
    image_list = page.get_images()

    # Title page is always important
    if page_num == 0:
        score += 100

    # Pages with many images (figures/charts)
    if len(image_list) > 0:
        score += 20 * len(image_list)

    # Pages with figure/table captions
    fig_matches = len(re.findall(r'(?:Fig(?:ure)?|Table|Chart|Map)\s*\.?\s*\d', text, re.IGNORECASE))
    score += fig_matches * 15

    # Pages with "Results" or "Discussion" or "Conclusion" headings
    if re.search(r'\n\s*\d?\s*\.?\s*(?:Results|Discussion|Conclusion|Findings)', text, re.IGNORECASE):
        score += 10

    # Penalize reference/bibliography pages
    if re.search(r'\n\s*(?:References|Bibliography|Works Cited)\s*\n', text, re.IGNORECASE):
        score -= 30

    # Slight preference for earlier pages
    score -= page_num * 0.5

    return score


def select_key_pages(pdf_path, max_images=5):
    """Select the most important pages from a PDF."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if total_pages <= max_images:
        selected = list(range(total_pages))
        doc.close()
        return selected

    # Score each page
    page_scores = []
    for i, page in enumerate(doc):
        score = score_page_importance(page, i, total_pages)
        page_scores.append((i, score))

    doc.close()

    # Always include page 0 (title page)
    page_scores.sort(key=lambda x: x[1], reverse=True)
    selected = set()
    selected.add(0)  # Always include title page

    for page_num, score in page_scores:
        if len(selected) >= max_images:
            break
        if score > 0:
            selected.add(page_num)

    # If we still need more, add pages sequentially
    if len(selected) < max_images:
        for i in range(total_pages):
            if len(selected) >= max_images:
                break
            selected.add(i)

    return sorted(selected)


def render_pages_to_images(pdf_path, page_numbers, output_dir, dpi=200):
    """Render selected pages to JPEG images."""
    doc = fitz.open(pdf_path)
    image_paths = []

    for page_num in page_numbers:
        if page_num >= len(doc):
            continue
        page = doc[page_num]
        # Render at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        filename = f"page_{page_num + 1:03d}.jpg"
        filepath = os.path.join(output_dir, filename)
        pix.save(filepath)
        image_paths.append(filepath)

    doc.close()
    return image_paths


def process_pdf(pdf_path, output_dir, max_images=5):
    """Process a single PDF and output metadata + images."""
    os.makedirs(output_dir, exist_ok=True)

    # Extract text and PDF metadata
    pages_text = extract_text_from_pdf(pdf_path)
    pdf_meta = extract_pdf_metadata(pdf_path)
    full_text = '\n'.join(pages_text)
    first_page_text = pages_text[0] if pages_text else ''

    # Extract metadata (PDF properties take priority, then text heuristics)
    title = extract_title_from_first_page(first_page_text, pdf_meta)
    authors = extract_authors_from_first_page(first_page_text, title, pdf_meta)
    abstract = extract_abstract(full_text)
    journal = extract_journal(first_page_text, pdf_meta)
    doi = extract_doi_from_text(full_text)
    corresponding_author = extract_corresponding_author(full_text)

    metadata = {
        'title': title,
        'authors': authors,
        'corresponding_author': corresponding_author,
        'abstract': abstract,
        'journal': journal,
        'doi': doi,
        'pdf_filename': os.path.basename(pdf_path),
        'total_pages': len(pages_text),
    }

    # Save metadata
    meta_path = os.path.join(output_dir, 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Select and render key pages
    selected_pages = select_key_pages(pdf_path, max_images)
    image_paths = render_pages_to_images(pdf_path, selected_pages, output_dir)

    metadata['selected_pages'] = [p + 1 for p in selected_pages]  # 1-indexed
    metadata['image_files'] = [os.path.basename(p) for p in image_paths]

    # Update metadata with image info
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return metadata


def main():
    parser = argparse.ArgumentParser(description='Extract metadata and key pages from academic paper PDF')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('output_dir', help='Directory to save output files')
    parser.add_argument('--max-images', type=int, default=5, help='Maximum number of page images to extract (default: 5)')
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"ERROR: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    result = process_pdf(args.pdf_path, args.output_dir, args.max_images)

    # Print summary
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
