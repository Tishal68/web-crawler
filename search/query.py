"""
Query understanding and intent analysis module.
Extracts keywords, entities, user intent, time sensitivity, and search variations.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class QueryAnalysis:
    """Structured understanding of user search intent and semantics."""
    original_query: str
    clean_query: str
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    intent: str = "exploratory"  # "factual", "exploratory", "comparison", "temporal_current"
    is_time_sensitive: bool = False
    is_comparison: bool = False
    target_year: Optional[int] = None
    search_variations: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "clean_query": self.clean_query,
            "keywords": self.keywords,
            "entities": self.entities,
            "intent": self.intent,
            "is_time_sensitive": self.is_time_sensitive,
            "is_comparison": self.is_comparison,
            "target_year": self.target_year,
            "search_variations": self.search_variations,
        }


class QueryAnalyzer:
    """Analyzes raw search queries to extract semantic intent, entities, and variations."""

    TEMPORAL_TRIGGERS: Set[str] = {
        "latest", "today", "current", "recent", "recently", "price", "prices",
        "ranking", "rankings", "schedule", "schedules", "winner", "winners",
        "2026", "2025", "2024", "this week", "this month", "new features",
        "updates", "news", "release", "released", "roadmap", "now"
    }

    STOPWORDS: Set[str] = {
        "a", "an", "the", "in", "on", "at", "for", "of", "with", "by", "to",
        "and", "or", "is", "are", "was", "were", "what", "which", "who", "whom",
        "how", "why", "where", "when", "can", "could", "should", "would", "do",
        "does", "did", "tell", "me", "about", "show", "find", "give"
    }

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze search query and return QueryAnalysis object."""
        clean = (query or "").strip()
        lower = clean.lower()

        # 1. Temporal Sensitivity
        is_time_sensitive = any(trigger in lower for trigger in self.TEMPORAL_TRIGGERS)
        year_match = re.search(r"\b(202[0-9]|19[0-9]{2})\b", clean)
        target_year = int(year_match.group(1)) if year_match else (2026 if "latest" in lower or "current" in lower else None)

        # 2. Comparison Check
        is_comparison = bool(
            re.search(r"\b(vs\.?|versus|compare|comparison|difference between)\b", lower)
            or (" or " in lower and len(clean.split()) <= 6)
        )

        # 3. Intent Classification
        if is_comparison:
            intent = "comparison"
        elif is_time_sensitive:
            intent = "temporal_current"
        elif any(lower.startswith(prefix) for prefix in ("who ", "when ", "where ", "what is ", "current price")):
            intent = "factual"
        else:
            intent = "exploratory"

        # 4. Keyword & Entity Extraction
        tokens = re.findall(r"\b[A-Za-z0-9+#.-]+\b", clean)
        keywords = [t.lower() for t in tokens if t.lower() not in self.STOPWORDS and len(t) > 1]

        # Entities: Title-cased tokens, acronyms (ALL_CAPS), technical terms
        entities = []
        for word in clean.split():
            clean_word = re.sub(r"[^\w+#.-]", "", word)
            if not clean_word:
                continue
            if clean_word.isupper() and len(clean_word) >= 2:
                entities.append(clean_word)
            elif clean_word[0].isupper() and clean_word.lower() not in self.STOPWORDS:
                entities.append(clean_word)

        # Deduplicate while preserving order
        unique_entities = []
        for e in entities:
            if e not in unique_entities:
                unique_entities.append(e)

        # 5. Search Variations Generation
        variations = [clean]
        if is_comparison:
            comp_match = re.search(r"(?:compare\s+)?([A-Za-z0-9_+#.-]+)\s+(?:vs\.?|versus|or)\s+([A-Za-z0-9_+#.-]+)", clean, re.IGNORECASE)
            if comp_match:
                item_a, item_b = comp_match.group(1), comp_match.group(2)
                variations.append(f"{item_a} vs {item_b} comparison differences")
                variations.append(f"{item_a} features overview")
                variations.append(f"{item_b} features overview")
        elif len(keywords) >= 4 and not clean.endswith("?"):
            # Sub-topic focused variation
            core_terms = " ".join(keywords[:4])
            if core_terms != clean.lower():
                variations.append(core_terms)

        return QueryAnalysis(
            original_query=query,
            clean_query=clean,
            keywords=keywords,
            entities=unique_entities,
            intent=intent,
            is_time_sensitive=is_time_sensitive,
            is_comparison=is_comparison,
            target_year=target_year,
            search_variations=variations,
        )
