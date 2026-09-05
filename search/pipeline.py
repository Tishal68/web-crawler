"""
Search Pipeline Module.
Orchestrates end-to-end Web Search, Source Discovery, Evidence Extraction,
Cross-Source Verification, Contradiction Detection, and Grounded Answer Generation.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from .provider import SearchProvider, SearchResult, SearchResultSet
from .google_provider import GoogleSearchProvider
from .multi_provider import MultiEngineSearchProvider
from .query import QueryAnalyzer, QueryAnalysis
from .ranking import rank_search_results
from .cache import SearchCache
from evidence.extractor import EvidenceExtractor
from evidence.models import ExtractedPageEvidence, EvidencePassage, ConfidenceReport
from evidence.relevance import rank_and_filter_passages
from evidence.verifier import EvidenceVerifier
from evidence.confidence import calculate_confidence
from evidence.coverage import cluster_evidence_by_facets, EvidenceCoverageReport
from answer.generator import GroundedAnswer, AnswerGenerator
from crawler.database import CrawlDatabase


@dataclass
class SearchPipelineResult:
    """Complete result bundle produced by the search pipeline."""
    query: str
    query_analysis: QueryAnalysis
    provider_used: str
    ranked_results: List[SearchResult] = field(default_factory=list)
    extracted_evidence: List[ExtractedPageEvidence] = field(default_factory=list)
    top_passages: List[EvidencePassage] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[ConfidenceReport] = None
    coverage: Optional[EvidenceCoverageReport] = None
    answer: Optional[GroundedAnswer] = None
    total_elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "query_analysis": self.query_analysis.to_dict(),
            "provider_used": self.provider_used,
            "ranked_results": [r.to_dict() for r in self.ranked_results],
            "extracted_evidence": [e.to_dict() for e in self.extracted_evidence],
            "top_passages": [p.to_dict() for p in self.top_passages],
            "confidence": self.confidence.to_dict() if self.confidence else None,
            "coverage": self.coverage.to_dict() if self.coverage else None,
            "answer": self.answer.to_dict() if self.answer else None,
            "total_elapsed": round(self.total_elapsed, 3),
        }



class SearchPipeline:
    """Unified coordinator for web search, extraction, verification, and answer grounding."""

    def __init__(
        self,
        cache: Optional[SearchCache] = None,
        db: Optional[CrawlDatabase] = None,
        timeout: float = 6.0,
    ):
        self.cache = cache or SearchCache(default_ttl_seconds=1800)
        self.db = db
        self.timeout = timeout

        self.query_analyzer = QueryAnalyzer()
        self.google_provider = GoogleSearchProvider()
        self.multi_provider = MultiEngineSearchProvider()
        self.evidence_extractor = EvidenceExtractor(timeout=self.timeout)
        self.verifier = EvidenceVerifier()
        self.answer_generator = AnswerGenerator()

    def get_preferred_provider(self, requested: str = "auto") -> SearchProvider:
        """Select appropriate provider based on user request or availability."""
        req = requested.lower().strip()
        if req == "google":
            if self.google_provider.is_available():
                return self.google_provider
            return self.multi_provider
        elif req == "multi" or req == "bing":
            return self.multi_provider

        # Auto-selection: use Google if configured, else MultiEngine fallback
        if self.google_provider.is_available():
            return self.google_provider
        return self.multi_provider

    def run(
        self,
        query: str,
        num_sources: int = 8,
        provider_preference: str = "auto",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> SearchPipelineResult:
        """Execute end-to-end search pipeline."""
        start_time = time.time()

        def _update(status: str, pct: float):
            if progress_callback:
                try:
                    progress_callback(status, pct)
                except Exception:
                    pass

        # 1. Query Understanding
        _update("Analyzing search query & intent...", 0.10)
        analysis = self.query_analyzer.analyze(query)

        # 2. Select and query search provider
        provider = self.get_preferred_provider(provider_preference)
        _update(f"Searching web via {provider.provider_name}...", 0.25)

        # Check Cache
        cached_set = self.cache.get(query, provider.provider_name, num_sources)
        if cached_set:
            result_set = cached_set
        else:
            # Fetch candidate results (extra buffer to allow ranking & diversity filtering)
            fetch_count = min(20, num_sources + 5)
            result_set = provider.search(query, num_results=fetch_count)

            # Multi-angle query discovery for complex multi-facet queries
            if getattr(analysis, "facets", None) and len(analysis.facets) > 1:
                seen_urls = {r.url for r in result_set.results}
                for facet in analysis.facets[:3]:
                    if facet.search_query and facet.search_query.strip().lower() != query.strip().lower():
                        try:
                            f_res = provider.search(facet.search_query, num_results=3)
                            for r in f_res.results:
                                if r.url not in seen_urls:
                                    seen_urls.add(r.url)
                                    result_set.results.append(r)
                        except Exception:
                            pass

            self.cache.set(query, provider.provider_name, result_set, num_results=num_sources)

        # 3. Multi-factor Result Ranking
        _update("Ranking sources by authority, relevance, and diversity...", 0.45)
        ranked = rank_search_results(
            results=result_set.results,
            query_analysis=analysis,
            max_results=num_sources,
            domain_diversity_limit=2,
        )

        # 4. Deep Page Fetching & Evidence Extraction
        _update("Fetching pages and extracting structured evidence...", 0.65)
        extracted_pages = self.evidence_extractor.extract_from_search_results(
            results=ranked,
            max_workers=min(4, max(1, len(ranked))),
        )


        # 5. Extract & Rank Structured Passages with Facet Clustering
        _update("Extracting relevant passages and mapping topic facets...", 0.75)
        all_passages: List[EvidencePassage] = []
        for page in extracted_pages:
            all_passages.extend(page.passages)

        top_passages = rank_and_filter_passages(
            passages=all_passages,
            query_analysis=analysis,
            max_passages=12,
        )

        # Cluster evidence across decomposed query facets
        coverage = cluster_evidence_by_facets(
            passages=all_passages if len(all_passages) < 60 else top_passages,
            facets=getattr(analysis, "facets", []),
        )

        # 6. Verification, Corroboration & Contradiction Detection
        _update("Cross-checking sources and verifying facts...", 0.85)
        verification = self.verifier.verify(
            extracted_evidence=extracted_pages,
            top_passages=top_passages,
            query_analysis=analysis,
        )

        # 7. Grounded Confidence Scoring (Never 100%)
        confidence = calculate_confidence(
            independent_domains=verification["independent_domains"],
            contradictions=verification["contradictions"],
            extracted_evidence=extracted_pages,
            is_time_sensitive=analysis.is_time_sensitive,
        )

        # 8. Synthesize Grounded Answer & Citations
        _update("Synthesizing grounded answer and verified citations...", 0.95)
        answer = self.answer_generator.generate_answer(
            query=query,
            query_analysis=analysis,
            passages=top_passages,
            verification_summary=verification,
            confidence_report=confidence,
            coverage_report=coverage,
        )

        total_elapsed = time.time() - start_time
        _update("Complete", 1.0)

        # Persist to database if available
        if self.db:
            try:
                self.db.save_search_history(
                    query=query,
                    provider_name=provider.provider_name,
                    results_count=len(ranked),
                    direct_answer=answer.direct_answer,
                    confidence_badge=confidence.badge_label,
                    confidence_score=confidence.score,
                    has_contradictions=confidence.has_contradictions,
                    citations=[c.to_dict() for c in answer.citations],
                    session_data={
                        "analysis": analysis.to_dict(),
                        "ranked_urls": [r.url for r in ranked],
                        "coverage": coverage.to_dict() if coverage else None,
                        "total_elapsed": round(total_elapsed, 3),
                    },
                )
            except Exception:
                pass

        return SearchPipelineResult(
            query=query,
            query_analysis=analysis,
            provider_used=provider.provider_name,
            ranked_results=ranked,
            extracted_evidence=extracted_pages,
            top_passages=top_passages,
            verification=verification,
            confidence=confidence,
            coverage=coverage,
            answer=answer,
            total_elapsed=total_elapsed,
        )

