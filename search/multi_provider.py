"""
Multi-engine search provider that performs live web searches across multiple
open internet search engines (Bing, Algolia Open Index, Brave, Wikipedia)
without requiring API keys, ensuring out-of-the-box operation and fallback resilience.
"""

import time
import base64
import urllib.parse
from typing import Optional, Dict, Any, List
import requests
from bs4 import BeautifulSoup

from .provider import SearchProvider, SearchResult, SearchResultSet
from crawler.url_utils import is_valid_url, is_safe_target_url, normalize_url, get_domain


def decode_bing_u(u_val: str) -> Optional[str]:
    """Decode base64 encoded destination URL from Bing's redirect parameter."""
    if not u_val or not isinstance(u_val, str):
        return None
    raw = u_val[2:] if u_val.startswith("a1") else u_val
    padded = raw + "=" * (-len(raw) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
        if decoded.startswith("http://") or decoded.startswith("https://"):
            return decoded
    except Exception:
        pass
    return None


class MultiEngineSearchProvider(SearchProvider):
    """
    Zero-configuration search provider combining Bing live web search,
    Hacker News Algolia Open Index, and encyclopedic sources with domain diversity.
    """

    SEARCH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    SEARCH_ENGINE_DOMAINS = {
        "bing.com", "microsoft.com", "live.com", "msn.com",
        "duckduckgo.com", "google.com", "yahoo.com",
        "schema.org", "w3.org",
    }

    def __init__(self, timeout: float = 7.0, session: Optional[requests.Session] = None):
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def provider_name(self) -> str:
        return "Multi-Engine Open Web Search"

    def is_available(self) -> bool:
        """Always available as it does not require private API credentials."""
        return True

    def search(self, query: str, num_results: int = 10) -> SearchResultSet:
        """Execute web search across multiple open web engines and return unified results."""
        start_time = time.perf_counter()
        clean_query = (query or "").strip()

        if not clean_query:
            return SearchResultSet(query=clean_query, results=[], provider_name=self.provider_name)

        results: List[SearchResult] = []
        seen_urls = set()
        domain_counts: Dict[str, int] = {}
        max_per_domain = 2

        def try_add(title: str, url: str, snippet: str, date: Optional[str] = None) -> bool:
            if not url or url in seen_urls:
                return False
            norm = normalize_url(url)
            if not norm or norm in seen_urls or not is_valid_url(norm):
                return False
            is_safe, _ = is_safe_target_url(norm, resolve_dns=False)
            if not is_safe:
                return False

            dom = get_domain(norm).lower()
            if not dom or any(dom == b or dom.endswith("." + b) for b in self.SEARCH_ENGINE_DOMAINS):
                return False

            # Cap Wikipedia at max 2 entries so web search results remain diverse
            if "wikipedia.org" in dom and domain_counts.get("en.wikipedia.org", 0) >= 2:
                return False

            if domain_counts.get(dom, 0) >= max_per_domain:
                return False

            seen_urls.add(norm)
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
            results.append(
                SearchResult(
                    title=title or dom,
                    url=norm,
                    snippet=snippet or "",
                    published_date=date,
                    rank=len(results) + 1,
                )
            )
            return True

        # 1. Bing Live Open Web Search
        if len(results) < num_results:
            try:
                bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_query)}&setlang=en-US&cc=US"
                headers = {
                    "User-Agent": self.SEARCH_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                resp = self.session.get(bing_url, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for li in soup.find_all("li", class_="b_algo"):
                        h2 = li.find("h2")
                        if not h2:
                            continue
                        a = h2.find("a")
                        if not a:
                            continue
                        title = h2.get_text().strip()
                        href = a.get("href", "").strip()
                        target_url = None

                        if "bing.com/ck/a" in href and "u=" in href:
                            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if "u" in qs:
                                target_url = decode_bing_u(qs["u"][0])
                        elif href.startswith("http"):
                            target_url = href

                        if target_url:
                            # Extract snippet text from li
                            caption_div = li.find("div", class_="b_caption") or li.find("p")
                            snippet_text = caption_div.get_text().strip() if caption_div else ""
                            try_add(title, target_url, snippet_text)
                            if len(results) >= num_results:
                                break
            except Exception:
                pass

        # 2. Hacker News Algolia Open Web Index
        if len(results) < num_results:
            try:
                algolia_url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(clean_query)}&hitsPerPage=12"
                resp = self.session.get(algolia_url, headers={"User-Agent": self.SEARCH_USER_AGENT}, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    for hit in data.get("hits", []):
                        hit_url = hit.get("url")
                        if hit_url:
                            title = hit.get("title") or ""
                            date = hit.get("created_at", "")[:10] if hit.get("created_at") else None
                            snippet = hit.get("story_text") or hit.get("comment_text") or title
                            try_add(title, hit_url, snippet, date=date)
                            if len(results) >= num_results:
                                break
            except Exception:
                pass

        # 3. Wikipedia Full-Text Knowledge API
        if len(results) < num_results:
            try:
                wiki_api = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": clean_query,
                    "srlimit": 3,
                    "format": "json",
                }
                resp = self.session.get(wiki_api, params=params, headers={"User-Agent": "WebResearchEngine/2.0"}, timeout=self.timeout)
                if resp.status_code == 200:
                    for item in resp.json().get("query", {}).get("search", []):
                        title = item.get("title")
                        snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text()
                        if title:
                            slug = title.replace(" ", "_")
                            wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(slug)}"
                            try_add(title, wiki_url, snippet)
                            if len(results) >= num_results:
                                break
            except Exception:
                pass

        elapsed = time.perf_counter() - start_time
        return SearchResultSet(
            query=clean_query,
            results=results,
            provider_name=self.provider_name,
            total_results=len(results),
            search_time=elapsed,
        )
