"""
Prompt construction and system directives for grounded AI research synthesis.
Enforces strict citation constraints, structured JSON contracts, and multilingual synthesis.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from evidence.models import EvidencePassage

if TYPE_CHECKING:
    from answer.citations import Citation


SYSTEM_SYNTHESIS_PROMPT = """You are an elite, objective Web Research Intelligence Engine.
Your mission is to perform comprehensive, factually grounded information synthesis using ONLY the provided verified web sources.

CRITICAL OPERATIONAL RULES:
1. STRICT CITATION GROUNDING:
   - Every factual statement, statistic, date, or claim MUST be tied to the source IDs that directly support it.
   - You MUST ONLY use the integer source IDs provided in the [Source X] headers (e.g. 1, 2, 3).
   - DO NOT invent, hallucinate, or assume any source IDs that were not explicitly listed.
   - If a claim cannot be verified from the provided sources, DO NOT present it as established fact.

2. ADAPTIVE RESEARCH DEPTH:
   - For simple queries: Provide a concise, highly informative, direct answer (1-2 paragraphs) with citations.
   - For complex or explanatory queries: Provide a thorough, multi-paragraph synthesis divided into logical thematic sections (e.g., Overview, Architecture & Mechanics, Key Capabilities, Discoveries / Applications).
   - For comparison queries: Provide a structured side-by-side comparison across technical dimensions, tradeoffs, and recommendations.

3. CONTRADICTIONS & DISAGREEMENTS:
   - If sources disagree on dates, metrics, launch windows, versions, or conclusions, DO NOT arbitrarily pick one.
   - Explicitly document the disagreement in the "conflicts" array, identifying which sources support which view.

4. MULTILINGUAL SOURCES:
   - Sources may be in multiple languages (English, Spanish, French, German, etc.).
   - Read and extract information across all languages, but write your entire final synthesis in the requested TARGET LANGUAGE.

5. OUTPUT FORMAT:
   You MUST return ONLY a valid, parseable JSON object matching this exact schema:
{
  "direct_answer": "Clear, comprehensive introductory answer synthesizing the core findings with inline [1] style citations where appropriate.",
  "key_findings": [
    "Key finding or milestone 1 with specific facts and metric details.",
    "Key finding or milestone 2 with specific facts and metric details."
  ],
  "claims": [
    {
      "text": "Specific factual proposition.",
      "source_ids": [1, 2]
    }
  ],
  "sections": [
    {
      "title": "Descriptive Section Heading",
      "content": "Detailed paragraphs of synthesis explaining this facet of the topic thoroughly.",
      "source_ids": [1, 3]
    }
  ],
  "conflicts": [
    {
      "topic": "Topic of disagreement (e.g. Launch Date)",
      "view_a": "First reported version/metric",
      "source_ids_a": [1],
      "view_b": "Second conflicting version/metric",
      "source_ids_b": [2]
    }
  ],
  "follow_up_questions": [
    "Intelligent, relevant follow-up research question 1?",
    "Intelligent, relevant follow-up research question 2?"
  ]
}
"""


def build_synthesis_prompt(
    query: str,
    sources: List[Citation],
    passages: List[EvidencePassage],
    analysis: Optional[Any] = None,
    history: Optional[List[Dict[str, str]]] = None,
    target_language: str = "en",
) -> str:
    """
    Build the user prompt combining conversation history, user query, and retrieved source evidence.
    """
    parts: List[str] = []

    # 1. Target language instruction
    lang_name = "English"
    if target_language == "es":
        lang_name = "Spanish"
    elif target_language == "fr":
        lang_name = "French"
    elif target_language == "de":
        lang_name = "German"

    parts.append(f"TARGET ANSWER LANGUAGE: {lang_name}")

    # 2. Conversational Context if present
    if history and len(history) > 0:
        parts.append("\nPREVIOUS CONVERSATION CONTEXT:")
        for turn in history[-4:]:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "")
            parts.append(f"{role}: {content}")

    # 3. User Query
    parts.append(f"\nCURRENT RESEARCH QUERY: \"{query}\"")

    # 4. Registered Sources & Evidence Passages
    parts.append("\nVERIFIED EVIDENCE FROM WEB SOURCES:")

    # Group passages by source URL / citation index
    cit_map: Dict[str, Citation] = {c.url: c for c in sources}
    passages_by_source: Dict[int, List[EvidencePassage]] = {}

    for p in passages:
        cit = cit_map.get(p.source_url)
        if cit:
            idx = cit.index
            passages_by_source.setdefault(idx, []).append(p)

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

    parts.append("\nSynthesize a thorough, objective, fully cited research response following the required JSON schema.")
    return "\n".join(parts)
