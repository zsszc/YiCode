"""
数据迁移脚本 — 将 problems.json + problem_content.json 导入 SQLite。

用法:
    cd backend
    python -m scripts.seed_problems
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal, engine, Base
from app.models.problem import Problem

LISTNODE_DEF = """class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

"""

TREENODE_DEF = """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

"""


def build_starter_code(entry: dict) -> str:
    """根据内容条目生成编辑器初始代码。"""
    header = "from typing import List, Optional\n\n"
    kind = entry.get("kind")
    defs = ""
    if kind == "linked":
        defs = LISTNODE_DEF + "\n"
    elif kind == "tree":
        defs = TREENODE_DEF + "\n"
    sig = entry["sig"]
    if sig.startswith("class "):
        # 设计题：sig 本身就是完整类骨架
        return header + sig + "\n"
    return header + defs + "class Solution:\n    " + sig + "\n        pass\n"


def seed(db=None):
    """导入题目及内容。幂等：已存在的题目只补全缺失的内容字段。"""
    Base.metadata.create_all(bind=engine)
    own_db = db is None
    if own_db:
        db = SessionLocal()

    data_path = ROOT.parent / "data" / "problems.json"
    content_path = ROOT.parent / "data" / "problem_content.json"
    if not data_path.exists():
        print(f"未找到 {data_path}，跳过数据导入")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    content = {}
    if content_path.exists():
        with open(content_path, "r", encoding="utf-8") as f:
            content = json.load(f)

    added, updated = 0, 0
    for cat in data.get("categories", []):
        for p in cat.get("problems", []):
            entry = content.get(p.get("slug"), {})
            problem = db.query(Problem).filter(Problem.id == p["id"]).first()
            if not problem:
                problem = Problem(
                    id=p["id"],
                    title=p["title"],
                    slug=p.get("slug"),
                    difficulty=p["difficulty"],
                    category=cat["name"],
                    leetcode_url=f"https://leetcode.cn/problems/{p.get('slug', '')}/",
                    is_custom=False,
                )
                db.add(problem)
                added += 1
            # 补全/刷新内容字段（仅当当前为空时，避免覆盖用户自定义修改）
            if entry and not problem.description:
                problem.description = entry.get("desc")
                problem.function_name = entry.get("fn")
                problem.starter_code = build_starter_code(entry)
                problem.test_cases = json.dumps(
                    {
                        "tests": entry.get("tests", []),
                        "unord": bool(entry.get("unord")),
                        "inplace": bool(entry.get("inplace")),
                        "eps": bool(entry.get("eps")),
                        "design": entry.get("design"),
                    },
                    ensure_ascii=False,
                )
                updated += 1

    db.commit()
    if own_db:
        db.close()
    print(f"导入完成：新增 {added} 道题，补全内容 {updated} 道题")


if __name__ == "__main__":
    seed()
