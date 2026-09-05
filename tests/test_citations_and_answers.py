"""
Unit tests for CitationRegistry and AnswerGenerator.
Verifies the anti-hallucination citation invariant and grounded answer synthesis.
"""

import pytest
from answer.citations import CitationRegistry, Citation
from answer.generator import AnswerGenerator
from evidence.models import EvidencePassage, ConfidenceReport
from search.query import QueryAnalyzer


def test_citation_registry_sequential_and_deduplication():
    registry = CitationRegistry()

    idx1 = registry.register(url="https://nature.com/article1", title="Article 1", domain="nature.com")
    assert idx1 == 1

    idx2 = registry.register(url="https://nist.gov/standard", title="NIST Standard", domain="nist.gov")
    assert idx2 == 2

    # Re-registering same URL must return the identical index
    idx1_again = registry.register(url="https://nature.com/article1", title="Article 1 Updated", domain="nature.com")
    assert idx1_again == 1
    assert len(registry.all_citations()) == 2


def test_citation_registry_rejects_empty_url():
    registry = CitationRegistry()
    with pytest.raises(ValueError):
        registry.register(url="", title="Empty", domain="example.com")


def test_answer_generator_grounding_and_citations():
    generator = AnswerGenerator()
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze("latest developments in quantum computing")

    passages = [
        EvidencePassage(
            text="IBM and other laboratories have advanced quantum error mitigation and scaling past 1,000 qubits.",
            source_url="https://research.ibm.com/quantum",
            source_domain="ibm.com",
            source_title="IBM Quantum",
            source_type="Company Primary Source",
        ),
        EvidencePassage(
            text="NIST has finalized post-quantum encryption standards to protect communications from quantum decryption.",
            source_url="https://nist.gov/pqc",
            source_domain="nist.gov",
            source_title="NIST PQC",
            source_type="Official Government",
        ),
    ]

    confidence = ConfidenceReport(
        badge_label="🟢 Strongly Corroborated",
        badge_color="#10B981",
        score=0.88,
        independent_sources_count=2,
        rationales=["Corroborated by 2 authoritative domains."],
    )

    grounded = generator.generate_answer(
        query="latest developments in quantum computing",
        query_analysis=analysis,
        passages=passages,
        verification_summary={"independent_domains": ["ibm.com", "nist.gov"], "contradictions": []},
        confidence_report=confidence,
    )

    assert grounded.direct_answer
    assert "[1]" in grounded.direct_answer
    assert len(grounded.citations) == 2
    assert any("IBM" in f or "quantum" in f.lower() for f in grounded.key_findings)
    assert grounded.confidence.score < 0.95
    # Markdown contains references section
    assert "Sources & Verified References" in grounded.markdown_output
    assert "ibm.com" in grounded.markdown_output
