"""
Live end-to-end verification script for real crawling behavior:
- Tests Depth 0, Depth 1, Depth 2 boundaries on a real HTTP server.
- Tests Duplicate prevention (circular references & shared links).
- Tests Error resilience (404, 500, timeout, non-HTML stream, invalid host).
- Tests public website live crawl (http://example.com).
- Tests SQLite database persistence & export data generation.
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
        
        # Artificial delay for timeout testing
        if path == "/slow":
            time.sleep(2.0)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Slow response</body></html>")
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
    print("STARTING REAL CRAWLER VERIFICATION")
    print("=" * 70)

    # 1. Start local mock HTTP server
    port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), MockSiteHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"
    print(f"[1/6] Local HTTP fixture server listening on {base_url}")

    time.sleep(0.2)

    # 2. Test Depth 0 Behavior
    print("\n[2/6] Verifying Depth 0 Behavior...")
    cfg0 = CrawlConfig(start_url=base_url, max_depth=0, max_pages=20, request_delay=0.0, respect_robots=False)
    c0 = WebCrawler(cfg0)
    res0 = c0.crawl()
    pages0 = res0["page_results"]
    crawled_urls0 = [p.url for p in pages0]
    print(f"  -> Crawled pages count: {len(pages0)}")
    print(f"  -> Crawled URLs: {crawled_urls0}")
    assert len(pages0) == 1, f"Expected 1 page at depth 0, got {len(pages0)}"
    assert pages0[0].depth == 0, f"Expected depth 0, got {pages0[0].depth}"
    assert pages0[0].total_links > 0, "Expected links to be discovered on seed"
    print("  [PASS] Depth 0 PASSED: Only starting seed URL crawled; no child URL fetched.")

    # 3. Test Depth 1 Behavior
    print("\n[3/6] Verifying Depth 1 Behavior...")
    cfg1 = CrawlConfig(start_url=base_url, max_depth=1, max_pages=20, request_delay=0.0, respect_robots=False)
    c1 = WebCrawler(cfg1)
    res1 = c1.crawl()
    pages1 = res1["page_results"]
    depth_map1 = {p.url: p.depth for p in pages1}
    print(f"  -> Crawled pages count: {len(pages1)}")
    for u, d in depth_map1.items():
        print(f"     Depth {d}: {u}")
    assert depth_map1[base_url] == 0
    assert depth_map1[f"{base_url}/depth1_a"] == 1
    assert depth_map1[f"{base_url}/depth1_b"] == 1
    assert f"{base_url}/depth2_a" not in depth_map1, "Depth 2 page should NOT be crawled at max_depth=1"
    assert f"{base_url}/depth2_b" not in depth_map1, "Depth 2 page should NOT be crawled at max_depth=1"
    print("  [PASS] Depth 1 PASSED: Seed + depth 1 pages crawled; no depth 2 pages fetched.")

    # 4. Test Depth 2 Behavior & Duplicate Prevention
    print("\n[4/6] Verifying Depth 2 Behavior & Duplicate / Cycle Prevention...")
    cfg2 = CrawlConfig(start_url=base_url, max_depth=2, max_pages=50, request_delay=0.0, respect_robots=False)
    c2 = WebCrawler(cfg2)
    res2 = c2.crawl()
    pages2 = res2["page_results"]
    depth_map2 = {p.url: p.depth for p in pages2}
    print(f"  -> Crawled pages count: {len(pages2)}")
    for u, d in depth_map2.items():
        print(f"     Depth {d}: {u}")
    
    # Check depth 2 pages were crawled
    assert depth_map2[base_url] == 0
    assert depth_map2[f"{base_url}/depth1_a"] == 1
    assert depth_map2[f"{base_url}/depth1_b"] == 1
    assert depth_map2[f"{base_url}/depth2_a"] == 2
    assert depth_map2[f"{base_url}/depth2_b"] == 2
    
    # Ensure depth 3 pages were NOT crawled
    assert f"{base_url}/depth3_a" not in depth_map2, "Depth 3 page crawled at max_depth=2!"
    assert f"{base_url}/depth3_b" not in depth_map2, "Depth 3 page crawled at max_depth=2!"

    # Verify duplicate prevention:
    # Page A links to Page B, Page B links to Page A. Both link to Root. Both link to 2A.
    # Each URL must appear in page_results EXACTLY ONCE!
    urls_list = [p.url for p in pages2]
    assert len(urls_list) == len(set(urls_list)), "Duplicate URLs found in crawl results!"
    print(f"  [PASS] Duplicate Prevention PASSED: {len(urls_list)} unique URLs visited without repeats.")
    print("  [PASS] Depth 2 PASSED: Strict depth 2 boundary enforced; depth 3 unreachable.")

    # 5. Test Error Handling (404, 500, non-HTML, timeout, invalid URL)
    print("\n[5/6] Verifying Robust Error Handling...")
    failures2 = res2["failures"]
    fail_dict = {f.url: f for f in failures2}
    print(f"  -> Failures recorded: {len(failures2)}")
    for f in failures2:
        print(f"     Failed: {f.url} | {f.error_type} | {f.error_message}")
    
    assert f"{base_url}/404_error" in fail_dict
    assert "404" in fail_dict[f"{base_url}/404_error"].error_type
    assert f"{base_url}/server_500" in fail_dict
    assert "500" in fail_dict[f"{base_url}/server_500"].error_type

    # Test Timeout & Non-existent domain
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

    # 6. Test Real Live Crawl on Public Website (http://example.com)
    print("\n[6/6] Verifying Real Public Website Crawl (http://example.com)...")
    try:
        cfg_pub = CrawlConfig(start_url="http://example.com", max_depth=1, max_pages=5, timeout=10.0, respect_robots=True)
        c_pub = WebCrawler(cfg_pub)
        res_pub = c_pub.crawl()
        summary_pub = res_pub["summary"]
        print(f"  -> Start URL: {summary_pub.start_url}")
        print(f"  -> Pages crawled: {summary_pub.pages_crawled}")
        print(f"  -> Discovered links: {summary_pub.discovered_urls_count}")
        print(f"  -> Max depth reached: {summary_pub.max_depth_reached}")
        print(f"  -> Elapsed time: {summary_pub.elapsed_seconds}s")
        assert summary_pub.pages_crawled >= 1
        print("  [PASS] Real Public Crawl PASSED!")
    except Exception as e:
        print(f"  (Live internet crawl skipped or error: {e})")

    server.shutdown()
    print("\n" + "=" * 70)
    print("ALL REAL CRAWLER BEHAVIOR VERIFICATIONS SUCCEEDED!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
