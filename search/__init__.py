"""
Search Package: Search provider abstraction, query understanding,
source quality classification, result ranking, and caching.
"""

from .provider import SearchProvider, SearchResult, SearchResultSet
from .google_provider import GoogleSearchProvider
from .multi_provider import MultiEngineSearchProvider
from .query import QueryAnalyzer, QueryAnalysis
from .source_quality import SourceType, classify_source, score_source_quality
from .ranking import rank_search_results
from .cache import SearchCache


def __getattr__(name: str):
    if name in ("SearchPipeline", "SearchPipelineResult"):
        from .pipeline import SearchPipeline, SearchPipelineResult
        return SearchPipeline if name == "SearchPipeline" else SearchPipelineResult
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "SearchProvider",
    "SearchResult",
    "SearchResultSet",
    "GoogleSearchProvider",
    "MultiEngineSearchProvider",
    "QueryAnalyzer",
    "QueryAnalysis",
    "SourceType",
    "classify_source",
    "score_source_quality",
    "rank_search_results",
    "SearchCache",
    "SearchPipeline",
    "SearchPipelineResult",
]
