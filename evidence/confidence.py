"""
Explainable confidence rating module.
Calculates grounded confidence badges, scores, and transparent rationales.
CRITICAL CONSTRAINT: Never outputs 1.0 (100%) or claims absolute certainty.
"""

from typing import List, Dict, Any
from .models import ConfidenceReport, ContradictionAlert, ExtractedPageEvidence


def calculate_confidence(
    independent_domains: List[str],
    contradictions: List[ContradictionAlert],
    extracted_evidence: List[ExtractedPageEvidence],
    is_time_sensitive: bool = False,
) -> ConfidenceReport:
    """
    Computes a grounded, explainable confidence report.
    Guaranteed to never output 100% or claim absolute certainty.
    """
    domain_count = len(independent_domains)
    has_contradictions = len(contradictions) > 0
    rationales: List[str] = []

    # Count high authority domains
    high_authority_types = {
        "Official Government",
        "University / Academic",
        "Standards Organization",
        "Scientific Publication",
        "Company Primary Source",
        "Established Journalism",
    }
    high_auth_count = sum(
        1 for ev in extracted_evidence
        if ev.source_type in high_authority_types and ev.fetch_success
    )

    if has_contradictions:
        badge_label = "🔴 Conflicting Sources"
        badge_color = "#EF4444"
        score = min(0.48, max(0.20, 0.40 - 0.05 * len(contradictions)))
        rationales.append(f"Detected {len(contradictions)} direct disagreement(s) between independent sources.")
        for c in contradictions[:2]:
            rationales.append(f"Discrepancy on {c.topic_or_entity} between {c.source_a_domain} and {c.source_b_domain}.")

    elif domain_count >= 3 and high_auth_count >= 1:
        badge_label = "🟢 Strongly Corroborated"
        badge_color = "#10B981"
        score = min(0.92, 0.82 + (0.02 * min(5, domain_count)))
        rationales.append(f"Corroborated by {domain_count} independent domains.")
        rationales.append(f"Includes {high_auth_count} recognized authoritative or primary sources.")
        rationales.append("No factual contradictions or discrepancies detected.")

    elif domain_count >= 2:
        badge_label = "🟡 Moderately Supported"
        badge_color = "#F59E0B"
        score = 0.72 if high_auth_count >= 1 else 0.65
        rationales.append(f"Cross-referenced across {domain_count} independent domains.")
        if high_auth_count > 0:
            rationales.append(f"Supported by {high_auth_count} recognized authoritative source(s).")
        rationales.append("No direct contradictions detected among retrieved sources.")

    else:
        badge_label = "🟠 Limited Evidence"
        badge_color = "#F97316"
        score = 0.45 if high_auth_count >= 1 else 0.35
        rationales.append("Information is based on limited independent source coverage.")
        if domain_count == 1:
            rationales.append(f"Only 1 independent domain ({independent_domains[0] if independent_domains else 'web'}) was retrieved.")
        else:
            rationales.append("No full web page bodies could be verified; reliance on snippet data.")

    # Guardrail: Never ever allow 1.0 (100%)
    score = min(0.94, max(0.10, score))

    return ConfidenceReport(
        badge_label=badge_label,
        badge_color=badge_color,
        score=score,
        independent_sources_count=domain_count,
        corroborating_domains=independent_domains,
        has_contradictions=has_contradictions,
        contradictions=contradictions,
        rationales=rationales,
    )
