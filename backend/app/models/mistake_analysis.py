"""
错题归因模型 — Phase 4
记录用户每次错题的原因分类。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class MistakeAnalysis(Base):
    """错题归因分析。"""
    __tablename__ = "mistake_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    review_log_id = Column(Integer, ForeignKey("review_logs.id"), nullable=True)

    # 归因分类
    mistake_type = Column(String, nullable=False)
    # concept_gap: 概念不清
    # code_bug: 代码逻辑错误
    # edge_case: 边界情况遗漏
    # time_pressure: 时间压力/仓促
    # hint_dependency: 过度依赖提示
    # wrong_approach: 方法选择错误

    # 详细描述
    description = Column(Text, default="")
    # 关联知识点
    related_knowledge = Column(Text, default="")  # JSON list of knowledge_node ids
    # 建议行动
    suggested_action = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())
