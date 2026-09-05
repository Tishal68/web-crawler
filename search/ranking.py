"""
Search result ranking module.
Applies multi-factor scoring (relevance, domain authority, freshness, and diversity)
to rank retrieved search results before evidence extraction.
"""

from typing import List, Optional, Dict
from .provider import SearchResult
from .query import QueryAnalysis
from .source_quality import score_source_quality
from crawler.url_utils import get_domain


def rank_search_results(
    results: List[SearchResult],
    query_analysis: Optional[QueryAnalysis] = None,
    max_results: int = 10,
    domain_diversity_limit: int = 2,
) -> List[SearchResult]:
    """
    Ranks search results by balancing semantic relevance, authority, recency,
    and domain diversity.

    Args:
        results: Raw search results from provider.
        query_analysis: Optional parsed query intent and keywords.
        max_results: Maximum number of ranked results to return.
        domain_diversity_limit: Max results allowed per unique root domain.

    Returns:
        List of ranked SearchResult objects with updated scores and ranks.
    """
    if not results:
        return []

    # Weights configuration based on query intent
    if query_analysis and query_analysis.is_time_sensitive:
        w_relevance = 0.40
        w_authority = 0.30
        w_recency = 0.30
    else:
        w_relevance = 0.50
        w_authority = 0.35
        w_recency = 0.15

    scored_items = []

    for item in results:
        # Score source quality & authority
        sq = score_source_quality(
            url=item.url,
            title=item.title,
            snippet=item.snippet,
            published_date=item.published_date,
            query=query_analysis.clean_query if query_analysis else "",
        )

        item.source_type = sq["source_type"].value if hasattr(sq["source_type"], "value") else str(sq["source_type"])
        item.authority_score = sq["authority_score"]

        # Relevance scoring
        rel_score = sq["relevance_score"]
        if query_analysis:
            title_lower = (item.title or "").lower()
            snippet_lower = (item.snippet or "").lower()

            # Exact clean query match bonus
            if query_analysis.clean_query.lower() in title_lower:
                rel_score += 0.20
            elif query_analysis.clean_query.lower() in snippet_lower:
                rel_score += 0.10

            # Entity match bonus
            for entity in query_analysis.entities:
                e_lower = entity.lower()
                if e_lower in title_lower:
                    rel_score += 0.10
                elif e_lower in snippet_lower:
                    rel_score += 0.05

            # Target year match bonus for time-sensitive queries
            if query_analysis.target_year:
                year_str = str(query_analysis.target_year)
                if year_str in (item.published_date or "") or year_str in title_lower:
                    rel_score += 0.15

        item.relevance_score = min(1.0, rel_score)

        # Composite score
        composite = (
            (item.relevance_score * w_relevance)
            + (item.authority_score * w_authority)
            + (sq["recency_score"] * w_recency)
        )
        scored_items.append((composite, item))

    # Sort descending by composite score
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # Domain diversity pass
    ranked: List[SearchResult] = []
    overflow: List[SearchResult] = []
    domain_counts: Dict[str, int] = {}

    for composite, item in scored_items:
        dom = get_domain(item.url).lower()
        curr_count = domain_counts.get(dom, 0)
        if curr_count < domain_diversity_limit:
            ranked.append(item)
            domain_counts[dom] = curr_count + 1
        else:
            overflow.append(item)

        if len(ranked) >= max_results:
            break

    # If we still have room under max_results, pull from overflow
    if len(ranked) < max_results and overflow:
        for item in overflow:
            ranked.append(item)
            if len(ranked) >= max_results:
                break

    # Re-assign 1-indexed ranks
    for idx, item in enumerate(ranked, start=1):
        item.rank = idx

    return ranked
