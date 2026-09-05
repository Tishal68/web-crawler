"""
Data models for evidence extraction, cross-source verification,
contradiction detection, and confidence scoring.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class EvidencePassage:
    """An individual text passage extracted from a webpage."""
    text: str
    source_url: str
    source_domain: str
    source_title: str
    heading_context: str = ""
    relevance_score: float = 0.0
    published_date: Optional[str] = None
    source_type: str = "General Web Source"
    passage_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_url": self.source_url,
            "source_domain": self.source_domain,
            "source_title": self.source_title,
            "heading_context": self.heading_context,
            "relevance_score": round(self.relevance_score, 3),
            "published_date": self.published_date,
            "source_type": self.source_type,
            "passage_id": self.passage_id,
        }


@dataclass
class ExtractedPageEvidence:
    """Collection of structured evidence extracted from a single source URL."""
    url: str
    title: str
    domain: str
    source_type: str = "General Web Source"
    published_date: Optional[str] = None
    passages: List[EvidencePassage] = field(default_factory=list)
    top_passage: Optional[EvidencePassage] = None
    fetch_success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "source_type": self.source_type,
            "published_date": self.published_date,
            "passages_count": len(self.passages),
            "top_passage": self.top_passage.to_dict() if self.top_passage else None,
            "fetch_success": self.fetch_success,
            "error_message": self.error_message,
        }


@dataclass
class FactClaim:
    """A factual claim or proposition identified across sources."""
    statement: str
    primary_source_url: str
    corroborating_domains: List[str] = field(default_factory=list)
    corroborating_urls: List[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_corroborated(self) -> bool:
        return len(set(self.corroborating_domains)) >= 2


@dataclass
class ContradictionAlert:
    """Identifies a direct factual conflict between two or more sources."""
    topic_or_entity: str
    claim_a: str
    source_a_url: str
    source_a_domain: str
    claim_b: str
    source_b_url: str
    source_b_domain: str
    explanation: str

    def to_display_string(self) -> str:
        """Format an explicit human-readable contradiction warning."""
        return (
            f"⚠️ **Sources disagree on {self.topic_or_entity}:**\n"
            f"- **{self.source_a_domain}** reports: *\"{self.claim_a}\"*\n"
            f"- **{self.source_b_domain}** reports: *\"{self.claim_b}\"*"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_or_entity": self.topic_or_entity,
            "claim_a": self.claim_a,
            "source_a_url": self.source_a_url,
            "source_a_domain": self.source_a_domain,
            "claim_b": self.claim_b,
            "source_b_url": self.source_b_url,
            "source_b_domain": self.source_b_domain,
            "explanation": self.explanation,
        }


@dataclass
class ConfidenceReport:
    """Grounded confidence assessment for retrieved information."""
    badge_label: str  # e.g., "🟢 Strongly Corroborated"
    badge_color: str  # e.g., "green", "orange", "red"
    score: float  # Value between 0.0 and 0.95 (NEVER 1.0)
    independent_sources_count: int
    corroborating_domains: List[str] = field(default_factory=list)
    has_contradictions: bool = False
    contradictions: List[ContradictionAlert] = field(default_factory=list)
    rationales: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "badge_label": self.badge_label,
            "badge_color": self.badge_color,
            "score": round(self.score, 2),
            "independent_sources_count": self.independent_sources_count,
            "corroborating_domains": self.corroborating_domains,
            "has_contradictions": self.has_contradictions,
            "contradictions_count": len(self.contradictions),
            "rationales": self.rationales,
        }
