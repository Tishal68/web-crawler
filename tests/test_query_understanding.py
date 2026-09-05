"""
Unit tests for QueryAnalyzer and QueryAnalysis.
"""

import pytest
from search.query import QueryAnalyzer, QueryAnalysis


@pytest.fixture
def analyzer():
    return QueryAnalyzer()


def test_time_sensitive_query(analyzer):
    analysis = analyzer.analyze("latest developments in quantum computing")
    assert analysis.is_time_sensitive
    assert analysis.intent == "temporal_current"
    assert "quantum" in analysis.keywords
    assert "computing" in analysis.keywords
    assert analysis.target_year == 2026


def test_year_detection_query(analyzer):
    analysis = analyzer.analyze("Nobel prize physics 2024 winners")
    assert analysis.is_time_sensitive
    assert analysis.target_year == 2024
    assert "physics" in analysis.keywords


def test_comparison_intent(analyzer):
    analysis = analyzer.analyze("React vs Vue 3 state management")
    assert analysis.is_comparison
    assert analysis.intent == "comparison"
    assert "React" in analysis.entities or "react" in analysis.keywords
    assert any("vs" in v or "differences" in v for v in analysis.search_variations)


def test_factual_query(analyzer):
    analysis = analyzer.analyze("who created Python programming language")
    assert analysis.intent == "factual"
    assert "Python" in analysis.entities or "python" in analysis.keywords


def test_entity_extraction(analyzer):
    analysis = analyzer.analyze("NIST standards for Post-Quantum Cryptography PQC")
    assert "NIST" in analysis.entities
    assert "PQC" in analysis.entities


def test_search_variations_generation(analyzer):
    analysis = analyzer.analyze("compare Python vs Go performance")
    assert len(analysis.search_variations) >= 2
