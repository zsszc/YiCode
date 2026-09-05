"""
模板刷题 API — 面试突击背诵模式

数据为静态内置（app/data/templates_data.py），不依赖数据库。
变式练习由 LLM 生成并落库为自定义题，复用站内判题。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.data.templates_data import get_template, get_template_list
from app.dependencies import get_db
from app.models.problem import Problem

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
def list_templates():
    """模板列表（摘要，不含代码正文）。"""
    return get_template_list()


@router.get("/{slug}")
def get_template_detail(slug: str):
    """模板详情：完整代码 + 易错点 + 关联题目。"""
    tpl = get_template(slug)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return tpl


@router.post("/{slug}/variant", status_code=201)
async def generate_variant_problem(slug: str, db: Session = Depends(get_db)):
    """AI 变式练习：根据模板生成原创练习题，落库为自定义题（可判题）。"""
    from app.services.variant_service import VariantError, generate_variant

    tpl = get_template(slug)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")

    last_error = None
    for _attempt in range(2):  # LLM 输出不稳定，最多重试一次
        try:
            variant = await generate_variant(tpl)
            break
        except VariantError as e:
            last_error = e
    else:
        raise HTTPException(status_code=502, detail=f"AI 出题失败：{last_error}")

    problem = Problem(
        title=f"[变式] {variant['title']}",
        slug=f"variant-{slug}",
        difficulty="中等",
        category=f"模板·{tpl['name']}",
        is_custom=True,
        description=variant["description"],
        starter_code=variant["starter_code"],
        function_name=variant["function_name"],
        test_cases=json.dumps({"tests": variant["tests"]}, ensure_ascii=False),
        leetcode_url=None,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return {"id": problem.id, "title": problem.title, "template": tpl["name"]}

