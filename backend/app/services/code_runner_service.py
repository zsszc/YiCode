"""
代码安全沙箱 — Phase 5.2
基于 AST 静态分析 + 子进程隔离的代码执行环境。

安全层级：
1. 静态分析（AST）— 编译前拦截危险代码
2. 运行时包装 — 删除危险内置函数、劫持 __import__
3. 子进程隔离 — 超时杀死、输出截断
"""

import ast
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
        """为 AST 节点添加 _parent 引用，辅助判断节点上下文。"""
        node._parent = parent
        for child in ast.iter_child_nodes(node):
            self._add_parents(child, node)
        """检查代码，返回违规列表（空列表表示安全）。"""
        self.violations = []
        try:
            tree = ast.parse(source)
            self.visit(tree)
        except SyntaxError as e:
            self.violations.append(f"语法错误: {e}")
        return self.violations

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

# 保存 __import__ 引用（在删除前先保存）
_original_import = __import__

# 禁止危险内置函数
_banned_builtins = ''' + repr(BANNED_BUILTINS) + '''
for name in _banned_builtins:
    if name in dir(builtins):
        try:
            delattr(builtins, name)
        except AttributeError:
            pass

# 禁止危险模块导入
_banned_modules = ''' + repr(BANNED_IMPORTS) + '''

def _safe_import(name, *args, **kwargs):
    base = name.split('.')[0]
    if base in _banned_modules:
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
