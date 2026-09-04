"""
代码执行 API Router — Phase 4.3
在线运行 Python 验证题解
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.code_runner_service import run_python_code

router = APIRouter(prefix="/code", tags=["code"])


class CodeRunRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10000, description="Python 代码")
    stdin: str | None = Field(None, max_length=1000, description="标准输入内容")
    timeout: int = Field(5, ge=1, le=30, description="超时时间（秒）")


class CodeRunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool


@router.post("/run", response_model=CodeRunResponse)
async def run_code(req: CodeRunRequest):
    """在线运行 Python 代码。"""
    result = run_python_code(
        code=req.code,
        timeout_seconds=req.timeout,
        stdin_input=req.stdin,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
    }
