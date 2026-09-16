"""Utilities for detecting and enforcing user-requested exact word counts."""

from __future__ import annotations

import re
from typing import Optional, List, Dict, Any, Tuple

_REQUESTED_WORD_COUNT_RE = re.compile(r"(?<!\w)(?:exactly\s+|exact\s+|about\s+|around\s+)?(\d{2,5})\s*[- ]?words?\b", re.IGNORECASE)
_CITATION_RE = re.compile(r"\[\d+\]")
_MARKDOWN_RE = re.compile(r"[`*_>#]")
_WORD_RE = re.compile(r"[\w]+(?:['’\-][\w]+)*", re.UNICODE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def extract_requested_word_count(query: str) -> Optional[int]:
    for match in _REQUESTED_WORD_COUNT_RE.finditer(query or ""):
        value = int(match.group(1))
        if 10 <= value <= 10000:
            return value
    return None


def remove_word_count_instruction(query: str) -> str:
    """Remove the length instruction before querying the web."""
    cleaned = _REQUESTED_WORD_COUNT_RE.sub(" ", query or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,;:-")
    return cleaned or (query or "").strip()


def strip_non_countable_markup(text: str) -> str:
    cleaned = _CITATION_RE.sub(" ", text or "")
    return _MARKDOWN_RE.sub(" ", cleaned)


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(strip_non_countable_markup(text)))


def _sentence_units(text: str, default_source_id: Optional[int] = None) -> List[Dict[str, Any]]:
    units: List[Dict[str, Any]] = []
    for raw in _SENTENCE_RE.split((text or "").strip()):
        sentence = " ".join(raw.split()).strip()
        if not sentence or count_words(sentence) < 5:
            continue
        source_ids = [int(v) for v in re.findall(r"\[(\d+)\]", sentence)]
        if default_source_id is not None and not source_ids:
            source_ids = [default_source_id]
        units.append({"text": sentence, "words": count_words(sentence), "score": 1.0, "source_ids": source_ids})
    return units


def build_evidence_units(answer_text: str, passages: Optional[List[Any]] = None, source_lookup: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    units: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for unit in _sentence_units(answer_text):
        fp = strip_non_countable_markup(unit["text"]).lower()
        if fp and fp not in seen:
            seen.add(fp)
            unit["score"] = 3.0
            units.append(unit)

    for passage in passages or []:
        source_id = source_lookup.get(getattr(passage, "source_url", "")) if source_lookup else None
        for unit in _sentence_units(getattr(passage, "text", ""), source_id):
            fp = strip_non_countable_markup(unit["text"]).lower()
            if not fp or fp in seen:
                continue
            seen.add(fp)
            unit["score"] = 1.5 + min(2.0, unit["words"] / 80.0)
            units.append(unit)
    return units


def _exact_subset(units: List[Dict[str, Any]], target: int) -> Optional[List[Dict[str, Any]]]:
    dp: Dict[int, Tuple[float, List[int]]] = {0: (0.0, [])}
    for idx, unit in enumerate(units):
        weight = int(unit["words"])
        if weight <= 0 or weight > target:
            continue
        for current, (score, chosen) in list(dp.items()):
            nxt = current + weight
            if nxt > target:
                continue
            candidate = (score + float(unit.get("score", 1.0)), chosen + [idx])
            if nxt not in dp or candidate[0] > dp[nxt][0]:
                dp[nxt] = candidate
    result = dp.get(target)
    return [units[i] for i in result[1]] if result else None


def _source_fragment(text: str, words_needed: int) -> str:
    if words_needed <= 0:
        return ""
    tokens = re.findall(r"\S+", (text or "").strip())
    if not tokens:
        return ""
    fragment = " ".join(tokens[:words_needed])
    return fragment + ("." if not re.search(r"[.!?]$", fragment) else "")


def fit_exact_word_count(answer_text: str, target: int, passages: Optional[List[Any]] = None, source_lookup: Optional[Dict[str, int]] = None) -> Optional[str]:
    """Return an evidence-derived answer with exactly target prose words."""
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

    # Find the strongest complete-sentence subset below target.
    dp: Dict[int, Tuple[float, List[int]]] = {0: (0.0, [])}
    for idx, unit in enumerate(units):
        weight = int(unit["words"])
        if weight <= 0 or weight >= target:
            continue
        for current, (score, chosen) in list(dp.items()):
            nxt = current + weight
            if nxt >= target:
                continue
            candidate = (score + float(unit.get("score", 1.0)), chosen + [idx])
            if nxt not in dp or candidate[0] > dp[nxt][0]:
                dp[nxt] = candidate

    if not dp:
        return None
    best_words = max(dp.keys())
    best = dp[best_words][1]
    remaining = target - best_words
    used = set(best)

    for idx, unit in enumerate(units):
        if idx in used:
            continue
        fragment = _source_fragment(unit["text"], remaining)
        if count_words(fragment) == remaining:
            result = " ".join([units[i]["text"] for i in best] + [fragment]).strip()
            if count_words(result) == target:
                return result
    return None
