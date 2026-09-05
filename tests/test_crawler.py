"""
Integration and mock unit tests for WebCrawler traversal depths, duplicate prevention,
error handling resilience, and SQLite storage.
"""

import pytest
from unittest.mock import MagicMock, patch
import requests

from crawler.models import CrawlConfig, PageResult, CrawlFailure
from crawler.crawler import WebCrawler
from crawler.database import CrawlDatabase


# Helper to build mock response
def mock_html_response(url: str, html: str, status_code: int = 200) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status_code
    resp.url = url
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp._content = html.encode("utf-8")
    return resp


class TestWebCrawlerDepthAndTraversal:
    @patch.object(WebCrawler, "fetch_page")
    def test_depth_0_crawls_only_seed(self, mock_fetch):
        # Starting page has 2 links
        seed_html = """
        <html><head><title>Seed Page</title></head>
        <body>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
        </body></html>
        """
        mock_fetch.return_value = (
            mock_html_response("https://example.com", seed_html),
            0.05,
            None,
            None,
        )

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=0,
            max_pages=50,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Depth 0: only seed page is crawled
        assert len(results["page_results"]) == 1
        page = results["page_results"][0]
        assert page.url == "https://example.com"
        assert page.depth == 0
        assert page.title == "Seed Page"
        assert page.unique_links == 2
        assert mock_fetch.call_count == 1

    @patch.object(WebCrawler, "fetch_page")
    def test_depth_1_crawls_seed_and_direct_links(self, mock_fetch):
        site_map = {
            "https://example.com": """
                <html><head><title>Home</title></head><body>
                    <a href="/sub1">Sub 1</a>
                    <a href="/sub2">Sub 2</a>
                </body></html>
            """,
            "https://example.com/sub1": """
                <html><head><title>Sub 1</title></head><body>
                    <a href="/deep">Deep Page</a>
                </body></html>
            """,
            "https://example.com/sub2": """
                <html><head><title>Sub 2</title></head><body>
                    <p>Leaf page</p>
                </body></html>
            """,
            "https://example.com/deep": """
                <html><head><title>Deep Page</title></head><body></body></html>
            """,
        }

        def side_effect(url, timeout):
            html = site_map.get(url, "<html><body>Not Found</body></html>")
            return mock_html_response(url, html), 0.02, None, None

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=1,
            max_pages=50,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Depth 1 should crawl: Home (depth 0), Sub 1 (depth 1), Sub 2 (depth 1)
        # Deep page (depth 2) should NOT be crawled!
        crawled_urls = [p.url for p in results["page_results"]]
        assert len(crawled_urls) == 3
        assert "https://example.com" in crawled_urls
        assert "https://example.com/sub1" in crawled_urls
        assert "https://example.com/sub2" in crawled_urls
        assert "https://example.com/deep" not in crawled_urls

    @patch.object(WebCrawler, "fetch_page")
    def test_depth_2_traversal(self, mock_fetch):
        site_map = {
            "https://example.com": '<html><head><title>Home</title></head><body><a href="/d1">D1</a></body></html>',
            "https://example.com/d1": '<html><head><title>D1</title></head><body><a href="/d2">D2</a></body></html>',
            "https://example.com/d2": '<html><head><title>D2</title></head><body><a href="/d3">D3</a></body></html>',
            "https://example.com/d3": '<html><head><title>D3</title></head><body></body></html>',
        }

        def side_effect(url, timeout):
            html = site_map.get(url, "<html><body>404</body></html>")
            return mock_html_response(url, html), 0.01, None, None

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=2,
            max_pages=50,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Depth 2 should crawl: Home (0), D1 (1), D2 (2). D3 (depth 3) must NOT be crawled.
        crawled_urls = [p.url for p in results["page_results"]]
        assert len(crawled_urls) == 3
        assert "https://example.com" in crawled_urls
        assert "https://example.com/d1" in crawled_urls
        assert "https://example.com/d2" in crawled_urls
        assert "https://example.com/d3" not in crawled_urls

    @patch.object(WebCrawler, "fetch_page")
    def test_duplicate_prevention_and_circular_loops(self, mock_fetch):
        # A links to B and C. B links to A and C. C links to A.
        site_map = {
            "https://example.com": '<html><head><title>A</title></head><body><a href="/b">B</a><a href="/c">C</a></body></html>',
            "https://example.com/b": '<html><head><title>B</title></head><body><a href="/">A</a><a href="/c">C</a></body></html>',
            "https://example.com/c": '<html><head><title>C</title></head><body><a href="/">A</a></body></html>',
        }

        def side_effect(url, timeout):
            return mock_html_response(url, site_map[url]), 0.01, None, None

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=5,
            max_pages=50,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Each URL must be crawled exactly once
        crawled_urls = [p.url for p in results["page_results"]]
        assert len(crawled_urls) == 3
        assert len(set(crawled_urls)) == 3
        assert mock_fetch.call_count == 3

    @patch.object(WebCrawler, "fetch_page")
    def test_max_pages_limit(self, mock_fetch):
        # Seed page links to 10 pages, but max_pages is capped at 3
        html = '<html><head><title>Home</title></head><body>' + "".join(f'<a href="/p{i}">P{i}</a>' for i in range(10)) + '</body></html>'
        
        def side_effect(url, timeout):
            return mock_html_response(url, html), 0.01, None, None

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=2,
            max_pages=3,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        assert len(results["page_results"]) == 3


