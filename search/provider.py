"""
Abstract search provider interface and core search data models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from crawler.url_utils import get_domain, normalize_url


@dataclass
class SearchResult:
    """Represents an individual search result item."""
    title: str
    url: str
    snippet: str
    display_domain: str = ""
    published_date: Optional[str] = None
    source_type: str = "Unknown"
    rank: int = 0
    relevance_score: float = 0.0
    authority_score: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.display_domain and self.url:
            self.display_domain = get_domain(self.url)
        if self.url:
            norm = normalize_url(self.url)
            if norm:
                self.url = norm

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "display_domain": self.display_domain,
            "published_date": self.published_date,
            "source_type": self.source_type,
            "rank": self.rank,
            "relevance_score": self.relevance_score,
            "authority_score": self.authority_score,
        }


@dataclass
class SearchResultSet:
    """Represents the complete result set of a search query."""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    provider_name: str = "Unknown"
    total_results: int = 0
    search_time: float = 0.0
    error_message: Optional[str] = None

    def __len__(self) -> int:
        return len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "provider_name": self.provider_name,
            "total_results": self.total_results,
            "search_time": round(self.search_time, 3),
            "error_message": self.error_message,
        }


class SearchProvider(ABC):
    """Abstract base class for all web search providers."""

    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> SearchResultSet:
        """Execute web search query and return standardized SearchResultSet."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available for requests."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier name for this search provider."""
        pass
