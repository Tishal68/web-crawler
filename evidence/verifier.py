"""
Cross-source verification and corroboration engine.
Checks agreement across independent root domains and analyzes source diversity.
"""

from typing import List, Dict, Set, Any
from .models import EvidencePassage, FactClaim, ContradictionAlert, ExtractedPageEvidence
from .contradiction import ContradictionDetector
from search.query import QueryAnalysis
import re


class EvidenceVerifier:
    """Verifies factual corroboration and detects conflicts across independent sources."""

    def __init__(self):
        self.contradiction_detector = ContradictionDetector()

    def verify(
        self,
        extracted_evidence: List[ExtractedPageEvidence],
        top_passages: List[EvidencePassage],
        query_analysis: QueryAnalysis,
    ) -> Dict[str, Any]:
        """
        Cross-check claims and extract corroboration metrics across independent domains.
        """
        # 1. Independent domains
        independent_domains = sorted(list({
            p.source_domain for p in top_passages if p.source_domain
        }))

        # 2. Source authority distribution
        authority_distribution: Dict[str, int] = {}
        for ev in extracted_evidence:
            st = ev.source_type
            authority_distribution[st] = authority_distribution.get(st, 0) + 1

        # 3. Detect Contradictions
        contradictions = self.contradiction_detector.detect_contradictions(top_passages)

        # 4. Extract Corroborated Claims
        # Find key phrases / propositions that appear in 2+ independent domains
        corroborated_claims: List[FactClaim] = []
        domain_passage_map: Dict[str, List[EvidencePassage]] = {}
        for p in top_passages:
            domain_passage_map.setdefault(p.source_domain, []).append(p)

        # Look for multi-token entities / n-grams mentioned across multiple domains
        candidate_entities = query_analysis.entities + query_analysis.keywords
        for kw in candidate_entities:
            if len(kw) < 4:
                continue
            matching_domains: List[str] = []
            matching_urls: List[str] = []
            sample_sentence = ""

            for dom, p_list in domain_passage_map.items():
                for p in p_list:
                    if re.search(rf"\b{re.escape(kw)}\b", p.text, re.IGNORECASE):
                        if dom not in matching_domains:
                            matching_domains.append(dom)
                        if p.source_url not in matching_urls:
                            matching_urls.append(p.source_url)
                        if not sample_sentence:
                            # Extract single sentence containing the keyword
                            sentences = re.split(r"(?<=[.!?])\s+", p.text)
                            for s in sentences:
                                if re.search(rf"\b{re.escape(kw)}\b", s, re.IGNORECASE):
                                    sample_sentence = s.strip()
                                    break

            if len(matching_domains) >= 2 and sample_sentence:
                corroborated_claims.append(FactClaim(
                    statement=sample_sentence,
                    primary_source_url=matching_urls[0],
                    corroborating_domains=matching_domains,
                    corroborating_urls=matching_urls,
                    confidence=min(0.92, 0.5 + 0.15 * len(matching_domains)),
                ))

        return {
            "independent_domains": independent_domains,
            "domain_count": len(independent_domains),
            "authority_distribution": authority_distribution,
            "corroborated_claims": corroborated_claims[:5],  # top 5 key verified claims
            "contradictions": contradictions,
            "has_contradictions": len(contradictions) > 0,
        }