class TestCrawlerErrorHandling:
    @patch.object(WebCrawler, "fetch_page")
    def test_graceful_http_and_network_error_recovery(self, mock_fetch):
        # Seed links to page1 (404), page2 (timeout), page3 (valid 200)
        seed_html = """
        <html><head><title>Seed</title></head><body>
            <a href="/404">404</a>
            <a href="/timeout">Timeout</a>
            <a href="/ok">OK</a>
        </body></html>
        """

        def side_effect(url, timeout):
            if url == "https://example.com":
                return mock_html_response(url, seed_html, 200), 0.01, None, None
            elif url == "https://example.com/404":
                resp = requests.Response()
                resp.status_code = 404
                resp.reason = "Not Found"
                return resp, 0.01, None, None
            elif url == "https://example.com/timeout":
                return None, 1.0, "Timeout Error", "Connection timed out"
            elif url == "https://example.com/ok":
                return mock_html_response(url, "<html><head><title>OK Page</title></head><body></body></html>", 200), 0.01, None, None
            return None, 0.01, "Unknown", "Unknown"

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=1,
            max_pages=10,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Crawler did not crash!
        # Successful: seed and /ok -> 2
        assert len(results["page_results"]) == 2
        # Failures: /404 and /timeout -> 2
        assert len(results["failures"]) == 2
        failure_urls = [f.url for f in results["failures"]]
        assert "https://example.com/404" in failure_urls
        assert "https://example.com/timeout" in failure_urls

    @patch.object(WebCrawler, "fetch_page")
    def test_http_403_429_500_and_non_html(self, mock_fetch):
        seed_html = """
        <html><head><title>Seed</title></head><body>
            <a href="/forbidden">403</a>
            <a href="/rate-limit">429</a>
            <a href="/server-error">500</a>
            <a href="/binary-data">PDF Stream</a>
        </body></html>
        """

        def side_effect(url, timeout):
            if url == "https://example.com":
                return mock_html_response(url, seed_html, 200), 0.01, None, None
            elif url == "https://example.com/forbidden":
                resp = requests.Response()
                resp.status_code = 403
                resp.reason = "Forbidden"
                return resp, 0.01, None, None
            elif url == "https://example.com/rate-limit":
                resp = requests.Response()
                resp.status_code = 429
                resp.reason = "Too Many Requests"
                return resp, 0.01, None, None
            elif url == "https://example.com/server-error":
                resp = requests.Response()
                resp.status_code = 500
                resp.reason = "Internal Server Error"
                return resp, 0.01, None, None
            elif url == "https://example.com/binary-data":
                resp = requests.Response()
                resp.status_code = 200
                resp.headers["Content-Type"] = "application/pdf"
                resp._content = b"%PDF-1.4..."
                return resp, 0.01, None, None
            return None, 0.01, "Error", "Error"

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=1,
            max_pages=10,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        assert len(results["page_results"]) == 1
        assert len(results["failures"]) == 4
        err_types = [f.error_type for f in results["failures"]]
        assert "HTTP 403" in err_types
        assert "HTTP 429" in err_types
        assert "HTTP 500" in err_types
        assert "Non-HTML Resource" in err_types

    def test_invalid_starting_url(self):
        config = CrawlConfig(start_url="invalid://url or nothing")
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        assert len(results["page_results"]) == 0
        assert len(results["failures"]) == 1
        assert results["failures"][0].error_type == "Invalid Starting URL"

    @patch("crawler.robots.RobotsManager.is_allowed")
    @patch.object(WebCrawler, "fetch_page")
    def test_respect_robots_txt_disallow(self, mock_fetch, mock_robots):
        seed_html = '<html><body><a href="/disallowed">Secret</a></body></html>'
        mock_fetch.return_value = (mock_html_response("https://example.com", seed_html), 0.01, None, None)

        def robots_rule(url, ua=None):
            if "/disallowed" in url:
                return False
            return True

        mock_robots.side_effect = robots_rule

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=1,
            max_pages=10,
            request_delay=0.0,
            respect_robots=True,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Seed page should be crawled, but /disallowed should be recorded as a failure / skipped
        assert len(results["page_results"]) == 1
        assert len(results["failures"]) == 1
        assert results["failures"][0].error_type == "Robots.txt Disallowed"



