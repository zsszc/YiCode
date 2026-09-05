"""
AI 变式练习生成服务 — 根据算法模板生成一道可直接判题的练习题

生成结果直接落库为自定义题（is_custom=True），复用站内判题/AI Tutor 全套能力。
"""

import json
import re
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()

VARIANT_SYSTEM_PROMPT = """你是一位算法出题专家。根据给定的算法模板，设计一道**原创变式练习题**，用于面试突击训练。

要求：
1. 题目必须运用该模板的核心思想，但不能照抄经典原题（换场景、换数据形态）
2. 难度：简单~中等，10 分钟内可完成
3. 函数签名必须是 class Solution 的一个方法
4. 题面 description 用 Markdown，必须包含：题目描述、示例、**输入格式**（ACM 用）、**输出格式**（ACM 用）
5. 测试用例的 input 是「参数列表的 JSON 字符串」，例如函数签名 twoSum(self, nums, target)，
   则 input 为 "[[2,7,11,15], 9]"（外层数组包住所有参数）；
   expected 是该用例期望返回值的 JSON 字符串，例如 "[0, 1]"
6. 同时提供 ACM 模式（完整程序读写标准输入输出）的模板和用例：
   - acm_starter：完整可运行程序骨架，用 input() 读输入、print() 写输出，
     **禁止使用 import sys / sys.stdin**（本平台安全沙箱不支持），核心逻辑留空给用户
   - io_tests：stdin/stdout 对，stdout 是期望的完整输出（末尾换行可有可无）
7. 输出**严格 JSON**（不要 markdown 围栏），格式：
{
  "title": "题目标题",
  "description": "题面（Markdown，含示例、输入格式、输出格式）",
  "function_name": "函数名（小写下划线）",
  "starter_code": "class Solution:\\n    def 函数名(self, 参数):  # 带类型注解\\n        pass",
  "tests": [
    {"input": "[[...], ...]", "expected": "..."},
    {"input": "...", "expected": "..."},
    {"input": "...", "expected": "..."}
  ],
  "acm_starter": "n = int(input())\\n# TODO: 解析输入并求解\\n",
  "io_tests": [
    {"stdin": "...", "stdout": "..."},
    {"stdin": "...", "stdout": "..."}
  ]
}"""


class VariantError(Exception):
    pass


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 对象（容错围栏/前后废话）。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise VariantError("AI 输出中没有 JSON 对象")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise VariantError(f"AI 输出的 JSON 无法解析: {e}")


def _validate(data: dict) -> dict:
    """校验并规范化生成结果，不合格抛 VariantError。"""
    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()
    fn = str(data.get("function_name") or "").strip()
    starter = str(data.get("starter_code") or "").strip()
    tests = data.get("tests")

    if not title or not description:
        raise VariantError("缺少标题或题面")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", fn or ""):
        raise VariantError(f"函数名不合法: {fn!r}")
    if "class Solution" not in starter or fn not in starter:
        raise VariantError("starter_code 中未找到匹配的 Solution 方法")
    if not isinstance(tests, list) or not (1 <= len(tests) <= 6):
        raise VariantError("测试用例数量应为 1~6 组")

    norm_tests = []
    for t in tests:
        inp, exp = str(t.get("input", "")).strip(), str(t.get("expected", "")).strip()
        if not inp or not exp:
            raise VariantError("测试用例缺 input/expected")
        # input 必须是合法 JSON 数组字符串（参数列表）
        try:
            parsed = json.loads(inp)
            if not isinstance(parsed, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise VariantError(f"测试用例 input 不是 JSON 数组: {inp[:60]}")
        json.loads(exp)  # expected 也必须是合法 JSON
        norm_tests.append({"input": inp, "expected": exp})

    # ACM 部分（可选，有则校验结构）
    acm_starter = str(data.get("acm_starter") or "").strip()
    io_tests = data.get("io_tests") or []
    norm_io = []
    if isinstance(io_tests, list):
        for t in io_tests[:6]:
            stdin, stdout = str(t.get("stdin", "")), str(t.get("stdout", "")).strip()
            if stdin.strip() and stdout:
                norm_io.append({"stdin": stdin, "stdout": stdout})

    return {
        "title": title[:60],
        "description": description,
        "function_name": fn,
        "starter_code": starter,
        "tests": norm_tests,
        "acm_starter": acm_starter or None,
        "io_tests": norm_io,
    }


async def generate_variant(template: dict, problem_id_hint: Optional[int] = None) -> dict:
    """调用 LLM 生成变式题，失败抛 VariantError。调用方负责重试。"""
    if not settings.llm_api_key:
        raise VariantError("未配置 LLM_API_KEY，无法使用 AI 出题")

    user_content = (
        f"算法模板：{template['name']}\n"
        f"适用场景：{template['scenario']}\n"
        f"模板代码：\n```python\n{template['code']}\n```\n\n"
        "请基于这个模板出一道原创变式练习题。"
    )

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": VARIANT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                # reasoning 模型需要较大余量
                "max_tokens": max(settings.llm_max_tokens, 4096),
            },
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"].get("content") or ""
    return _validate(_extract_json(content))
