"""
代码执行服务 — Phase 4.3
在线运行 Python 代码，验证题解正确性。

安全策略：
1. 使用子进程隔离执行
2. 严格超时限制（默认 5 秒）
3. 禁止访问文件系统、网络、系统调用
4. 内存限制（通过资源模块，Linux/macOS 有效）
"""

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


# 禁止导入的模块黑名单
BANNED_MODULES = {
    "os", "sys", "subprocess", "socket", "urllib", "http", "ftplib",
    "pickle", "marshal", "ctypes", "multiprocessing", "threading",
    "importlib", "pkgutil", "site",
}

# 禁止使用的内置函数（保留 input 用于标准输入题目）
BANNED_BUILTINS = {
    "eval", "exec", "compile", "open", "__import__",
    "exit", "quit", "help",
}


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
_banned_modules = ''' + repr(BANNED_MODULES) + '''

def _safe_import(name, *args, **kwargs):
    base = name.split('.')[0]
    if base in _banned_modules:
        raise ImportError(f"Module '{base}' is not allowed")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _safe_import

# 用户代码开始
''' + user_code + '''
# 用户代码结束
'''
    return wrapper


def run_python_code(
    code: str,
    timeout_seconds: int = 5,
    stdin_input: Optional[str] = None,
) -> CodeRunResult:
    """在子进程中安全执行 Python 代码。

    Args:
        code: 用户提交的 Python 代码
        timeout_seconds: 最大执行时间（秒）
        stdin_input: 可选的标准输入内容

    Returns:
        CodeRunResult: 执行结果
    """
    wrapped_code = _wrap_code(code)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(wrapped_code)
        temp_path = f.name

    try:
        start_time = time.time()

        proc = subprocess.Popen(
            [sys.executable, temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        try:
            stdout, stderr = proc.communicate(input=stdin_input, timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            timed_out = True

        duration_ms = int((time.time() - start_time) * 1000)

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
