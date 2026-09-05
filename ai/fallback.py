"""
Deterministic Deep Research Synthesizer.
Used as an instant fallback when no external LLM API key is configured
or when external API calls time out or fail.
Synthesizes structured multi-paragraph research answers with verified citation mappings.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from .schemas import (
    SynthesizedResearchResponse,
    SynthesizedClaim,
    SynthesizedSection,
    SynthesizedConflict,
)
from evidence.models import EvidencePassage

if TYPE_CHECKING:
    from answer.citations import Citation


class DeterministicResearchSynthesizer:
    """Produces structured, fully cited research reports from extracted evidence without requiring an LLM API key."""

    def synthesize(
        self,
        query: str,
        sources: List[Citation],
        passages: List[EvidencePassage],
        analysis: Optional[Any] = None,
        contradictions: Optional[List[Any]] = None,
        coverage_report: Optional[Any] = None,
    ) -> SynthesizedResearchResponse:
        """Synthesize a structured research response from passages and citations."""
        if not passages:
            return SynthesizedResearchResponse(
                direct_answer=f"No substantive web evidence could be retrieved for '{query}'. Please verify internet connectivity or try refining your search keywords.",
                key_findings=[],
                claims=[],
                sections=[],
                conflicts=[],
                follow_up_questions=[f"What are key sources for {query}?", f"Overview of {query}"],
            )

        url_to_cit: Dict[str, Citation] = {c.url: c for c in sources}

        # 1. Deduplicate and collect top informative sentences
        sentences: List[Dict[str, Any]] = []
        seen = set()

        for p in passages:
            cit = url_to_cit.get(p.source_url)
            cit_id = cit.index if cit else 1
            raw_sents = re.split(r"(?<=[.!?])\s+", p.text)
            for raw in raw_sents:
                clean = " ".join(raw.split()).strip()
                if len(clean) < 35 or len(clean.split()) < 6:
                    continue
                # Skip promotional boilerplate
                if any(bad in clean.lower() for bad in ("click here", "sign up", "all rights reserved", "terms of use", "privacy policy")):
                    continue
                fp = clean[:70].lower()
                if fp in seen:
                    continue
                seen.add(fp)
                sentences.append({
                    "text": clean,
                    "source_id": cit_id,
                    "heading": p.heading_context or "General Overview",
                    "passage": p,
                })

        if not sentences:
            sentences = [{
                "text": passages[0].text[:300].strip(),
                "source_id": 1,
                "heading": "General Overview",
                "passage": passages[0],
            }]

        # 2. Build direct answer with citations
        top_sents = sentences[:3]
        direct_parts = []
        direct_claims = []
        for s in top_sents:
            sid = s["source_id"]
            txt = s["text"]
            if not txt.endswith((".", "!", "?")):
                txt += "."
            direct_parts.append(f"{txt} [{sid}]")
            direct_claims.append(SynthesizedClaim(text=txt, source_ids=[sid]))

        direct_answer = " ".join(direct_parts)

        # 3. Build Key Findings with Citations
        key_findings = []
        for s in sentences[:5]:
            t = s["text"]
            if not t.endswith((".", "!", "?")):
                t += "."
            sid = s["source_id"]
            key_findings.append(f"{t} [{sid}]")

        # 4. Group into structured thematic sections (prioritize facet clusters if available)
        sections: List[SynthesizedSection] = []
        if coverage_report and getattr(coverage_report, "clusters", None):
            for cluster in coverage_report.clusters:
                if cluster.passages:
                    cluster_sents = []
                    cluster_sids = []
                    for cp in cluster.passages:
                        c_cit = url_to_cit.get(cp.source_url)
                        c_sid = c_cit.index if c_cit else 1
                        raw_c_sents = re.split(r"(?<=[.!?])\s+", cp.text)
                        for rcs in raw_c_sents:
                            c_clean = " ".join(rcs.split()).strip()
                            if len(c_clean) >= 30 and len(c_clean.split()) >= 5:
                                if not c_clean.endswith((".", "!", "?")):
                                    c_clean += "."
                                cluster_sents.append(f"{c_clean} [{c_sid}]")
                                cluster_sids.append(c_sid)
                                if len(cluster_sents) >= 3:
                                    break
                        if len(cluster_sents) >= 3:
                            break
                    if cluster_sents:
                        sections.append(SynthesizedSection(
                            title=cluster.title,
                            content=" ".join(cluster_sents),
                            source_ids=list(dict.fromkeys(cluster_sids)),
                        ))

        if not sections:
            sections_by_heading: Dict[str, List[Dict[str, Any]]] = {}
            for s in sentences[1:14]:
                h = s["heading"]
                if h in ("Search Snippet", "General Overview", ""):
                    h = "Core Findings & Technical Details"
                sections_by_heading.setdefault(h, []).append(s)

            for heading, sents in sections_by_heading.items():
                sec_sids = list(dict.fromkeys(s["source_id"] for s in sents))
                sec_body = " ".join(
                    f"{s['text']} [{s['source_id']}]" if s['text'].endswith(('.', '!', '?')) else f"{s['text']}. [{s['source_id']}]"
                    for s in sents
                )
                sections.append(SynthesizedSection(
                    title=heading,
                    content=sec_body,
                    source_ids=sec_sids,
                ))

        # 5. Extract conflicts from contradiction alerts if provided
        conflicts: List[SynthesizedConflict] = []
        if contradictions:
            for c in contradictions:
                topic = getattr(c, "topic", "Information Discrepancy")
                va = getattr(c, "statement_a", "")
                vb = getattr(c, "statement_b", "")
                conflicts.append(SynthesizedConflict(
                    topic=topic,
                    view_a=va,
                    source_ids_a=[1],
                    view_b=vb,
                    source_ids_b=[2] if len(sources) > 1 else [1],
                ))

        # 6. Generate intelligent follow-up questions
        follow_ups = [
            f"What are the most recent updates on {query}?",
            f"How does {query} compare with leading alternatives?",
            f"What are the main technical challenges or limitations of {query}?",
        ]

        return SynthesizedResearchResponse(
            direct_answer=direct_answer,
            key_findings=key_findings,
            claims=direct_claims,
            sections=sections,
            conflicts=conflicts,
            follow_up_questions=follow_ups,
        )
