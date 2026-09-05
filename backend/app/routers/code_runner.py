"""
代码执行 API Router — Phase 4.3
在线运行 Python 验证题解
"""

from fastapi import APIRouter, Depends, HTTPException
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


class RunTestsRequest(BaseModel):
    problem_id: int = Field(..., description="题目 ID")
    code: str = Field(..., min_length=1, max_length=20000, description="Python 代码")
    timeout: int = Field(15, ge=1, le=30, description="超时时间（秒）")
    mode: str = Field("function", description="判题模式：function=核心代码 / acm=完整程序 stdin/stdout")


class JudgeCase(BaseModel):
    input: str
    expected: str
    actual: str
    ok: bool


class RunTestsResponse(BaseModel):
    passed: int
    total: int
    cases: list[JudgeCase]
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    sandbox_blocked: bool = False


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


@router.post("/run-tests", response_model=RunTestsResponse)
async def run_tests(req: RunTestsRequest, db: Session = Depends(get_db)):
    """针对某道题的内置测试用例运行并判题（支持 function / acm 两种模式）。"""
    import json

    from app.models.problem import Problem
    from app.services.code_runner_service import run_problem_tests, run_acm_tests

    problem = db.query(Problem).filter(Problem.id == req.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail=f"题目 #{req.problem_id} 不存在")
    if not problem.test_cases:
        raise HTTPException(status_code=400, detail="本题暂未配置测试用例，请使用自由运行")

    spec = json.loads(problem.test_cases)

    if req.mode == "acm":
        io_tests = spec.get("io_tests") or []
        if not io_tests:
            raise HTTPException(status_code=400, detail="本题暂无 ACM 判题用例，可用「运行」配合自定义输入调试")
        result = run_acm_tests(code=req.code, io_tests=io_tests, timeout_seconds=req.timeout)
    else:
        if not problem.function_name:
            raise HTTPException(status_code=400, detail="本题暂未配置测试用例，请使用自由运行")
        result = run_problem_tests(
            code=req.code,
            function_name=problem.function_name,
            spec=spec,
            timeout_seconds=req.timeout,
        )
    return {
        "passed": result.passed,
        "total": result.total,
        "cases": result.cases,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
        "sandbox_blocked": result.sandbox_blocked,
    }


class LintRequest(BaseModel):
    code: str = Field(..., max_length=20000, description="Python 代码")


class CompleteRequest(BaseModel):
    code: str = Field(..., max_length=20000, description="当前编辑器完整代码")
    cursor_line: int = Field(..., ge=1, description="光标行（1-based）")
    cursor_col: int = Field(..., ge=0, description="光标列（0-based）")
    problem_id: int | None = Field(None, description="题目 ID（提供上下文）")


@router.post("/lint")
async def lint_code(req: LintRequest):
    """静态诊断：返回波浪线/hover 所需的诊断列表（本地 AST 分析，毫秒级）。"""
    from app.services.code_lint_service import lint_python

    return {"diagnostics": lint_python(req.code)}


@router.post("/complete")
async def complete(req: CompleteRequest, db: Session = Depends(get_db)):
    """AI 内联补全：返回光标处的建议代码（ghost text）。"""
    from app.services.code_complete_service import complete_code

    problem_context = None
    if req.problem_id:
        from app.models.problem import Problem
        problem = db.query(Problem).filter(Problem.id == req.problem_id).first()
        if problem:
            problem_context = f"题目: {problem.title}\n{(problem.description or '')[:600]}"

    completion = await complete_code(
        code=req.code,
        cursor_line=req.cursor_line,
        cursor_col=req.cursor_col,
        problem_context=problem_context,
    )
    return {"completion": completion}
