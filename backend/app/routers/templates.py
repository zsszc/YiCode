"""
模板刷题 API — 面试突击背诵模式

数据为静态内置（app/data/templates_data.py），不依赖数据库。
"""

from fastapi import APIRouter, HTTPException

from app.data.templates_data import get_template, get_template_list

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
