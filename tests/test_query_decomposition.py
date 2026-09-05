"""
Unit tests for query decomposition, complexity classification, and facet extraction.
"""

import pytest
from search.query import QueryAnalyzer, QueryComplexity, QueryFacet


def test_query_complexity_classification():
    analyzer = QueryAnalyzer()

    # Simple definition queries
    res_simple = analyzer.analyze("what is python")
    assert res_simple.complexity == QueryComplexity.SIMPLE

    # Comparison queries
    res_comp = analyzer.analyze("compare Python vs Rust concurrency and performance")
    assert res_comp.complexity == QueryComplexity.COMPARISON

    # Complex multi-facet research queries
    res_jwst = analyzer.analyze("James Webb Space Telescope instruments and recent discoveries")
    assert res_jwst.complexity == QueryComplexity.COMPLEX

    res_qc = analyzer.analyze("latest developments in quantum computing")
    assert res_qc.complexity == QueryComplexity.COMPLEX


def test_facet_decomposition_for_jwst():
    analyzer = QueryAnalyzer()
    res = analyzer.analyze("James Webb Space Telescope discoveries and how it works")

    assert len(res.facets) >= 3
    facet_titles = [f.title for f in res.facets]
    assert any("Overview" in t or "Mission" in t for t in facet_titles)
    assert any("Instruments" in t for t in facet_titles)
    assert any("Discoveries" in t for t in facet_titles)

    # Check search query generated for facets
    for f in res.facets:
        assert f.facet_id
        assert len(f.keywords) > 0
        assert f.search_query


def test_facet_decomposition_for_comparison():
    analyzer = QueryAnalyzer()
    res = analyzer.analyze("PostgreSQL vs MongoDB trade-offs and performance")

    assert res.complexity == QueryComplexity.COMPARISON
    assert len(res.facets) >= 3
    facet_titles = [f.title for f in res.facets]
    assert any("Architecture" in t for t in facet_titles)
    assert any("Trade-offs" in t or "Performance" in t for t in facet_titles)


def test_follow_up_questions_generation():
    analyzer = QueryAnalyzer()
    res = analyzer.analyze("James Webb Space Telescope exoplanet atmospheres")

    assert len(res.follow_up_questions) >= 3
    for q in res.follow_up_questions:
        assert len(q) > 10
        assert "?" in q or "how" in q.lower() or "what" in q.lower() or "which" in q.lower()

