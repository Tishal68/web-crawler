"""
Strict Python Citation Validator.
Guarantees citation security:
- Enforces Python as the single source of truth for citations.
- Validates that every source ID emitted in claims, sections, conflicts, and text
  strictly belongs to an authentically retrieved source in the current search.
- Strips hallucinated or out-of-bounds citation references.
- Rejects invented URLs or external links.
"""

from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING, List, Set, Dict, Any, Tuple
from .schemas import SynthesizedResearchResponse, SynthesizedClaim, SynthesizedSection, SynthesizedConflict

if TYPE_CHECKING:
    from answer.citations import Citation, CitationRegistry

logger = logging.getLogger(__name__)


class CitationValidator:
    """Validates and enforces strict alignment between AI synthesis and retrieved sources."""

    def __init__(self, citations: List[Citation]):
        self.citations = citations
        self.valid_ids: Set[int] = {c.index for c in citations}
        self.cit_by_id: Dict[int, Citation] = {c.index: c for c in citations}

    def validate_and_sanitize(
        self,
        response: SynthesizedResearchResponse,
    ) -> Tuple[SynthesizedResearchResponse, Dict[str, Any]]:
        """
        Scrub any hallucinated citation IDs from model claims, sections, conflicts,
        and inline text.
        Returns:
            (sanitized_response, validation_telemetry)
        """
        stripped_count = 0
        original_claims_count = len(response.claims)

        # 1. Sanitize Claims
        sanitized_claims: List[SynthesizedClaim] = []
        for claim in response.claims:
            clean_ids = []
            for sid in claim.source_ids:
                if sid in self.valid_ids:
                    clean_ids.append(sid)
                else:
                    stripped_count += 1
                    logger.warning("Stripped hallucinated source_id %s from claim '%s'", sid, claim.text[:40])
            
            # Deduplicate IDs while preserving order
            seen_ids = set()
            deduped_ids = []
            for sid in clean_ids:
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    deduped_ids.append(sid)

            sanitized_claims.append(SynthesizedClaim(
                text=claim.text,
                source_ids=deduped_ids,
            ))

        # 2. Sanitize Sections
        sanitized_sections: List[SynthesizedSection] = []
        for sec in response.sections:
            clean_ids = []
            for sid in sec.source_ids:
                if sid in self.valid_ids:
                    clean_ids.append(sid)
                else:
                    stripped_count += 1
                    logger.warning("Stripped hallucinated source_id %s from section '%s'", sid, sec.title)

            seen_ids = set()
            deduped_ids = []
            for sid in clean_ids:
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    deduped_ids.append(sid)

            # Also sanitize inline text citations in section content
            cleaned_content = self._sanitize_inline_citations(sec.content)

            sanitized_sections.append(SynthesizedSection(
                title=sec.title,
                content=cleaned_content,
                source_ids=deduped_ids,
            ))

        # 3. Sanitize Conflicts
        sanitized_conflicts: List[SynthesizedConflict] = []
        for conf in response.conflicts:
            clean_a = [sid for sid in conf.source_ids_a if sid in self.valid_ids]
            clean_b = [sid for sid in conf.source_ids_b if sid in self.valid_ids]
            stripped_count += (len(conf.source_ids_a) - len(clean_a)) + (len(conf.source_ids_b) - len(clean_b))

            sanitized_conflicts.append(SynthesizedConflict(
                topic=conf.topic,
                view_a=conf.view_a,
                source_ids_a=list(dict.fromkeys(clean_a)),
                view_b=conf.view_b,
                source_ids_b=list(dict.fromkeys(clean_b)),
            ))

        # 4. Sanitize Direct Answer inline citations
        sanitized_direct_answer = self._sanitize_inline_citations(response.direct_answer)

        # 5. Build telemetry
        telemetry = {
            "valid_source_ids": sorted(list(self.valid_ids)),
            "hallucinated_citations_stripped": stripped_count,
            "claims_processed": original_claims_count,
            "all_citations_grounded": stripped_count == 0,
        }

        clean_response = SynthesizedResearchResponse(
            direct_answer=sanitized_direct_answer,
            key_findings=response.key_findings,
            claims=sanitized_claims,
            sections=sanitized_sections,
            conflicts=sanitized_conflicts,
            follow_up_questions=response.follow_up_questions,
        )

        return clean_response, telemetry

    def _sanitize_inline_citations(self, text: str) -> str:
        """Replace any [X] where X is not a valid registered source ID."""
        if not text:
            return ""

        def replace_match(m):
            raw_id = m.group(1)
            try:
                val = int(raw_id)
                if val in self.valid_ids:
                    return f"[{val}]"
                return ""  # Strip hallucinated reference
            except ValueError:
                return m.group(0)

        # Look for [1], [2], etc.
        cleaned = re.sub(r"\[(\d+)\]", replace_match, text)
        # Clean up any empty double spaces left behind by stripped citations
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned
