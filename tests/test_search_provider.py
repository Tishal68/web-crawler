"""
Unit tests for SearchProvider interface, GoogleSearchProvider,
MultiEngineSearchProvider, and SearchCache.
"""

import time
from unittest.mock import patch, MagicMock
import pytest

from search.provider import SearchResult, SearchResultSet, SearchProvider
from search.google_provider import GoogleSearchProvider
from search.multi_provider import MultiEngineSearchProvider, decode_bing_u
from search.cache import SearchCache


class DummyProvider(SearchProvider):
    @property
    def provider_name(self) -> str:
        return "Dummy"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, num_results: int = 10) -> SearchResultSet:
        return SearchResultSet(
            query=query,
            provider_name=self.provider_name,
            results=[
                SearchResult(title="Result 1", url="https://example.com/1", snippet="Snippet 1"),
                SearchResult(title="Result 2", url="https://example.com/2", snippet="Snippet 2"),
            ],
            total_results=2,
        )


def test_search_result_normalization_and_domain():
    res = SearchResult(
        title="Test Page",
        url="https://Sub.Example.com/Path/#Fragment",
        snippet="A snippet",
    )
    assert res.display_domain == "sub.example.com"
    assert "#Fragment" not in res.url
    d = res.to_dict()
    assert d["title"] == "Test Page"
    assert d["url"] == res.url


def test_search_result_set_to_dict():
    rs = SearchResultSet(
        query="test query",
        provider_name="TestEngine",
        results=[
            SearchResult(title="A", url="https://a.com", snippet="Sa"),
        ],
        total_results=1,
        search_time=0.45,
    )
    d = rs.to_dict()
    assert d["query"] == "test query"
    assert len(d["results"]) == 1
    assert d["total_results"] == 1
    assert d["search_time"] == 0.45


def test_google_provider_availability(monkeypatch):
    monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)
    gp = GoogleSearchProvider()
    assert not gp.is_available()

    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "AIzaSyTestKey123")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx123456789")
    gp_ready = GoogleSearchProvider()
    assert gp_ready.is_available()


def test_google_provider_credential_masking(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "AIzaSySecretLongKey987654")
    gp = GoogleSearchProvider()
    masked = gp._get_masked_key()
    assert masked.startswith("AIza")
    assert masked.endswith("7654")
    assert "SecretLong" not in masked


def test_google_provider_search_mocked(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "dummy_key")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "dummy_cx")
    gp = GoogleSearchProvider()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "searchInformation": {"totalResults": "42"},
        "items": [
            {
                "title": "Quantum Advancements",
                "link": "https://nature.com/articles/quantum-2026",
                "snippet": "Researchers announce breakthroughs in error correction.",
                "pagemap": {
                    "metatags": [{"article:published_time": "2026-02-15"}]
                }
            }
        ]
    }

    with patch.object(gp.session, "get", return_value=mock_resp):
        res_set = gp.search("quantum computing 2026", num_results=5)
        assert len(res_set.results) == 1
        r = res_set.results[0]
        assert r.title == "Quantum Advancements"
        assert r.published_date == "2026-02-15"
        assert r.display_domain == "nature.com"
        assert res_set.total_results == 42


def test_decode_bing_u():
    import base64
    assert decode_bing_u(None) is None
    assert decode_bing_u("") is None
    encoded = "a1" + base64.urlsafe_b64encode(b"https://example.com").decode().rstrip("=")
    assert decode_bing_u(encoded) == "https://example.com"


def test_multi_provider_availability():
    mp = MultiEngineSearchProvider()
    assert mp.is_available()
    assert mp.provider_name == "Multi-Engine Open Web Search"


def test_extract_query_stems():
    from search.multi_provider import extract_query_stems
    stems = extract_query_stems("James Webb Space Telescope instruments and discoveries")
    assert "telescope" in stems
    assert "webb" in stems
    assert "instrument" in stems
    assert "discoveri" in stems
    assert "and" not in stems


def test_multi_provider_relevance_filtering():
    from search.multi_provider import MultiEngineSearchProvider
    mp = MultiEngineSearchProvider()

    # Mock response with 1 relevant and 1 completely off-target result
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
        <body>
            <li class="b_algo">
                <h2><a href="https://example.com/relevant">Webb Space Telescope Instruments Overview</a></h2>
                <div class="b_caption"><p>NASA Webb Space Telescope instruments and discoveries</p></div>
            </li>
            <li class="b_algo">
                <h2><a href="https://example.com/spam">King James Version Online Chapters</a></h2>
                <div class="b_caption"><p>Read scripture chapters online</p></div>
            </li>
        </body>
    </html>
    """
    with patch.object(mp.session, "get", return_value=mock_resp):
        res_set = mp.search("James Webb Space Telescope instruments", num_results=5)
        urls = [r.url for r in res_set.results]
        assert "https://example.com/relevant" in urls
        assert "https://example.com/spam" not in urls


def test_search_cache_ttl_and_stats():
    cache = SearchCache(default_ttl_seconds=1)
    rs = SearchResultSet(query="cache test", provider_name="Dummy", results=[])

    # Cache Miss
    assert cache.get("cache test", "Dummy", 5) is None
    # Set Cache
    cache.set("cache test", "Dummy", rs, num_results=5)
    # Cache Hit
    hit = cache.get("cache test", "Dummy", 5)
    assert hit is not None
    assert hit.query == "cache test"

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1

    # Wait for TTL expiration
    time.sleep(1.1)
    assert cache.get("cache test", "Dummy", 5) is None

    cache.clear()
    assert cache.stats()["size"] == 0
