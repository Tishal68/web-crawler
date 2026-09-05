"""
Unit tests for search query detection and multi-source web discovery.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests

from crawler.search_discovery import is_search_query, discover_search_urls


class TestSearchQueryDetection:
    """Test classification between explicit URLs/domains and internet search queries."""

    def test_explicit_urls(self):
        assert not is_search_query("https://example.com")
        assert not is_search_query("http://example.com/about")
        assert not is_search_query("https://en.wikipedia.org/wiki/Web_crawler")
        assert not is_search_query("http://192.168.1.1:8080/index.html")

    def test_domain_names_without_scheme(self):
        assert not is_search_query("example.com")
        assert not is_search_query("en.wikipedia.org")
        assert not is_search_query("subdomain.domain.co.uk")
        assert not is_search_query("docs.python.org/3/")

    def test_explicit_non_http_uri_schemes(self):
        assert not is_search_query("file:///C:/test.txt")
        assert not is_search_query("ftp://files.example.com")
        assert not is_search_query("invalid://url or nothing")
        assert not is_search_query("javascript:alert(1)")
        assert not is_search_query("data:text/html,<h1>hi</h1>")
        assert not is_search_query("mailto:admin@example.com")

    def test_words_phrases_and_sentences(self):
        assert is_search_query("artificial intelligence")
        assert is_search_query("how does a web crawler work?")
        assert is_search_query("quantum computing algorithms and qubits")
        assert is_search_query("python web scraping tutorial")
        assert is_search_query("search for quotes across the internet")
        assert is_search_query("machine learning")
        assert is_search_query("algorithm")

    def test_empty_and_whitespace(self):
        assert not is_search_query("")
        assert not is_search_query("   ")
        assert not is_search_query(None)


class TestSearchDiscovery:
    """Test search discovery URL resolution and SSRF defense."""

    @patch("requests.post")
    def test_duckduckgo_search_discovery(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
            <body>
                <a class="result__url" href="https://en.wikipedia.org/wiki/Web_crawler">Wikipedia Crawler</a>
                <a class="result__url" href="https://docs.python.org/3/library/urllib.html">Python Docs</a>
                <a class="result__url" href="https://duckduckgo.com/y.js?ad_provider=bing">Ad Redirect</a>
                <a class="result__url" href="http://127.0.0.1/admin">Internal SSRF</a>
            </body>
        </html>
        """
        mock_post.return_value = mock_resp

        results = discover_search_urls("web crawler architecture", max_results=5)
        assert len(results) >= 2
        assert "https://en.wikipedia.org/wiki/Web_crawler" in results
        assert "https://docs.python.org/3/library/urllib.html" in results
        # Ad redirect and loopback SSRF must be filtered out!
        assert not any("127.0.0.1" in r for r in results)
        assert not any("duckduckgo.com/y.js" in r for r in results)

    @patch("requests.post")
    @patch("requests.get")
    def test_fallback_to_wikipedia_when_duckduckgo_fails(self, mock_get, mock_post):
        # DuckDuckGo fails with 403 or network error
        mock_post.side_effect = requests.RequestException("Network Error")

        # Wikipedia OpenSearch responds
        mock_wiki = MagicMock()
        mock_wiki.status_code = 200
        mock_wiki.json.return_value = [
            "web crawler",
            ["Web crawler", "Web scraping"],
            ["A web crawler is a bot...", "Web scraping is..."],
            ["https://en.wikipedia.org/wiki/Web_crawler", "https://en.wikipedia.org/wiki/Web_scraping"]
        ]
        mock_get.return_value = mock_wiki

        results = discover_search_urls("web crawler", max_results=5)
        assert len(results) == 2
        assert "https://en.wikipedia.org/wiki/Web_crawler" in results
        assert "https://en.wikipedia.org/wiki/Web_scraping" in results

    @patch("requests.post")
    @patch("requests.get")
    def test_discovery_graceful_on_total_failure(self, mock_get, mock_post):
        mock_post.side_effect = requests.RequestException("DDG down")
        mock_get.side_effect = requests.RequestException("Wiki down")

        results = discover_search_urls("some rare term", max_results=5)
        assert results == []
