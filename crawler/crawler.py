"""
Core WebCrawler engine implementing queue-based Breadth-First Search (BFS),
duplicate detection, robots.txt compliance, robust error handling, streamed resource protection,
and event streaming.
"""

import collections
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple, Optional, Generator
from urllib.parse import urljoin

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
    is_safe_target_url,
)
from .parser import parse_page_html
from .robots import RobotsManager
from .search_discovery import is_search_query, discover_search_urls

# Maximum allowed download size for HTML pages (10 MB)
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


def _safe_close(resp: Optional[requests.Response]) -> None:
    """Safely close a requests Response without raising if raw socket is missing or already closed."""
    if resp is not None:
        try:
            resp.close()
        except Exception:
            pass


class WebCrawler:
    """
    Breadth-First Search web crawler that extracts page metadata, counts hyperlinks,
    tracks depth, prevents duplicate visits, protects against oversized/non-HTML streams,
    and handles network failures gracefully.
    """

    def __init__(self, config: Optional[CrawlConfig] = None):
        self.config = config or CrawlConfig(start_url="")
        self.session = requests.Session()
        self.robots_manager = RobotsManager(timeout=5.0, user_agent=self.config.user_agent)

        # Explicit state semantics
        self.discovered_urls: Set[str] = set()
        self.queued_urls: Set[str] = set()
        self.attempted_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.skipped_urls: Set[str] = set()

        # Backward compatibility alias
        self.visited_urls: Set[str] = set()

        self.page_results: List[PageResult] = []
        self.failures: List[CrawlFailure] = []
        self.graph_edges: List[Tuple[str, str, int]] = []  # (source_url, target_url, target_depth)

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
        """Extract title, metadata, readable text, and categorized hyperlinks from HTML."""
        target_terms = self.config.keyword_filter or self.config.search_query
        return parse_page_html(
            html_content=html,
            base_url=url,
            base_domain=base_domain,
            allow_subdomains=self.config.allow_subdomains,
            target_terms=target_terms,
        )

    def fetch_page(
        self, url: str, timeout: float
    ) -> Tuple[Optional[requests.Response], float, Optional[str], Optional[str]]:
        """
        Fetch a webpage via HTTP GET with stream inspection, Content-Type verification,
        oversized payload protection, and explicit exception classification.
        Returns: (response, response_time, error_type, error_message)
        """
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        }

        start_time = time.perf_counter()
        current_fetch_url = url
        resp = None
        max_redirect_hops = 10
        redirect_hops = 0

        try:
            while True:
                # Validate SSRF target security on every redirect hop before connecting
                is_safe, ssrf_err = is_safe_target_url(current_fetch_url, resolve_dns=True)
                if not is_safe:
                    _safe_close(resp)
                    elapsed = time.perf_counter() - start_time
                    return None, elapsed, "SSRF Blocked", f"Request to {current_fetch_url} prohibited by security policy: {ssrf_err}"

                resp = self.session.get(
                    current_fetch_url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=False,
                    stream=True,
                    verify=True,
                )

                # Check for HTTP redirect response codes
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        break
                    _safe_close(resp)
                    redirect_hops += 1
                    if redirect_hops > max_redirect_hops:
                        elapsed = time.perf_counter() - start_time
                        return None, elapsed, "Redirect Loop", f"Exceeded maximum redirects limit of {max_redirect_hops}"
                    next_url = urljoin(current_fetch_url, location)
                    if not is_valid_url(next_url):
                        elapsed = time.perf_counter() - start_time
                        return None, elapsed, "Invalid Redirect", f"Redirect target is malformed or invalid: {location}"
                    current_fetch_url = next_url
                    continue
                else:
                    break

            elapsed = time.perf_counter() - start_time
            if resp:
                resp.url = current_fetch_url

            # Status code check for 4xx and 5xx
            if resp.status_code >= 400:
                _safe_close(resp)
                return resp, elapsed, f"HTTP {resp.status_code}", f"Server returned HTTP {resp.status_code} ({resp.reason})"

            # Content-Type early inspection
            if not self.is_html_response(resp):
                c_type = resp.headers.get("Content-Type", "Unknown")
                _safe_close(resp)
                return resp, elapsed, "Non-HTML Resource", f"Skipped non-HTML Content-Type: {c_type}"

            # Content-Length safety check
            content_len_header = resp.headers.get("Content-Length")
            if content_len_header and content_len_header.isdigit():
                if int(content_len_header) > MAX_RESPONSE_BYTES:
                    _safe_close(resp)
                    return resp, elapsed, "Oversized Resource", f"Content-Length {content_len_header} exceeds {MAX_RESPONSE_BYTES} bytes limit"

            # Stream body with size ceiling to prevent memory exhaustion
            chunks = []
            bytes_received = 0
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
                bytes_received += len(chunk)
                if bytes_received > MAX_RESPONSE_BYTES:
                    _safe_close(resp)
                    return resp, elapsed, "Oversized Resource", f"Stream exceeded maximum allowed limit of {MAX_RESPONSE_BYTES} bytes"

            # Populate response content cache
            resp._content = b"".join(chunks)
            return resp, elapsed, None, None

        except requests.exceptions.SSLError as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
            return None, elapsed, "SSL Error", f"SSL certificate verification failed: {str(e)}"
        except requests.exceptions.ConnectTimeout as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
            return None, elapsed, "Connection Timeout", f"Server connection timed out after {timeout}s: {str(e)}"
        except requests.exceptions.ReadTimeout as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
            return None, elapsed, "Read Timeout", f"Server read timed out after {timeout}s: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
            return None, elapsed, "Connection Error", f"DNS resolution or network connection failed: {str(e)}"
        except requests.exceptions.TooManyRedirects as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
            return None, elapsed, "Redirect Loop", f"Exceeded maximum redirects: {str(e)}"
        except requests.exceptions.RequestException as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
            return None, elapsed, "Request Exception", str(e)
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            _safe_close(resp)
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

        # Reset all state tracking sets
        self.discovered_urls.clear()
        self.queued_urls.clear()
        self.attempted_urls.clear()
        self.crawled_urls.clear()
        self.failed_urls.clear()
        self.skipped_urls.clear()
        self.visited_urls.clear()

        self.page_results.clear()
        self.failures.clear()
        self.graph_edges.clear()

        # Check if input is a search query/sentence or direct URL
        raw_start = (self.config.start_url or "").strip()
        is_query = is_search_query(raw_start)

        if is_query:
            # User wants to crawl across the internet for words/sentence/topic
            self.config.search_query = raw_start
            self.config.stay_on_domain = False  # Search traversal spans multiple domains across internet

            yield CrawlProgressEvent(
                event_type="searching",
                current_url=raw_start,
                current_depth=0,
                pages_crawled=0,
                discovered_count=0,
                failed_count=0,
                message=f"🔍 Resolving websites across internet for: '{raw_start}'...",
            )

            discovered_seeds = discover_search_urls(
                raw_start,
                max_results=min(self.config.max_pages, 8),
                timeout=self.config.timeout,
                session=self.session,
            )

            if not discovered_seeds:
                failure = CrawlFailure(
                    url=raw_start or "None",
                    depth=0,
                    error_type="Search Discovery Failed",
                    error_message=f"Could not discover reachable websites across internet for query '{raw_start}'. Please check internet connection or refine your words/sentence.",
                )
                self.failures.append(failure)
                self.failed_urls.add(raw_start or "None")
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
                    stay_on_domain=False,
                    max_depth_reached=0,
                    search_query=raw_start,
                )
                yield CrawlProgressEvent(
                    event_type="failure",
                    current_url=raw_start,
                    current_depth=0,
                    pages_crawled=0,
                    discovered_count=0,
                    failed_count=1,
                    message=f"Search error: {failure.error_message}",
                    failure=failure,
                )
                return summary

            normalized_start = discovered_seeds[0]
            start_domain = get_domain(normalized_start)
            queue = collections.deque([(s_url, 0, None) for s_url in discovered_seeds])
            for s_url in discovered_seeds:
                self.queued_urls.add(s_url)
                self.visited_urls.add(s_url)
                self.discovered_urls.add(s_url)

            yield CrawlProgressEvent(
                event_type="start",
                current_url=raw_start,
                current_depth=0,
                pages_crawled=0,
                discovered_count=len(discovered_seeds),
                failed_count=0,
                message=f"Discovered {len(discovered_seeds)} websites across internet. Initiating multi-domain crawl for: '{raw_start}'",
            )
        else:
            norm_target = raw_start
            if norm_target and "://" not in norm_target:
                norm_target = "https://" + norm_target

            normalized_start = self.normalize_url(norm_target)

            if not normalized_start:
                failure = CrawlFailure(
                    url=raw_start or "None",
                    depth=0,
                    error_type="Invalid Starting URL",
                    error_message="The provided starting URL is malformed or does not use http/https.",
                )
                self.failures.append(failure)
                self.failed_urls.add(raw_start or "None")
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

            # Verify start URL satisfies SSRF security policy
            is_safe_start, ssrf_reason = is_safe_target_url(normalized_start, resolve_dns=False)
            if not is_safe_start:
                failure = CrawlFailure(
                    url=raw_start or "None",
                    depth=0,
                    error_type="SSRF Blocked",
                    error_message=f"Starting URL prohibited by security policy: {ssrf_reason}",
                )
                self.failures.append(failure)
                self.failed_urls.add(raw_start or "None")
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
                    message=f"Security Policy: {failure.error_message}",
                    failure=failure,
                )
                return summary

            start_domain = get_domain(normalized_start)

            # Queue contains tuples: (url, depth, parent_url)
            queue = collections.deque([(normalized_start, 0, None)])
            self.queued_urls.add(normalized_start)
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
        total_attempts = 0
        # Safety ceiling on total attempts to avoid infinite loops if dead links dominate
        max_attempts_limit = self.config.max_attempts or max(self.config.max_pages * 5, 200)

        while queue and len(self.page_results) < self.config.max_pages and total_attempts < max_attempts_limit:
            current_url, current_depth, parent_url = queue.popleft()
            self.attempted_urls.add(current_url)
            total_attempts += 1
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

            # Check robots.txt policy if requested
            if self.config.respect_robots:
                allowed = self.robots_manager.is_allowed(current_url, self.config.user_agent)
                if not allowed:
                    fail = CrawlFailure(
                        url=current_url,
                        depth=current_depth,
                        error_type="Robots.txt Disallowed",
                        error_message="Access disallowed by host robots.txt policy.",
                    )
                    self.failures.append(fail)
                    self.skipped_urls.add(current_url)
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

            # Polite request delay between fetches
            if self.config.request_delay > 0 and len(self.page_results) > 0:
                time.sleep(self.config.request_delay)

            # Fetch page via HTTP
            resp, elapsed, err_type, err_msg = self.fetch_page(current_url, self.config.timeout)

            # Handle network/connection/status errors
            if err_type is not None:
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type=err_type,
                    error_message=err_msg or "Failed to retrieve page.",
                )
                self.failures.append(fail)
                if err_type in ("Non-HTML Resource", "Oversized Resource"):
                    self.skipped_urls.add(current_url)
                else:
                    self.failed_urls.add(current_url)
                yield CrawlProgressEvent(
                    event_type="failure" if err_type not in ("Non-HTML Resource", "Oversized Resource") else "skipped",
                    current_url=current_url,
                    current_depth=current_depth,
                    pages_crawled=len(self.page_results),
                    discovered_count=len(self.discovered_urls),
                    failed_count=len(self.failures),
                    message=f"Failed/Skipped {current_url}: {err_type} - {err_msg}",
                    failure=fail,
                )
                continue

            if resp is None:
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type="Network Error",
                    error_message="Failed to connect to host.",
                )
                self.failures.append(fail)
                self.failed_urls.add(current_url)
                continue

            # Status code check (handles mocked fetch_page in tests as well)
            if resp.status_code >= 400:
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type=f"HTTP {resp.status_code}",
                    error_message=f"Server returned HTTP {resp.status_code} ({resp.reason or ''})",
                )
                self.failures.append(fail)
                self.failed_urls.add(current_url)
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

            # Content-Type check (handles mocked fetch_page in tests as well)
            if not self.is_html_response(resp):
                c_type = resp.headers.get("Content-Type", "")
                fail = CrawlFailure(
                    url=current_url,
                    depth=current_depth,
                    error_type="Non-HTML Resource",
                    error_message=f"Skipped non-HTML content type: {c_type}",
                )
                self.failures.append(fail)
                self.skipped_urls.add(current_url)
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

            # Determine final URL after any redirects for accurate relative link resolution
            final_url = resp.url if resp.url else current_url
            content_type = resp.headers.get("Content-Type", "")

            # If stay_on_domain is False (cross-domain internet search/surfing),
            # classify internal vs external relative to the page's own domain
            page_domain = get_domain(final_url)
            extract_domain = start_domain if self.config.stay_on_domain else page_domain

            # Parse HTML content
            parsed_data = self.extract_links(
                url=final_url,
                html=resp.text,
                base_domain=extract_domain,
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
                text_snippet=parsed_data.get("text_snippet", ""),
                word_count=parsed_data.get("word_count", 0),
                matching_sentences=parsed_data.get("matching_sentences", []),
                match_count=parsed_data.get("match_count", 0),
            )
            self.page_results.append(page_res)
            self.crawled_urls.add(current_url)

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
                # Select eligible candidates based on domain policy
                if self.config.stay_on_domain:
                    candidates = parsed_data["internal_urls"]
                else:
                    # Unrestricted Internet Surfing: interleave external outbound links with internal links
                    # so the crawler actively hops between diverse internet websites instead of getting
                    # trapped in thousands of internal links of a single website!
                    ext_links = parsed_data["external_urls"]
                    int_links = parsed_data["internal_urls"]
                    candidates = []
                    max_len = max(len(ext_links), len(int_links))
                    for idx in range(max_len):
                        if idx < len(ext_links):
                            candidates.append(ext_links[idx])
                        if idx < len(int_links):
                            candidates.append(int_links[idx])

                for link in candidates:
                    # Prevent duplicate queueing
                    if link not in self.queued_urls:
                        # Skip binary links
                        if is_binary_url(link):
                            self.skipped_urls.add(link)
                            continue

                        # Security check: skip internal/loopback candidate URLs
                        if not is_safe_target_url(link, resolve_dns=False)[0]:
                            self.skipped_urls.add(link)
                            continue

                        # Domain constraint check
                        if self.config.stay_on_domain and not is_same_domain(
                            link, start_domain, allow_subdomains=self.config.allow_subdomains
                        ):
                            continue

                        # Enqueue and mark queued immediately
                        self.queued_urls.add(link)
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
            search_query=self.config.search_query,
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
        Returns dictionary containing summary, page_results, failures, graph_edges,
        and state tracking sets.
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
            "queued_urls": list(self.queued_urls),
            "attempted_urls": list(self.attempted_urls),
            "crawled_urls": list(self.crawled_urls),
            "failed_urls": list(self.failed_urls),
            "skipped_urls": list(self.skipped_urls),
            "visited_urls": list(self.visited_urls),
        }
