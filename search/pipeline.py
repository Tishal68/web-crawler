"""Search pipeline for web discovery, evidence extraction, verification, and grounded synthesis."""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from .provider import SearchProvider, SearchResult, SearchResultSet
from .google_provider import GoogleSearchProvider
from .multi_provider import MultiEngineSearchProvider
from .query import QueryAnalyzer, QueryAnalysis, QueryComplexity, rewrite_follow_up_query
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
from ai import BaseLLMProvider
from answer.word_count import extract_requested_word_count, remove_word_count_instruction


@dataclass
class SearchPipelineResult:
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
    requested_word_count: Optional[int] = None

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
            "requested_word_count": self.requested_word_count,
        }


class SearchPipeline:
    def __init__(self, cache: Optional[SearchCache] = None, db: Optional[CrawlDatabase] = None,
                 timeout: float = 6.0, ai_provider: Optional[BaseLLMProvider] = None):
        self.cache = cache or SearchCache(default_ttl_seconds=1800)
        self.db = db
        self.timeout = timeout
        self.query_analyzer = QueryAnalyzer()
        self.google_provider = GoogleSearchProvider()
        self.multi_provider = MultiEngineSearchProvider()
        self.evidence_extractor = EvidenceExtractor(timeout=self.timeout)
        self.verifier = EvidenceVerifier()
        self.answer_generator = AnswerGenerator(llm_provider=ai_provider)

    def get_preferred_provider(self, requested: str = "auto") -> SearchProvider:
        req = requested.lower().strip()
        if req == "google":
            return self.google_provider if self.google_provider.is_available() else self.multi_provider
        if req in ("multi", "bing"):
            return self.multi_provider
        return self.google_provider if self.google_provider.is_available() else self.multi_provider

    def run(self, query: str, num_sources: int = 12, provider_preference: str = "auto",
            progress_callback: Optional[Callable[[str, float], None]] = None,
            conversation_history: Optional[List[Dict[str, str]]] = None,
            target_language: str = "en") -> SearchPipelineResult:
        start_time = time.time()
        requested_word_count = extract_requested_word_count(query)

        def _update(status: str, pct: float):
            if progress_callback:
                try:
                    progress_callback(status, pct)
                except Exception:
                    pass

        # Strip only the output-length instruction before web retrieval. The original
        # query remains available to synthesis so the answer follows the user's wording.
        search_target = remove_word_count_instruction(query)
        if conversation_history:
            search_target = rewrite_follow_up_query(search_target, conversation_history)
        analysis = self.query_analyzer.analyze(search_target)

        provider = self.get_preferred_provider(provider_preference)
        _update(f"Searching web via {provider.provider_name}...", 0.25)

        effective_source_target = max(12, num_sources)
        cached_set = self.cache.get(search_target, provider.provider_name, effective_source_target)
        if cached_set:
            result_set = cached_set
        else:
            fetch_count = min(30, effective_source_target + 12)
            result_set = provider.search(search_target, num_results=fetch_count)

            if getattr(analysis, "facets", None) and len(analysis.facets) > 1:
                seen_urls = {r.url for r in result_set.results}
                for facet in analysis.facets[:4]:
                    if facet.search_query and facet.search_query.strip().lower() != search_target.strip().lower():
                        try:
                            f_res = provider.search(facet.search_query, num_results=4)
                            for r in f_res.results:
                                if r.url not in seen_urls:
                                    seen_urls.add(r.url)
                                    result_set.results.append(r)
                        except Exception:
                            pass
            self.cache.set(search_target, provider.provider_name, result_set, num_results=effective_source_target)

        _update("Ranking sources by authority, relevance, freshness, and diversity...", 0.45)
        ranked = rank_search_results(
            results=result_set.results,
            query_analysis=analysis,
            max_results=effective_source_target,
            domain_diversity_limit=2,
        )

        _update("Fetching multiple independent sources and extracting evidence...", 0.62)
        extracted_pages = self.evidence_extractor.extract_from_search_results(
            results=ranked,
            max_workers=min(6, max(1, len(ranked))),
        )

        _update("Building a broader evidence set for detailed synthesis...", 0.72)
        all_passages: List[EvidencePassage] = []
        for page in extracted_pages:
            all_passages.extend(page.passages)

        evidence_limit = 36 if requested_word_count is None else min(48, max(36, requested_word_count // 8))
        top_passages = rank_and_filter_passages(
            passages=all_passages,
            query_analysis=analysis,
            max_passages=evidence_limit,
        )

        coverage = cluster_evidence_by_facets(
            passages=all_passages if len(all_passages) < 100 else top_passages,
            facets=getattr(analysis, "facets", []),
        )

        is_complex = getattr(analysis, "complexity", None) == QueryComplexity.COMPLEX
        if is_complex and coverage and coverage.unverified_requirements:
            for uncovered_facet in [f for f in getattr(analysis, "facets", [])
                                    if f.title in coverage.unverified_requirements and f.search_query][:2]:
                _update(f"Deep Research Loop: targeted retrieval for '{uncovered_facet.title}'...", 0.79)
                try:
                    target_res = provider.search(uncovered_facet.search_query, num_results=4)
                    existing_urls = {p.url for p in extracted_pages}
                    new_candidates = [r for r in target_res.results if r.url not in existing_urls]
                    if new_candidates:
                        new_pages = self.evidence_extractor.extract_from_search_results(
                            results=new_candidates[:3], max_workers=min(3, len(new_candidates))
                        )
                        extracted_pages.extend(new_pages)
                        for np in new_pages:
                            all_passages.extend(np.passages)
                        top_passages = rank_and_filter_passages(
                            passages=all_passages, query_analysis=analysis, max_passages=evidence_limit
                        )
                        coverage = cluster_evidence_by_facets(
                            passages=all_passages if len(all_passages) < 120 else top_passages,
                            facets=getattr(analysis, "facets", []),
                        )
                except Exception:
                    pass

        _update("Cross-checking sources and verifying facts...", 0.86)
        verification = self.verifier.verify(
            extracted_evidence=extracted_pages,
            top_passages=top_passages,
            query_analysis=analysis,
        )

        confidence = calculate_confidence(
            independent_domains=verification["independent_domains"],
            contradictions=verification["contradictions"],
            extracted_evidence=extracted_pages,
            is_time_sensitive=analysis.is_time_sensitive,
        )

        _update("Synthesizing detailed, source-backed answer...", 0.94)
        answer = self.answer_generator.generate_answer(
            query=query,
            query_analysis=analysis,
            passages=top_passages,
            verification_summary=verification,
            confidence_report=confidence,
            coverage_report=coverage,
            history=conversation_history,
            target_language=target_language,
            requested_word_count=requested_word_count,
        )

        total_elapsed = time.time() - start_time
        _update("Complete", 1.0)

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
                        "requested_word_count": requested_word_count,
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
            requested_word_count=requested_word_count,
        )
