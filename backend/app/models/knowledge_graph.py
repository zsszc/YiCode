"""
知识图谱模型 — Phase 4
题目之间的知识点依赖关系。
"""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, UniqueConstraint
from app.core.database import Base


class KnowledgeNode(Base):
    """知识点节点。"""
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)  # 数据结构/算法/技巧
    description = Column(Text, default="")
    difficulty_weight = Column(Float, default=1.0)  # 难度权重


class ProblemKnowledge(Base):
    """题目-知识点关联。"""
    __tablename__ = "problem_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    knowledge_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    importance = Column(Float, default=1.0)  # 该知识点对本题的重要程度

    __table_args__ = (
        UniqueConstraint("problem_id", "knowledge_id", name="uq_problem_knowledge"),
    )


class KnowledgeDependency(Base):
    """知识点之间的依赖关系。"""
    __tablename__ = "knowledge_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_knowledge_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    to_knowledge_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    strength = Column(Float, default=1.0)  # 依赖强度

    __table_args__ = (
        UniqueConstraint("from_knowledge_id", "to_knowledge_id", name="uq_knowledge_dep"),
    )


class UserKnowledgeMastery(Base):
    """用户对知识点的掌握程度。"""
    __tablename__ = "user_knowledge_mastery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    knowledge_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    mastery_level = Column(Float, default=0.0)  # 0-1，掌握程度
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    last_practiced = Column(String, nullable=True)  # ISO date

    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_id", name="uq_user_knowledge"),
    )
