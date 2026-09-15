"""
Unit and integration tests for PlaywrightBrowserManager and JavaScript rendering in WebCrawler.
"""

from unittest.mock import patch, MagicMock
import pytest

from crawler.models import CrawlConfig, PageResult
from crawler.browser_fetcher import PlaywrightBrowserManager
from crawler.crawler import WebCrawler


class TestPlaywrightBrowserManager:
    """Tests for headless browser manager and SSRF protection."""

    def test_availability(self):
        """is_available should return a boolean without throwing an exception."""
        avail = PlaywrightBrowserManager.is_available()
        assert isinstance(avail, bool)

    def test_ssrf_pre_navigation_blocked(self):
        """Private/internal IP targets must be blocked before any browser navigation."""
        manager = PlaywrightBrowserManager()
        # Attempt to target AWS metadata service
        html, status, elapsed, err_type, err_msg, final_url = manager.fetch_page("http://169.254.169.254/latest/meta-data/")
        assert err_type == "SSRF Blocked"
        assert html is None
        assert "security policy" in err_msg.lower()

        # Attempt loopback
        html, status, elapsed, err_type, err_msg, final_url = manager.fetch_page("http://127.0.0.1:8080/admin")
        assert err_type == "SSRF Blocked"
        assert html is None

    def test_browser_lifecycle_state(self):
        """Browser manager should report active after start and inactive after close."""
        manager = PlaywrightBrowserManager()
        assert manager._is_active is False
        started = manager.start()
        if started:
            assert manager._is_active is True
            manager.close()
            assert manager._is_active is False
            assert manager._browser is None
            assert manager._context is None

    def test_render_js_config_defaults(self):
        """CrawlConfig must default to render_js=False and js_wait_time=2.0."""
        config = CrawlConfig(start_url="https://example.com")
        assert config.render_js is False
        assert config.js_wait_time == 2.0

        custom_config = CrawlConfig(start_url="https://example.com", render_js=True, js_wait_time=3.5)
        assert custom_config.render_js is True
        assert custom_config.js_wait_time == 3.5

    def test_crawler_cleans_up_browser_in_finally(self):
        """WebCrawler must safely close the browser manager when the crawl finishes."""
        mock_bm = MagicMock()
        mock_bm.start.return_value = True
        mock_bm.fetch_page.return_value = (
            "<html><head><title>Test SPA</title></head><body><a href='/link1'>Link 1</a></body></html>",
            200,
            0.5,
            None,
            None,
            "https://example.com/",
        )

        config = CrawlConfig(start_url="https://example.com", max_pages=1, render_js=True)
        crawler = WebCrawler(config=config)

        with patch("crawler.crawler.PlaywrightBrowserManager", return_value=mock_bm):
            events = list(crawler.crawl_stream())
            assert mock_bm.start.called
            assert mock_bm.close.called
            assert len(crawler.page_results) == 1
            assert crawler.page_results[0].title == "Test SPA"
