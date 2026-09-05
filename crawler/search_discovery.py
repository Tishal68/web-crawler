"""
Search discovery engine that enables crawling arbitrary words, phrases, sentences,
and topics across the internet by resolving authoritative seed URLs from multiple
search providers with strict SSRF filtering.
"""

import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from .url_utils import is_valid_url, is_safe_target_url, normalize_url, is_binary_url

# Standard user-agent for public API and search requests
SEARCH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 WebCrawlerSearch/1.0"


def is_search_query(text: str) -> bool:
    """
    Determine whether user input is an arbitrary search query (words, sentence, phrase)
    or an explicit website URL.

    Returns:
        True if the text is words/sentence/phrase intended for web search.
        False if it is a valid HTTP/HTTPS URL or domain.
    """
    if not text or not isinstance(text, str):
        return False

    cleaned = text.strip()
    if not cleaned:
        return False

    # Explicit URI schemes (http://, https://, file://, ftp://, invalid://, etc.) are URLs/targets, not search queries
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        return False
    if cleaned.lower().startswith(("javascript:", "data:", "file:", "ftp:", "mailto:")):
        return False

    # If it contains whitespace, multiple words, or question marks, it's a search phrase
    if any(ch in cleaned for ch in (" ", "\t", "\n", "?")):
        return True

    # Check if it looks like a domain without scheme (e.g. 'example.com', 'en.wikipedia.org')
    if "." in cleaned and not cleaned.startswith(".") and not cleaned.endswith("."):
        parts = cleaned.split("/")
        host_part = parts[0]
        # Basic check for domain-like structure
        if re.match(r"^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:[0-9]+)?$", host_part):
            return False

    # Single words without dots (e.g. 'python', 'crawler', 'robotics') are search terms
    return True


def discover_search_urls(
    query: str,
    max_results: int = 8,
    timeout: float = 7.0,
    session: Optional[requests.Session] = None,
) -> List[str]:
    """
    Discover authoritative seed URLs across the internet for a given word, sentence,
    or topic query. Uses DuckDuckGo HTML search and Wikipedia OpenSearch API as multi-source
    discovery, returning safe, deduplicated destination URLs.

    Args:
        query: Words or sentence to search for.
        max_results: Maximum number of seed URLs to return.
        timeout: Request timeout in seconds.
        session: Optional requests.Session instance.

    Returns:
        List of safe, normalized, deduplicated HTTP/S URLs.
    """
    if not query or not query.strip():
        return []

    post_fn = session.post if session is not None else requests.post
    get_fn = session.get if session is not None else requests.get

    discovered_urls: List[str] = []
    seen_urls = set()

    clean_query = query.strip()

    # 1. DuckDuckGo Search (attempts Lite and HTML endpoints for direct web links)
    for endpoint in ("https://lite.duckduckgo.com/lite/", "https://html.duckduckgo.com/html/"):
        if len(discovered_urls) >= max_results:
            break
        try:
            ddg_resp = post_fn(
                endpoint,
                data={"q": clean_query},
                headers={"User-Agent": SEARCH_USER_AGENT},
                timeout=timeout,
            )
            if ddg_resp.status_code == 200:
                soup = BeautifulSoup(ddg_resp.text, "html.parser")
                for a_tag in soup.find_all("a", class_=["result-link", "result__url"]):
                    href = a_tag.get("href", "").strip()
                    if not href:
                        continue

                    # Handle DDG redirect wrappers if present: /l/?uddg=<url>
                    if "/l/?uddg=" in href:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "uddg" in parsed_qs:
                            href = parsed_qs["uddg"][0]

                    # Filter out advertising clicks or self-referential links
                    if any(bad in href for bad in ("duckduckgo.com/y.js", "ad_provider", "bing.com/aclick", "duckduckgo.com")):
                        continue

                    norm = normalize_url(href)
                    if norm and norm not in seen_urls and is_valid_url(norm) and not is_binary_url(norm):
                        is_safe, _ = is_safe_target_url(norm, resolve_dns=False)
                        if is_safe:
                            discovered_urls.append(norm)
                            seen_urls.add(norm)
                            if len(discovered_urls) >= max_results:
                                break
        except Exception:
            pass

    # 2. Wikipedia Full-Text Query Search (handles arbitrary complex sentences, phrases, & questions)
    if len(discovered_urls) < max_results:
        try:
            wiki_api = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": clean_query,
                "srlimit": max_results,
                "format": "json",
            }
            wiki_resp = get_fn(
                wiki_api,
                params=params,
                headers={"User-Agent": "WebCrawlerAnalytics/2.0 (research@example.com)"},
                timeout=timeout,
            )
            if wiki_resp.status_code == 200:
                data = wiki_resp.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title")
                    if title:
                        article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        norm = normalize_url(article_url)
                        if norm and norm not in seen_urls and is_valid_url(norm):
                            is_safe, _ = is_safe_target_url(norm, resolve_dns=False)
                            if is_safe:
                                discovered_urls.append(norm)
                                seen_urls.add(norm)
                                if len(discovered_urls) >= max_results:
                                    break
        except Exception:
            pass

    # 3. Wikipedia OpenSearch API (reliable fallback for topic keywords)
    if len(discovered_urls) < max_results:
        try:
            wiki_api = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": clean_query,
                "limit": max_results,
                "namespace": "0",
                "format": "json",
            }
            wiki_resp = get_fn(
                wiki_api,
                params=params,
                headers={"User-Agent": "WebCrawlerAnalytics/2.0 (research@example.com)"},
                timeout=timeout,
            )
            if wiki_resp.status_code == 200:
                data = wiki_resp.json()
                if len(data) >= 4 and isinstance(data[3], list):
                    for wiki_url in data[3]:
                        norm = normalize_url(wiki_url)
                        if norm and norm not in seen_urls and is_valid_url(norm):
                            is_safe, _ = is_safe_target_url(norm, resolve_dns=False)
                            if is_safe:
                                discovered_urls.append(norm)
                                seen_urls.add(norm)
                                if len(discovered_urls) >= max_results:
                                    break
        except Exception:
            pass

    return discovered_urls[:max_results]
