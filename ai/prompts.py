"""Prompt construction and system directives for grounded AI research synthesis."""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from evidence.models import EvidencePassage

if TYPE_CHECKING:
    from answer.citations import Citation


SYSTEM_SYNTHESIS_PROMPT = """You are an objective Web Research Intelligence Engine.
Use ONLY the verified web evidence supplied in the prompt.

CRITICAL RULES:
1. Every factual statement, statistic, date, or claim must be supported by the provided source IDs.
2. Never invent facts, sources, URLs, citations, or source IDs.
3. Use multiple independent sources when they contain useful evidence. Do not over-rely on one domain.
4. Do not repeat the same fact using different wording merely to make an answer longer.
5. Prefer information-dense details, examples, mechanisms, dates, metrics, context, limitations, and source-backed distinctions.
6. If sources disagree, preserve the disagreement and identify which sources support each view.
7. For simple queries, be concise but complete. For explanatory or complex queries, provide a genuinely detailed multi-paragraph synthesis.
8. If an EXACT WORD COUNT is supplied, treat it as a hard requirement for the final direct_answer. The final direct_answer must contain exactly that many prose words. Never pad with repetition or unsupported information. If necessary, select and combine only source-supported information to meet the target.
9. Numeric citation markers such as [1] must reference only supplied sources.
10. Return ONLY valid JSON matching the requested schema.

JSON SCHEMA:
{
  "direct_answer": "Detailed, factual, source-backed answer with inline [1] citations.",
  "key_findings": ["Distinct evidence-backed finding 1", "Distinct evidence-backed finding 2"],
  "claims": [{"text": "Specific factual proposition", "source_ids": [1, 2]}],
  "sections": [{"title": "Descriptive Section Heading", "content": "Detailed synthesis", "source_ids": [1, 3]}],
  "conflicts": [{"topic": "Disagreement", "view_a": "First view", "source_ids_a": [1], "view_b": "Second view", "source_ids_b": [2]}],
  "follow_up_questions": ["Relevant follow-up question"]
}
"""


def build_synthesis_prompt(
    query: str,
    sources: List[Citation],
    passages: List[EvidencePassage],
    analysis: Optional[Any] = None,
    history: Optional[List[Dict[str, str]]] = None,
    target_language: str = "en",
    requested_word_count: Optional[int] = None,
) -> str:
    """Build the synthesis prompt from the query and verified source evidence."""
    parts: List[str] = []

    lang_name = {"es": "Spanish", "fr": "French", "de": "German"}.get(target_language, "English")
    parts.append(f"TARGET ANSWER LANGUAGE: {lang_name}")

    if requested_word_count:
        parts.append(
            f"\nEXACT WORD COUNT: {requested_word_count} words for direct_answer. "
            "This is a hard requirement. Count prose words deterministically. "
            "Do not use repetition, filler, invented facts, or unsupported claims to reach the target."
        )

    if history:
        parts.append("\nPREVIOUS CONVERSATION CONTEXT:")
        for turn in history[-4:]:
            parts.append(f"{turn.get('role', 'user').capitalize()}: {turn.get('content', '')}")

    parts.append(f"\nCURRENT RESEARCH QUERY: \"{query}\"")
    parts.append("\nVERIFIED EVIDENCE FROM WEB SOURCES:")

    cit_map: Dict[str, Citation] = {c.url: c for c in sources}
    passages_by_source: Dict[int, List[EvidencePassage]] = {}
    for p in passages:
        cit = cit_map.get(p.source_url)
        if cit:
            passages_by_source.setdefault(cit.index, []).append(p)

    for cit in sources:
        idx = cit.index
        parts.append(f"\n--- [Source {idx}] ---")
        parts.append(f"Title: {cit.title}")
        parts.append(f"Domain: {cit.domain} ({cit.source_type})")
        if cit.published_date:
            parts.append(f"Published Date: {cit.published_date}")
        parts.append(f"URL: {cit.url}")
        source_passages = passages_by_source.get(idx, [])
        if source_passages:
            parts.append("Key Evidence Passages:")
            for sp in source_passages[:5]:
                header = f" [{sp.heading_context}]" if sp.heading_context else ""
                lang_tag = f" (Language: {sp.language})" if sp.language and sp.language != "en" else ""
                parts.append(f"  *{header}{lang_tag}: {sp.text.strip()}")
        elif cit.sample_quote:
            parts.append(f"  * Evidence Snippet: {cit.sample_quote.strip()}")
        else:
            parts.append("  * (Source retrieved without full body text)")

    parts.append("\nSynthesize a detailed, objective, fully cited research response using only this evidence.")
    return "\n".join(parts)
