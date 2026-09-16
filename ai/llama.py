"""
Hosted Llama LLM Provider.
Integrates hosted Llama models via OpenAI-compatible REST APIs.
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
    """Hosted Llama implementation using OpenAI-compatible chat-completions APIs."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None, timeout: float = 25.0):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self.timeout = timeout
        self._detect_configuration()

    def _get_secret_or_env(self, key: str) -> Optional[str]:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets is not None and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
        return os.environ.get(key)

    def _detect_configuration(self) -> None:
        if not self._api_key:
            for env_name in ("GROQ_API_KEY", "TOGETHER_API_KEY", "OPENROUTER_API_KEY", "LLAMA_API_KEY", "OPENAI_API_KEY"):
                val = self._get_secret_or_env(env_name)
                if val:
                    self._api_key = val
                    self._detected_env = env_name
                    break

        if not self._base_url:
            custom_base = self._get_secret_or_env("LLAMA_BASE_URL") or self._get_secret_or_env("OPENAI_BASE_URL")
            if custom_base:
                self._base_url = custom_base.rstrip("/")
            elif getattr(self, "_detected_env", None) == "GROQ_API_KEY" or (self._api_key or "").startswith("gsk_"):
                self._base_url = "https://api.groq.com/openai/v1"
            elif getattr(self, "_detected_env", None) == "TOGETHER_API_KEY":
                self._base_url = "https://api.together.xyz/v1"
            elif getattr(self, "_detected_env", None) == "OPENROUTER_API_KEY":
                self._base_url = "https://openrouter.ai/api/v1"
            else:
                self._base_url = "https://api.groq.com/openai/v1"

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
        label = "Hosted Llama"
        if self._base_url:
            if "groq.com" in self._base_url:
                label = "Llama 3.3 (Groq)"
            elif "together" in self._base_url:
                label = "Llama 3.1 (Together AI)"
            elif "openrouter" in self._base_url:
                label = "Llama 3.3 (OpenRouter)"
        return f"{label} [{self._model}]"

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def synthesize(
        self,
        query: str,
        sources: List[Citation],
        passages: List[EvidencePassage],
        analysis: Optional[Any] = None,
        history: Optional[List[Dict[str, str]]] = None,
        target_language: str = "en",
        requested_word_count: Optional[int] = None,
    ) -> Optional[SynthesizedResearchResponse]:
        if not self.is_available():
            return None

        user_prompt = build_synthesis_prompt(
            query=query,
            sources=sources,
            passages=passages,
            analysis=analysis,
            history=history,
            target_language=target_language,
            requested_word_count=requested_word_count,
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AntigravityResearchEngine/2.0",
        }
        if "openrouter" in (self._base_url or ""):
            headers["HTTP-Referer"] = "https://github.com/Tishal68/web-crawler"
            headers["X-Title"] = "AI Web Search & Crawler"

        # Give the model enough room for detailed research and exact-count drafting.
        requested_tokens = min(7000, max(3000, (requested_word_count or 0) * 2 + 1200))
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_SYNTHESIS_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": requested_tokens,
        }

        try:
            resp = requests.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                logger.error("LLM synthesis API returned HTTP %s: %s", resp.status_code, resp.text[:200])
                return None

            choices = resp.json().get("choices", [])
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                return None

            parsed_json = self._parse_json_safe(content)
            if not parsed_json:
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
        cleaned = text.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass
        match = re.search(r"(\{[\s\S]*\})", cleaned)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        return None
