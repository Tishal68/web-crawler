"""
Search discovery engine that enables crawling arbitrary words, phrases, sentences,
and topics across the internet by resolving authoritative seed URLs from multiple
open search providers with strict SSRF filtering and domain diversity.
"""

import re
import base64
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from .url_utils import is_valid_url, is_safe_target_url, normalize_url, is_binary_url, get_domain

# Standard user-agent for public search requests
SEARCH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Internal/Self-referential domains to filter out from search results
SEARCH_ENGINE_DOMAINS = {
    "bing.com",
    "microsoft.com",
    "live.com",
    "msn.com",
    "xbox.com",
    "windows.com",
    "duckduckgo.com",
    "google.com",
    "yahoo.com",
    "schema.org",
    "w3.org",
}

# Generic dictionary/reference sites to avoid when crawling topic queries
DICTIONARY_DOMAINS = {
    "merriam-webster.com",
    "dictionary.cambridge.org",
    "thefreedictionary.com",
    "dictionary.com",
    "wordreference.com",
}


def decode_bing_u(u_val: str) -> Optional[str]:
    """
    Decode base64 encoded destination URL from Bing's redirect 'u' parameter.
    Bing URLs are of the form: https://www.bing.com/ck/a?!...&u=a1aHR0cHM6Ly9...
    """
    if not u_val or not isinstance(u_val, str):
        return None

    # Bing's 'u' parameter typically starts with 'a1' indicating base64 encoded URL
    raw = u_val[2:] if u_val.startswith("a1") else u_val
    # Restore base64 padding
    padded = raw + "=" * (-len(raw) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
        if decoded.startswith("http://") or decoded.startswith("https://"):
            return decoded
    except Exception:
        pass
    return None


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
    max_per_domain: int = 2,
) -> List[str]:
    """
    Discover authoritative seed URLs across the entire internet for a given word, sentence,
    or topic query using multi-source discovery (Bing Web Search, Algolia Open Index,
    Brave Search, and Wikipedia) with strict SSRF filtering and domain diversity.

    Args:
        query: Words or sentence to search for.
        max_results: Maximum number of seed URLs to return.
        timeout: Request timeout in seconds per provider.
        session: Optional requests.Session instance.
        max_per_domain: Maximum allowed seed URLs per domain to ensure internet-wide diversity.

    Returns:
        List of safe, normalized, deduplicated HTTP/S URLs spanning diverse internet domains.
    """
    if not query or not query.strip():
        return []

    clean_query = query.strip()
    get_fn = session.get if session is not None else requests.get
    post_fn = session.post if session is not None else requests.post

    discovered_urls: List[str] = []
    seen_urls = set()
    domain_counts: Dict[str, int] = {}

    is_multi_word = len(clean_query.split()) > 1

    def try_add_candidate(raw_url: str) -> bool:
        """Validate, normalize, check SSRF, and add candidate if domain diversity allows."""
        if not raw_url:
            return False

        norm = normalize_url(raw_url)
        if not norm or norm in seen_urls or not is_valid_url(norm) or is_binary_url(norm):
            return False

        # SSRF validation
        is_safe, _ = is_safe_target_url(norm, resolve_dns=False)
        if not is_safe:
            return False

        dom = get_domain(norm).lower()
        if not dom or any(dom == bad or dom.endswith("." + bad) for bad in SEARCH_ENGINE_DOMAINS):
            return False

        # For multi-word queries, avoid generic dictionary entry cards
        if is_multi_word and any(dom == d or dom.endswith("." + d) for d in DICTIONARY_DOMAINS):
            return False

        # If it's Wikipedia, cap Wikipedia at max_per_domain so it doesn't crowd out the web
        if "wikipedia.org" in dom and domain_counts.get("en.wikipedia.org", 0) >= max_per_domain:
            return False

        # Domain diversity constraint
        if domain_counts.get(dom, 0) >= max_per_domain:
            return False

        seen_urls.add(norm)
        domain_counts[dom] = domain_counts.get(dom, 0) + 1
        discovered_urls.append(norm)
        return True

    # =========================================================================
    # 1. Bing Live Open Web Search (Primary internet-wide web search engine)
    # =========================================================================
    if len(discovered_urls) < max_results:
        try:
            bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_query)}&setlang=en-US&cc=US"
            headers = {
                "User-Agent": SEARCH_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = get_fn(bing_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.find_all("li", class_="b_algo"):
                    # Check if li has h2 title link
                    h2 = li.find("h2")
                    if not h2:
                        continue
                    a_tag = h2.find("a")
                    if not a_tag:
                        continue

                    href = a_tag.get("href", "").strip()
                    target_url = None

                    # If Bing redirect wrapper, decode the base64 destination URL
                    if "bing.com/ck/a" in href and "u=" in href:
                        qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "u" in qs:
                            target_url = decode_bing_u(qs["u"][0])
                    elif href.startswith("http"):
                        target_url = href

                    if target_url:
                        try_add_candidate(target_url)
                        if len(discovered_urls) >= max_results:
                            break
        except Exception:
            pass

    # =========================================================================
    # 2. Hacker News Algolia Open Web Search (Blogs, tech, news, independent web)
    # =========================================================================
    if len(discovered_urls) < max_results:
        try:
            algolia_url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(clean_query)}&hitsPerPage=15"
            hn_resp = get_fn(algolia_url, headers={"User-Agent": SEARCH_USER_AGENT}, timeout=timeout)
            if hn_resp.status_code == 200:
                data = hn_resp.json()
                for hit in data.get("hits", []):
                    hit_url = hit.get("url")
                    if hit_url:
                        try_add_candidate(hit_url)
                        if len(discovered_urls) >= max_results:
                            break
        except Exception:
            pass

    # =========================================================================
    # 3. Brave Search (Live fallback)
    # =========================================================================
    if len(discovered_urls) < max_results:
        try:
            brave_url = f"https://search.brave.com/search?q={urllib.parse.quote(clean_query)}"
            b_resp = get_fn(brave_url, headers={"User-Agent": SEARCH_USER_AGENT}, timeout=timeout)
            if b_resp.status_code == 200 and len(b_resp.text) > 10000:
                soup = BeautifulSoup(b_resp.text, "html.parser")
                for a_tag in soup.find_all("a"):
                    href = a_tag.get("href", "").strip()
                    if href.startswith("http") and not any(bad in href for bad in ("brave.com", "search.brave")):
                        try_add_candidate(href)
                        if len(discovered_urls) >= max_results:
                            break
        except Exception:
            pass

    # =========================================================================
    # 4. DuckDuckGo HTML Search (Fallback attempt)
    # =========================================================================
    if len(discovered_urls) < max_results:
        try:
            ddg_resp = post_fn(
                "https://html.duckduckgo.com/html/",
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
                    if "/l/?uddg=" in href:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "uddg" in parsed_qs:
                            href = parsed_qs["uddg"][0]
                    try_add_candidate(href)
                    if len(discovered_urls) >= max_results:
                        break
        except Exception:
            pass

    # =========================================================================
    # 5. Wikipedia Full-Text Search (Knowledge graph complement)
    # =========================================================================
    if len(discovered_urls) < max_results:
        try:
            wiki_api = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": clean_query,
                "srlimit": 3,
                "format": "json",
            }
            wiki_resp = get_fn(
                wiki_api,
                params=params,
                headers={"User-Agent": "WebCrawlerAnalytics/2.0"},
                timeout=timeout,
            )
            if wiki_resp.status_code == 200:
                data = wiki_resp.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title")
                    if title:
                        article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        try_add_candidate(article_url)
                        if len(discovered_urls) >= max_results:
                            break
        except Exception:
            pass

    # =========================================================================
    # 6. Wikipedia OpenSearch API (Final fallback if still under target count)
    # =========================================================================
    if len(discovered_urls) < max_results:
        try:
            wiki_api = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": clean_query,
                "limit": 3,
                "namespace": "0",
                "format": "json",
            }
            wiki_resp = get_fn(
                wiki_api,
                params=params,
                headers={"User-Agent": "WebCrawlerAnalytics/2.0"},
                timeout=timeout,
            )
            if wiki_resp.status_code == 200:
                data = wiki_resp.json()
                if len(data) >= 4 and isinstance(data[3], list):
                    for wiki_url in data[3]:
                        try_add_candidate(wiki_url)
                        if len(discovered_urls) >= max_results:
                            break
        except Exception:
            pass

    return discovered_urls[:max_results]
