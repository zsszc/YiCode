"""
代码安全沙箱 — Phase 5.2
基于 AST 静态分析 + 子进程隔离的代码执行环境。

安全层级：
1. 静态分析（AST）— 编译前拦截危险代码
2. 运行时包装 — 删除危险内置函数、劫持 __import__
3. 子进程隔离 — 超时杀死、输出截断
"""

import ast
import json
import subprocess
import sys
import tempfile
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CodeRunResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool = False


# ========== AST 静态分析 ==========

BANNED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "urllib", "http", "ftplib",
    "pickle", "marshal", "ctypes", "multiprocessing", "threading",
    "importlib", "pkgutil", "site", "builtins",
    # 文件系统 / 自省 / 进程控制类，算法题用不到
    "shutil", "pathlib", "glob", "tempfile", "signal", "gc",
    "inspect", "pty", "mmap",
}

# 保留 input（stdin 刷题场景需要）
BANNED_BUILTINS = {
    "eval", "exec", "compile", "open", "__import__",
    "exit", "quit", "help",
}

BANNED_ATTRIBUTES = {
    "system", "popen", "fork", "kill", "execv", "execve",
    "spawn", "chmod", "chown", "remove", "unlink", "rmdir",
    "mkdir", "makedirs", "rename", "replace",
    # 防止通过 typing.sys / 帧对象等间接逃逸沙箱
    "modules", "_getframe", "f_globals", "__globals__", "gi_frame",
    "__subclasses__", "__builtins__", "sys", "os",
}


