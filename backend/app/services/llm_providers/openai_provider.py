"""
OpenAI-compatible LLM Provider
支持 OpenAI、Azure OpenAI 及任何兼容 OpenAI API 格式的服务。
"""

import time
from typing import Optional

import httpx

from app.config import get_settings
from app.services.llm_providers.base import BaseLLMProvider, HintResult, CodeReviewResult
from app.services.llm_providers.kimi_provider import (
    HINT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
    _build_hint_messages,
    _build_review_messages,
    _parse_review_json,
    _stream_chat,
)

settings = get_settings()

OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible LLM Provider。"""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url or OPENAI_BASE_URL
        self.model = settings.llm_model or OPENAI_DEFAULT_MODEL
        self.timeout = settings.llm_timeout_seconds
        self.max_tokens = settings.llm_max_tokens
        self.temperature = settings.llm_temperature

        if not self.api_key:
            raise RuntimeError("OpenAIProvider requires llm_api_key. Set it via .env or environment variable.")

    async def generate_hint(
        self,
        problem,
        level: int,
        user_code: Optional[str],
        profile,
    ) -> HintResult:
        start = time.time()
        messages = _build_hint_messages(problem, level, user_code, profile)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        latency = int((time.time() - start) * 1000)

        return HintResult(content=content, tokens_used=tokens, latency_ms=latency)

    async def generate_hint_stream(
        self,
        problem,
        level: int,
        user_code: Optional[str],
        profile,
    ):
        """流式生成解题提示。"""
        messages = _build_hint_messages(problem, level, user_code, profile)
        async for chunk in _stream_chat(
            self.base_url, self.api_key, self.model,
            messages, self.timeout, self.max_tokens, self.temperature,
        ):
            yield chunk

    async def review_code(
        self,
        problem,
        code: str,
        language: str,
    ) -> CodeReviewResult:
        start = time.time()
        messages = _build_review_messages(problem, code, language)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        raw_content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        latency = int((time.time() - start) * 1000)

        result = _parse_review_json(raw_content)
        result.tokens_used = tokens
        result.latency_ms = latency
        return result