class TestSQLiteDatabaseStorage:
    def test_save_and_retrieve_session(self, tmp_path):
        db_file = str(tmp_path / "test_crawler.db")
        db = CrawlDatabase(db_path=db_file)

        from crawler.models import CrawlSessionSummary
        summary = CrawlSessionSummary(
            session_id="test_sess_001",
            start_url="https://test.com",
            max_depth=2,
            max_pages=20,
            start_time="2026-09-05T10:00:00",
            end_time="2026-09-05T10:00:05",
            elapsed_seconds=5.0,
            pages_crawled=2,
            discovered_urls_count=5,
            failed_urls_count=1,
            total_internal_links=4,
            total_external_links=1,
            stay_on_domain=True,
            max_depth_reached=1,
        )

        pages = [
            PageResult(
                url="https://test.com",
                title="Test Home",
                depth=0,
                status_code=200,
                total_links=3,
                unique_links=3,
                internal_links_count=2,
                external_links_count=1,
                internal_urls=["https://test.com/about", "https://test.com/contact"],
                external_urls=["https://github.com"],
                response_time=0.12,
                content_type="text/html",
                domain="test.com",
            )
        ]

        failures = [
            CrawlFailure(
                url="https://test.com/broken",
                depth=1,
                error_type="HTTP 404",
                error_message="Not Found",
            )
        ]

        # Save session
        success = db.save_session(summary, pages, failures)
        assert success

        # Retrieve all sessions
        sessions = db.get_all_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "test_sess_001"

        # Retrieve pages
        retrieved_pages = db.get_session_pages("test_sess_001")
        assert len(retrieved_pages) == 1
        assert retrieved_pages[0]["url"] == "https://test.com"
        assert len(retrieved_pages[0]["internal_urls"]) == 2

        # Retrieve failures
        retrieved_failures = db.get_session_failures("test_sess_001")
        assert len(retrieved_failures) == 1
        assert retrieved_failures[0]["url"] == "https://test.com/broken"

        # Delete session
        del_res = db.delete_session("test_sess_001")
        assert del_res
        assert len(db.get_all_sessions()) == 0

    @patch.object(WebCrawler, "fetch_page")
    def test_cross_domain_surfing_interleaves_external_links(self, mock_fetch):
        # Starting page has multiple internal links and an external link
        seed_html = """
        <html><head><title>Home</title></head><body>
            <a href="/internal1">Internal 1</a>
            <a href="/internal2">Internal 2</a>
            <a href="/internal3">Internal 3</a>
            <a href="https://external-domain.org/article">External Article</a>
        </body></html>
        """
        ext_html = "<html><head><title>Ext</title></head><body><p>Hello world</p></body></html>"
        int1_html = "<html><head><title>Int</title></head><body><p>Internal</p></body></html>"

        def side_effect(url, timeout):
            if url == "https://example.com":
                return mock_html_response(url, seed_html, 200), 0.01, None, None
            elif url == "https://external-domain.org/article":
                return mock_html_response(url, ext_html, 200), 0.01, None, None
            elif "internal" in url:
                return mock_html_response(url, int1_html, 200), 0.01, None, None
            return None, 0.01, "Error", "Error"

        mock_fetch.side_effect = side_effect

        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=1,
            max_pages=3,
            stay_on_domain=False,
            request_delay=0.0,
            respect_robots=False,
        )
        crawler = WebCrawler(config=config)
        results = crawler.crawl()

        # Because external links are interleaved, the external link is crawled within the first 3 pages
        crawled_urls = [p.url for p in results["page_results"]]
        assert "https://external-domain.org/article" in crawled_urls

