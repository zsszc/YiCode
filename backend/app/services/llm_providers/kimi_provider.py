"""
Kimi LLM Provider — 使用 Moonshot AI API
文档: https://platform.moonshot.cn/
"""

import json
import time
from typing import Optional

import httpx

from app.config import get_settings
from app.services.llm_providers.base import BaseLLMProvider, HintResult, CodeReviewResult

settings = get_settings()

KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_DEFAULT_MODEL = "moonshot-v1-8k"


HINT_SYSTEM_PROMPT = """你是一位耐心的算法导师。用户正在做 LeetCode 题目。
请根据用户请求的 hint_level 提供合适的提示：
- level 1: 只给解题思路方向，不涉及具体算法
- level 2: 说明适用的算法/数据结构框架
- level 3: 提供关键代码片段（伪代码或核心逻辑）

要求：
1. 用中文回答
2. 鼓励性语气
3. 不直接给出完整 AC 代码
4. 如果用户已多次请求提示，适当给出更多细节"""

REVIEW_SYSTEM_PROMPT = """你是一位代码审查专家。请审查以下 LeetCode 题解代码。
用中文回答，输出严格 JSON 格式：
{
  "time_complexity": "时间复杂度分析",
  "space_complexity": "空间复杂度分析",
  "edge_cases": ["边界情况1", "边界情况2"],
  "style_suggestions": ["代码风格建议1"],
  "optimization_hints": ["优化建议1"],
  "rating": 1-5 的整数,
  "overall_comment": "总体评价"
}"""


def _build_hint_messages(problem, level: int, user_code: Optional[str], profile) -> list[dict]:
    """构建 hint 请求的 messages。"""
    content = f"题目: {problem.title}\n难度: {problem.difficulty}\n分类: {problem.category}"
    if profile:
        content += f"\n用户画像:\n- 首次尝试: {profile.first_try_success_rate:.0%} 成功率"
        content += f"\n- 提示依赖率: {profile.hint_dependency_rate:.0%}"
    if user_code:
        content += f"\n用户已写代码:\n```{user_code}```"
    content += f"\n\n请提供 hint_level={level} 的提示。"

    return [
        {"role": "system", "content": HINT_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def _build_review_messages(problem, code: str, language: str) -> list[dict]:
    """构建 code review 请求的 messages。"""
    content = f"题目: {problem.title}\n语言: {language}\n\n用户代码:\n```{language}\n{code}\n```"
    return [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


class KimiProvider(BaseLLMProvider):
    """Kimi (Moonshot AI) LLM Provider。"""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url or KIMI_BASE_URL
        self.model = settings.llm_model or KIMI_DEFAULT_MODEL
        self.timeout = settings.llm_timeout_seconds
        self.max_tokens = settings.llm_max_tokens
        self.temperature = settings.llm_temperature

        if not self.api_key:
            raise RuntimeError("KimiProvider requires llm_api_key. Set it via .env or environment variable.")

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
                    "temperature": 0.3,  # review 用较低 temperature
                },
            )
            resp.raise_for_status()
            data = resp.json()

        raw_content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        latency = int((time.time() - start) * 1000)

        # 解析 JSON
        result = _parse_review_json(raw_content)
        result.tokens_used = tokens
        result.latency_ms = latency
        return result


def _parse_review_json(raw: str) -> CodeReviewResult:
    """从 LLM 响应中解析 JSON，容错处理。"""
    # 尝试提取 JSON 块
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # fallback: 返回原始文本作为 overall_comment
        return CodeReviewResult(
            time_complexity="未知",
            space_complexity="未知",
            edge_cases=[],
            style_suggestions=[],
            optimization_hints=[],
            rating=3,
            overall_comment=text[:500],
        )

    return CodeReviewResult(
        time_complexity=data.get("time_complexity", "未知"),
        space_complexity=data.get("space_complexity", "未知"),
        edge_cases=data.get("edge_cases", []),
        style_suggestions=data.get("style_suggestions", []),
        optimization_hints=data.get("optimization_hints", []),
        rating=max(1, min(5, int(data.get("rating", 3)))),
        overall_comment=data.get("overall_comment", ""),
    )