class SecurityChecker(ast.NodeVisitor):
    """AST 访问者，用于检测代码中的危险操作。"""

    def __init__(self):
        self.violations: list[str] = []

    def check(self, source: str) -> list[str]:
        """检查代码，返回违规列表（空列表表示安全）。"""
        self.violations = []
        try:
            tree = ast.parse(source)
            self._add_parents(tree)
            self.visit(tree)
        except SyntaxError as e:
            self.violations.append(f"语法错误: {e}")
        return self.violations

    def _add_parents(self, node: ast.AST, parent: ast.AST | None = None):
        """为 AST 节点添加 _parent 引用，辅助判断节点上下文。"""
        node._parent = parent
        for child in ast.iter_child_nodes(node):
            self._add_parents(child, node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base in BANNED_IMPORTS:
                self.violations.append(f"禁止导入模块: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base = node.module.split(".")[0]
            if base in BANNED_IMPORTS:
                self.violations.append(f"禁止从模块导入: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 检测 eval('...')、exec('...') 等直接调用
        if isinstance(node.func, ast.Name) and node.func.id in BANNED_BUILTINS:
            self.violations.append(f"禁止调用内置函数: {node.func.id}")
        # 检测 getattr(obj, 'system') 等动态属性访问
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            self.violations.append("禁止调用 getattr 进行动态属性访问")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # 检测 obj.system、os.popen 等属性访问
        if node.attr in BANNED_ATTRIBUTES:
            self.violations.append(f"禁止访问危险属性: {node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # 检测直接使用 banned builtin 作为值（如 f = open）
        # 排除 Call.func 的情况（已由 visit_Call 处理）
        if node.id in BANNED_BUILTINS and not self._is_call_func(node):
            self.violations.append(f"禁止使用危险内置名: {node.id}")
        self.generic_visit(node)

    def _is_call_func(self, node: ast.Name) -> bool:
        """检查该 Name 节点是否作为 Call 的 func 出现。"""
        parent = getattr(node, "_parent", None)
        return isinstance(parent, ast.Call) and parent.func is node


def static_check(source: str) -> list[str]:
    """对代码进行静态安全检查，返回违规描述列表。"""
    checker = SecurityChecker()
    return checker.check(source)


# ========== 运行时包装 ==========

def _wrap_code(user_code: str) -> str:
    """将用户代码包装在安全沙箱中执行。"""
    wrapper = '''
import builtins
import traceback as _traceback

# 保存 __import__ 与堆栈引用
_original_import = __import__
_extract_stack = _traceback.extract_stack

# 说明：eval/exec/compile/open 等危险内置由 AST 静态分析在用户代码层面拦截。
# 不能在运行时从 builtins 中删除它们——Python 的 import 机制底层依赖 exec/open，
# 删除后任何模块导入都会失败。因此运行时只劫持 __import__。

# 禁止危险模块导入
_banned_modules = ''' + repr(BANNED_IMPORTS) + '''

def _safe_import(name, *args, **kwargs):
    base = name.split('.')[0]
    if base in _banned_modules:
        # 只拦截用户代码**直接**发起的导入：直接调用者（_safe_import 的上一帧）
        # 位于本文件（沙箱临时文件）才拦截；
        # 标准库内部的传递导入（如 typing/json 内部 import sys）放行。
        _st = _extract_stack()
        # _st[-1] 是 _safe_import 自身所在帧，_st[-2] 是发起 import 的帧
        if len(_st) >= 2 and _st[-2].filename == __file__:
            raise ImportError(f"Module '{base}' is not allowed in sandbox")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _safe_import

# 用户代码开始
''' + user_code + '''
# 用户代码结束
'''
    return wrapper


# ========== 执行引擎 ==========

MAX_OUTPUT_SIZE = 64 * 1024  # 64KB 输出上限


def run_python_code(
    code: str,
    timeout_seconds: int = 5,
    stdin_input: Optional[str] = None,
) -> CodeRunResult:
    """在子进程中安全执行 Python 代码。

    安全策略：
    1. AST 静态分析 — 编译前拦截危险代码
    2. 运行时包装 — 删除危险内置函数、劫持 __import__
    3. 子进程隔离 — 超时杀死、输出截断
    """
    # 1. 静态安全检查
    violations = static_check(code)
    if violations:
        return CodeRunResult(
            stdout="",
            stderr="安全沙箱拦截:\n" + "\n".join(f"  - {v}" for v in violations),
            exit_code=-2,
            duration_ms=0,
            timed_out=False,
        )

    # 2. 包装代码
    wrapped_code = _wrap_code(code)

    # 3. 写入临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(wrapped_code)
        temp_path = f.name

    try:
        start_time = time.time()

        # Windows 特定的进程隔离标志
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            [sys.executable, temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            **kwargs,
        )

        try:
            stdout, stderr = proc.communicate(input=stdin_input, timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            # 先尝试优雅终止
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                # 强制杀死
                if sys.platform == "win32":
                    import signal
                    os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
                else:
                    proc.kill()
                stdout, stderr = proc.communicate()
            timed_out = True

        duration_ms = int((time.time() - start_time) * 1000)

        # 截断超长输出
        if len(stdout) > MAX_OUTPUT_SIZE:
            stdout = stdout[:MAX_OUTPUT_SIZE] + f"\n... [输出截断，超过 {MAX_OUTPUT_SIZE} 字节上限]"
        if len(stderr) > MAX_OUTPUT_SIZE:
            stderr = stderr[:MAX_OUTPUT_SIZE] + f"\n... [错误输出截断，超过 {MAX_OUTPUT_SIZE} 字节上限]"

        return CodeRunResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode if not timed_out else -1,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )

    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


# ========== 在线判题（运行测试用例） ==========

_JUDGE_HARNESS = r"""
import json as _json

class _LNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class _TNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

_ctx = {}

def _build_linked(vals):
    head = None
    tail = None
    nodes = []
    for v in vals:
        n = _LNode(v)
        nodes.append(n)
        if head is None:
            head = n
        else:
            tail.next = n
        tail = n
    _ctx['list_nodes'] = nodes
    return head

def _build_cycle(vals, pos):
    head = _build_linked(vals)
    nodes = _ctx['list_nodes']
    if nodes and 0 <= pos < len(nodes):
        nodes[-1].next = nodes[pos]
    return head

def _build_tree(vals):
    if not vals:
        return None
    nodes = [_TNode(v) if v is not None else None for v in vals]
    _ctx['tree_nodes'] = [n for n in nodes if n is not None]
    kids = nodes[1:]
    for node in nodes:
        if node is not None and kids:
            node.left = kids.pop(0)
            if kids:
                node.right = kids.pop(0)
    return nodes[0]

def _build_intersect(spec):
    headA = _build_linked(spec['ilistA'])
    nodesA = list(_ctx['list_nodes'])
    skipA = spec.get('skipA', 0)
    skipB = spec.get('skipB', 0)
    bvals = spec['ilistB'][:skipB]
    headB = _build_linked(bvals)
    nodesB = list(_ctx['list_nodes'])
    if 0 <= skipA < len(nodesA):
        if nodesB:
            nodesB[-1].next = nodesA[skipA]
        else:
            headB = nodesA[skipA]
    return headA, headB

def _ser(x):
    if x is None:
        return None
    if hasattr(x, 'left') or hasattr(x, 'right'):
        out = []
        q = [x]
        while q:
            n = q.pop(0)
            if n is None:
                out.append(None)
            else:
                out.append(n.val)
                q.append(n.left)
                q.append(n.right)
        while out and out[-1] is None:
            out.pop()
        return out
    if hasattr(x, 'val') or hasattr(x, 'next'):
        out = []
        seen = set()
        while x is not None:
            if id(x) in seen:
                break
            seen.add(id(x))
            out.append(x.val)
            x = x.next
        return out
    return x

def _norm(x):
    if isinstance(x, list):
        return sorted((_norm(i) for i in x), key=repr)
    return x

_UNORD = __UNORD__
_EPS = __EPS__
_INPLACE = __INPLACE__
_FN = __FN__
_DESIGN = __DESIGN__
_TESTS = _json.loads(__TESTS_JSON__)

def _close(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-5
    except (TypeError, ValueError):
        return False

def _eq(got, exp):
    if _EPS and isinstance(exp, (int, float)) and not isinstance(exp, bool):
        return _close(got, exp)
    if _EPS and isinstance(exp, list):
        if not isinstance(got, list) or len(got) != len(exp):
            return False
        return all(_eq(g, e) for g, e in zip(got, exp))
    if _UNORD and isinstance(got, list) and isinstance(exp, list):
        return _norm(got) == _norm(exp)
    return got == exp

def _build_arg(a):
    if isinstance(a, dict):
        if 'ilistA' in a:
            return _build_intersect(a)
        if 'list' in a:
            return _build_linked(a['list'] or [])
        if 'clist' in a:
            return _build_cycle(a['clist'] or [], a.get('pos', -1))
        if 'lists' in a:
            return [_build_linked(v or []) for v in a['lists']]
        if 'tree' in a:
            return _build_tree(a['tree'] or [])
        if 'tval' in a:
            for n in _ctx.get('tree_nodes', []):
                if n.val == a['tval']:
                    return n
            return None
    return a

def _check_expected(exp, got):
    if isinstance(exp, dict):
        if 'list' in exp:
            gv = _ser(got)
            return _eq(gv if gv is not None else [], exp['list'] or [])
        if 'tree' in exp:
            gv = _ser(got)
            return _eq(gv if gv is not None else [], exp['tree'] or [])
        if 'cpos' in exp:
            pos = exp['cpos']
            nodes = _ctx.get('list_nodes', [])
            want = nodes[pos] if 0 <= pos < len(nodes) else None
            return got is want
        if 'tval' in exp:
            return got is not None and hasattr(got, 'val') and got.val == exp['tval']
    return _eq(got, exp)

def _display(v):
    v = _ser(v)
    try:
        return _json.dumps(v, ensure_ascii=False)
    except TypeError:
        return repr(v)

_results = []

if _DESIGN:
    cls = globals()[_DESIGN['cls']]
    for case in _TESTS:
        obj = cls(*_DESIGN.get('init', []))
        got_list = []
        error = None
        try:
            for op, opargs in zip(case['ops'], case['opargs']):
                got_list.append(obj.__class__.__dict__[op](obj, *opargs))
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        exp_list = case['expected']
        ok = error is None and len(got_list) == len(exp_list) and all(
            (e is None and g is None) or _eq(g, e) for g, e in zip(got_list, exp_list)
        )
        _results.append({
            'input': _json.dumps({'ops': case['ops'], 'opargs': case['opargs']}, ensure_ascii=False),
            'expected': _json.dumps(exp_list, ensure_ascii=False),
            'actual': error or _json.dumps(got_list, ensure_ascii=False, default=str),
            'ok': ok,
        })
else:
    for case in _TESTS:
        args = []
        for a in case['args']:
            built = _build_arg(a)
            if isinstance(built, tuple):
                args.extend(built)
            else:
                args.append(built)
        try:
            got = Solution.__dict__[_FN](Solution(), *args)
            if _INPLACE:
                got = args[0]
            ok = _check_expected(case['expected'], got)
            actual = _display(got)
        except Exception as e:
            ok = False
            actual = f"{type(e).__name__}: {e}"
        _results.append({
            'input': _json.dumps(case['args'], ensure_ascii=False),
            'expected': _json.dumps(case['expected'], ensure_ascii=False),
            'actual': actual,
            'ok': ok,
        })

print("__JUDGE__" + _json.dumps(_results, ensure_ascii=False))
"""


def build_judge_script(user_code: str, function_name: str, spec: dict) -> str:
    """拼接用户代码与判题 harness，生成可执行脚本。"""
    harness = (
        _JUDGE_HARNESS
        .replace("__UNORD__", repr(bool(spec.get("unord"))))
        .replace("__EPS__", repr(bool(spec.get("eps"))))
        .replace("__INPLACE__", repr(bool(spec.get("inplace"))))
        .replace("__FN__", repr(function_name))
        .replace("__DESIGN__", repr(spec.get("design")))
        .replace("__TESTS_JSON__", repr(json.dumps(spec.get("tests", []), ensure_ascii=False)))
    )
    return user_code + "\n" + harness


@dataclass
class JudgeResult:
    passed: int
    total: int
    cases: list
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    sandbox_blocked: bool = False


def run_problem_tests(
    code: str,
    function_name: str,
    spec: dict,
    timeout_seconds: int = 15,
) -> JudgeResult:
    """在沙箱中运行用户代码并逐用例判题。"""
    import json as _json

    if not spec.get("tests"):
        return JudgeResult(
            passed=0, total=0, cases=[],
            stdout="", stderr="本题暂无测试用例", duration_ms=0,
        )

    script = build_judge_script(code, function_name, spec)
    result = run_python_code(script, timeout_seconds=timeout_seconds)

    judge_line = None
    rest_stdout = []
    for line in result.stdout.splitlines():
        if line.startswith("__JUDGE__"):
            judge_line = line[len("__JUDGE__"):]
        else:
            rest_stdout.append(line)

    if judge_line is None:
        return JudgeResult(
            passed=0,
            total=len(spec["tests"]),
            cases=[],
            stdout="\n".join(rest_stdout),
            stderr=result.stderr or "判题进程未产生结果（可能存在语法错误或超时）",
            duration_ms=result.duration_ms,
            timed_out=result.timed_out,
            sandbox_blocked=(result.exit_code == -2),
        )

    try:
        cases = _json.loads(judge_line)
    except _json.JSONDecodeError:
        cases = []

    passed = sum(1 for c in cases if c.get("ok"))
    return JudgeResult(
        passed=passed,
        total=len(cases),
        cases=cases,
        stdout="\n".join(rest_stdout),
        stderr=result.stderr,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
    )


def run_acm_tests(
    code: str,
    io_tests: list[dict],
    timeout_seconds: int = 15,
) -> JudgeResult:
    """ACM 模式判题：完整程序逐用例运行，stdin 喂入、比对 stdout。

    io_tests: [{"stdin": "...", "stdout": "..."}]
    比对规则：忽略首尾空白与行尾空格（宽松比对）。
    """
    import time as _time

    if not io_tests:
        return JudgeResult(
            passed=0, total=0, cases=[],
            stdout="", stderr="本题暂无 ACM 测试用例", duration_ms=0,
        )

    def norm(s: str) -> str:
        return "\n".join(line.rstrip() for line in (s or "").strip().splitlines())

    cases = []
    passed = 0
    total_ms = 0
    t0 = _time.time()
    for t in io_tests:
        expected = t.get("stdout", "")
        stdin_data = t.get("stdin", "")
        result = run_python_code(code, timeout_seconds=timeout_seconds, stdin_input=stdin_data)
        total_ms += result.duration_ms
        if result.exit_code == -2:
            return JudgeResult(
                passed=passed, total=len(io_tests), cases=cases,
                stdout="", stderr="代码被安全沙箱拦截",
                duration_ms=total_ms, sandbox_blocked=True,
            )
        if result.timed_out:
            cases.append({"input": stdin_data, "expected": expected, "actual": "(超时)", "ok": False})
            continue
        if result.exit_code != 0:
            err = (result.stderr or "运行错误").strip().splitlines()
            cases.append({"input": stdin_data, "expected": expected, "actual": err[-1] if err else "运行错误", "ok": False})
            continue
        ok = norm(result.stdout) == norm(expected)
        passed += 1 if ok else 0
        cases.append({
            "input": stdin_data,
            "expected": expected,
            "actual": result.stdout.strip(),
            "ok": ok,
        })

    return JudgeResult(
        passed=passed, total=len(io_tests), cases=cases,
        stdout="", stderr="", duration_ms=total_ms,
    )
