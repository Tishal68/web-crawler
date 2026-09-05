"""
Data models and configuration classes for the web crawler.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class CrawlConfig:
    """Configuration options for a crawl session."""
    start_url: str
    max_depth: int = 2
    max_pages: int = 50
    timeout: float = 10.0
    request_delay: float = 0.2
    stay_on_domain: bool = True
    allow_subdomains: bool = True
    respect_robots: bool = True
    max_attempts: Optional[int] = None
    user_agent: str = (
        "WebCrawlerAnalytics/1.0 (+http://localhost; Academic Assignment Bot)"
    )
    search_query: Optional[str] = None
    keyword_filter: Optional[str] = None


@dataclass
class PageResult:
    """Stores information extracted from a successfully crawled webpage."""
    url: str
    title: str
    depth: int
    status_code: int
    total_links: int
    unique_links: int
    internal_links_count: int
    external_links_count: int
    internal_urls: List[str] = field(default_factory=list)
    external_urls: List[str] = field(default_factory=list)
    response_time: float = 0.0  # in seconds
    content_type: str = ""
    domain: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_url: Optional[str] = None
    text_snippet: str = ""
    word_count: int = 0
    matching_sentences: List[str] = field(default_factory=list)
    match_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert page result to a dictionary suitable for tabular display."""
        d = {
            "URL": self.url,
            "Title": self.title,
            "Depth": self.depth,
            "Status": self.status_code,
            "Words": self.word_count,
            "Matches": self.match_count,
            "Links": self.total_links,
            "Internal": self.internal_links_count,
            "External": self.external_links_count,
            "Response Time (s)": round(self.response_time, 3),
            "Domain": self.domain,
            "Snippet": self.text_snippet,
            "Content Type": self.content_type,
            "Timestamp": self.timestamp,
        }
        return d


@dataclass
class CrawlFailure:
    """Stores details regarding an attempt to crawl a URL that failed."""
    url: str
    depth: int
    error_type: str
    error_message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert failure to dictionary format."""
        return {
            "URL": self.url,
            "Depth": self.depth,
            "Error Type": self.error_type,
            "Error Message": self.error_message,
            "Timestamp": self.timestamp,
        }


@dataclass
class CrawlProgressEvent:
    """Event emitted during the live crawl process."""
    event_type: str  # 'start', 'searching', 'fetching', 'success', 'failure', 'skipped', 'completed'
    current_url: str
    current_depth: int
    pages_crawled: int
    discovered_count: int
    failed_count: int
    message: str
    page_result: Optional[PageResult] = None
    failure: Optional[CrawlFailure] = None


@dataclass
class CrawlSessionSummary:
    """Summary metrics of a completed crawl session."""
    session_id: str
    start_url: str
    max_depth: int
    max_pages: int
    start_time: str
    end_time: str
    elapsed_seconds: float
    pages_crawled: int
    discovered_urls_count: int
    failed_urls_count: int
    total_internal_links: int
    total_external_links: int
    stay_on_domain: bool
    max_depth_reached: int = 0
    search_query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary metrics to dictionary."""
        d = {
            "Session ID": self.session_id,
            "Start URL": self.start_url,
            "Max Depth Config": self.max_depth,
            "Max Depth Reached": self.max_depth_reached,
            "Max Pages Config": self.max_pages,
            "Pages Crawled": self.pages_crawled,
            "Discovered URLs": self.discovered_urls_count,
            "Failed URLs": self.failed_urls_count,
            "Total Internal Links": self.total_internal_links,
            "Total External Links": self.total_external_links,
            "Elapsed Seconds": round(self.elapsed_seconds, 2),
            "Start Time": self.start_time,
            "End Time": self.end_time,
        }
        if self.search_query:
            d["Search Query"] = self.search_query
        return d
