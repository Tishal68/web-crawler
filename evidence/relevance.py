"""
Passage relevance scoring and ranking module.
Identifies and ranks the passages that most directly answer the user's query.
"""

import re
from typing import List, Set, Optional
from .models import EvidencePassage
from search.query import QueryAnalysis


def score_passage_relevance(passage: EvidencePassage, query_analysis: QueryAnalysis) -> float:
    """
    Score how directly a text passage answers the query.
    Returns float score between 0.0 and 1.0.
    """
    if not passage.text:
        return 0.0

    text_lower = passage.text.lower()
    words = text_lower.split()
    word_count = len(words)

    if word_count < 6:
        return 0.05

    score = 0.15

    # 1. Keyword coverage
    if query_analysis.keywords:
        text_words_set = set(re.findall(r"\b[a-z0-9+#.-]+\b", text_lower))
        matched_keywords = [k for k in query_analysis.keywords if k in text_words_set]
        coverage_ratio = len(matched_keywords) / len(query_analysis.keywords)
        score += (coverage_ratio * 0.40)

    # 2. Exact phrase match bonus
    clean_q = query_analysis.clean_query.lower()
    if clean_q in text_lower:
        score += 0.25
    else:
        # Check sub-phrases of 3+ words
        q_tokens = query_analysis.clean_query.lower().split()
        if len(q_tokens) >= 3:
            subphrase = " ".join(q_tokens[:3])
            if subphrase in text_lower:
                score += 0.15

    # 3. Heading context alignment
    if passage.heading_context:
        heading_lower = passage.heading_context.lower()
        if any(k in heading_lower for k in query_analysis.keywords):
            score += 0.15

    # 4. Entity presence bonus
    for entity in query_analysis.entities:
        if entity.lower() in text_lower:
            score += 0.10

    # 5. Intent-specific signals
    if query_analysis.is_time_sensitive:
        if query_analysis.target_year and str(query_analysis.target_year) in text_lower:
            score += 0.15
        elif any(t in text_lower for t in ("2026", "2025", "2024", "recent", "announced", "released")):
            score += 0.10

    if query_analysis.is_comparison:
        if any(w in text_lower for w in ("difference", "compared to", "versus", "whereas", "while", "unlike")):
            score += 0.15

    if query_analysis.intent == "factual":
        # Check for numeric or date answers
        if re.search(r"\b\d+(\.\d+)?(\s?%|\s?qubit|\s?billion|\s?million|\s?usd|\$)?\b", text_lower):
            score += 0.10

    # 6. Length penalty (overly verbose passages lose slight focus)
    if word_count > 300:
        score *= 0.85

    return min(1.0, round(score, 3))


def rank_and_filter_passages(
    passages: List[EvidencePassage],
    query_analysis: QueryAnalysis,
    max_passages: int = 15,
    min_score: float = 0.20,
) -> List[EvidencePassage]:
    """
    Score, filter, and rank candidate evidence passages.
    Ensures domain diversity across top passages.
    """
    if not passages:
        return []

    scored_passages = []
    for p in passages:
        p.relevance_score = score_passage_relevance(p, query_analysis)
        if p.relevance_score >= min_score:
            scored_passages.append(p)

    # Sort descending by relevance score
    scored_passages.sort(key=lambda x: x.relevance_score, reverse=True)

    # Deduplicate closely matching sentences
    unique_passages: List[EvidencePassage] = []
    seen_prefixes = set()

    for p in scored_passages:
        prefix = p.text[:80].lower()
        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)
        unique_passages.append(p)
        if len(unique_passages) >= max_passages:
            break

    return unique_passages
