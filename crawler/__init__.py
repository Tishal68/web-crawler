"""
Web Crawler package.
Provides modular components for URL normalization, HTML parsing,
robots.txt parsing, queue-based crawling, and database storage.
"""

from .crawler import WebCrawler
from .models import CrawlConfig, PageResult, CrawlFailure, CrawlSessionSummary
from .database import CrawlDatabase

__all__ = [
    "WebCrawler",
    "CrawlConfig",
    "PageResult",
    "CrawlFailure",
    "CrawlSessionSummary",
    "CrawlDatabase",
]
