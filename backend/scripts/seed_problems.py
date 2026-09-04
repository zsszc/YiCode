"""
数据迁移脚本 — 将原项目的 problems.json 导入 SQLite。

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


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 读取原项目数据
    data_path = ROOT.parent / "data" / "problems.json"
    if not data_path.exists():
        print(f"未找到 {data_path}，跳过数据导入")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for cat in data.get("categories", []):
        for p in cat.get("problems", []):
            exists = db.query(Problem).filter(Problem.id == p["id"]).first()
            if exists:
                continue
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
            count += 1

    db.commit()
    db.close()
    print(f"成功导入 {count} 道题目")


if __name__ == "__main__":
    seed()
