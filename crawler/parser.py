"""
HTML Parser utility for title extraction and hyperlink discovery.
"""

from bs4 import BeautifulSoup
from typing import Dict, Any
from .url_utils import normalize_url, is_binary_url, is_same_domain


def parse_page_html(
    html_content: str,
    base_url: str,
    base_domain: str,
    allow_subdomains: bool = True
) -> Dict[str, Any]:
    """
    Parse HTML content, extract page title, and discover, normalize, and classify
    hyperlinks into internal and external lists.

    Args:
        html_content: Raw HTML text of the webpage.
        base_url: The URL of the webpage being crawled (used for relative link resolution).
        base_domain: The domain of the crawl root (used for internal/external classification).
        allow_subdomains: Whether subdomains of base_domain are counted as internal.

    Returns:
        Dictionary containing:
        - title: Extracted title or fallback
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

    # 2. Extract and categorize hyperlinks
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
        "total_links_found": total_links_found,
        "unique_links_count": unique_links_count,
        "internal_urls": internal_list,
        "external_urls": external_list,
        "internal_count": len(internal_list),
        "external_count": len(external_list),
    }
