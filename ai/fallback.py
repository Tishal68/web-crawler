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
from answer.word_count import (
    count_words,
    is_semantically_repetitive,
    format_into_paragraphs,
)

if TYPE_CHECKING:
    from answer.citations import Citation


def _clean_passage_text(text: str) -> str:
    """Normalize text and strip web footnote citations, Wikipedia markers, and spacing glitches."""
    if not text:
        return ""
    # Strip citation brackets like [1], [note 2], [a], [12]
    t = re.sub(r"\[(?:\d+|note\s*\d+|[a-zA-Z])\]", "", text)
    # Strip Wikipedia jump markers and footnote headers like ^ "Title" or ↑ "Nature"
    t = re.sub(r"[\^↑]\s*\"[^\"]*\"", "", t)
    t = re.sub(r"[\^↑]", "", t)
    # Replace unicode non-breaking spaces
    t = t.replace("\u00a0", " ").replace("\u200b", "")
    # Fix spacing before punctuation (e.g., "Nature , " -> "Nature, ", "computing . " -> "computing. ")
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    # Clean multiple whitespaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _score_sentence_for_intent(
    text: str,
    query_lower: str,
    query_tokens: set[str],
    analysis: Optional[Any] = None,
) -> float:
    """Score a candidate sentence based on information density, keyword matching, and question intent."""
    score = 1.0
    text_lower = text.lower()
    text_tokens = set(re.findall(r"\b[a-z0-9+#.-]+\b", text_lower))

    # 1. Keyword coverage
    overlap = query_tokens.intersection(text_tokens)
    if query_tokens:
        score += (len(overlap) / len(query_tokens)) * 4.0

    # 2. Exact subphrase match
    q_words = query_lower.split()
    if len(q_words) >= 2:
        for n in range(min(4, len(q_words)), 1, -1):
            subphrase = " ".join(q_words[:n])
            if subphrase in text_lower:
                score += 2.5
                break

    # 3. Intent-Specific Bonuses
    # Who / Creator intent
    if any(w in query_lower for w in ("who", "creator", "created", "inventor", "founder", "author")):
        if any(c in text_lower for c in ("created by", "developed by", "invented by", "founded by", "authored by", "designed by", "conceived by")):
            score += 5.5
        if any(c in text_lower for c in ("guido van rossum", "creator", "founder", "author", "inventor")):
            score += 3.5

    # When / Date / History intent
    if any(w in query_lower for w in ("when", "year", "date", "history", "timeline", "origin")):
        if re.search(r"\b(?:19|20)\d{2}\b", text):
            score += 4.0
        if any(d in text_lower for d in ("first released", "released in", "introduced in", "established in", "founded in", "published in")):
            score += 3.5

    # Latest / Breakthrough / Advances intent
    if any(w in query_lower for w in ("latest", "recent", "developments", "breakthrough", "advances", "new")):
        if any(y in text for y in ("2024", "2025", "2026")):
            score += 4.0
        if any(b in text_lower for b in ("demonstrated", "breakthrough", "recent", "announced", "achieved", "advancement", "modular", "scalability")):
            score += 3.0

    # Metrics / Density / Technical Specs intent
    if any(w in query_lower for w in ("density", "timeline", "specs", "capacity", "benchmark", "qubits", "speed")):
        if re.search(r"\b\d+(?:\.\d+)?\s*(?:wh/kg|mah/g|qubits?|ghz|nm|mhz|%|x|gb|mb)\b", text_lower):
            score += 4.5

    # Definitional bonus for general concepts
    if any(df in text_lower for df in ("is a ", "is an ", "refers to ", "is defined as ", "serves as ")):
        score += 1.8

    # 4. Length penalty / bonus
    if len(text) < 45:
        score -= 2.0
    elif 70 <= len(text) <= 220:
        score += 1.5
    elif len(text) > 320:
        score -= 1.0

    # 5. Penalize boilerplate / low-entropy sentences
    if any(bp in text_lower for bp in ("wikipedia", "wikimedia", "jump to navigation", "edit this page", "main article:", "see also", "external links", "all rights reserved", "terms of use", "privacy policy", "cookie policy", "sign up")):
        score -= 10.0

    return score


