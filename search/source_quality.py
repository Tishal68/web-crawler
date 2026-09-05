"""
Source Quality Engine: Classifies web domains and scores source quality
using explainable signals (authority, primary vs secondary, relevance, recency, independence).
"""

from enum import Enum
from typing import Dict, Any, Optional
import urllib.parse
from crawler.url_utils import get_domain


class SourceType(str, Enum):
    GOVERNMENT = "Official Government"
    ACADEMIC = "University / Academic"
    STANDARDS_ORG = "Standards Organization"
    SCIENTIFIC = "Scientific Publication"
    COMPANY_PRIMARY = "Company Primary Source"
    ESTABLISHED_JOURNALISM = "Established Journalism"
    SPECIALIST_PUBLICATION = "Specialist Publication"
    COMMUNITY_DISCUSSION = "Community Discussion"
    UNKNOWN = "General Web Source"


STANDARDS_DOMAINS = {
    "w3.org", "ietf.org", "iso.org", "nist.gov", "ansi.org",
    "ieee.org", "itu.int", "ecma-international.org", "unicode.org"
}

SCIENTIFIC_DOMAINS = {
    "arxiv.org", "nature.com", "science.org", "sciencedirect.com",
    "frontiersin.org", "springer.com", "pnas.org", "cell.com",
    "biorxiv.org", "medrxiv.org", "nih.gov", "ncbi.nlm.nih.gov"
}

JOURNALISM_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "bloomberg.com", "wsj.com", "ft.com", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "economist.com",
    "cnbc.com", "forbes.com"
}

SPECIALIST_DOMAINS = {
    "pcmag.com", "techradar.com", "rtings.com", "arstechnica.com",
    "wired.com", "theverge.com", "anandtech.com", "geeksforgeeks.org",
    "w3schools.com", "realpython.com", "stackoverflow.blog",
    "space.com", "scitechdaily.com", "investopedia.com"
}

COMMUNITY_DOMAINS = {
    "reddit.com", "news.ycombinator.com", "quora.com", "medium.com",
    "dev.to", "hashnode.dev", "sub量stack.com", "substack.com", "discourse.org"
}


def classify_source(url: str, title: str = "") -> SourceType:
    """Classify a webpage source into an explainable authority tier."""
    if not url:
        return SourceType.UNKNOWN

    dom = get_domain(url).lower()

    if dom.endswith(".gov") or ".gov." in dom or dom in ("who.int", "un.org", "wmo.int", "nasa.gov"):
        return SourceType.GOVERNMENT

    if dom.endswith(".edu") or ".edu." in dom or ".ac." in dom:
        return SourceType.ACADEMIC

    if any(dom == s or dom.endswith("." + s) for s in STANDARDS_DOMAINS):
        return SourceType.STANDARDS_ORG

    if any(dom == s or dom.endswith("." + s) for s in SCIENTIFIC_DOMAINS):
        return SourceType.SCIENTIFIC

    if any(dom == j or dom.endswith("." + j) for j in JOURNALISM_DOMAINS):
        return SourceType.ESTABLISHED_JOURNALISM

    if any(dom == s or dom.endswith("." + s) for s in SPECIALIST_DOMAINS):
        return SourceType.SPECIALIST_PUBLICATION

    if any(dom == c or dom.endswith("." + c) for c in COMMUNITY_DOMAINS):
        return SourceType.COMMUNITY_DISCUSSION

    # Primary documentation heuristic: docs.python.org, developer.mozilla.org, etc.
    if dom.startswith("docs.") or dom.startswith("developer.") or "/docs" in url:
        return SourceType.COMPANY_PRIMARY

    return SourceType.UNKNOWN


def get_source_type_badge(source_type: SourceType) -> str:
    """Return an explainable visual badge for source type."""
    badges = {
        SourceType.GOVERNMENT: "🏛️ Government (.gov)",
        SourceType.ACADEMIC: "🎓 Academic (.edu)",
        SourceType.STANDARDS_ORG: "📐 Standards Org",
        SourceType.SCIENTIFIC: "🔬 Scientific Journal",
        SourceType.COMPANY_PRIMARY: "🏢 Primary Source",
        SourceType.ESTABLISHED_JOURNALISM: "📰 Journalism",
        SourceType.SPECIALIST_PUBLICATION: "🔍 Specialist Media",
        SourceType.COMMUNITY_DISCUSSION: "💬 Community Forum",
        SourceType.UNKNOWN: "🌐 Web Source",
    }
    return badges.get(source_type, "🌐 Web Source")


def score_source_quality(
    url: str,
    title: str = "",
    snippet: str = "",
    published_date: Optional[str] = None,
    query: str = "",
) -> Dict[str, Any]:
    """
    Compute explainable source quality scores.
    Returns dictionary with authority_score, relevance_score, recency_score, and composite_score.
    """
    source_type = classify_source(url, title)

    # Authority baseline by tier (0.0 to 1.0)
    authority_weights = {
        SourceType.GOVERNMENT: 0.95,
        SourceType.STANDARDS_ORG: 0.92,
        SourceType.ACADEMIC: 0.90,
        SourceType.SCIENTIFIC: 0.88,
        SourceType.COMPANY_PRIMARY: 0.85,
        SourceType.ESTABLISHED_JOURNALISM: 0.82,
        SourceType.SPECIALIST_PUBLICATION: 0.78,
        SourceType.COMMUNITY_DISCUSSION: 0.55,
        SourceType.UNKNOWN: 0.60,
    }
    authority_score = authority_weights.get(source_type, 0.60)

    # Query term relevance in title & snippet
    relevance_score = 0.5
    if query:
        q_tokens = set(query.lower().split())
        t_tokens = set(title.lower().split())
        s_tokens = set(snippet.lower().split())
        title_matches = len(q_tokens.intersection(t_tokens))
        snippet_matches = len(q_tokens.intersection(s_tokens))
        relevance_score = min(1.0, 0.3 + (title_matches * 0.25) + (snippet_matches * 0.1))

    # Recency score
    recency_score = 0.6
    if published_date:
        if any(y in published_date for y in ("2026", "2025")):
            recency_score = 0.95
        elif "2024" in published_date:
            recency_score = 0.80
        elif "2023" in published_date:
            recency_score = 0.65
        else:
            recency_score = 0.50

    # Composite quality score (combining authority 40%, relevance 45%, recency 15%)
    composite = (authority_score * 0.40) + (relevance_score * 0.45) + (recency_score * 0.15)

    return {
        "source_type": source_type,
        "source_type_badge": get_source_type_badge(source_type),
        "authority_score": round(authority_score, 2),
        "relevance_score": round(relevance_score, 2),
        "recency_score": round(recency_score, 2),
        "composite_score": round(composite, 2),
    }
