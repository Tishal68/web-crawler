"""
Abstract Base Class for LLM Answer Synthesis Providers.
Enables pluggable models (Hosted Llama via Groq/Together/OpenRouter, custom endpoints, or local).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from .schemas import SynthesizedResearchResponse
from evidence.models import EvidencePassage

if TYPE_CHECKING:
    from answer.citations import Citation


class BaseLLMProvider(ABC):
    """Abstract interface for an AI synthesis model provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the LLM provider (e.g. 'Hosted Llama 3.3 (Groq)')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if API credentials and endpoints are configured and active."""
        pass

    @abstractmethod
    def synthesize(
        self,
        query: str,
        sources: List[Citation],
        passages: List[EvidencePassage],
        analysis: Optional[Any] = None,
        history: Optional[List[Dict[str, str]]] = None,
        target_language: str = "en",
    ) -> Optional[SynthesizedResearchResponse]:
        """
        Synthesize evidence into a grounded, structured research response with claim citations.
        Returns None if synthesis fails or API is unavailable.
        """
        pass
