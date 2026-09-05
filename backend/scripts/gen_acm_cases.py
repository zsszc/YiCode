"""批量为题库题目生成 ACM 模式资源（acm_starter + io_tests）。

质量门：让 LLM 同时给出参考解 reference，用沙箱实际运行参考解，
只有通过全部 io_tests 的结果才落库，否则重试（默认 2 次）。

用法：
    cd backend
    python -m scripts.gen_acm_cases --db ../data/yicode.db [--limit 5] [--only-id 1,2] [--concurrency 3]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.services.code_runner_service import run_python_code  # noqa: E402

SYSTEM_PROMPT = """你是算法竞赛出题人。给定一道 LeetCode 风格的函数题，为它设计 ACM 模式（标准输入/输出）资源。

输出**纯 JSON**（不要 markdown 代码围栏）：
{
  "io_format": "输入格式与输出格式的中文说明（一两句话）",
  "acm_starter": "ACM 模式起始代码（读入框架，留 # TODO 让选手补全）",
  "reference": "完整正确解答（读 stdin、写 stdout）",
  "io_tests": [
    {"stdin": "...", "stdout": "..."}
  ]
}

硬性要求：
1. **禁止使用 import sys / sys.stdin / sys.stdout**，只能用 input() 和 print()（安全沙箱限制）。
2. io_tests 给 3 组：1 组最小规模、1 组常规、1 组稍大但仍小（所有数字绝对值不超过 10^6，数组长度不超过 50）。
3. stdin 末尾带一个换行；stdout 是期望的**完整输出**（末尾换行可有可无）。
4. 输入格式要自然贴合题意（例如数组题：第一行 n，第二行 n 个空格分隔整数；两数之和这类需要多参数的，每行一个参数）。
5. stdout 必须与 reference 程序的实际输出完全一致（你将自证：reference 跑这些 io_tests 必须全对）。
6. acm_starter 要能直接运行不报错（可以只读完输入然后 pass）。
7. reference 必须是正确解法，时间复杂度合理。"""


def extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("响应中无 JSON")
    return json.loads(m.group(0))


def norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in (s or "").strip().splitlines())


def verify(reference: str, io_tests: list[dict], timeout: int = 15) -> tuple[bool, str]:
    """用沙箱跑参考解，全部 io_tests 通过才算合格。"""
    for i, t in enumerate(io_tests):
        r = run_python_code(reference, timeout_seconds=timeout, stdin_input=t["stdin"])
        if r.exit_code != 0 or r.timed_out:
            return False, f"用例{i+1} 运行失败: {(r.stderr or '').strip().splitlines()[-1] if r.stderr else 'timeout'}"
        if norm(r.stdout) != norm(t["stdout"]):
            return False, f"用例{i+1} 期望 {t['stdout']!r} 实际 {r.stdout.strip()!r}"
    return True, ""


async def gen_one(client: httpx.AsyncClient, settings, prob: dict, retries: int = 2) -> dict | None:
    spec = json.loads(prob["test_cases"]) if prob["test_cases"] else {}
    fn_tests = (spec.get("tests") or [])[:3]
    user = (
        f"题目：{prob['title']}\n"
        f"难度：{prob['difficulty']} ｜ 分类：{prob['category']}\n\n"
        f"题面：\n{prob['description'][:2000]}\n\n"
        f"函数名：{prob['function_name']}\n"
        f"函数模式起始代码：\n```python\n{prob['starter_code']}\n```\n"
        f"函数模式测试用例（参考）：{json.dumps(fn_tests, ensure_ascii=False)[:800]}\n\n"
        "请为此题生成 ACM 模式资源。"
    )
    last_err = ""
    for attempt in range(retries + 1):
        try:
            prompt = user
            if last_err:
                prompt += (
                    f"\n\n⚠️ 你上一次的回答未通过检查：{last_err}\n"
                    "请修正后重新输出完整 JSON。再次强调：绝对禁止 import sys，"
                    "读输入只能用 input()；stdout 必须与 reference 真实输出一致。"
                )
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max(settings.llm_max_tokens, 4096),
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"].get("content") or ""
            data = extract_json(content)
            io_tests = [
                {"stdin": str(t.get("stdin", "")), "stdout": str(t.get("stdout", "")).strip()}
                for t in (data.get("io_tests") or [])[:4]
                if str(t.get("stdin", "")).strip() and str(t.get("stdout", "")).strip()
            ]
            reference = str(data.get("reference") or "")
            acm_starter = str(data.get("acm_starter") or "")
            # 规整空行：行尾空格去掉、3 个及以上连续换行压成 2 个
            acm_starter = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", acm_starter))
            if not io_tests or not reference or not acm_starter:
                raise ValueError("缺少必要字段")
            ok, why = verify(reference, io_tests)
            if not ok:
                raise ValueError(f"参考解自验证失败：{why}")
            return {
                "acm_starter": acm_starter,
                "io_tests": io_tests,
                "io_format": str(data.get("io_format") or ""),
                "reference": reference,
            }
        except Exception as e:  # noqa: BLE001
            last_err = str(e)[:200]
            await asyncio.sleep(2 * (attempt + 1))
    print(f"  ✗ #{prob['id']} {prob['title']}: {last_err}", flush=True)
    return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="../data/yicode.db")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only-id", default="")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()

    settings = get_settings()
    if not settings.llm_api_key:
        print("未配置 LLM_API_KEY"); sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id,title,difficulty,category,description,starter_code,test_cases,function_name "
        "FROM problems WHERE deleted=0 ORDER BY id"
    ).fetchall()

    targets = []
    for r in rows:
        spec = json.loads(r["test_cases"]) if r["test_cases"] else {}
        if spec.get("io_tests"):
            continue  # 已有 ACM 用例
        targets.append(dict(r))
    if args.only_id:
        ids = {int(x) for x in args.only_id.split(",")}
        targets = [t for t in targets if t["id"] in ids]
    if args.limit:
        targets = targets[: args.limit]

    print(f"待生成：{len(targets)} 题（题库共 {len(rows)} 题）")
    sem = asyncio.Semaphore(args.concurrency)
    done = ok_cnt = 0

    async with httpx.AsyncClient(timeout=120) as client:
        async def worker(p: dict) -> None:
            nonlocal done, ok_cnt
            async with sem:
                result = await gen_one(client, settings, p)
                if result:
                    spec = json.loads(p["test_cases"]) if p["test_cases"] else {}
                    spec["acm_starter"] = result["acm_starter"]
                    spec["io_tests"] = result["io_tests"]
                    spec["io_format"] = result["io_format"]
                    conn.execute(
                        "UPDATE problems SET test_cases=? WHERE id=?",
                        (json.dumps(spec, ensure_ascii=False), p["id"]),
                    )
                    conn.commit()
                    ok_cnt += 1
                done += 1
                if done % 10 == 0 or done == len(targets):
                    print(f"进度 {done}/{len(targets)}，成功 {ok_cnt}", flush=True)

        await asyncio.gather(*(worker(p) for p in targets))

    conn.close()
    print(f"完成：成功 {ok_cnt}/{len(targets)}")


if __name__ == "__main__":
    asyncio.run(main())
