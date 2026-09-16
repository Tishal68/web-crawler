"""
Utilities for detecting and enforcing user-requested exact word counts.

The count applies to the answer prose only. Numeric citation markers such as [1]
are excluded from the prose word count so citations do not distort a requested
word target.
"""

from __future__ import annotations

import re
from typing import Optional, List, Dict, Any, Tuple


_REQUESTED_WORD_COUNT_RE = re.compile(
    r"(?<!\w)(?:exactly\s+|exact\s+|about\s+|around\s+)?(\d{2,5})\s*[- ]?words?\b",
    re.IGNORECASE,
)
_CITATION_RE = re.compile(r"\[\d+\]")
_MARKDOWN_RE = re.compile(r"[`*_>#]")
_WORD_RE = re.compile(r"[\w]+(?:['’\-][\w]+)*", re.UNICODE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def extract_requested_word_count(query: str) -> Optional[int]:
    """Return an explicit numeric word-count request, or None when absent."""
    text = query or ""
    for match in _REQUESTED_WORD_COUNT_RE.finditer(text):
        value = int(match.group(1))
        if 10 <= value <= 10000:
            return value
    return None


def strip_non_countable_markup(text: str) -> str:
    """Remove citation markers and lightweight markdown syntax before counting."""
    cleaned = _CITATION_RE.sub(" ", text or "")
    cleaned = _MARKDOWN_RE.sub(" ", cleaned)
    return cleaned


def count_words(text: str) -> int:
    """Count user-visible prose words using a deterministic lexical rule."""
    cleaned = strip_non_countable_markup(text)
    return len(_WORD_RE.findall(cleaned))


def _sentence_units(text: str, default_source_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Convert prose into sentence-sized reusable units with source metadata."""
    units: List[Dict[str, Any]] = []
    for raw in _SENTENCE_RE.split((text or "").strip()):
        sentence = " ".join(raw.split()).strip()
        if not sentence or count_words(sentence) < 5:
            continue
        source_ids = [int(v) for v in re.findall(r"\[(\d+)\]", sentence)]
        if default_source_id is not None and not source_ids:
            source_ids = [default_source_id]
        units.append(
            {
                "text": sentence,
                "words": count_words(sentence),
                "score": 1.0,
                "source_ids": source_ids,
            }
        )
    return units


def build_evidence_units(
    answer_text: str,
    passages: Optional[List[Any]] = None,
    source_lookup: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Build a deduplicated pool of sentence units from the draft and evidence."""
    units: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for unit in _sentence_units(answer_text):
        fp = strip_non_countable_markup(unit["text"]).lower()
        if fp and fp not in seen:
            seen.add(fp)
            unit["score"] = 3.0
            units.append(unit)

    for passage in passages or []:
        source_id: Optional[int] = None
        if source_lookup:
            source_id = source_lookup.get(getattr(passage, "source_url", ""))
        source_units = _sentence_units(getattr(passage, "text", ""), source_id)
        for unit in source_units:
            fp = strip_non_countable_markup(unit["text"]).lower()
            if not fp or fp in seen:
                continue
            seen.add(fp)
            # Prefer useful evidence with more specific content.
            word_len = unit["words"]
            unit["score"] = 1.5 + min(2.0, word_len / 80.0)
            units.append(unit)

    return units


def _exact_subset(units: List[Dict[str, Any]], target: int) -> Optional[List[Dict[str, Any]]]:
    """Find a high-scoring set of complete sentence units totaling exactly target words."""
    if target <= 0:
        return []

    # dp[word_count] = (score, selected_indices)
    dp: Dict[int, Tuple[float, List[int]]] = {0: (0.0, [])}
    for idx, unit in enumerate(units):
        weight = int(unit["words"])
        if weight <= 0 or weight > target:
            continue
        snapshot = list(dp.items())
        for current, (score, chosen) in snapshot:
            nxt = current + weight
            if nxt > target:
                continue
            candidate = (score + float(unit.get("score", 1.0)), chosen + [idx])
            existing = dp.get(nxt)
            if existing is None or candidate[0] > existing[0]:
                dp[nxt] = candidate

    result = dp.get(target)
    if not result:
        return None
    return [units[i] for i in result[1]]


def _trim_fragment(text: str, words_needed: int) -> str:
    """Create a non-fabricated final fragment when exact sentence selection is impossible."""
    if words_needed <= 0:
        return ""
    tokens = re.findall(r"\S+", (text or "").strip())
    if not tokens:
        return ""
    selected = tokens[:words_needed]
    fragment = " ".join(selected)
    if fragment and not re.search(r"[.!?]$", fragment):
        fragment += "."
    return fragment


def fit_exact_word_count(
    answer_text: str,
    target: int,
    passages: Optional[List[Any]] = None,
    source_lookup: Optional[Dict[str, int]] = None,
) -> Optional[str]:
    """
    Return an evidence-derived answer with exactly target prose words.

    Preference order:
    1. Complete, non-repetitive sentence subset totaling exactly target.
    2. Complete sentence subset plus a final source-derived fragment.
    """
    if target is None or target <= 0:
        return answer_text
    if count_words(answer_text) == target:
        return answer_text.strip()

    units = build_evidence_units(answer_text, passages, source_lookup)
    if not units:
        return None

    exact = _exact_subset(units, target)
    if exact:
        return " ".join(unit["text"] for unit in exact).strip()

    # Find the strongest complete-sentence subset below target, then fill the remainder
    # from the next evidence sentence without inventing new information.
    best_units: List[Dict[str, Any]] = []
    best_words = 0
    dp: Dict[int, Tuple[float, List[int]]] = {0: (0.0, [])}
    for idx, unit in enumerate(units):
        weight = int(unit["words"])
        if weight <= 0 or weight > target:
            continue
        snapshot = list(dp.items())
        for current, (score, chosen) in snapshot:
            nxt = current + weight
            if nxt > target:
                continue
            candidate = (score + float(unit.get("score", 1.0)), chosen + [idx])
            existing = dp.get(nxt)
            if existing is None or candidate[0] > existing[0]:
                dp[nxt] = candidate
                if nxt > best_words or (nxt == best_words and candidate[0] > sum(u.get("score", 1.0) for u in best_units)):
                    best_words = nxt
                    best_units = [units[i] for i in chosen + [idx]]

    remaining = target - best_words
    if remaining > 0:
        used_ids = {id(u) for u in best_units}
        for unit in units:
            if id(unit) in used_ids or unit["words"] < remaining:
                continue
            fragment = _trim_fragment(unit["text"], remaining)
            if count_words(fragment) == remaining:
                candidate_text = " ".join(u["text"] for u in best_units + [{"text": fragment}]).strip()
                if count_words(candidate_text) == target:
                    return candidate_text

    return None
