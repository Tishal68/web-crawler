"""
Hosted Llama LLM Provider.
Integrates hosted Llama models via OpenAI-compatible REST APIs
(Groq, Together AI, OpenRouter, or custom self-hosted endpoints).
Uses lightweight HTTP requests without heavy proprietary dependencies.
"""

from __future__ import annotations

import os
import json
import logging
import re
from typing import TYPE_CHECKING, List, Dict, Any, Optional
import requests

from .model import BaseLLMProvider
from .schemas import SynthesizedResearchResponse
from .prompts import SYSTEM_SYNTHESIS_PROMPT, build_synthesis_prompt
from evidence.models import EvidencePassage

if TYPE_CHECKING:
    from answer.citations import Citation

logger = logging.getLogger(__name__)


class HostedLlamaProvider(BaseLLMProvider):
    """
    Hosted Llama implementation using OpenAI-compatible /chat/completions endpoints.
    Auto-detects Groq, Together AI, OpenRouter, or custom OpenAI-compatible proxies.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 25.0,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self.timeout = timeout
        self._detect_configuration()

    def _get_secret_or_env(self, key: str) -> Optional[str]:
        """Fetch secret safely from streamlit secrets or environment variables."""
        # 1. Try Streamlit secrets if running inside Streamlit
        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets is not None:
                if key in st.secrets:
                    return str(st.secrets[key])
        except Exception:
            pass

        # 2. Try OS environment
        return os.environ.get(key)

    def _detect_configuration(self) -> None:
        """Auto-configure endpoint, model, and authentication credentials."""
        # Check API key in priority order
        if not self._api_key:
            for env_name in (
                "GROQ_API_KEY",
                "TOGETHER_API_KEY",
                "OPENROUTER_API_KEY",
                "LLAMA_API_KEY",
                "OPENAI_API_KEY",
            ):
                val = self._get_secret_or_env(env_name)
                if val:
                    self._api_key = val
                    self._detected_env = env_name
                    break

        # If base URL wasn't provided, select based on detected provider key
        if not self._base_url:
            custom_base = self._get_secret_or_env("LLAMA_BASE_URL") or self._get_secret_or_env("OPENAI_BASE_URL")
            if custom_base:
                self._base_url = custom_base.rstrip("/")
            elif getattr(self, "_detected_env", None) == "GROQ_API_KEY":
                self._base_url = "https://api.groq.com/openai/v1"
            elif getattr(self, "_detected_env", None) == "TOGETHER_API_KEY":
                self._base_url = "https://api.together.xyz/v1"
            elif getattr(self, "_detected_env", None) == "OPENROUTER_API_KEY":
                self._base_url = "https://openrouter.ai/api/v1"
            elif self._api_key and self._api_key.startswith("gsk_"):
                self._base_url = "https://api.groq.com/openai/v1"
            else:
                self._base_url = "https://api.groq.com/openai/v1"

        # Model selection
        if not self._model:
            custom_model = self._get_secret_or_env("LLAMA_MODEL")
            if custom_model:
                self._model = custom_model
            elif "groq.com" in (self._base_url or ""):
                self._model = "llama-3.3-70b-versatile"
            elif "together" in (self._base_url or ""):
                self._model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
            elif "openrouter" in (self._base_url or ""):
                self._model = "meta-llama/llama-3.3-70b-instruct"
            else:
                self._model = "llama-3.3-70b-versatile"

    @property
    def provider_name(self) -> str:
        provider_label = "Hosted Llama"
        if self._base_url:
            if "groq.com" in self._base_url:
                provider_label = "Llama 3.3 (Groq)"
            elif "together" in self._base_url:
                provider_label = "Llama 3.1 (Together AI)"
            elif "openrouter" in self._base_url:
                provider_label = "Llama 3.3 (OpenRouter)"
        return f"{provider_label} [{self._model}]"

    def is_available(self) -> bool:
        """Returns True if an API key is present."""
        return bool(self._api_key and self._api_key.strip())

    def synthesize(
        self,
        query: str,
        sources: List[Citation],
        passages: List[EvidencePassage],
        analysis: Optional[Any] = None,
        history: Optional[List[Dict[str, str]]] = None,
        target_language: str = "en",
    ) -> Optional[SynthesizedResearchResponse]:
        """Call hosted Llama API with structured JSON output contract."""
        if not self.is_available():
            logger.info("Hosted Llama provider unavailable (no API key configured).")
            return None

        user_prompt = build_synthesis_prompt(
            query=query,
            sources=sources,
            passages=passages,
            analysis=analysis,
            history=history,
            target_language=target_language,
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AntigravityResearchEngine/2.0",
        }

        # Include OpenRouter headers if calling OpenRouter
        if "openrouter" in (self._base_url or ""):
            headers["HTTP-Referer"] = "https://github.com/Tishal68/web-crawler"
            headers["X-Title"] = "AI Web Search & Crawler"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_SYNTHESIS_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 3000,
        }

        endpoint = f"{self._base_url}/chat/completions"

        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                logger.error(
                    "LLM synthesis API returned HTTP %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                logger.error("LLM synthesis API returned empty choices")
                return None

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                logger.error("LLM synthesis API returned empty message content")
                return None

            # Parse JSON content
            parsed_json = self._parse_json_safe(content)
            if not parsed_json:
                logger.error("Failed to parse JSON from LLM output: %s", content[:150])
                return None

            return SynthesizedResearchResponse.from_dict(parsed_json)

        except requests.exceptions.Timeout:
            logger.warning("LLM API request timed out after %s seconds", self.timeout)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("LLM API request exception: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error during LLM synthesis: %s", e)
            return None

    def _parse_json_safe(self, text: str) -> Optional[Dict[str, Any]]:
        """Safely extract and parse JSON from model output."""
        cleaned = text.strip()
        # Direct parse attempt
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strip markdown code blocks ```json ... ```
        if "```" in cleaned:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if m:
                try:
                    return json.loads(m.group(1).strip())
                except json.JSONDecodeError:
                    pass

        # Fallback regex search for outer braces { ... }
        m_brace = re.search(r"(\{[\s\S]*\})", cleaned)
        if m_brace:
            try:
                return json.loads(m_brace.group(1).strip())
            except json.JSONDecodeError:
                pass

        return None
