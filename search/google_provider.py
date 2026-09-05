"""
Google Custom Search API Provider implementation.
Integrates with Google Web Search Service / Custom Search JSON API securely
using credentials from environment variables or Streamlit secrets.
"""

import os
import time
import requests
from typing import Optional, Dict, Any, List

from .provider import SearchProvider, SearchResult, SearchResultSet
from crawler.url_utils import is_valid_url, is_safe_target_url, normalize_url


class GoogleSearchProvider(SearchProvider):
    """
    Search provider using the Google Custom Search JSON API.
    Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID / GOOGLE_CSE_ID.
    """

    ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cse_id: Optional[str] = None,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ):
        self._api_key = api_key or self._get_secret("GOOGLE_SEARCH_API_KEY") or self._get_secret("GOOGLE_API_KEY")
        self._cse_id = (
            cse_id
            or self._get_secret("GOOGLE_SEARCH_ENGINE_ID")
            or self._get_secret("GOOGLE_CSE_ID")
            or self._get_secret("GOOGLE_SEARCH_CX")
        )
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def provider_name(self) -> str:
        return "Google Web Search"

    def _get_secret(self, key_name: str) -> Optional[str]:
        """Safely fetch secret from environment variables or Streamlit secrets."""
        val = os.environ.get(key_name)
        if val:
            return val.strip()
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key_name in st.secrets:
                return str(st.secrets[key_name]).strip()
        except Exception:
            pass
        return None

    def is_available(self) -> bool:
        """Check if both API key and Search Engine ID are configured."""
        return bool(self._api_key and self._cse_id)

    def get_masked_key(self) -> str:
        """Return masked API key for logging or UI diagnostics."""
        if not self._api_key:
            return "NOT_CONFIGURED"
        if len(self._api_key) <= 8:
            return "***"
        return f"{self._api_key[:4]}...{self._api_key[-4:]}"

    def _get_masked_key(self) -> str:
        """Alias for internal and test compatibility."""
        return self.get_masked_key()

    def search(self, query: str, num_results: int = 10) -> SearchResultSet:
        """Execute query against Google Custom Search API."""
        start_time = time.perf_counter()
        clean_query = (query or "").strip()

        if not clean_query:
            return SearchResultSet(
                query=clean_query,
                results=[],
                provider_name=self.provider_name,
                search_time=0.0,
            )

        if not self.is_available():
            return SearchResultSet(
                query=clean_query,
                results=[],
                provider_name=self.provider_name,
                search_time=0.0,
                error_message="Google Search API credentials not configured (GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID).",
            )

        params = {
            "key": self._api_key,
            "cx": self._cse_id,
            "q": clean_query,
            "num": min(max(1, num_results), 10),
        }

        try:
            resp = self.session.get(self.ENDPOINT, params=params, timeout=self.timeout)
            elapsed = time.perf_counter() - start_time

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                results: List[SearchResult] = []

                for idx, item in enumerate(items):
                    link = item.get("link", "").strip()
                    if not link or not is_valid_url(link):
                        continue

                    # SSRF prevention
                    is_safe, _ = is_safe_target_url(link, resolve_dns=False)
                    if not is_safe:
                        continue

                    title = item.get("title", "Untitled")
                    snippet = item.get("snippet", "")

                    # Extract published date from pagemap metatags if present
                    pub_date = self._extract_date_from_pagemap(item.get("pagemap", {}))

                    results.append(
                        SearchResult(
                            title=title,
                            url=link,
                            snippet=snippet,
                            published_date=pub_date,
                            rank=idx + 1,
                            raw_data={"google_item": item},
                        )
                    )

                total = int(data.get("searchInformation", {}).get("totalResults", len(results)))
                return SearchResultSet(
                    query=clean_query,
                    results=results,
                    provider_name=self.provider_name,
                    total_results=total,
                    search_time=elapsed,
                )

            elif resp.status_code in (400, 403):
                # Quota exceeded or invalid key - do not leak the key in error message
                return SearchResultSet(
                    query=clean_query,
                    results=[],
                    provider_name=self.provider_name,
                    search_time=elapsed,
                    error_message=f"Google Search API authorization or quota error (HTTP {resp.status_code}). Please verify Search Engine ID and API limits.",
                )
            else:
                return SearchResultSet(
                    query=clean_query,
                    results=[],
                    provider_name=self.provider_name,
                    search_time=elapsed,
                    error_message=f"Google Search API returned status code {resp.status_code}.",
                )

        except requests.exceptions.Timeout:
            elapsed = time.perf_counter() - start_time
            return SearchResultSet(
                query=clean_query,
                results=[],
                provider_name=self.provider_name,
                search_time=elapsed,
                error_message="Google Search API request timed out.",
            )
        except requests.exceptions.RequestException as e:
            elapsed = time.perf_counter() - start_time
            return SearchResultSet(
                query=clean_query,
                results=[],
                provider_name=self.provider_name,
                search_time=elapsed,
                error_message=f"Network error connecting to Google Search API: {type(e).__name__}",
            )

    @staticmethod
    def _extract_date_from_pagemap(pagemap: Dict[str, Any]) -> Optional[str]:
        """Extract publication/updated date from Google pagemap metadata."""
        if not pagemap or not isinstance(pagemap, dict):
            return None

        metatags = pagemap.get("metatags", [])
        if isinstance(metatags, list) and metatags:
            first_meta = metatags[0]
            if isinstance(first_meta, dict):
                for key in (
                    "article:published_time",
                    "og:published_time",
                    "date",
                    "pubdate",
                    "sailthru.date",
                    "article:modified_time",
                    "og:updated_time",
                ):
                    if key in first_meta and first_meta[key]:
                        return str(first_meta[key]).strip()[:10]
        return None
