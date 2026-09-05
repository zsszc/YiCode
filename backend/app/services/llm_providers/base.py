"""
LLM Provider 基础接口与类型定义
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HintResult:
    content: str
    tokens_used: int = 0
    latency_ms: int = 0


@dataclass
class CodeReviewResult:
    time_complexity: str
    space_complexity: str
    edge_cases: list[str]
    style_suggestions: list[str]
    optimization_hints: list[str]
    rating: int  # 1-5
    overall_comment: str
    tokens_used: int = 0
    latency_ms: int = 0


class BaseLLMProvider:
    """LLM Provider 抽象基类。"""

    async def generate_hint(
        self,
        problem: "Problem",
        level: int,
        user_code: Optional[str],
        profile: Optional["LearningProfile"],
    ) -> HintResult:
        raise NotImplementedError

    async def generate_hint_stream(
        self,
        problem: "Problem",
        level: int,
        user_code: Optional[str],
        profile: Optional["LearningProfile"],
    ):
        """流式生成解题提示（异步生成器，yield 字符串片段）。"""
        raise NotImplementedError

    async def review_code(
        self,
        problem: "Problem",
        code: str,
        language: str,
    ) -> CodeReviewResult:
        raise NotImplementedError

    async def chat(
        self,
        problem: Optional["Problem"],
        message: str,
        history: list[dict],
        user_code: Optional[str] = None,
    ) -> HintResult:
        """自由对话：结合题目上下文与用户代码回答用户提问。

        history: [{"role": "user"|"assistant", "content": str}, ...]
        """
        raise NotImplementedError

    async def chat_stream(
        self,
        problem: Optional["Problem"],
        message: str,
        history: list[dict],
        user_code: Optional[str] = None,
    ):
        """流式自由对话（异步生成器，yield 字符串片段）。

        默认实现：退化为一次性输出，子类可覆盖为真正的流式。
        """
        result = await self.chat(problem, message, history, user_code)
        yield result.content
