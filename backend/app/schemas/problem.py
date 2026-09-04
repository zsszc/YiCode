from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProblemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = None
    difficulty: str = Field(..., pattern="^(简单|中等|困难)$")
    category: str = Field(..., min_length=1, max_length=50)
    leetcode_url: Optional[str] = None
    is_custom: bool = False


class ProblemCreate(ProblemBase):
    id: Optional[int] = None


class ProblemOut(ProblemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deleted: bool = False


class ProblemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: Optional[str]
    difficulty: str
    category: str
    is_custom: bool
    status: str = "todo"
    next_review: Optional[str] = None
    note: str = ""


class CategoryOut(BaseModel):
    name: str
    problems: list[ProblemOut]
