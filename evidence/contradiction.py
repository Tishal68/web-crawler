"""
Contradiction detection module.
Identifies factual disagreements, conflicting metrics, differing timelines,
and polarity conflicts across independent web sources.
"""

import re
from typing import List, Dict, Tuple, Optional
from .models import EvidencePassage, ContradictionAlert


class ContradictionDetector:
    """Detects discrepancies between evidence passages from different root domains."""

    POLARITY_PAIRS: List[Tuple[str, str, str]] = [
        (r"\b(open[-\s]?source|permissive\s+license)\b", r"\b(closed[-\s]?source|proprietary)\b", "Software Licensing"),
        (r"\b(is\s+free|at\s+no\s+cost|free\s+of\s+charge)\b", r"\b(paid|subscription\s+required|commercial\s+license)\b", "Pricing Model"),
        (r"\b(approved|cleared|endorsed)\b", r"\b(rejected|denied|disapproved|unapproved)\b", "Regulatory/Official Status"),
        (r"\b(cancelled|canceled|discontinued|abandoned)\b", r"\b(ongoing|active|launched|in\s+production)\b", "Project Status"),
        (r"\b(supports|supported\s+by)\b", r"\b(does\s+not\s+support|unsupported|lacks\s+support)\b", "Feature Support"),
    ]

    def detect_contradictions(self, passages: List[EvidencePassage]) -> List[ContradictionAlert]:
        """
        Scan passages from different domains for numeric, temporal, or polarity conflicts.
        """
        alerts: List[ContradictionAlert] = []
        if len(passages) < 2:
            return alerts

        # Group passages by root domain
        domain_passages: Dict[str, List[EvidencePassage]] = {}
        for p in passages:
            if not p.source_domain:
                continue
            domain_passages.setdefault(p.source_domain, []).append(p)

        domains = list(domain_passages.keys())
        if len(domains) < 2:
            return alerts

        # Cross-check domain pairs
        seen_conflict_keys = set()

        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                dom_a, dom_b = domains[i], domains[j]
                passages_a = domain_passages[dom_a]
                passages_b = domain_passages[dom_b]

                # 1. Check Polarity Conflicts
                polarity_alert = self._check_polarity_conflicts(passages_a, passages_b, dom_a, dom_b)
                if polarity_alert:
                    key = f"polarity_{polarity_alert.topic_or_entity}_{dom_a}_{dom_b}"
                    if key not in seen_conflict_keys:
                        seen_conflict_keys.add(key)
                        alerts.append(polarity_alert)

                # 2. Check Numeric Metric Conflicts
                numeric_alert = self._check_numeric_conflicts(passages_a, passages_b, dom_a, dom_b)
                if numeric_alert:
                    key = f"numeric_{numeric_alert.topic_or_entity}_{dom_a}_{dom_b}"
                    if key not in seen_conflict_keys:
                        seen_conflict_keys.add(key)
                        alerts.append(numeric_alert)

                # 3. Check Temporal/Year Conflicts
                temporal_alert = self._check_temporal_conflicts(passages_a, passages_b, dom_a, dom_b)
                if temporal_alert:
                    key = f"temporal_{temporal_alert.topic_or_entity}_{dom_a}_{dom_b}"
                    if key not in seen_conflict_keys:
                        seen_conflict_keys.add(key)
                        alerts.append(temporal_alert)

        return alerts

    def _check_polarity_conflicts(
        self,
        passages_a: List[EvidencePassage],
        passages_b: List[EvidencePassage],
        dom_a: str,
        dom_b: str,
    ) -> Optional[ContradictionAlert]:
        """Detect opposing categorical stances."""
        for p_a in passages_a:
            text_a = p_a.text
            lower_a = text_a.lower()

            for p_b in passages_b:
                text_b = p_b.text
                lower_b = text_b.lower()

                # Check common subject keyword overlap
                tokens_a = set(re.findall(r"\b[a-zA-Z]{4,}\b", lower_a))
                tokens_b = set(re.findall(r"\b[a-zA-Z]{4,}\b", lower_b))
                shared_tokens = tokens_a.intersection(tokens_b)

                if len(shared_tokens) < 3:
                    continue

                for pos_pattern, neg_pattern, category in self.POLARITY_PAIRS:
                    has_pos_a = bool(re.search(pos_pattern, lower_a))
                    has_neg_a = bool(re.search(neg_pattern, lower_a))
                    has_pos_b = bool(re.search(pos_pattern, lower_b))
                    has_neg_b = bool(re.search(neg_pattern, lower_b))

                    if (has_pos_a and has_neg_b) or (has_neg_a and has_pos_b):
                        return ContradictionAlert(
                            topic_or_entity=f"{category} discrepancy",
                            claim_a=self._truncate_sentence(text_a),
                            source_a_url=p_a.source_url,
                            source_a_domain=dom_a,
                            claim_b=self._truncate_sentence(text_b),
                            source_b_url=p_b.source_url,
                            source_b_domain=dom_b,
                            explanation=f"Contradictory assertions regarding {category.lower()}.",
                        )
        return None

    def _check_numeric_conflicts(
        self,
        passages_a: List[EvidencePassage],
        passages_b: List[EvidencePassage],
        dom_a: str,
        dom_b: str,
    ) -> Optional[ContradictionAlert]:
        """Detect numerical metric discrepancies for the same subject."""
        # Find patterns like "120 qubits", "$40 billion", "99.5% accuracy"
        metric_regex = re.compile(
            r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:is|has|achieved|reached|cost|weighs|holds)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(qubits?|billion|million|percent|%|parameters?|flops?|usd|\$|mph|km|kg)\b",
            re.IGNORECASE
        )

        for p_a in passages_a:
            for match_a in metric_regex.finditer(p_a.text):
                subj_a = match_a.group(1).lower().strip()
                val_a_str = match_a.group(2).replace(",", "")
                unit_a = match_a.group(3).lower().strip()

                try:
                    val_a = float(val_a_str)
                except ValueError:
                    continue

                for p_b in passages_b:
                    for match_b in metric_regex.finditer(p_b.text):
                        subj_b = match_b.group(1).lower().strip()
                        val_b_str = match_b.group(2).replace(",", "")
                        unit_b = match_b.group(3).lower().strip()

                        if unit_a == unit_b and (subj_a in subj_b or subj_b in subj_a):
                            try:
                                val_b = float(val_b_str)
                            except ValueError:
                                continue

                            # If numbers differ significantly (> 15% delta)
                            if abs(val_a - val_b) > 0.15 * max(val_a, val_b):
                                return ContradictionAlert(
                                    topic_or_entity=f"{subj_a.title()} ({unit_a})",
                                    claim_a=self._truncate_sentence(p_a.text),
                                    source_a_url=p_a.source_url,
                                    source_a_domain=dom_a,
                                    claim_b=self._truncate_sentence(p_b.text),
                                    source_b_url=p_b.source_url,
                                    source_b_domain=dom_b,
                                    explanation=f"Source A reports {val_a} {unit_a}, while Source B reports {val_b} {unit_b}.",
                                )
        return None

    def _check_temporal_conflicts(
        self,
        passages_a: List[EvidencePassage],
        passages_b: List[EvidencePassage],
        dom_a: str,
        dom_b: str,
    ) -> Optional[ContradictionAlert]:
        """Detect conflicting release/launch/effective years for the same subject."""
        event_year_regex = re.compile(
            r"\b(released?|launched?|announced?|unveiled?|founded?|effective)\s+(?:in\s+)?([A-Za-z]+\s+)?(202[0-9]|201[0-9])\b",
            re.IGNORECASE
        )

        for p_a in passages_a:
            for match_a in event_year_regex.finditer(p_a.text):
                action_a = match_a.group(1).lower()
                year_a = match_a.group(3)

                for p_b in passages_b:
                    for match_b in event_year_regex.finditer(p_b.text):
                        action_b = match_b.group(1).lower()
                        year_b = match_b.group(3)

                        if action_a == action_b and year_a != year_b:
                            # Verify subject overlap
                            toks_a = set(re.findall(r"\b[a-zA-Z]{4,}\b", p_a.text.lower()))
                            toks_b = set(re.findall(r"\b[a-zA-Z]{4,}\b", p_b.text.lower()))
                            if len(toks_a.intersection(toks_b)) >= 2:
                                return ContradictionAlert(
                                    topic_or_entity=f"{action_a.title()} date / year",
                                    claim_a=self._truncate_sentence(p_a.text),
                                    source_a_url=p_a.source_url,
                                    source_a_domain=dom_a,
                                    claim_b=self._truncate_sentence(p_b.text),
                                    source_b_url=p_b.source_url,
                                    source_b_domain=dom_b,
                                    explanation=f"Source A reports {action_a} in {year_a}, whereas Source B reports {year_b}.",
                                )
        return None

    def _truncate_sentence(self, text: str, max_chars: int = 150) -> str:
        """Helper to keep contradiction claim excerpts readable."""
        text = " ".join(text.split())
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3].rstrip() + "..."
