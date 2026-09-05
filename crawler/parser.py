"""
HTML Parser utility for title extraction, hyperlink discovery, visible text extraction,
and sentence/keyword matching.
"""

import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from .url_utils import normalize_url, is_binary_url, is_same_domain


def parse_page_html(
    html_content: str,
    base_url: str,
    base_domain: str,
    allow_subdomains: bool = True,
    target_terms: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse HTML content, extract page title, visible text, word count, text snippet,
    matching sentences, and discover, normalize, and classify hyperlinks into internal
    and external lists.

    Args:
        html_content: Raw HTML text of the webpage.
        base_url: The URL of the webpage being crawled (used for relative link resolution).
        base_domain: The domain of the crawl root (used for internal/external classification).
        allow_subdomains: Whether subdomains of base_domain are counted as internal.
        target_terms: Optional search words, sentence, or phrase to mine and match.

    Returns:
        Dictionary containing:
        - title: Extracted title or fallback
        - text_snippet: Clean visible text excerpt
        - word_count: Total word count of visible text
        - matching_sentences: Sentences containing target terms
        - match_count: Total occurrences of target terms
        - total_links_found: Raw total number of <a> tags with href
        - unique_links_count: Total unique valid HTTP/S links discovered
        - internal_urls: List of unique internal URLs
        - external_urls: List of unique external URLs
        - internal_count: Number of unique internal links
        - external_count: Number of unique external links
    """
    if not html_content:
        return {
            "title": "Empty Page",
            "text_snippet": "",
            "word_count": 0,
            "matching_sentences": [],
            "match_count": 0,
            "total_links_found": 0,
            "unique_links_count": 0,
            "internal_urls": [],
            "external_urls": [],
            "internal_count": 0,
            "external_count": 0,
        }

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return {
            "title": "Parse Error",
            "text_snippet": "",
            "word_count": 0,
            "matching_sentences": [],
            "match_count": 0,
            "total_links_found": 0,
            "unique_links_count": 0,
            "internal_urls": [],
            "external_urls": [],
            "internal_count": 0,
            "external_count": 0,
        }

    # 1. Title extraction
    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()

    if not title:
        # Fallback to first <h1>
        h1_tag = soup.find("h1")
        if h1_tag:
            title = h1_tag.get_text().strip()

    if not title:
        title = "Untitled Page"

    # Clean multi-line whitespace in title
    title = " ".join(title.split())

    # 2. Extract visible body text (decompose boilerplate and non-content tags)
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()

    body = soup.find("body") or soup
    raw_text = body.get_text(separator=" ", strip=True)
    clean_text = " ".join(raw_text.split())

    words = clean_text.split()
    word_count = len(words)
    if len(clean_text) > 320:
        text_snippet = clean_text[:317].strip() + "..."
    else:
        text_snippet = clean_text

    # 3. Sentence & Word Mining
    matching_sentences: List[str] = []
    match_count = 0

    if target_terms and target_terms.strip() and clean_text:
        term_clean = target_terms.strip()
        term_lower = term_clean.lower()

        # Split text into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 15]

        # Individual word tokens from query
        query_words = [w.lower() for w in re.findall(r"\b\w{3,}\b", term_clean)]

        matched_set = set()
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # Exact phrase match or multi-word match
            has_match = False
            if term_lower in sentence_lower:
                has_match = True
                match_count += sentence_lower.count(term_lower)
            elif query_words:
                found_words = sum(1 for w in query_words if w in sentence_lower)
                if found_words >= max(1, len(query_words) // 2):
                    has_match = True
                    match_count += found_words

            if has_match and sentence not in matched_set:
                matched_set.add(sentence)
                matching_sentences.append(sentence)
                if len(matching_sentences) >= 5:
                    break

    # 4. Extract and categorize hyperlinks
    raw_anchor_tags = soup.find_all("a", href=True)
    total_links_found = len(raw_anchor_tags)

    internal_urls_set = set()
    external_urls_set = set()

    for anchor in raw_anchor_tags:
        raw_href = anchor.get("href", "")
        if not raw_href:
            continue

        normalized = normalize_url(raw_href, base_url=base_url)
        if not normalized:
            continue

        # Skip direct binary files (PDFs, images, ZIPs, etc.)
        if is_binary_url(normalized):
            continue

        if is_same_domain(normalized, base_domain, allow_subdomains=allow_subdomains):
            internal_urls_set.add(normalized)
        else:
            external_urls_set.add(normalized)

    internal_list = sorted(internal_urls_set)
    external_list = sorted(external_urls_set)
    unique_links_count = len(internal_list) + len(external_list)

    return {
        "title": title,
        "text_snippet": text_snippet,
        "word_count": word_count,
        "matching_sentences": matching_sentences,
        "match_count": match_count,
        "total_links_found": total_links_found,
        "unique_links_count": unique_links_count,
        "internal_urls": internal_list,
        "external_urls": external_list,
        "internal_count": len(internal_list),
        "external_count": len(external_list),
    }
