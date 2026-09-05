"""
Unit tests for AI synthesis, HostedLlamaProvider, CitationValidator, and deterministic research synthesizer.
"""

from unittest.mock import patch, MagicMock
import pytest
import json

from ai.schemas import (
    SynthesizedClaim,
    SynthesizedSection,
    SynthesizedConflict,
    SynthesizedResearchResponse,
)
from ai.citation_validator import CitationValidator
from ai.llama import HostedLlamaProvider
from ai.fallback import DeterministicResearchSynthesizer
from answer.citations import Citation
from evidence.models import EvidencePassage


def make_citation(index: int, url: str, title: str, domain: str) -> Citation:
    return Citation(index=index, url=url, title=title, domain=domain, source_type="General Web Source")


def make_passage(text: str, url: str, domain: str = "example.com", title: str = "Title") -> EvidencePassage:
    return EvidencePassage(
        text=text,
        source_url=url,
        source_domain=domain,
        source_title=title,
        relevance_score=0.9,
    )


class TestCitationValidator:
    """Tests for validating and sanitizing LLM citation IDs against authentic sources."""

    def _make_validator_with_two_sources(self) -> CitationValidator:
        citations = [
            make_citation(1, "https://nasa.gov/jwst", "JWST Findings", "nasa.gov"),
            make_citation(2, "https://esa.int/jwst", "ESA Space Telescope", "esa.int"),
        ]
        return CitationValidator(citations)

    def test_retains_valid_citation_ids(self):
        validator = self._make_validator_with_two_sources()
        response = SynthesizedResearchResponse(
            direct_answer="JWST discovered ancient galaxies [1] and captured spectroscopy data [2].",
            claims=[SynthesizedClaim(text="Galaxies discovered", source_ids=[1, 2])],
        )
        cleaned, telemetry = validator.validate_and_sanitize(response)
        assert "[1]" in cleaned.direct_answer
        assert "[2]" in cleaned.direct_answer
        assert telemetry["hallucinated_citations_stripped"] == 0
        assert cleaned.claims[0].source_ids == [1, 2]

    def test_strips_hallucinated_citation_ids(self):
        validator = CitationValidator([
            make_citation(1, "https://nasa.gov/jwst", "JWST Findings", "nasa.gov"),
        ])
        response = SynthesizedResearchResponse(
            direct_answer="JWST found galaxies [1] and also [99] claimed something.",
            claims=[SynthesizedClaim(text="Galaxies", source_ids=[1, 99, 42])],
        )
        cleaned, telemetry = validator.validate_and_sanitize(response)
        assert "[1]" in cleaned.direct_answer
        assert "[99]" not in cleaned.direct_answer
        assert telemetry["hallucinated_citations_stripped"] >= 1
        assert cleaned.claims[0].source_ids == [1]

    def test_section_source_ids_stripped(self):
        validator = self._make_validator_with_two_sources()
        response = SynthesizedResearchResponse(
            direct_answer="Answer [1].",
            sections=[
                SynthesizedSection(
                    title="Section 1",
                    content="Content [1] with extra [8].",
                    source_ids=[1, 8],
                )
            ],
        )
        cleaned, telemetry = validator.validate_and_sanitize(response)
        assert cleaned.sections[0].source_ids == [1]
        assert "[8]" not in cleaned.sections[0].content
        assert telemetry["hallucinated_citations_stripped"] >= 1

    def test_all_citations_grounded_flag(self):
        validator = self._make_validator_with_two_sources()
        response = SynthesizedResearchResponse(
            direct_answer="Fact [1].",
            claims=[SynthesizedClaim(text="A", source_ids=[1])],
        )
        _, telemetry = validator.validate_and_sanitize(response)
        assert telemetry["all_citations_grounded"] is True


class TestHostedLlamaProvider:
    """Tests for Hosted LLM provider integration."""

    def test_is_available_false_when_no_api_key(self):
        provider = HostedLlamaProvider(api_key=None)
        provider._api_key = None
        assert provider.is_available() is False

    def test_is_available_true_with_groq_key(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}):
            provider = HostedLlamaProvider()
            assert provider.is_available() is True

    def test_successful_structured_synthesis_call(self):
        fake_response_json = {
            "direct_answer": "Quantum computing has achieved new logical qubit milestones [1].",
            "key_findings": ["Neutral atom systems demonstrated fault-tolerant operation."],
            "claims": [
                {"text": "Neutral atoms used for logical qubits.", "source_ids": [1]}
            ],
            "sections": [
                {
                    "title": "Fault-Tolerant Breakthroughs",
                    "content": "Researchers demonstrated error-corrected neutral atom systems [1].",
                    "source_ids": [1],
                }
            ],
            "conflicts": [],
            "follow_up_questions": ["What is the commercial timeline for neutral atom quantum computers?"],
        }

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "choices": [{"message": {"content": json.dumps(fake_response_json)}}]
        }

        sources = [make_citation(1, "https://nature.com/articles/quantum", "Quantum Breakthrough", "nature.com")]
        passages = [make_passage("Logical qubits demonstrated in neutral atoms.", "https://nature.com/articles/quantum", "nature.com", "Quantum Breakthrough")]

        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}):
            with patch("requests.post", return_value=mock_post_resp):
                provider = HostedLlamaProvider()
                result = provider.synthesize(query="quantum computing breakthroughs", sources=sources, passages=passages)

        assert result is not None
        assert isinstance(result, SynthesizedResearchResponse)
        assert "logical qubit milestones" in result.direct_answer
        assert len(result.sections) == 1
        assert result.sections[0].title == "Fault-Tolerant Breakthroughs"

    def test_synthesize_returns_none_when_unavailable(self):
        provider = HostedLlamaProvider(api_key=None)
        provider._api_key = None
        result = provider.synthesize(query="test", sources=[], passages=[])
        assert result is None


class TestDeterministicResearchSynthesizer:
    """Tests for zero-config fallback research synthesizer."""

    def test_synthesizes_structured_sections_and_citations(self):
        synthesizer = DeterministicResearchSynthesizer()
        sources = [
            make_citation(1, "https://nasa.gov/mission", "NASA JWST Observations", "nasa.gov"),
            make_citation(2, "https://esa.int/webb", "ESA Webb Research", "esa.int"),
        ]
        passages = [
            make_passage("The James Webb Space Telescope detected atmospheric carbon dioxide on WASP-39 b.", "https://nasa.gov/mission", "nasa.gov", "NASA JWST Observations"),
            make_passage("Observations reveal unexpected galaxy mass density at redshift z > 10.", "https://nasa.gov/mission", "nasa.gov", "NASA JWST Observations"),
            make_passage("WASP-39 b spectrum confirms significant carbon dioxide concentrations.", "https://esa.int/webb", "esa.int", "ESA Webb Research"),
        ]

        response = synthesizer.synthesize(
            query="James Webb Space Telescope exoplanet discoveries",
            sources=sources,
            passages=passages,
        )

        assert response is not None
        assert isinstance(response, SynthesizedResearchResponse)
        assert len(response.direct_answer) > 40
        assert len(response.follow_up_questions) >= 1

    def test_empty_passages_returns_graceful_fallback(self):
        synthesizer = DeterministicResearchSynthesizer()
        response = synthesizer.synthesize(
            query="exotic topic with no results",
            sources=[],
            passages=[],
        )
        assert response is not None
        assert isinstance(response, SynthesizedResearchResponse)
        assert len(response.direct_answer) > 0
