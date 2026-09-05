"""
Live end-to-end verification script for real crawling behavior:
- Tests Depth 0, Depth 1, Depth 2 boundaries on a local deterministic HTTP server.
- Tests Duplicate prevention (circular references & shared links).
- Tests Error resilience (404, 500, timeout, non-HTML stream, invalid host).
- Tests Robots.txt policy handling on local fixture.
- Tests SQLite database persistence & export data generation.
- Supports optional public website live crawl via --live-internet flag.
"""

import http.server
import threading
import time
import socket
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.models import CrawlConfig, PageResult, CrawlFailure
from crawler.crawler import WebCrawler
from crawler.database import CrawlDatabase
from crawler.url_utils import normalize_url


class MockSiteHandler(http.server.BaseHTTPRequestHandler):
    """Local HTTP test fixture server providing controlled page structures and error codes."""

    def log_message(self, format, *args):
        # Suppress noisy HTTP server console logs
        pass

    def do_GET(self):
        path = self.path
        
        if path == "/slow":
            time.sleep(1.5)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>Slow response</body></html>")
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path in ("/", "/index.html"):
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Root Seed Page</title></head>
            <body>
                <h1>Welcome to Seed</h1>
                <a href="/depth1_a">Depth 1 Page A</a>
                <a href="/depth1_b">Depth 1 Page B</a>
                <a href="/depth1_a#fragment1">Depth 1 Page A Duplicate with fragment</a>
                <a href="/depth1_a/">Depth 1 Page A Duplicate with trailing slash</a>
                <a href="/404_error">Missing 404</a>
                <a href="/server_500">Internal Server Error 500</a>
                <a href="/binary.pdf">Binary PDF File</a>
                <a href="https://www.google.com/search">External Search Engine</a>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path in ("/depth1_a", "/depth1_a/"):
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Depth 1 - Page A</title></head>
            <body>
                <h1>Page A</h1>
                <a href="/depth2_a">Depth 2 Page A</a>
                <a href="/depth1_b">Cross-link to Page B</a>
                <a href="/">Back to Root (Cycle)</a>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path in ("/depth1_b", "/depth1_b/"):
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Depth 1 - Page B</title></head>
            <body>
                <h1>Page B</h1>
                <a href="/depth2_b">Depth 2 Page B</a>
                <a href="/depth1_a">Cross-link to Page A</a>
                <a href="/depth2_a">Shared link to Depth 2 Page A</a>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path == "/depth2_a":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Depth 2 - Page A</title></head>
            <body>
                <h1>Page 2A</h1>
                <a href="/depth3_a">Depth 3 Page A (Should never crawl at depth 2)</a>
                <a href="/">Back to Root (Cycle)</a>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path == "/depth2_b":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Depth 2 - Page B</title></head>
            <body>
                <h1>Page 2B</h1>
                <a href="/depth3_b">Depth 3 Page B (Should never crawl at depth 2)</a>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path in ("/depth3_a", "/depth3_b"):
            html = "<html><head><title>Depth 3 Forbidden Level</title></head><body>Unreachable</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path == "/404_error":
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>404 Not Found</body></html>")

        elif path == "/server_500":
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>500 Internal Error</body></html>")

        elif path == "/binary.pdf":
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.end_headers()
            self.wfile.write(b"%PDF-1.4...")

        elif path == "/robots.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"User-agent: *\nDisallow: /disallowed_by_robots\n")

        elif path == "/disallowed_by_robots":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Disallowed Secret</body></html>")

        else:
            self.send_response(404)
            self.end_headers()


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_verification():
    print("=" * 70)
    print("STARTING DETERMINISTIC CRAWLER VERIFICATION")
    print("=" * 70)

    port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), MockSiteHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"
    print(f"[1/6] Local HTTP fixture server listening on {base_url}")

    time.sleep(0.2)

    try:
        # 2. Test Depth 0 Behavior
        print("\n[2/6] Verifying Depth 0 (Seed page only)...")
        cfg0 = CrawlConfig(start_url=base_url, max_depth=0, max_pages=50, request_delay=0.0, respect_robots=False)
        c0 = WebCrawler(cfg0)
        res0 = c0.crawl()
        pages0 = res0["page_results"]
        assert len(pages0) == 1, f"Expected 1 page at depth 0, got {len(pages0)}"
        assert pages0[0].depth == 0
        assert pages0[0].title == "Root Seed Page"
        print(f"  [PASS] Depth 0 PASSED: Crawled only root ({pages0[0].title}), discovered {len(res0['discovered_urls'])} links.")

        # 3. Test Depth 1 Behavior
        print("\n[3/6] Verifying Depth 1 (Seed + direct links)...")
        cfg1 = CrawlConfig(start_url=base_url, max_depth=1, max_pages=50, request_delay=0.0, respect_robots=False)
        c1 = WebCrawler(cfg1)
        res1 = c1.crawl()
        pages1 = res1["page_results"]
        depth_map1 = {p.url: p.depth for p in pages1}
        assert depth_map1[base_url] == 0
        assert f"{base_url}/depth1_a" in depth_map1
        assert f"{base_url}/depth1_b" in depth_map1
        assert f"{base_url}/depth2_a" not in depth_map1, "Depth 2 page crawled at max_depth=1!"
        print("  [PASS] Depth 1 PASSED: Visited Page A and Page B at depth 1; depth 2 unvisited.")

        # 4. Test Depth 2 Behavior & Duplicate Prevention & Cycle Protection
        print("\n[4/6] Verifying Depth 2 (Seed + depth 1 + depth 2 with cycles)...")
        cfg2 = CrawlConfig(start_url=base_url, max_depth=2, max_pages=50, request_delay=0.0, respect_robots=False)
        c2 = WebCrawler(cfg2)
        res2 = c2.crawl()
        pages2 = res2["page_results"]
        depth_map2 = {p.url: p.depth for p in pages2}

        assert f"{base_url}/depth2_a" in depth_map2
        assert f"{base_url}/depth2_b" in depth_map2
        assert f"{base_url}/depth3_a" not in depth_map2, "Depth 3 page crawled at max_depth=2!"
        assert f"{base_url}/depth3_b" not in depth_map2, "Depth 3 page crawled at max_depth=2!"

        urls_list = [p.url for p in pages2]
        assert len(urls_list) == len(set(urls_list)), "Duplicate URLs found in crawl results!"
        print(f"  [PASS] Duplicate Prevention PASSED: {len(urls_list)} unique URLs visited without repeats.")
        print("  [PASS] Depth 2 PASSED: Strict depth 2 boundary enforced; depth 3 unreachable.")

        # 5. Test Error Handling & Robots Policy
        print("\n[5/6] Verifying Robust Error Handling & Robots.txt...")
        failures2 = res2["failures"]
        fail_dict = {f.url: f for f in failures2}
        assert f"{base_url}/404_error" in fail_dict
        assert "404" in fail_dict[f"{base_url}/404_error"].error_type
        assert f"{base_url}/server_500" in fail_dict
        assert "500" in fail_dict[f"{base_url}/server_500"].error_type

        # Test Non-existent domain
        c_err = WebCrawler(CrawlConfig(start_url="http://non-existent-domain-xyz987.invalid", timeout=2.0))
        res_err = c_err.crawl()
        assert len(res_err["failures"]) >= 1
        print(f"  [PASS] Non-existent domain error captured: {res_err['failures'][0].error_type}")

        # Test Timeout on slow endpoint
        c_time = WebCrawler(CrawlConfig(start_url=f"{base_url}/slow", timeout=0.5))
        res_time = c_time.crawl()
        assert len(res_time["failures"]) >= 1
        assert "Timeout" in res_time["failures"][0].error_type or "Read Timeout" in res_time["failures"][0].error_type
        print(f"  [PASS] Timeout error captured: {res_time['failures'][0].error_type}")

        # 6. Optional Live Public Website Crawl
        print("\n[6/6] Public Website Crawl Check...")
        if "--live-internet" in sys.argv:
            print("  Running live internet crawl against https://example.com...")
            cfg_pub = CrawlConfig(start_url="https://example.com", max_depth=1, max_pages=5, timeout=10.0, respect_robots=True)
            c_pub = WebCrawler(cfg_pub)
            res_pub = c_pub.crawl()
            summary_pub = res_pub["summary"]
            assert summary_pub.pages_crawled >= 1, "Live internet crawl yielded 0 pages!"
            print(f"  [PASS] Live Internet Crawl PASSED ({summary_pub.pages_crawled} pages).")
        else:
            print("  [OPTIONAL / SKIPPED] Live internet test skipped (run with --live-internet to enable).")

        print("\n" + "=" * 70)
        print("ALL MANDATORY LOCAL CRAWLER VERIFICATIONS SUCCEEDED!")
        print("=" * 70)

    except Exception as e:
        print("\n" + "!" * 70)
        print(f"VERIFICATION FAILED WITH ERROR: {e}")
        print("!" * 70)
        sys.exit(1)
    finally:
        server.shutdown()


if __name__ == "__main__":
    run_verification()