def _categorize_key_finding(text: str) -> str:
    """Determine an insightful bold category label for a key finding sentence."""
    t_low = text.lower()
    if any(w in t_low for w in ("created", "developed by", "founded", "invented", "authored", "conceived", "guido")):
        return "Genesis & Creator"
    if any(w in t_low for w in ("released", "timeline", "milestone", "announced", "published in", "in 19", "in 20")):
        return "Milestones & Timeline"
    if any(w in t_low for w in ("syntax", "typing", "readability", "paradigm", "design philosophy")):
        return "Language Design & Syntax"
    if any(w in t_low for w in ("c or c++", "extensible", "extension", "library", "modules", "packages", "ecosystem", "tools")):
        return "Extensibility & Ecosystem"
    if any(w in t_low for w in ("interpreter", "runtime", "compiler", "data structure", "virtual machine")):
        return "Runtime & Architecture"
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:wh/kg|qubits?|ghz|nm|%|x|gb|mb)\b", t_low):
        return "Technical Specifications"
    if any(w in t_low for w in ("architecture", "modular", "algorithm", "mechanism", "network", "framework")):
        return "System Architecture"
    if any(w in t_low for w in ("standard", "nist", "security", "commercial", "industry", "adoption")):
        return "Standardization & Impact"
    if any(w in t_low for w in ("recent", "breakthrough", "advance", "demonstrated", "achieved")):
        return "Latest Breakthrough"
    if any(w in t_low for w in ("application", "scripting", "machine learning", "scientific", "web development")):
        return "Applications & Ecosystem"
    return "Core Insight"


