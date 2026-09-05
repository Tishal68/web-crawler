"""
Grounded answer generator module.
Synthesizes structured, evidence-backed answers with strict citation mapping,
direct answer extraction, corroboration breakdown, and explicit contradiction alerts.
"""

import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

from .citations import CitationRegistry, Citation
from evidence.models import EvidencePassage, ConfidenceReport, ContradictionAlert, FactClaim
from search.query import QueryAnalysis, QueryComplexity
from evidence.coverage import cluster_evidence_by_facets, EvidenceCoverageReport
from ai.model import BaseLLMProvider
from ai.llama import HostedLlamaProvider
from ai.citation_validator import CitationValidator
from ai.fallback import DeterministicResearchSynthesizer
from ai.schemas import SynthesizedResearchResponse

logger = logging.getLogger(__name__)


@dataclass
class GroundedAnswer:
    """The synthesized answer object containing verified claims, citations, and confidence."""
    query: str
    direct_answer: str
    key_findings: List[str] = field(default_factory=list)
    claims: List[Any] = field(default_factory=list)
    confidence: Optional[ConfidenceReport] = None
    contradictions: List[ContradictionAlert] = field(default_factory=list)
    corroborated_claims: List[FactClaim] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    markdown_output: str = ""
    generation_time: float = 0.0
    follow_up_questions: List[str] = field(default_factory=list)
    structured_sections: List[Dict[str, Any]] = field(default_factory=list)
    coverage_report: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "direct_answer": self.direct_answer,
            "key_findings": self.key_findings,
            "claims": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.claims],
            "confidence": self.confidence.to_dict() if self.confidence else None,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "caveats": self.caveats,
            "citations": [c.to_dict() for c in self.citations],
            "generation_time": round(self.generation_time, 3),
            "follow_up_questions": self.follow_up_questions,
            "structured_sections": self.structured_sections,
            "coverage_report": self.coverage_report.to_dict() if hasattr(self.coverage_report, "to_dict") else None,
        }



