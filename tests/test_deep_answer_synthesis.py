"""
Unit tests for deep answer synthesis across complex multi-facet queries.
Verifies that the engine produces structured thematic reports rather than shallow snippets.
"""

import pytest
from answer.generator import AnswerGenerator
from evidence.models import EvidencePassage, ConfidenceReport
from search.query import QueryAnalyzer, QueryComplexity
from evidence.coverage import cluster_evidence_by_facets


def test_deep_answer_synthesis_jwst():
    generator = AnswerGenerator()
    analyzer = QueryAnalyzer()
    query = "James Webb Space Telescope instruments and recent discoveries"
    analysis = analyzer.analyze(query)

    passages = [
        EvidencePassage(
            text="The James Webb Space Telescope is an infrared space observatory located at the Sun-Earth L2 Lagrange point 1.5 million kilometers from Earth.",
            source_url="https://webbtelescope.org/overview",
            source_domain="webbtelescope.org",
            source_title="Webb Telescope Overview",
            heading_context="Mission Profile",
            passage_id="webb_1",
        ),
        EvidencePassage(
            text="Webb carries four state-of-the-art scientific instruments: NIRCam, NIRSpec, MIRI, and the Fine Guidance Sensor/NIRISS.",
            source_url="https://nasa.gov/jwst/instruments",
            source_domain="nasa.gov",
            source_title="NASA JWST Instruments",
            heading_context="Observatory Payload",
            passage_id="nasa_1",
        ),
        EvidencePassage(
            text="The Mid-Infrared Instrument (MIRI) operates at mid-infrared wavelengths from 5 to 28 microns, using an actively cooled cryocooler.",
            source_url="https://esa.int/jwst/miri",
            source_domain="esa.int",
            source_title="ESA MIRI Instrument",
            heading_context="MIRI Specifications",
            passage_id="esa_1",
        ),
        EvidencePassage(
            text="JWST observations confirmed the detection of carbon dioxide in the atmosphere of the hot gas giant exoplanet WASP-39b.",
            source_url="https://nature.com/articles/jwst-wasp39b",
            source_domain="nature.com",
            source_title="Nature WASP-39b Discovery",
            heading_context="Exoplanetary Atmospheres",
            passage_id="nature_1",
        ),
        EvidencePassage(
            text="Astronomers using Webb identified candidate galaxies existing just 300 million years after the Big Bang with extreme redshift values.",
            source_url="https://science.org/articles/jwst-early-universe",
            source_domain="science.org",
            source_title="Science Early Universe",
            heading_context="Cosmic Dawn",
            passage_id="science_1",
        ),
    ]

    confidence = ConfidenceReport(
        badge_label="🟢 Strongly Corroborated",
        badge_color="#10B981",
        score=0.91,
        independent_sources_count=5,
        corroborating_domains=["webbtelescope.org", "nasa.gov", "esa.int", "nature.com", "science.org"],
        rationales=["Cross-corroborated by 5 distinct primary domains."],
    )

    answer = generator.generate_answer(
        query=query,
        query_analysis=analysis,
        passages=passages,
        verification_summary={"independent_domains": ["webbtelescope.org", "nasa.gov", "esa.int", "nature.com", "science.org"], "contradictions": []},
        confidence_report=confidence,
    )

    # 1. Direct answer must be grounded and cited
    assert answer.direct_answer
    assert "[1]" in answer.direct_answer

    # 2. Structured thematic sections must be synthesized
    assert len(answer.structured_sections) >= 2
    section_titles = [s["title"] for s in answer.structured_sections]
    assert any("Instruments" in t for t in section_titles)
    assert any("Discoveries" in t for t in section_titles)

    # 3. Key findings must be populated with citations
    assert len(answer.key_findings) >= 3
    for f in answer.key_findings:
        assert "[" in f and "]" in f

    # 4. Follow up research prompts must exist
    assert len(answer.follow_up_questions) >= 3

    # 5. Citations strictly map to authentic domains
    assert len(answer.citations) >= 4
    citation_urls = [c.url for c in answer.citations]
    assert "https://nasa.gov/jwst/instruments" in citation_urls
    assert "https://nature.com/articles/jwst-wasp39b" in citation_urls

    # 6. Markdown output has structured sections
    assert "Deep Research Analysis & Thematic Synthesis" in answer.markdown_output
    assert "Sources & Verified References" in answer.markdown_output
    assert "Coverage Telemetry" in answer.markdown_output

