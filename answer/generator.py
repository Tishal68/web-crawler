"""
Grounded answer generator module.
Synthesizes structured, evidence-backed answers with strict citation mapping,
direct answer extraction, corroboration breakdown, and explicit contradiction alerts.
"""

import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .citations import CitationRegistry, Citation
from evidence.models import EvidencePassage, ConfidenceReport, ContradictionAlert, FactClaim
from search.query import QueryAnalysis, QueryComplexity
from evidence.coverage import cluster_evidence_by_facets, EvidenceCoverageReport



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
    follow_up_questions: List[str] = field(default_factory=list)
    structured_sections: List[Dict[str, Any]] = field(default_factory=list)
    coverage_report: Optional[Any] = None

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
            "follow_up_questions": self.follow_up_questions,
            "structured_sections": self.structured_sections,
            "coverage_report": self.coverage_report.to_dict() if hasattr(self.coverage_report, "to_dict") else None,
        }



class AnswerGenerator:
    """Synthesizes structured, fully cited, deep research answers from extracted evidence passages."""

    @staticmethod
    def _clean_sentence(raw: str) -> Optional[str]:
        """Normalize sentence text, removing leading symbols, bullets, or numbers."""
        s = raw.strip()
        s = re.sub(r"^(\d+[\.\)]|[-*•])\s*", "", s).strip()
        if len(s) < 25:
            return None
        if not s[0].isalnum():
            return None
        lower = s.lower()
        if any(lower.startswith(prefix) for prefix in (
            "credit:", "credit ", "photo credit", "image credit", "source:", "photo:", "image:"
        )):
            return None
        if any(bad in lower for bad in (
            "all rights reserved", "terms of use", "privacy policy", "cookie policy",
            "copyright ©", "click here", "sign up for"
        )):
            return None
        s = s[0].upper() + s[1:]
        if not s.endswith((".", "!", "?")):
            s += "."
        return s

    def _extract_coherent_sentences(
        self,
        passages: List[EvidencePassage],
        max_sentences: int = 4,
    ) -> List[Dict[str, Any]]:
        """Extract top distinct, informative sentences from passages with their passage references."""
        candidates: List[Dict[str, Any]] = []
        seen_texts = set()

        for p in passages:
            splits = re.split(r"(?<=[.!?])\s+", p.text)
            for raw_s in splits:
                s = self._clean_sentence(raw_s)
                if not s:
                    continue
                if len(s.split()) < 6:
                    continue
                fingerprint = s[:60].lower()
                if fingerprint in seen_texts:
                    continue
                seen_texts.add(fingerprint)
                candidates.append({
                    "sentence": s,
                    "passage": p,
                    "domain": p.source_domain,
                    "url": p.source_url,
                })
                if len(candidates) >= max_sentences * 2:
                    break
            if len(candidates) >= max_sentences * 2:
                break
        return candidates[:max_sentences]

    def generate_answer(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        passages: List[EvidencePassage],
        verification_summary: Dict[str, Any],
        confidence_report: ConfidenceReport,
        coverage_report: Optional[EvidenceCoverageReport] = None,
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

        # 1. Synthesize Direct Answer / Executive Summary
        top_passage = passages[0]
        top_cite = passage_citation_map.get(top_passage.passage_id or top_passage.text[:40], 1)

        direct_sentences = [self._clean_sentence(s) for s in re.split(r"(?<=[.!?])\s+", top_passage.text) if self._clean_sentence(s)]
        if direct_sentences:
            core_summary = ". ".join(s.rstrip(".") for s in direct_sentences[:2]) + "."
            direct_answer = f"{core_summary} [{top_cite}]"
        else:
            cleaned_top = self._clean_sentence(top_passage.text[:220]) or top_passage.text[:220]
            direct_answer = f"{cleaned_top} [{top_cite}]"

        # Blend secondary passage from distinct domain for multi-perspective synthesis
        secondary_passages = [p for p in passages[1:] if p.source_domain != top_passage.source_domain]
        if secondary_passages:
            sec_p = secondary_passages[0]
            sec_cite = passage_citation_map.get(sec_p.passage_id or sec_p.text[:40], 2)
            sec_sentences = [self._clean_sentence(s) for s in re.split(r"(?<=[.!?])\s+", sec_p.text) if self._clean_sentence(s)]
            if sec_sentences:
                sec_text = sec_sentences[0].rstrip(".") + "."
                # Ensure it's not identical to the first passage
                if sec_text.lower() not in direct_answer.lower():
                    direct_answer += f" Furthermore, {sec_text} [{sec_cite}]"

        # 2. Build Structured Thematic Sections
        structured_sections: List[Dict[str, Any]] = []
        is_simple = getattr(query_analysis, "complexity", None) == QueryComplexity.SIMPLE

        if not is_simple and coverage_report and coverage_report.clusters:
            for cluster in coverage_report.clusters:
                if cluster.passages:
                    c_sentences = self._extract_coherent_sentences(cluster.passages, max_sentences=3)
                    if c_sentences:
                        sec_parts = []
                        cited_indices = []
                        for item in c_sentences:
                            p = item["passage"]
                            c_idx = passage_citation_map.get(p.passage_id or p.text[:40], 1)
                            cited_indices.append(c_idx)
                            s = item["sentence"].rstrip(".")
                            sec_parts.append(f"{s}. [{c_idx}]")
                        sec_content = " ".join(sec_parts)
                    else:
                        first_p = cluster.passages[0]
                        c_idx = passage_citation_map.get(first_p.passage_id or first_p.text[:40], 1)
                        sec_content = f"{first_p.text[:300].rstrip('.')} [{c_idx}]"
                        cited_indices = [c_idx]

                    structured_sections.append({
                        "facet_id": cluster.facet_id,
                        "title": cluster.title,
                        "content": sec_content,
                        "citations": sorted(list(set(cited_indices))),
                        "status": cluster.status,
                    })
                else:
                    structured_sections.append({
                        "facet_id": cluster.facet_id,
                        "title": cluster.title,
                        "content": f"No direct corroborating passages retrieved in live search for {cluster.title}.",
                        "citations": [],
                        "status": "uncovered",
                    })

        # 3. Extract Key Findings (Bulleted takeaways with citations)
        key_findings: List[str] = []
        seen_domains_for_findings = set()
        seen_finding_texts = set()

        for p in passages:
            if len(key_findings) >= 5:
                break
            cite_idx = passage_citation_map.get(p.passage_id or p.text[:40], 1)
            sentences = [self._clean_sentence(s) for s in re.split(r"(?<=[.!?])\s+", p.text) if self._clean_sentence(s)]
            for s in sentences:
                clean_s = s.strip()
                if not clean_s.endswith("."):
                    clean_s += "."
                fingerprint = clean_s[:50].lower()
                if fingerprint in seen_finding_texts:
                    continue
                # For rich passage sets (>2), avoid repeating exact direct answer verbatim
                if len(passages) > 2 and clean_s.lower() in direct_answer.lower():
                    continue
                finding = f"{clean_s} [{cite_idx}]"
                key_findings.append(finding)
                seen_finding_texts.add(fingerprint)
                seen_domains_for_findings.add(p.source_domain)
                break

        # Fallback if key findings were empty
        if not key_findings and passages:
            for p in passages[:3]:
                cite_idx = passage_citation_map.get(p.passage_id or p.text[:40], 1)
                snippet = " ".join(p.text.split()[:30])
                if not snippet.endswith("."):
                    snippet += "..."
                key_findings.append(f"{snippet} [{cite_idx}]")

        # 4. Transparent Caveats
        caveats = [
            "Information is synthesized probabilistically from live public web pages; accuracy reflects source reporting at the time of retrieval.",
            "For mission-critical, legal, or health decisions, verify directly with primary documentation and original publications.",
        ]
        if query_analysis.is_time_sensitive:
            caveats.insert(0, "Time-sensitive query: developments may be actively evolving past the indexed publication dates.")

        contradictions = verification_summary.get("contradictions", [])
        corroborated_claims = verification_summary.get("corroborated_claims", [])
        follow_up_questions = getattr(query_analysis, "follow_up_questions", [])

        # 5. Assemble Complete Markdown Output
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
            md_lines.append(f"> **Coverage Telemetry:** {coverage_report.covered_facets} of {coverage_report.total_facets} information requirements verified across {len(verification_summary.get('independent_domains', []))} independent domain(s).")
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
            confidence=confidence_report,
            contradictions=contradictions,
            corroborated_claims=corroborated_claims,
            caveats=caveats,
            citations=registry.all_citations(),
            markdown_output=markdown_output,
            generation_time=gen_time,
            follow_up_questions=follow_up_questions,
            structured_sections=structured_sections,
            coverage_report=coverage_report,
        )

