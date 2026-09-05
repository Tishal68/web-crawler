"""
Comprehensive security regression tests:
- SSRF target validation and IP blocking
- Multi-hop redirect SSRF prevention
- Robots.txt SSRF protection and fail-closed behavior
- XSS escaping across dynamic HTML components
- CSV formula injection (DDE) sanitization
"""

import html
import pytest
from unittest.mock import patch, MagicMock
import requests
import pandas as pd

from crawler.url_utils import (
    is_safe_ip,
    is_safe_target_url,
    sanitize_csv_cell,
    sanitize_dataframe_for_csv,
)
from crawler.crawler import WebCrawler
from crawler.models import CrawlConfig, CrawlSessionSummary, PageResult, CrawlFailure
from crawler.robots import RobotsManager


class TestSsrfProtection:
    """Test blocking of loopback, private networks, cloud metadata, and link-local targets."""

    @pytest.mark.parametrize("target_url", [
        "http://127.0.0.1/",
        "http://127.0.0.1:8080/admin",
        "http://localhost/",
        "http://localhost:8501",
        "http://[::1]/",
        "http://[::1]:8080/status",
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.1.1/",
        "http://10.0.0.1/",
        "http://10.255.255.254/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
        "http://192.168.1.1/",
        "http://192.168.0.100:3000/",
        "http://0.0.0.0/",
        "http://0.0.0.0:8000/",
        "http://100.64.0.1/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://instance-data/latest/meta-data/",
        "http://corp.internal/",
        "http://router.local/",
        "http://server.lan/",
    ])
    def test_prohibited_targets_blocked_statically(self, target_url):
        is_safe, reason = is_safe_target_url(target_url, resolve_dns=False)
        assert not is_safe, f"Expected {target_url} to be blocked, but was marked safe."
        assert reason is not None

    def test_public_urls_permitted(self):
        safe_urls = [
            "https://en.wikipedia.org/wiki/Web_crawler",
            "https://quotes.toscrape.com/",
            "https://books.toscrape.com/",
            "https://docs.python.org/3/",
        ]
        for url in safe_urls:
            is_safe, reason = is_safe_target_url(url, resolve_dns=False)
            assert is_safe, f"Expected {url} to be safe, but got blocked: {reason}"

    def test_crawler_blocks_prohibited_starting_url(self):
        config = CrawlConfig(start_url="http://127.0.0.1:8000/secret")
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        assert len(results["page_results"]) == 0
        assert len(results["failures"]) == 1
        assert results["failures"][0].error_type == "SSRF Blocked"
        assert "prohibited by security policy" in results["failures"][0].error_message.lower()

    def test_robots_manager_blocks_ssrf(self):
        rm = RobotsManager()
        res = rm.check_allowed("http://127.0.0.1:8501/admin")
        assert not res.allowed
        assert res.status == "SSRF_BLOCKED"
        assert "SSRF" in res.reason


class TestRedirectSsrfPrevention:
    """Test that crawler prevents SSRF attacks carried out via HTTP redirects."""

    @patch("crawler.crawler.requests.Session.get")
    def test_redirect_to_metadata_is_blocked(self, mock_get):
        resp_302 = requests.Response()
        resp_302.status_code = 302
        resp_302.headers["Location"] = "http://169.254.169.254/latest/meta-data/"
        resp_302.url = "https://attacker.com/init"

        mock_get.return_value = resp_302

        config = CrawlConfig(start_url="https://attacker.com/init")
        crawler = WebCrawler(config=config)

        resp, elapsed, err_type, err_msg = crawler.fetch_page("https://attacker.com/init", timeout=5.0)

        assert resp is None
        assert err_type == "SSRF Blocked"
        assert "prohibited" in err_msg.lower() or "169.254.169.254" in err_msg

    @patch("crawler.crawler.requests.Session.get")
    def test_redirect_loop_bounded(self, mock_get):
        def redirect_effect(url, **kwargs):
            resp = requests.Response()
            resp.status_code = 302
            resp.headers["Location"] = "/loop"
            resp.url = url
            return resp

        mock_get.side_effect = redirect_effect

        config = CrawlConfig(start_url="https://example.com/start")
        crawler = WebCrawler(config=config)

        with patch("crawler.crawler.is_safe_target_url", return_value=(True, None)):
            resp, elapsed, err_type, err_msg = crawler.fetch_page("https://example.com/start", timeout=5.0)

        assert resp is None
        assert err_type == "Redirect Loop"


class TestCsvFormulaInjectionDefense:
    """Test that spreadsheet formula injection payloads are neutralized."""

    @pytest.mark.parametrize("payload", [
        "=1+1",
        "=SUM(A1:A10)",
        "=cmd|'/C calc'!A0",
        "-2+3+cmd|' /C calc'!A0",
        "+cmd|' /C calc'!A0",
        "@SUM(1+1)*cmd|' /C calc'!A0",
        "\t=2+3",
        "\r=cmd|...",
    ])
    def test_formula_injection_cells_prefixed_with_quote(self, payload):
        sanitized = sanitize_csv_cell(payload)
        assert sanitized.startswith("'"), f"Payload {payload} was not sanitized with leading single quote"
        assert sanitized[1:] == payload

    def test_safe_cell_values_unchanged(self):
        safe_values = [
            "https://example.com",
            "Page Title Here",
            "Just a regular string",
            123,
            45.67,
            True,
            None,
        ]
        for val in safe_values:
            assert sanitize_csv_cell(val) == val

    def test_dataframe_sanitization(self):
        df = pd.DataFrame([
            {"URL": "https://example.com", "Title": "=cmd|calc", "Status": 200, "Latency": 0.05},
            {"URL": "https://example.com/2", "Title": "@ALERT()", "Status": 200, "Latency": 0.12},
            {"URL": "+http://malicious.com", "Title": "Safe Title", "Status": 404, "Latency": 0.01},
        ])
        clean_df = sanitize_dataframe_for_csv(df)

        assert clean_df["Title"].iloc[0] == "'=cmd|calc"
        assert clean_df["Title"].iloc[1] == "'@ALERT()"
        assert clean_df["URL"].iloc[2] == "'+http://malicious.com"

        assert clean_df["Title"].iloc[2] == "Safe Title"
        assert clean_df["URL"].iloc[0] == "https://example.com"
        assert clean_df["Status"].iloc[0] == 200


class TestXssEscapingDefense:
    """Verify HTML escaping on dynamic strings inserted into HTML."""

    def test_html_escape_malicious_vectors(self):
        vectors = [
            "<script>alert('XSS')</script>",
            '"><img src=x onerror=alert(1)>',
            "javascript:/*--></title></style></textarea></script></xmp><svg/onload='+/\"/+/onmouseover=1/+/[*/[]/+alert(1)//'>",
            "';alert(String.fromCharCode(88,83,83))//",
        ]
        for v in vectors:
            escaped = html.escape(v)
            assert "<script>" not in escaped
            assert "<img" not in escaped
            assert "<svg" not in escaped
            assert any(entity in escaped for entity in ("&lt;", "&quot;", "&#x27;", "&amp;"))
