"""
AI 内联代码补全服务 — 类似 Copilot 的 ghost text 补全

使用高速模型，只返回应该插入到光标处的代码片段。
"""

from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()

# 补全用高速模型，首 token 延迟低；若端点不支持可回退主模型
COMPLETE_MODEL = "kimi-for-coding-highspeed"

COMPLETE_SYSTEM_PROMPT = """你是 IDE 内联代码补全引擎（类似 GitHub Copilot），为刷题场景补全 Python 代码。

严格规则：
1. 只输出应该插入到 <CURSOR> 位置的代码，绝对不要输出解释、注释说明或 markdown 围栏
2. 绝对不要重复 <CURSOR> 之前已经存在的代码
3. 补全要短：优先补完当前语句；若当前语句已完整，则补全下一个逻辑块（1~8 行）
4. 结合题目上下文与用户已有代码的变量命名、风格
5. 如果光标处不适合补全（如空文件、注释中间），输出空字符串
6. 输出必须以正确的缩进开始（如果光标在行首）"""


def _insert_cursor_marker(code: str, cursor_line: int, cursor_col: int) -> str:
    """在指定行列插入 <CURSOR> 标记。"""
    lines = code.split("\n")
    if not (1 <= cursor_line <= len(lines)):
        return code + "\n<CURSOR>"
    idx = cursor_line - 1
    line = lines[idx]
    col = max(0, min(cursor_col, len(line)))
    lines[idx] = line[:col] + "<CURSOR>" + line[col:]
    return "\n".join(lines)


async def complete_code(
    code: str,
    cursor_line: int,
    cursor_col: int,
    problem_context: Optional[str] = None,
) -> str:
    """返回光标处的建议补全文本；无法补全时返回空字符串。"""
    if not settings.llm_api_key:
        return ""

    marked = _insert_cursor_marker(code, cursor_line, cursor_col)
    # 控制上下文长度：光标前 80 行 + 后 30 行
    lines = marked.split("\n")
    cursor_idx = next((i for i, l in enumerate(lines) if "<CURSOR>" in l), len(lines))
    lo = max(0, cursor_idx - 80)
    hi = min(len(lines), cursor_idx + 30)
    snippet = "\n".join(lines[lo:hi])

    user_content = ""
    if problem_context:
        user_content += f"题目信息:\n{problem_context[:800]}\n\n"
    user_content += f"用户代码（<CURSOR> 为光标位置）:\n```python\n{snippet}\n```"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": COMPLETE_MODEL,
                    "messages": [
                        {"role": "system", "content": COMPLETE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    # reasoning 模型会把 max_tokens 消耗在思考上，给足余量
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        # 补全是锦上添花，任何失败都静默降级为空
        return ""

    text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    # 去掉可能的 markdown 围栏
    if text.startswith("```"):
        parts = text.split("\n")
        parts = parts[1:] if len(parts) > 1 else []
        if parts and parts[-1].strip().startswith("```"):
            parts = parts[:-1]
        text = "\n".join(parts)
    # 防御：模型偶尔会复述指令或输出解释文字，过长的补全直接截断
    if len(text) > 600:
        text = "\n".join(text.split("\n")[:10])
    return text
