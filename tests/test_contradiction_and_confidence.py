"""
Unit tests for ContradictionDetector, explicit disagreement formatting,
and explainable confidence assessment (guaranteed never 100%).
"""

import pytest
from evidence.contradiction import ContradictionDetector
from evidence.confidence import calculate_confidence
from evidence.models import EvidencePassage, ExtractedPageEvidence


def test_numeric_contradiction_detection():
    detector = ContradictionDetector()

    p_a = EvidencePassage(
        text="The new IBM Condor processor operates with 1,121 qubits in laboratory tests.",
        source_url="https://ibm.com/press/condor",
        source_domain="ibm.com",
        source_title="IBM Condor",
    )
    p_b = EvidencePassage(
        text="The IBM Condor processor operates with 433 qubits in recent benchmarks.",
        source_url="https://techblog.io/condor-review",
        source_domain="techblog.io",
        source_title="Condor Review",
    )

    conflicts = detector.detect_contradictions([p_a, p_b])
    assert len(conflicts) >= 1
    alert = conflicts[0]
    assert alert.source_a_domain != alert.source_b_domain
    disp = alert.to_display_string()
    assert "Sources disagree" in disp
    assert "ibm.com" in disp
    assert "techblog.io" in disp


def test_temporal_contradiction_detection():
    detector = ContradictionDetector()

    p_a = EvidencePassage(
        text="The enterprise platform was officially released in October 2023.",
        source_url="https://news-site-a.com/release",
        source_domain="news-site-a.com",
        source_title="Release News",
    )
    p_b = EvidencePassage(
        text="The enterprise platform was officially released in March 2025.",
        source_url="https://news-site-b.com/release",
        source_domain="news-site-b.com",
        source_title="Platform Overview",
    )

    conflicts = detector.detect_contradictions([p_a, p_b])
    assert len(conflicts) >= 1
    assert "Released" in conflicts[0].topic_or_entity or "date" in conflicts[0].topic_or_entity.lower()


def test_polarity_contradiction_detection():
    detector = ContradictionDetector()

    p_a = EvidencePassage(
        text="The framework core is completely open source under Apache 2.0 license.",
        source_url="https://source-a.org/license",
        source_domain="source-a.org",
        source_title="Source A",
    )
    p_b = EvidencePassage(
        text="The framework core is proprietary and closed source for enterprise clients.",
        source_url="https://source-b.org/pricing",
        source_domain="source-b.org",
        source_title="Source B",
    )

    conflicts = detector.detect_contradictions([p_a, p_b])
    assert len(conflicts) >= 1
    assert "Licensing" in conflicts[0].topic_or_entity


def test_confidence_strongly_corroborated():
    ev1 = ExtractedPageEvidence(url="https://nist.gov/pqc", title="NIST", domain="nist.gov", source_type="Official Government")
    ev2 = ExtractedPageEvidence(url="https://mit.edu/crypto", title="MIT", domain="mit.edu", source_type="University / Academic")
    ev3 = ExtractedPageEvidence(url="https://reuters.com/tech", title="Reuters", domain="reuters.com", source_type="Established Journalism")

    report = calculate_confidence(
        independent_domains=["nist.gov", "mit.edu", "reuters.com"],
        contradictions=[],
        extracted_evidence=[ev1, ev2, ev3],
    )

    assert "Strongly Corroborated" in report.badge_label
    assert report.score < 0.96  # Invariant: Never 1.0 (100%)
    assert report.score >= 0.80
    assert not report.has_contradictions


def test_confidence_conflicting_sources():
    detector = ContradictionDetector()
    p_a = EvidencePassage(
        text="The system reached 1000 qubits.",
        source_url="https://a.com",
        source_domain="a.com",
        source_title="A",
    )
    p_b = EvidencePassage(
        text="The system reached 200 qubits.",
        source_url="https://b.com",
        source_domain="b.com",
        source_title="B",
    )
    conflicts = detector.detect_contradictions([p_a, p_b])

    report = calculate_confidence(
        independent_domains=["a.com", "b.com"],
        contradictions=conflicts,
        extracted_evidence=[],
    )

    assert "Conflicting Sources" in report.badge_label
    assert report.has_contradictions
    assert report.score <= 0.50