class AnswerGenerator:
    """Synthesizes structured, fully cited, deep research answers from extracted evidence passages."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider or HostedLlamaProvider()
        self.fallback_synthesizer = DeterministicResearchSynthesizer()

    def generate_answer(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        passages: List[EvidencePassage],
        verification_summary: Dict[str, Any],
        confidence_report: ConfidenceReport,
        coverage_report: Optional[EvidenceCoverageReport] = None,
        history: Optional[List[Dict[str, str]]] = None,
        target_language: str = "en",
    ) -> GroundedAnswer:
        """Synthesize an adaptive, deeply grounded research answer from retrieved evidence."""
        start_time = time.time()
        registry = CitationRegistry()

        if not passages:
            return GroundedAnswer(
                query=query,
                direct_answer="No relevant web evidence could be retrieved for this query. Try refining your search terms or checking network access.",
                confidence=confidence_report,
                caveats=["No search index results or accessible web pages answered this query."],
                generation_time=time.time() - start_time,
                follow_up_questions=getattr(query_analysis, "follow_up_questions", []),
            )

        # Build coverage report if not provided
        if coverage_report is None:
            coverage_report = cluster_evidence_by_facets(
                passages=passages,
                facets=getattr(query_analysis, "facets", []),
            )

        # Register citations for all retrieved passages
        for p in passages:
            registry.register(
                url=p.source_url,
                title=p.source_title,
                domain=p.source_domain,
                source_type=p.source_type,
                published_date=p.published_date,
                sample_quote=p.text,
            )

        citations_list = registry.all_citations()

        # 1. Attempt LLM Synthesis with Hosted Llama
        synthesized_resp: Optional[SynthesizedResearchResponse] = None
        if self.llm_provider and self.llm_provider.is_available():
            try:
                synthesized_resp = self.llm_provider.synthesize(
                    query=query,
                    sources=citations_list,
                    passages=passages,
                    analysis=query_analysis,
                    history=history,
                    target_language=target_language,
                )
            except Exception as e:
                logger.warning("LLM provider synthesis exception: %s", e)
                synthesized_resp = None

        # 2. Fallback to Deterministic Research Synthesizer if LLM not configured or failed
        if not synthesized_resp:
            synthesized_resp = self.fallback_synthesizer.synthesize(
                query=query,
                sources=citations_list,
                passages=passages,
                analysis=query_analysis,
                contradictions=verification_summary.get("contradictions"),
                coverage_report=coverage_report,
            )

        # 3. Strict Python Citation Validation
        validator = CitationValidator(citations_list)
        sanitized_resp, val_telemetry = validator.validate_and_sanitize(synthesized_resp)

        direct_answer = sanitized_resp.direct_answer
        key_findings = sanitized_resp.key_findings
        structured_sections = [
            {
                "title": s.title,
                "content": s.content,
                "citations": s.source_ids,
            }
            for s in sanitized_resp.sections
        ]
        claims = sanitized_resp.claims

        # 4. Transparent Caveats
        caveats = [
            "Information is synthesized probabilistically from live public web pages; accuracy reflects source reporting at the time of retrieval.",
            "For mission-critical, legal, or health decisions, verify directly with primary documentation and original publications.",
        ]
        if getattr(query_analysis, "is_time_sensitive", False):
            caveats.insert(0, "Time-sensitive query: developments may be actively evolving past the indexed publication dates.")

        contradictions = verification_summary.get("contradictions", [])
        corroborated_claims = verification_summary.get("corroborated_claims", [])
        follow_up_questions = (
            sanitized_resp.follow_up_questions
            or getattr(query_analysis, "follow_up_questions", [])
        )

        # 5. Assemble Complete Markdown Output
        md_lines = []

        # Confidence Badge Header
        md_lines.append(f"### {confidence_report.badge_label} (Confidence Score: {confidence_report.score:.2f} / 1.00)")
        md_lines.append("")
        md_lines.append(
            f"> **Corroboration Summary:** Synthesized across {confidence_report.independent_sources_count} independent domain(s). "
            + " · ".join(confidence_report.rationales)
        )
        md_lines.append("")

        # Direct Answer Section
        md_lines.append("#### 🎯 Direct Answer")
        md_lines.append(direct_answer)
        md_lines.append("")

        # In-depth Structured Research Sections
        if structured_sections:
            md_lines.append("#### 🔬 Deep Research Analysis & Thematic Synthesis")
            for sec in structured_sections:
                md_lines.append(f"##### {sec['title']}")
                md_lines.append(sec["content"])
                md_lines.append("")

        # Contradictions Alert Section (if any detected)
        if contradictions:
            md_lines.append("#### ⚠️ Source Discrepancies & Contradictions")
            for c in contradictions:
                md_lines.append(c.to_display_string())
                md_lines.append("")

        # Key Findings Section
        if key_findings:
            md_lines.append("#### 🔍 Key Findings & Evidence")
            for f in key_findings:
                md_lines.append(f"- {f}")
            md_lines.append("")

        # Recommended Follow-Up Questions
        if follow_up_questions:
            md_lines.append("#### 💡 Recommended Follow-Up Research")
            for q in follow_up_questions:
                md_lines.append(f"- {q}")
            md_lines.append("")

        # Sources & References Section
        md_lines.append(registry.format_references_markdown())
        md_lines.append("")

        # Grounding and Coverage Caveats Section
        md_lines.append("---")
        md_lines.append("#### ℹ️ Grounding & Verification Notes")
        if coverage_report:
            md_lines.append(
                f"> **Coverage Telemetry:** {coverage_report.covered_facets} of {coverage_report.total_facets} information requirements verified across {len(verification_summary.get('independent_domains', []))} independent domain(s)."
            )
            if coverage_report.unverified_requirements:
                md_lines.append(f"> **Unverified Requirements:** {'; '.join(coverage_report.unverified_requirements)}")
            md_lines.append("")
        for caveat in caveats:
            md_lines.append(f"- *{caveat}*")

        markdown_output = "\n".join(md_lines)
        gen_time = time.time() - start_time

        return GroundedAnswer(
            query=query,
            direct_answer=direct_answer,
            key_findings=key_findings,
            claims=claims,
            confidence=confidence_report,
            contradictions=contradictions,
            corroborated_claims=corroborated_claims,
            caveats=caveats,
            citations=citations_list,
            markdown_output=markdown_output,
            generation_time=gen_time,
            follow_up_questions=follow_up_questions,
            structured_sections=structured_sections,
            coverage_report=coverage_report,
        )

