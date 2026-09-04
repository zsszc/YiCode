"""
LLM Provider 工厂 — 根据配置自动创建对应的 Provider 实例。
"""

from app.config import get_settings
from app.services.llm_providers.base import BaseLLMProvider
from app.services.llm_providers.mock_provider import MockLLMProvider
from app.services.llm_providers.kimi_provider import KimiProvider
from app.services.llm_providers.openai_provider import OpenAIProvider

settings = get_settings()


def get_llm_provider() -> BaseLLMProvider:
    """根据配置创建 LLM Provider 实例。
    
    优先级：
    1. 如果 llm_provider == "kimi" 且有 api_key → KimiProvider
    2. 如果 llm_provider == "openai" 且有 api_key → OpenAIProvider
    3. 其他情况 → MockLLMProvider（fallback，无需 API key）
    """
    provider_name = settings.llm_provider.lower()
    has_key = bool(settings.llm_api_key)

    if provider_name == "kimi" and has_key:
        return KimiProvider()

    if provider_name == "openai" and has_key:
        return OpenAIProvider()

    # Fallback to mock
    return MockLLMProvider()
