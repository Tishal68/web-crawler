"""
Evidence Package: Passage extraction, relevance ranking, cross-source verification,
contradiction detection, and confidence scoring.
"""

from .models import (
    EvidencePassage,
    ExtractedPageEvidence,
    FactClaim,
    ContradictionAlert,
    ConfidenceReport,
)
from .extractor import EvidenceExtractor
from .relevance import score_passage_relevance, rank_and_filter_passages
from .contradiction import ContradictionDetector
from .verifier import EvidenceVerifier
from .confidence import calculate_confidence

__all__ = [
    "EvidencePassage",
    "ExtractedPageEvidence",
    "FactClaim",
    "ContradictionAlert",
    "ConfidenceReport",
    "EvidenceExtractor",
    "score_passage_relevance",
    "rank_and_filter_passages",
    "ContradictionDetector",
    "EvidenceVerifier",
    "calculate_confidence",
]
