"""
Core WebCrawler engine implementing queue-based Breadth-First Search (BFS),
duplicate detection, robots.txt compliance, robust error handling, and event streaming.
"""

import collections
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple, Optional, Generator

import requests

from .models import (
    CrawlConfig,
    PageResult,
    CrawlFailure,
    CrawlProgressEvent,
    CrawlSessionSummary,
)
from .url_utils import (
    normalize_url,
    is_valid_url,
    is_binary_url,
    get_domain,
    is_same_domain,
)
from .parser import parse_page_html
from .robots import RobotsManager


class WebCrawler:
    """
    Breadth-First Search web crawler that extracts page metadata, counts hyperlinks,
    tracks depth, prevents duplicate visits, and handles network failures gracefully.
    """

    def __init__(self, config: Optional[CrawlConfig] = None):
        self.config = config or CrawlConfig(start_url="")
        self.session = requests.Session()
        self.robots_manager = RobotsManager(timeout=5.0, user_agent=self.config.user_agent)

        # State tracking
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.page_results: List[PageResult] = []
        self.failures: List[CrawlFailure] = []
        self.graph_edges: List[Tuple[str, str, int]] = []  # (source_url, target_url, target_depth)

    # Required API methods as per architectural specifications
    def normalize_url(self, url: str, base_url: Optional[str] = None) -> Optional[str]:
        """Normalize URL and remove fragments."""
        return normalize_url(url, base_url=base_url)

    def is_valid_url(self, url: str) -> bool:
        """Validate URL syntax and scheme."""
        return is_valid_url(url)

    def is_html_response(self, response: requests.Response) -> bool:
        """Verify response contains HTML content."""
        content_type = response.headers.get("Content-Type", "").lower()
        return "text/html" in content_type or "application/xhtml+xml" in content_type

    def extract_links(self, url: str, html: str, base_domain: str) -> Dict[str, Any]:
        """Extract title, metadata, and categorized hyperlinks from HTML."""
        return parse_page_html(
            html_content=html,
            base_url=url,
            base_domain=base_domain,
            allow_subdomains=True,
        )

    def fetch_page(self, url: str, timeout: float) -> Tuple[Optional[requests.Response], float, Optional[str], Optional[str]]:
        """
        Fetch a webpage via HTTP GET with stream inspection and timeout.
        Returns: (response, response_time, error_type, error_message)
        """
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        start_time = time.perf_counter()
        try:
            # We fetch stream=True first or full GET with timeout
            resp = self.session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                verify=True,
            )
            elapsed = time.perf_counter() - start_time
            return resp, elapsed, None, None
        except requests.exceptions.SSLError as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "SSL Error", f"SSL certificate verification failed: {str(e)}"
        except requests.exceptions.ConnectTimeout as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "Connection Timeout", f"Server connection timed out after {timeout}s: {str(e)}"
        except requests.exceptions.ReadTimeout as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "Read Timeout", f"Server read timed out after {timeout}s: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "Connection Error", f"DNS or network connection failed: {str(e)}"
        except requests.exceptions.TooManyRedirects as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "Redirect Loop", f"Exceeded maximum redirects: {str(e)}"
        except requests.exceptions.RequestException as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "Request Exception", str(e)
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return None, elapsed, "Unexpected Exception", f"{type(e).__name__}: {str(e)}"

    def crawl_stream(
        self, config: Optional[CrawlConfig] = None
    ) -> Generator[CrawlProgressEvent, None, CrawlSessionSummary]:
        """
        Execute BFS crawling as an event generator.
        Yields CrawlProgressEvent instances for live UI rendering.
        Returns the final CrawlSessionSummary.
        """
        if config:
            self.config = config

        start_time_iso = datetime.now().isoformat()
        crawl_start_perf = time.perf_counter()
        session_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Reset state
        self.visited_urls.clear()
        self.discovered_urls.clear()
        self.page_results.clear()
        self.failures.clear()
        self.graph_edges.clear()

        # Validate start URL
        raw_start = (self.config.start_url or "").strip()
        normalized_start = self.normalize_url(raw_start)

        if not normalized_start:
            failure = CrawlFailure(
                url=raw_start or "None",
                depth=0,
                error_type="Invalid Starting URL",
                error_message="The provided starting URL is malformed or does not use http/https.",
            )
            self.failures.append(failure)
            summary = CrawlSessionSummary(
                session_id=session_id,
                start_url=raw_start,
                max_depth=self.config.max_depth,
                max_pages=self.config.max_pages,
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
                elapsed_seconds=round(time.perf_counter() - crawl_start_perf, 2),
                pages_crawled=0,
                discovered_urls_count=0,
                failed_urls_count=1,
                total_internal_links=0,
                total_external_links=0,
                stay_on_domain=self.config.stay_on_domain,
                max_depth_reached=0,
            )
            yield CrawlProgressEvent(
                event_type="failure",
                current_url=raw_start,
                current_depth=0,
                pages_crawled=0,
                discovered_count=0,
                failed_count=1,
                message=f"Starting URL error: {failure.error_message}",
                failure=failure,
            )
            return summary

        start_domain = get_domain(normalized_start)

        # Queue contains items: (url, depth, parent_url)
        queue = collections.deque([(normalized_start, 0, None)])
        self.visited_urls.add(normalized_start)
        self.discovered_urls.add(normalized_start)

        yield CrawlProgressEvent(
            event_type="start",
            current_url=normalized_start,
            current_depth=0,
            pages_crawled=0,
            discovered_count=1,
            failed_count=0,
            message=f"Crawl initialized for {normalized_start} (Max Depth: {self.config.max_depth}, Max Pages: {self.config.max_pages})",
        )

        max_depth_reached = 0

        while queue and len(self.page_results) < self.config.max_pages:
            current_url, current_depth, parent_url = queue.popleft()
            max_depth_reached = max(max_depth_reached, current_depth)

            # Inform UI of pending fetch
            yield CrawlProgressEvent(
                event_type="fetching",
                current_url=current_url,
                current_depth=current_depth,
                pages_crawled=len(self.page_results),
                discovered_count=len(self.discovered_urls),
                failed_count=len(self.failures),
                message=f"Crawling depth {current_depth}... Processing {len(self.page_results) + 1}/{self.config.max_pages} pages",
            )

            # Check robots.txt if requested
            if self.config.respect_robots:
                if not self.robots_manager.is_allowed(current_url, self.config.user_agent):
                    fail = CrawlFailure(
                        url=current_url,
                        depth=current_depth,
                        error_type="Robots.txt Disallowed",
                        error_message="Access disallowed by host robots.txt policy.",
                    )
                    self.failures.append(fail)
                    yield CrawlProgressEvent(
                        event_type="skipped",
                        current_url=current_url,
                        current_depth=current_depth,
                        pages_crawled=len(self.page_results),
                        discovered_count=len(self.discovered_urls),
                        failed_count=len(self.failures),
                        message=f"Skipped {current_url}: Disallowed by robots.txt",
                        failure=fail,
                    )
                    continue

            # Polite request delay
            if self.config.request_delay > 0 and len(self.page_results) > 0:
                time.sleep(self.config.request_delay)

            # Fetch page
            resp, elapsed, err_type, err_msg = self.fetch_page(current_url, self.config.timeout)

            # Handle network/connection failures
            if resp is None:
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type=err_type or "Network Error",
                    error_message=err_msg or "Failed to connect to host.",
                )
                self.failures.append(fail)
                yield CrawlProgressEvent(
                    event_type="failure",
                    current_url=current_url,
                    current_depth=current_depth,
                    pages_crawled=len(self.page_results),
                    discovered_count=len(self.discovered_urls),
                    failed_count=len(self.failures),
                    message=f"Failed {current_url}: {fail.error_type} - {fail.error_message}",
                    failure=fail,
                )
                continue

            # Handle HTTP status code errors (4xx, 5xx)
            if resp.status_code >= 400:
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type=f"HTTP {resp.status_code}",
                    error_message=f"Server returned HTTP status code {resp.status_code} ({resp.reason}).",
                )
                self.failures.append(fail)
                yield CrawlProgressEvent(
                    event_type="failure",
                    current_url=current_url,
                    current_depth=current_depth,
                    pages_crawled=len(self.page_results),
                    discovered_count=len(self.discovered_urls),
                    failed_count=len(self.failures),
                    message=f"HTTP Error {resp.status_code} on {current_url}",
                    failure=fail,
                )
                continue

            # Validate Content-Type
            content_type = resp.headers.get("Content-Type", "")
            if not self.is_html_response(resp):
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type="Non-HTML Resource",
                    error_message=f"Skipped non-HTML content type: {content_type}",
                )
                self.failures.append(fail)
                yield CrawlProgressEvent(
                    event_type="skipped",
                    current_url=current_url,
                    current_depth=current_depth,
                    pages_crawled=len(self.page_results),
                    discovered_count=len(self.discovered_urls),
                    failed_count=len(self.failures),
                    message=f"Skipped non-HTML content at {current_url}",
                    failure=fail,
                )
                continue

            # Parse HTML content
            parsed_data = self.extract_links(
                url=current_url,
                html=resp.text,
                base_domain=start_domain,
            )

            # Record successfully crawled page
            page_res = PageResult(
                url=current_url,
                title=parsed_data["title"],
                depth=current_depth,
                status_code=resp.status_code,
                total_links=parsed_data["total_links_found"],
                unique_links=parsed_data["unique_links_count"],
                internal_links_count=parsed_data["internal_count"],
                external_links_count=parsed_data["external_count"],
                internal_urls=parsed_data["internal_urls"],
                external_urls=parsed_data["external_urls"],
                response_time=elapsed,
                content_type=content_type,
                domain=get_domain(current_url),
                parent_url=parent_url,
            )
            self.page_results.append(page_res)

            # Track graph edge from parent to current page
            if parent_url:
                self.graph_edges.append((parent_url, current_url, current_depth))

            # Discovered URLs tracking
            all_page_links = parsed_data["internal_urls"] + parsed_data["external_urls"]
            for link in all_page_links:
                self.discovered_urls.add(link)

            yield CrawlProgressEvent(
                event_type="success",
                current_url=current_url,
                current_depth=current_depth,
                pages_crawled=len(self.page_results),
                discovered_count=len(self.discovered_urls),
                failed_count=len(self.failures),
                message=f"Crawled: {page_res.title[:45]} ({parsed_data['unique_links_count']} links)",
                page_result=page_res,
            )

            # BFS expansion to next depth if current_depth < max_depth
            if current_depth < self.config.max_depth:
                # Filter candidates for next level
                candidates = parsed_data["internal_urls"]
                if not self.config.stay_on_domain:
                    # If allowed to leave domain, include external HTML links
                    candidates = candidates + parsed_data["external_urls"]

                for link in candidates:
                    # Prevent duplicate crawl visits
                    if link not in self.visited_urls:
                        # Skip binary links
                        if is_binary_url(link):
                            continue

                        # Domain constraint check
                        if self.config.stay_on_domain and not is_same_domain(link, start_domain):
                            continue

                        # Mark visited immediately to prevent duplicate queueing
                        self.visited_urls.add(link)
                        queue.append((link, current_depth + 1, current_url))

        # Crawl cycle complete
        elapsed_total = time.perf_counter() - crawl_start_perf
        end_time_iso = datetime.now().isoformat()

        tot_internal = sum(p.internal_links_count for p in self.page_results)
        tot_external = sum(p.external_links_count for p in self.page_results)

        summary = CrawlSessionSummary(
            session_id=session_id,
            start_url=normalized_start,
            max_depth=self.config.max_depth,
            max_pages=self.config.max_pages,
            start_time=start_time_iso,
            end_time=end_time_iso,
            elapsed_seconds=round(elapsed_total, 2),
            pages_crawled=len(self.page_results),
            discovered_urls_count=len(self.discovered_urls),
            failed_urls_count=len(self.failures),
            total_internal_links=tot_internal,
            total_external_links=tot_external,
            stay_on_domain=self.config.stay_on_domain,
            max_depth_reached=max_depth_reached,
        )

        yield CrawlProgressEvent(
            event_type="completed",
            current_url=normalized_start,
            current_depth=max_depth_reached,
            pages_crawled=len(self.page_results),
            discovered_count=len(self.discovered_urls),
            failed_count=len(self.failures),
            message=f"Crawl completed! {len(self.page_results)} pages crawled in {round(elapsed_total, 2)}s.",
        )

        return summary

    def crawl(self, config: Optional[CrawlConfig] = None) -> Dict[str, Any]:
        """
        Synchronous batch crawl execution without event streaming.
        Returns dictionary containing summary, page_results, failures, and graph_edges.
        """
        gen = self.crawl_stream(config)
        summary = None
        try:
            while True:
                next(gen)
        except StopIteration as e:
            summary = e.value

        return {
            "summary": summary,
            "page_results": self.page_results,
            "failures": self.failures,
            "graph_edges": self.graph_edges,
            "discovered_urls": list(self.discovered_urls),
            "visited_urls": list(self.visited_urls),
        }
