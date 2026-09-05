"""
Unit tests for source quality classification and hybrid multi-factor result ranking.
"""

import pytest
from search.source_quality import classify_source, score_source_quality, SourceType
from search.ranking import rank_search_results
from search.provider import SearchResult
from search.query import QueryAnalyzer


def test_classify_source_tiers():
    assert classify_source("https://www.nist.gov/publications/pqc") == SourceType.GOVERNMENT
    assert classify_source("https://cs.stanford.edu/research/quantum") == SourceType.ACADEMIC
    assert classify_source("https://www.w3.org/TR/webdriver/") == SourceType.STANDARDS_ORG
    assert classify_source("https://www.nature.com/articles/d41586-024-00123") == SourceType.SCIENTIFIC
    assert classify_source("https://www.reuters.com/technology/quantum-news") == SourceType.ESTABLISHED_JOURNALISM
    assert classify_source("https://docs.python.org/3/library/asyncio.html") == SourceType.COMPANY_PRIMARY
    assert classify_source("https://arstechnica.com/gadgets/2025/review") == SourceType.SPECIALIST_PUBLICATION
    assert classify_source("https://www.reddit.com/r/QuantumComputing/") == SourceType.COMMUNITY_DISCUSSION
    assert classify_source("https://random-personal-blog-xyz.com/post") == SourceType.UNKNOWN


def test_score_source_quality():
    res = score_source_quality(
        url="https://csrc.nist.gov/publications",
        title="NIST Post-Quantum Standards",
        snippet="Official specifications for post-quantum cryptographic algorithms.",
        published_date="2025-08-13",
        query="NIST post-quantum",
    )
    assert res["authority_score"] >= 0.90
    assert res["relevance_score"] >= 0.50
    assert res["recency_score"] >= 0.80
    assert res["composite_score"] >= 0.80


def test_rank_search_results_diversity():
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze("quantum algorithms")

    # 4 results from the same domain and 2 from other domains
    raw_results = [
        SearchResult(title="Medium 1", url="https://medium.com/post1", snippet="Quantum info"),
        SearchResult(title="Medium 2", url="https://medium.com/post2", snippet="Quantum info"),
        SearchResult(title="Medium 3", url="https://medium.com/post3", snippet="Quantum info"),
        SearchResult(title="Medium 4", url="https://medium.com/post4", snippet="Quantum info"),
        SearchResult(title="NIST Spec", url="https://nist.gov/pqc", snippet="Quantum algorithm standard"),
        SearchResult(title="Nature Paper", url="https://nature.com/article1", snippet="Quantum algorithm research"),
        SearchResult(title="Ars Review", url="https://arstechnica.com/qc", snippet="Quantum algorithm research"),
    ]

    ranked = rank_search_results(
        results=raw_results,
        query_analysis=analysis,
        max_results=5,
        domain_diversity_limit=2,
    )

    # Count occurrences of medium.com in top results
    medium_count = sum(1 for r in ranked if "medium.com" in r.url)
    assert medium_count <= 2
    # Check that high authority NIST is ranked high
    nist_res = next(r for r in ranked if "nist.gov" in r.url)
    assert nist_res.rank in (1, 2)
