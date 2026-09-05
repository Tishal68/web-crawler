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


from crawler.search_discovery import is_search_query, discover_search_urls, decode_bing_u


class TestBingDecode:
    def test_decode_bing_u(self):
        # 'https://www.ibm.com/think/topics/quantum-computing'
        u_param = "a1aHR0cHM6Ly93d3cuaWJtLmNvbS90aGluay90b3BpY3MvcXVhbnR1bS1jb21wdXRpbmc"
        assert decode_bing_u(u_param) == "https://www.ibm.com/think/topics/quantum-computing"

    def test_decode_bing_u_invalid(self):
        assert decode_bing_u("") is None
        assert decode_bing_u(None) is None
        assert decode_bing_u("invalid_not_base64") is None


class TestSearchDiscovery:
    """Test search discovery URL resolution, multi-source engines, and SSRF defense."""

    @patch("requests.get")
    def test_bing_search_discovery(self, mock_get):
        bing_resp = MagicMock()
        bing_resp.status_code = 200
        bing_resp.text = """
        <html>
            <body>
                <li class="b_algo">
                    <h2><a href="https://www.bing.com/ck/a?!&&u=a1aHR0cHM6Ly93d3cuaWJtLmNvbS9xdWFudHVt">IBM Quantum</a></h2>
                </li>
                <li class="b_algo">
                    <h2><a href="https://www.bing.com/ck/a?!&&u=a1aHR0cHM6Ly93d3cubmFzYS5nb3Yvc3BhY2U">NASA Space</a></h2>
                </li>
                <li class="b_algo">
                    <h2><a href="https://www.bing.com/ck/a?!&&u=a1aHR0cDovLzEyNy4wLjAuMS9hZG1pbg">SSRF Loopback</a></h2>
                </li>
            </body>
        </html>
        """
        mock_get.return_value = bing_resp

        results = discover_search_urls("quantum computing", max_results=5)
        assert len(results) == 2
        assert "https://www.ibm.com/quantum" in results
        assert "https://www.nasa.gov/space" in results
        # SSRF blocked
        assert not any("127.0.0.1" in r for r in results)

    @patch("requests.get")
    def test_algolia_open_index_discovery(self, mock_get):
        # Bing returns empty, Algolia returns tech articles
        bing_resp = MagicMock()
        bing_resp.status_code = 403

        hn_resp = MagicMock()
        hn_resp.status_code = 200
        hn_resp.json.return_value = {
            "hits": [
                {"title": "Words Filippo", "url": "https://words.filippo.io/crqc-timeline/"},
                {"title": "Quantum Country", "url": "https://quantum.country/intro"},
                {"title": "Internal", "url": "http://169.254.169.254/latest"},
            ]
        }
        mock_get.side_effect = [bing_resp, hn_resp]

        results = discover_search_urls("quantum cryptography", max_results=5)
        assert any("words.filippo.io" in r for r in results)
        assert "https://quantum.country/intro" in results
        # Link-local metadata blocked
        assert not any("169.254.169.254" in r for r in results)

    @patch("requests.post")
    @patch("requests.get")
    def test_duckduckgo_search_discovery(self, mock_get, mock_post):
        # GET (Bing, Algolia, Brave) fails
        mock_get.side_effect = requests.RequestException("GET failed")

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
    def test_fallback_to_wikipedia_when_others_fail(self, mock_get, mock_post):
        # DuckDuckGo and other engines fail
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
        # Bing, Algolia, Brave, and Wiki Query all fail; Wiki OpenSearch succeeds
        mock_get.side_effect = [
            requests.RequestException("Bing fail"),
            requests.RequestException("Algolia fail"),
            requests.RequestException("Brave fail"),
            requests.RequestException("Wiki Query fail"),
            mock_wiki,
        ]

        results = discover_search_urls("web crawler", max_results=5, max_per_domain=2)
        assert len(results) == 2
        assert "https://en.wikipedia.org/wiki/Web_crawler" in results
        assert "https://en.wikipedia.org/wiki/Web_scraping" in results

    @patch("requests.post")
    @patch("requests.get")
    def test_discovery_graceful_on_total_failure(self, mock_get, mock_post):
        mock_post.side_effect = requests.RequestException("DDG down")
        mock_get.side_effect = requests.RequestException("GET down")

        results = discover_search_urls("some rare term", max_results=5)
        assert results == []