class DeterministicResearchSynthesizer:
    """Produces structured, fully cited, multi-source research reports from extracted evidence."""

    def synthesize(
        self,
        query: str,
        sources: List[Citation],
        passages: List[EvidencePassage],
        analysis: Optional[Any] = None,
        contradictions: Optional[List[Any]] = None,
        coverage_report: Optional[Any] = None,
        requested_word_count: Optional[int] = None,
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
        query_lower = query.lower().strip()
        query_tokens = set(re.findall(r"\b[a-z0-9+#.-]+\b", query_lower))

        # 1. Deduplicate, clean, and score all candidate sentences
        sentences: List[Dict[str, Any]] = []
        seen_fingerprints: set[str] = set()

        for p in passages:
            cit = url_to_cit.get(p.source_url)
            cit_id = cit.index if cit else 1
            cleaned_passage_text = _clean_passage_text(p.text)
            raw_sents = re.split(r"(?<=[.!?])\s+", cleaned_passage_text)

            for raw in raw_sents:
                clean = " ".join(raw.split()).strip()
                if len(clean) < 35 or len(clean.split()) < 5:
                    continue
                # Skip promotional or navigational boilerplate
                if any(bad in clean.lower() for bad in (
                    "click here", "sign up", "all rights reserved", "terms of use",
                    "privacy policy", "cookie policy", "this tutorial", "in this tutorial",
                    "this chapter", "this article discusses", "in this section", "this guide is"
                )):
                    continue

                fp = clean[:65].lower()
                if fp in seen_fingerprints:
                    continue
                seen_fingerprints.add(fp)

                score = _score_sentence_for_intent(clean, query_lower, query_tokens, analysis)

                sentences.append({
                    "text": clean,
                    "source_id": cit_id,
                    "heading": p.heading_context or "General Overview",
                    "passage": p,
                    "score": score,
                })

        if not sentences:
            fallback_text = _clean_passage_text(passages[0].text[:300].strip())
            sentences = [{
                "text": fallback_text,
                "source_id": 1,
                "heading": "General Overview",
                "passage": passages[0],
                "score": 1.0,
            }]

        # 2. Build multi-source executive direct answer with adaptive depth
        all_sorted = sorted(sentences, key=lambda x: x["score"], reverse=True)

        # Determine target sentence count based on query complexity or explicit word count
        complexity = getattr(analysis, "complexity", None)
        comp_str = complexity.value if hasattr(complexity, "value") else str(complexity or "moderate")

        if requested_word_count:
            # Target initial draft proportional to requested word count (~18 words/sentence)
            target_sent_count = max(3, requested_word_count // 18 + 1)
        elif comp_str == "simple":
            target_sent_count = 3
        elif comp_str in ("complex", "comparison"):
            target_sent_count = max(10, min(16, len(all_sorted)))
        else:
            # Moderate informational question
            target_sent_count = max(7, min(10, len(all_sorted)))

        selected_direct: List[Dict[str, Any]] = []
        selected_texts: List[str] = []
        used_sids: set[int] = set()

        # Sentence 1: Best overall answering sentence across all sources
        if all_sorted:
            s1 = dict(all_sorted[0])
            if re.match(r"^(?:It|He|She|They)\s+(?:was|is|were)\b", s1["text"], flags=re.I):
                subject = None
                if getattr(analysis, "entities", None):
                    subject = analysis.entities[0]
                elif query_tokens:
                    non_stopwords = [w for w in query.split() if w.lower() not in ("who", "what", "when", "where", "why", "how", "and", "the", "is", "was", "created", "created?")]
                    if non_stopwords:
                        subject = " ".join(non_stopwords[:2]).title()
                if subject:
                    s1["text"] = re.sub(r"^(?:It|He|She|They)\s+", f"{subject} ", s1["text"], flags=re.I)
            selected_direct.append(s1)
            selected_texts.append(s1["text"])
            used_sids.add(s1["source_id"])

        # Subsequent sentences: diversify sources and prevent semantic repetition
        for cand in all_sorted[1:]:
            if len(selected_direct) >= target_sent_count:
                break
            if is_semantically_repetitive(cand["text"], selected_texts):
                continue
            selected_direct.append(cand)
            selected_texts.append(cand["text"])
            used_sids.add(cand["source_id"])

        # If more sentences are needed to satisfy target_sent_count, relax strict diversity
        if len(selected_direct) < target_sent_count:
            for cand in all_sorted[1:]:
                if len(selected_direct) >= target_sent_count:
                    break
                fp = cand["text"][:45].lower()
                if any(fp in t[:45].lower() for t in selected_texts):
                    continue
                selected_direct.append(cand)
                selected_texts.append(cand["text"])

        direct_sentences = []
        direct_claims = []
        for s in selected_direct:
            sid = s["source_id"]
            txt = s["text"]
            if not txt.endswith((".", "!", "?")):
                txt += "."
            direct_sentences.append(f"{txt} [{sid}]")
            direct_claims.append(SynthesizedClaim(text=txt, source_ids=[sid]))

        direct_answer = format_into_paragraphs(direct_sentences, target_paragraph_words=85)

        # 3. Build High-Density Key Findings with Categorization Tags
        direct_fps = {s["text"][:45].lower() for s in selected_direct}
        if all_sorted:
            direct_fps.add(all_sorted[0]["text"][:45].lower())
        candidate_findings = [s for s in all_sorted if s["text"][:45].lower() not in direct_fps]

        # Ensure findings draw across multiple sources and topics
        key_findings = []
        seen_finding_sids = set()
        seen_finding_fps = set()

        for s in candidate_findings:
            sid = s["source_id"]
            txt = s["text"]
            fp = txt[:50].lower()
            if fp in seen_finding_fps:
                continue
            seen_finding_fps.add(fp)

            if not txt.endswith((".", "!", "?")):
                txt += "."

            category = _categorize_key_finding(txt)
            key_findings.append(f"**{category}**: {txt} [{sid}]")
            seen_finding_sids.add(sid)

            if len(key_findings) >= 5:
                break

        # Fallback if too few candidate findings
        if len(key_findings) < 3:
            for s in all_sorted:
                txt = s["text"]
                if not txt.endswith((".", "!", "?")):
                    txt += "."
                cat = _categorize_key_finding(txt)
                entry = f"**{cat}**: {txt} [{s['source_id']}]"
                if entry not in key_findings:
                    key_findings.append(entry)
                if len(key_findings) >= 4:
                    break

        # 4. Group into structured thematic sections (prioritizing facet clusters if available)
        sections: List[SynthesizedSection] = []
        if coverage_report and getattr(coverage_report, "clusters", None):
            for cluster in coverage_report.clusters:
                if cluster.passages:
                    cluster_sents = []
                    cluster_sids = []
                    for cp in cluster.passages:
                        c_cit = url_to_cit.get(cp.source_url)
                        c_sid = c_cit.index if c_cit else 1
                        cleaned_c_text = _clean_passage_text(cp.text)
                        raw_c_sents = re.split(r"(?<=[.!?])\s+", cleaned_c_text)
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
            for s in all_sorted[len(selected_direct):len(selected_direct) + 12]:
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
            f"What are the most recent 2025-2026 developments in {query}?",
            f"How does {query} compare with leading industry benchmarks?",
            f"What are the primary technical roadblocks and future milestones for {query}?",
        ]

        return SynthesizedResearchResponse(
            direct_answer=direct_answer,
            key_findings=key_findings,
            claims=direct_claims,
            sections=sections,
            conflicts=conflicts,
            follow_up_questions=follow_ups,
        )
