"""
Evidence coverage and facet clustering module.
Maps retrieved evidence passages to decomposed query facets,
evaluates topic coverage across independent sources, and flags unverified requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re

from evidence.models import EvidencePassage
from search.query import QueryFacet


@dataclass
class FacetEvidenceCluster:
    """Group of evidence passages supporting a specific query facet."""
    facet_id: str
    title: str
    description: str
    passages: List[EvidencePassage] = field(default_factory=list)
    corroborating_domains: List[str] = field(default_factory=list)
    status: str = "uncovered"  # "fully_covered", "partially_covered", "uncovered"
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet_id": self.facet_id,
            "title": self.title,
            "description": self.description,
            "passages_count": len(self.passages),
            "corroborating_domains": self.corroborating_domains,
            "status": self.status,
            "confidence_score": round(self.confidence_score, 2),
            "top_quotes": [p.text[:140] for p in self.passages[:3]],
        }


@dataclass
class EvidenceCoverageReport:
    """Telemetry report of how well the retrieved evidence answers each facet of the query."""
    clusters: List[FacetEvidenceCluster] = field(default_factory=list)
    total_facets: int = 0
    covered_facets: int = 0
    coverage_ratio: float = 0.0
    unverified_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_facets": self.total_facets,
            "covered_facets": self.covered_facets,
            "coverage_ratio": round(self.coverage_ratio, 2),
            "clusters": [c.to_dict() for c in self.clusters],
            "unverified_requirements": self.unverified_requirements,
        }


def score_passage_for_facet(passage: EvidencePassage, facet: QueryFacet) -> float:
    """Calculate relevance score of a passage to a specific facet (0.0 to 1.0)."""
    text_lower = (passage.text + " " + (passage.heading_context or "")).lower()
    score = 0.0

    # 1. Facet keyword matches
    matched_keywords = 0
    for kw in facet.keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue
        if re.search(r"\b" + re.escape(kw_lower) + r"\b", text_lower):
            matched_keywords += 1
        elif len(kw_lower) >= 4:
            stem = kw_lower[:-3] if kw_lower.endswith("ies") else kw_lower.rstrip("sedy")
            if len(stem) >= 3 and stem in text_lower:
                matched_keywords += 1

    if facet.keywords:
        kw_ratio = matched_keywords / len(facet.keywords)
        score += kw_ratio * 0.60

    # 2. Facet title terms match
    title_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9]{3,}\b", facet.title)]
    matched_title = 0
    for tw in title_words:
        if re.search(r"\b" + re.escape(tw) + r"\b", text_lower):
            matched_title += 1
        elif len(tw) >= 4:
            stem = tw[:-3] if tw.endswith("ies") else tw.rstrip("sedy")
            if len(stem) >= 3 and stem in text_lower:
                matched_title += 1
    if title_words:
        score += (matched_title / len(title_words)) * 0.30

    # 3. Heading context bonus
    if passage.heading_context:
        hc_lower = passage.heading_context.lower()
        if any(re.search(r"\b" + re.escape(kw.lower()) + r"\b", hc_lower) for kw in facet.keywords):
            score += 0.15

    return min(1.0, score)



def cluster_evidence_by_facets(
    passages: List[EvidencePassage],
    facets: List[QueryFacet],
) -> EvidenceCoverageReport:
    """
    Group extracted evidence passages into facet clusters,
    evaluate independent corroboration per facet, and compute coverage telemetry.
    """
    if not facets:
        facets = [QueryFacet(facet_id="general", title="Overview", description="General topic overview", keywords=[])]

    clusters: List[FacetEvidenceCluster] = []
    cluster_map: Dict[str, FacetEvidenceCluster] = {}

    for f in facets:
        c = FacetEvidenceCluster(
            facet_id=f.facet_id,
            title=f.title,
            description=f.description,
            passages=[],
            corroborating_domains=[],
        )
        clusters.append(c)
        cluster_map[f.facet_id] = c

    # Cluster passages into matching facets
    for passage in passages:
        best_facet_id = None
        best_score = 0.0

        for f in facets:
            s = score_passage_for_facet(passage, f)
            if s > best_score:
                best_score = s
                best_facet_id = f.facet_id

            # If passage is exceptionally relevant to this facet, include it
            if s >= 0.35 and f.facet_id in cluster_map:
                if passage not in cluster_map[f.facet_id].passages:
                    cluster_map[f.facet_id].passages.append(passage)

        # Ensure passage is at least in its best matching cluster if score is acceptable
        if best_facet_id and best_score >= 0.12:
            if passage not in cluster_map[best_facet_id].passages:
                cluster_map[best_facet_id].passages.append(passage)
            passage.facet_id = best_facet_id
        elif clusters:
            # Assign to primary/first cluster as fallback
            if passage not in clusters[0].passages:
                clusters[0].passages.append(passage)
            passage.facet_id = clusters[0].facet_id

    # Compute status and corroborating domains for each cluster
    covered_count = 0
    unverified: List[str] = []

    for c in clusters:
        domains = list({p.source_domain for p in c.passages if p.source_domain})
        c.corroborating_domains = domains

        if len(domains) >= 2:
            c.status = "fully_covered"
            c.confidence_score = min(0.92, 0.55 + 0.15 * min(3, len(domains)) + 0.03 * min(5, len(c.passages)))
            covered_count += 1
        elif len(domains) == 1:
            c.status = "partially_covered"
            c.confidence_score = min(0.70, 0.40 + 0.05 * min(4, len(c.passages)))
            covered_count += 1
        else:
            c.status = "uncovered"
            c.confidence_score = 0.0
            unverified.append(f"{c.title}: {c.description}")

    total_f = len(clusters)
    ratio = (covered_count / total_f) if total_f > 0 else 1.0

    return EvidenceCoverageReport(
        clusters=clusters,
        total_facets=total_f,
        covered_facets=covered_count,
        coverage_ratio=ratio,
        unverified_requirements=unverified,
    )

