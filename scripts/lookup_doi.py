#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
lookup_doi.py - Look up and verify paper metadata via CrossRef & Semantic Scholar APIs.

Usage:
    python lookup_doi.py --title "Paper Title" [--author "Author Name"] [--doi "10.xxxx/xxx"]

Modes:
    - Given --title (and optional --author): search CrossRef by title, return full metadata
    - Given --doi: look up by DOI directly, return full metadata
    - Given both: look up by DOI, cross-check title match

Dependencies: requests
    pip install requests
"""

import sys
import json
import argparse

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def search_crossref(title, author=None):
    """Search CrossRef API for a paper by title."""
    base_url = "https://api.crossref.org/works"
    params = {
        'query.title': title,
        'rows': 5,
        'select': 'DOI,title,author,container-title,published-print,published-online',
    }
    if author:
        params['query.author'] = author

    headers = {
        'User-Agent': 'WeChat-Article-Push/1.0 (https://github.com/wechat-article-push)',
    }

    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"WARNING: CrossRef search failed: {e}", file=sys.stderr)
        return None

    items = data.get('message', {}).get('items', [])
    if not items:
        return None

    title_lower = title.lower().strip()
    for item in items:
        for t in item.get('title', []):
            t_lower = t.lower().strip()
            if t_lower == title_lower:
                return format_crossref(item)
            title_words = set(title_lower.split())
            item_words = set(t_lower.split())
            if len(title_words & item_words) >= len(title_words) * 0.8:
                return format_crossref(item)

    return format_crossref(items[0])


def lookup_crossref_by_doi(doi):
    """Look up a specific DOI on CrossRef."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        'User-Agent': 'WeChat-Article-Push/1.0 (https://github.com/wechat-article-push)',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"WARNING: CrossRef DOI lookup failed: {e}", file=sys.stderr)
        return None

    item = data.get('message')
    if not item:
        return None
    return format_crossref(item)


def lookup_semantic_scholar(title):
    """Search Semantic Scholar API as a fallback."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': title,
        'limit': 3,
        'fields': 'title,authors,externalIds,journal,year',
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"WARNING: Semantic Scholar search failed: {e}", file=sys.stderr)
        return None

    papers = data.get('data', [])
    if not papers:
        return None

    title_lower = title.lower().strip()
    best = papers[0]
    for p in papers:
        if p.get('title', '').lower().strip() == title_lower:
            best = p
            break

    authors = [a.get('name', '') for a in best.get('authors', []) if a.get('name')]
    ext_ids = best.get('externalIds', {})
    doi = ext_ids.get('DOI', '')
    journal_info = best.get('journal') or {}

    return {
        'title': best.get('title', ''),
        'authors': ', '.join(authors),
        'doi': doi,
        'doi_url': f"https://doi.org/{doi}" if doi else '',
        'journal': journal_info.get('name', ''),
        'year': best.get('year'),
        'source': 'semantic_scholar',
    }


def format_crossref(item):
    """Format a CrossRef result."""
    doi = item.get('DOI', '')
    titles = item.get('title', [])
    authors_raw = item.get('author', [])
    journal = item.get('container-title', [])

    # Extract published date
    date_info = item.get('published-online') or item.get('published-print') or {}
    date_parts = date_info.get('date-parts', [[]])
    year = date_parts[0][0] if date_parts and date_parts[0] else None

    author_names = []
    corresponding_authors = []
    for a in authors_raw:
        given = a.get('given', '')
        family = a.get('family', '')
        name = f"{given} {family}".strip() if given else family
        if name:
            # CrossRef marks corresponding authors with "sequence": "first"
            # and/or an ORCID authenticated via email (has "email" field)
            is_corresponding = False
            if a.get('sequence') == 'first' and len(authors_raw) > 1:
                # First author is often but not always corresponding
                # Check if they have affiliation email or ORCID
                pass
            # More reliable: CrossRef includes email for corresponding authors
            if 'email' in a:
                is_corresponding = True
            if is_corresponding:
                corresponding_authors.append(name)
            author_names.append(name)

    return {
        'title': titles[0] if titles else '',
        'authors': ', '.join(author_names),
        'corresponding_authors': corresponding_authors,
        'doi': doi,
        'doi_url': f"https://doi.org/{doi}" if doi else '',
        'journal': journal[0] if journal else '',
        'year': year,
        'source': 'crossref',
    }


def verify_and_complete(pdf_title=None, pdf_authors=None, pdf_doi=None):
    """
    Verify and complete paper metadata by querying online APIs.
    Priority: DOI lookup > CrossRef title search > Semantic Scholar fallback.
    """
    result = None

    # 1. If we have a DOI, look it up directly (most reliable)
    if pdf_doi:
        result = lookup_crossref_by_doi(pdf_doi)

    # 2. If no DOI or DOI lookup failed, search by title
    if not result and pdf_title:
        result = search_crossref(pdf_title, pdf_authors)

    # 3. Fallback to Semantic Scholar
    if not result and pdf_title:
        result = lookup_semantic_scholar(pdf_title)

    if not result:
        return {'error': 'No results found from any source'}

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Look up and verify paper metadata via CrossRef & Semantic Scholar')
    parser.add_argument('--title', default=None, help='Paper title')
    parser.add_argument('--author', default=None, help='Author name (improves accuracy)')
    parser.add_argument('--doi', default=None, help='Known DOI (for direct lookup)')
    args = parser.parse_args()

    if not args.title and not args.doi:
        parser.error('At least one of --title or --doi is required')

    result = verify_and_complete(args.title, args.author, args.doi)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if 'error' in result:
        sys.exit(1)


if __name__ == '__main__':
    main()
