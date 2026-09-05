"""
Unit tests for EvidenceExtractor, date extraction, and passage relevance scoring.
"""

import pytest
from evidence.extractor import EvidenceExtractor
from evidence.relevance import score_passage_relevance, rank_and_filter_passages
from evidence.models import EvidencePassage
from search.query import QueryAnalyzer


@pytest.fixture
def extractor():
    return EvidenceExtractor(timeout=3.0)


def test_extract_date_json_ld(extractor):
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "headline": "Breakthrough in Quantum Chips",
          "datePublished": "2025-11-20T08:00:00Z"
        }
        </script>
      </head>
      <body><p>Content here.</p></body>
    </html>
    """
    ev = extractor.extract_from_html(html, url="https://example.com/quantum", title="Breakthrough")
    assert ev.published_date == "2025-11-20"
    assert ev.fetch_success


def test_extract_passages_and_headings(extractor):
    html = """
    <html>
      <head><title>Quantum Computing Progress</title></head>
      <body>
        <nav><a href="#">Home</a> Cookie policy</nav>
        <h1>Quantum Computing Advances</h1>
        <h2>Error Correction</h2>
        <p>Researchers have achieved a critical milestone by demonstrating fault-tolerant logical qubits with physical fidelity exceeding 99.9%.</p>
        <p>Short</p>
        <h2>Hardware Scaling</h2>
        <p>New superconducting architectures have demonstrated scaling up to 1,000 physical qubits in a single dilution refrigerator.</p>
        <footer>Copyright 2026. All rights reserved.</footer>
      </body>
    </html>
    """
    ev = extractor.extract_from_html(html, url="https://example.org/qc", title="Quantum Progress")
    assert len(ev.passages) >= 2
    p1 = ev.passages[0]
    assert "Error Correction" in p1.heading_context or "Quantum" in p1.heading_context
    assert "fault-tolerant logical qubits" in p1.text


def test_fallback_to_snippet_on_empty(extractor):
    ev = extractor.extract_from_html(
        html="",
        url="https://example.com/broken",
        title="Broken Page",
        snippet="This snippet explains quantum error mitigation.",
    )
    assert not ev.fetch_success
    assert len(ev.passages) == 1
    assert "error mitigation" in ev.passages[0].text


def test_passage_relevance_scoring():
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze("latest developments in quantum computing")

    p_relevant = EvidencePassage(
        text="Recent 2026 developments in quantum computing have focused on logical qubits and fault tolerance.",
        source_url="https://nature.com/article",
        source_domain="nature.com",
        source_title="Quantum Computing 2026",
    )
    p_irrelevant = EvidencePassage(
        text="The local weather forecast for tomorrow calls for sunny skies and light breezes.",
        source_url="https://weather.com/forecast",
        source_domain="weather.com",
        source_title="Weather",
    )

    s_rel = score_passage_relevance(p_relevant, analysis)
    s_irrel = score_passage_relevance(p_irrelevant, analysis)

    assert s_rel > s_irrel
    assert s_rel >= 0.50

    ranked = rank_and_filter_passages([p_irrelevant, p_relevant], analysis)
    assert len(ranked) >= 1
    assert ranked[0] == p_relevant
