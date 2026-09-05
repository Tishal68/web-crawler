"""
Unit tests for SearchPipeline end-to-end orchestration.
"""

from unittest.mock import patch, MagicMock
import pytest
from search.pipeline import SearchPipeline
from search.provider import SearchProvider, SearchResult, SearchResultSet
from evidence.models import ExtractedPageEvidence, EvidencePassage


class MockSearchProvider(SearchProvider):
    @property
    def provider_name(self) -> str:
        return "MockEngine"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, num_results: int = 10) -> SearchResultSet:
        return SearchResultSet(
            query=query,
            provider_name=self.provider_name,
            results=[
                SearchResult(
                    title="NIST Post-Quantum Cryptography",
                    url="https://csrc.nist.gov/projects/pqc",
                    snippet="NIST has announced official standards for quantum-resistant cryptography.",
                    published_date="2024-08-13",
                ),
                SearchResult(
                    title="Nature Quantum Review",
                    url="https://nature.com/articles/quantum-review",
                    snippet="Review of global post-quantum cryptography standards and deployment.",
                    published_date="2024-09-01",
                ),
            ],
            total_results=2,
        )


def test_search_pipeline_end_to_end():
    pipeline = SearchPipeline()
    # Inject mock provider
    mock_prov = MockSearchProvider()
    pipeline.multi_provider = mock_prov

    # Mock evidence extractor to avoid real external HTTP traffic during tests
    def mock_extract(results, max_workers=4):
        return [
            ExtractedPageEvidence(
                url="https://csrc.nist.gov/projects/pqc",
                title="NIST Post-Quantum Cryptography",
                domain="csrc.nist.gov",
                source_type="Official Government",
                published_date="2024-08-13",
                passages=[
                    EvidencePassage(
                        text="NIST has released the first set of finalized post-quantum cryptographic standards.",
                        source_url="https://csrc.nist.gov/projects/pqc",
                        source_domain="csrc.nist.gov",
                        source_title="NIST PQC",
                        heading_context="Standards Release",
                        source_type="Official Government",
                        passage_id="nist_1",
                    )
                ],
            ),
            ExtractedPageEvidence(
                url="https://nature.com/articles/quantum-review",
                title="Nature Quantum Review",
                domain="nature.com",
                source_type="Scientific Publication",
                published_date="2024-09-01",
                passages=[
                    EvidencePassage(
                        text="Global institutions are transitioning to post-quantum standards to secure data.",
                        source_url="https://nature.com/articles/quantum-review",
                        source_domain="nature.com",
                        source_title="Nature Review",
                        heading_context="Adoption",
                        source_type="Scientific Publication",
                        passage_id="nature_1",
                    )
                ],
            ),
        ]

    with patch.object(pipeline.evidence_extractor, "extract_from_search_results", side_effect=mock_extract):
        result = pipeline.run(
            query="post-quantum cryptography standards NIST",
            num_sources=5,
            provider_preference="multi",
        )

        assert result.query == "post-quantum cryptography standards NIST"
        assert len(result.ranked_results) >= 2
        assert len(result.top_passages) >= 2
        assert result.answer is not None
        assert result.answer.direct_answer
        assert "[1]" in result.answer.direct_answer
        assert result.confidence is not None
        assert result.confidence.score < 0.95
        assert len(result.answer.citations) >= 2
        d = result.to_dict()
        assert d["query"] == result.query
