"""
Grounded answer generator module.
Synthesizes structured, evidence-backed answers with strict citation mapping,
direct answer extraction, corroboration breakdown, and explicit contradiction alerts.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .citations import CitationRegistry, Citation
from evidence.models import EvidencePassage, ConfidenceReport, ContradictionAlert, FactClaim
from search.query import QueryAnalysis


@dataclass
class GroundedAnswer:
    """The synthesized answer object containing verified claims, citations, and confidence."""
    query: str
    direct_answer: str
    key_findings: List[str] = field(default_factory=list)
    confidence: Optional[ConfidenceReport] = None
    contradictions: List[ContradictionAlert] = field(default_factory=list)
    corroborated_claims: List[FactClaim] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    markdown_output: str = ""
    generation_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "direct_answer": self.direct_answer,
            "key_findings": self.key_findings,
            "confidence": self.confidence.to_dict() if self.confidence else None,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "caveats": self.caveats,
            "citations": [c.to_dict() for c in self.citations],
            "generation_time": round(self.generation_time, 3),
        }


class AnswerGenerator:
    """Synthesizes structured, fully cited answers from extracted evidence passages."""

    def generate_answer(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        passages: List[EvidencePassage],
        verification_summary: Dict[str, Any],
        confidence_report: ConfidenceReport,
    ) -> GroundedAnswer:
        """Synthesize a complete grounded answer from retrieved evidence."""
        start_time = time.time()
        registry = CitationRegistry()

        if not passages:
            return GroundedAnswer(
                query=query,
                direct_answer="No relevant web evidence could be retrieved for this query. Try refining your search terms or checking network access.",
                confidence=confidence_report,
                caveats=["No search index results or accessible web pages answered this query."],
                generation_time=time.time() - start_time,
            )

        # Register citations for all used passages
        passage_citation_map: Dict[str, int] = {}
        for p in passages:
            idx = registry.register(
                url=p.source_url,
                title=p.source_title,
                domain=p.source_domain,
                source_type=p.source_type,
                published_date=p.published_date,
                sample_quote=p.text,
            )
            passage_citation_map[p.passage_id or p.text[:40]] = idx

        # 1. Synthesize Direct Answer
        top_passage = passages[0]
        top_cite = passage_citation_map.get(top_passage.passage_id or top_passage.text[:40], 1)

        # Clean passage text to form direct answer
        direct_sentences = [s.strip() for s in top_passage.text.split(". ") if len(s.strip()) > 20]
        if direct_sentences:
            core_summary = ". ".join(direct_sentences[:2])
            if not core_summary.endswith("."):
                core_summary += "."
            direct_answer = f"{core_summary} [{top_cite}]"
        else:
            direct_answer = f"{top_passage.text} [{top_cite}]"

        # If second top passage from a different domain exists, blend for multi-perspective answer
        secondary_passages = [p for p in passages[1:] if p.source_domain != top_passage.source_domain]
        if secondary_passages:
            sec_p = secondary_passages[0]
            sec_cite = passage_citation_map.get(sec_p.passage_id or sec_p.text[:40], 2)
            sec_sentences = [s.strip() for s in sec_p.text.split(". ") if len(s.strip()) > 20]
            if sec_sentences:
                direct_answer += f" Furthermore, {sec_sentences[0]} [{sec_cite}]"

        # 2. Extract Key Findings (Bulleted takeaways with citations)
        key_findings: List[str] = []
        seen_domains_for_findings = set()

        for p in passages:
            if len(key_findings) >= 5:
                break
            cite_idx = passage_citation_map.get(p.passage_id or p.text[:40], 1)
            sentences = [s.strip() for s in p.text.split(". ") if len(s.strip()) > 25]
            for s in sentences:
                clean_s = s.strip()
                if not clean_s.endswith("."):
                    clean_s += "."
                # For rich passage sets (>2), avoid repeating exact direct answer verbatim
                if len(passages) > 2 and clean_s.lower() in direct_answer.lower():
                    continue
                finding = f"{clean_s} [{cite_idx}]"
                if finding not in key_findings:
                    key_findings.append(finding)
                    seen_domains_for_findings.add(p.source_domain)
                    break

        # Fallback if all candidate sentences were filtered
        if not key_findings and passages:
            for p in passages[:3]:
                cite_idx = passage_citation_map.get(p.passage_id or p.text[:40], 1)
                snippet = " ".join(p.text.split()[:30])
                if not snippet.endswith("."):
                    snippet += "..."
                key_findings.append(f"{snippet} [{cite_idx}]")

        # 3. Transparent Caveats
        caveats = [
            "Information is synthesized probabilistically from live public web pages; accuracy reflects source reporting at the time of retrieval.",
            "For mission-critical, legal, or health decisions, verify directly with primary documentation and original publications.",
        ]
        if query_analysis.is_time_sensitive:
            caveats.insert(0, "Time-sensitive query: developments may be actively evolving past the indexed publication dates.")

        contradictions = verification_summary.get("contradictions", [])
        corroborated_claims = verification_summary.get("corroborated_claims", [])

        # 4. Assemble Complete Markdown Output
        md_lines = []

        # Confidence Badge Header
        md_lines.append(f"### {confidence_report.badge_label} (Confidence Score: {confidence_report.score:.2f} / 1.00)")
        md_lines.append("")
        md_lines.append(f"> **Corroboration Summary:** Synthesized across {confidence_report.independent_sources_count} independent domain(s). " +
                        " · ".join(confidence_report.rationales))
        md_lines.append("")

        # Direct Answer Section
        md_lines.append("#### 🎯 Direct Answer")
        md_lines.append(direct_answer)
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

        # Sources & References Section
        md_lines.append(registry.format_references_markdown())
        md_lines.append("")

        # Caveats Section
        md_lines.append("---")
        md_lines.append("#### ℹ️ Grounding & Verification Notes")
        for caveat in caveats:
            md_lines.append(f"- *{caveat}*")

        markdown_output = "\n".join(md_lines)
        gen_time = time.time() - start_time

        return GroundedAnswer(
            query=query,
            direct_answer=direct_answer,
            key_findings=key_findings,
            confidence=confidence_report,
            contradictions=contradictions,
            corroborated_claims=corroborated_claims,
            caveats=caveats,
            citations=registry.all_citations(),
            markdown_output=markdown_output,
            generation_time=gen_time,
        )
