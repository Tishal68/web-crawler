"""
Structured response schemas for AI answer synthesis and citation grounding.
Enforces typed output contracts with strict integer source IDs.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SynthesizedClaim:
    """An individual factual claim linked to specific integer source IDs."""
    text: str
    source_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_ids": self.source_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesizedClaim":
        text = str(data.get("text", "")).strip()
        raw_ids = data.get("source_ids", [])
        valid_ids: List[int] = []
        if isinstance(raw_ids, list):
            for i in raw_ids:
                try:
                    valid_ids.append(int(i))
                except (ValueError, TypeError):
                    pass
        return cls(text=text, source_ids=valid_ids)


@dataclass
class SynthesizedSection:
    """A thematic section of the comprehensive research report."""
    title: str
    content: str
    source_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "source_ids": self.source_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesizedSection":
        title = str(data.get("title", "")).strip()
        content = str(data.get("content", "")).strip()
        raw_ids = data.get("source_ids", [])
        valid_ids: List[int] = []
        if isinstance(raw_ids, list):
            for i in raw_ids:
                try:
                    valid_ids.append(int(i))
                except (ValueError, TypeError):
                    pass
        return cls(title=title, content=content, source_ids=valid_ids)


@dataclass
class SynthesizedConflict:
    """Explicit contradiction or disagreement documented between sources."""
    topic: str
    view_a: str
    view_b: str
    source_ids_a: List[int] = field(default_factory=list)
    source_ids_b: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "view_a": self.view_a,
            "source_ids_a": self.source_ids_a,
            "view_b": self.view_b,
            "source_ids_b": self.source_ids_b,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesizedConflict":
        topic = str(data.get("topic", "")).strip()
        view_a = str(data.get("view_a", "")).strip()
        view_b = str(data.get("view_b", "")).strip()
        
        def parse_ids(raw):
            out = []
            if isinstance(raw, list):
                for i in raw:
                    try:
                        out.append(int(i))
                    except (ValueError, TypeError):
                        pass
            return out

        return cls(
            topic=topic,
            view_a=view_a,
            source_ids_a=parse_ids(data.get("source_ids_a")),
            view_b=view_b,
            source_ids_b=parse_ids(data.get("source_ids_b")),
        )


@dataclass
class SynthesizedResearchResponse:
    """The complete structured research response produced by an AI model."""
    direct_answer: str
    key_findings: List[str] = field(default_factory=list)
    claims: List[SynthesizedClaim] = field(default_factory=list)
    sections: List[SynthesizedSection] = field(default_factory=list)
    conflicts: List[SynthesizedConflict] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direct_answer": self.direct_answer,
            "key_findings": self.key_findings,
            "claims": [c.to_dict() for c in self.claims],
            "sections": [s.to_dict() for s in self.sections],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "follow_up_questions": self.follow_up_questions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesizedResearchResponse":
        direct_answer = str(data.get("direct_answer", "") or data.get("answer", "")).strip()
        
        raw_kf = data.get("key_findings", [])
        key_findings = [str(x).strip() for x in raw_kf if str(x).strip()] if isinstance(raw_kf, list) else []

        raw_claims = data.get("claims", [])
        claims = [SynthesizedClaim.from_dict(c) for c in raw_claims if isinstance(c, dict)] if isinstance(raw_claims, list) else []

        raw_sections = data.get("sections", [])
        sections = [SynthesizedSection.from_dict(s) for s in raw_sections if isinstance(s, dict)] if isinstance(raw_sections, list) else []

        raw_conflicts = data.get("conflicts", [])
        conflicts = [SynthesizedConflict.from_dict(cf) for cf in raw_conflicts if isinstance(cf, dict)] if isinstance(raw_conflicts, list) else []

        raw_fu = data.get("follow_up_questions", [])
        follow_up = [str(x).strip() for x in raw_fu if str(x).strip()] if isinstance(raw_fu, list) else []

        return cls(
            direct_answer=direct_answer,
            key_findings=key_findings,
            claims=claims,
            sections=sections,
            conflicts=conflicts,
            follow_up_questions=follow_up,
        )
