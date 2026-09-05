"""
AI Research and Synthesis package.
Provides modular LLM integration, structured schemas, citation validation,
and deterministic research fallbacks.
"""

from .schemas import (
    SynthesizedClaim,
    SynthesizedSection,
    SynthesizedConflict,
    SynthesizedResearchResponse,
)
from .model import BaseLLMProvider
from .llama import HostedLlamaProvider
from .prompts import build_synthesis_prompt, SYSTEM_SYNTHESIS_PROMPT
from .citation_validator import CitationValidator
from .fallback import DeterministicResearchSynthesizer

__all__ = [
    "SynthesizedClaim",
    "SynthesizedSection",
    "SynthesizedConflict",
    "SynthesizedResearchResponse",
    "BaseLLMProvider",
    "HostedLlamaProvider",
    "build_synthesis_prompt",
    "SYSTEM_SYNTHESIS_PROMPT",
    "CitationValidator",
    "DeterministicResearchSynthesizer",
]
