"""
静态代码诊断服务 — 为编辑器提供波浪线/hover 诊断数据

不依赖第三方 linter，基于 ast 实现一组对刷题场景高价值、低误报的检查：
- 语法错误（精确行列）
- 可能未定义的变量（作用域感知，保守策略）
- 可变默认参数 def f(x=[])
- == None / == True / == False 比较
- 裸 except
- 函数体只有 pass（未实现提醒）
- print 调试输出提醒
"""

from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass, asdict


@dataclass
class Diagnostic:
    line: int          # 1-based
    col: int           # 0-based
    end_line: int
    end_col: int
    severity: str      # error | warning | info
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


BUILTIN_NAMES = set(dir(builtins)) | {"self", "cls"}


def lint_python(code: str) -> list[dict]:
    """对 Python 代码做静态诊断，返回诊断列表。"""
    diagnostics: list[Diagnostic] = []

    # 1) 语法错误
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        line = e.lineno or 1
        col = (e.offset - 1) if e.offset else 0
        diagnostics.append(Diagnostic(
            line=line, col=col,
            end_line=e.end_lineno or line,
            end_col=(e.end_offset - 1) if e.end_offset else col + 1,
            severity="error",
            message=f"语法错误: {e.msg}",
        ))
        return [d.to_dict() for d in diagnostics]

    # 2) AST 启发式检查
    checker = _HeuristicChecker(diagnostics)
    checker.visit(tree)

    # 3) 未定义名字（保守）
    undef = _UndefinedNameChecker(tree)
    diagnostics.extend(undef.check())

    diagnostics.sort(key=lambda d: (d.line, d.col))
    return [d.to_dict() for d in diagnostics]


class _HeuristicChecker(ast.NodeVisitor):
    """扫描常见编码问题。"""

    def __init__(self, out: list[Diagnostic]):
        self.out = out

    def _add(self, node: ast.AST, severity: str, message: str):
        self.out.append(Diagnostic(
            line=getattr(node, "lineno", 1),
            col=getattr(node, "col_offset", 0),
            end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            end_col=getattr(node, "end_col_offset", getattr(node, "col_offset", 0) + 1),
            severity=severity,
            message=message,
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node):
        # 可变默认参数
        defaults = list(node.args.defaults) + list(node.args.kw_defaults)
        for d in defaults:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                self._add(d, "warning", "可变对象作为默认参数会在多次调用间共享，建议用 None 并在函数体内初始化")
        # 只有 pass 的函数
        body = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            self._add(node, "info", f"函数 {node.name} 还没有实现（只有 pass）")

    def visit_Compare(self, node: ast.Compare):
        for op, comp in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comp, ast.Constant):
                if comp.value is None:
                    sug = "is not None" if isinstance(op, ast.NotEq) else "is None"
                    self._add(node, "warning", f"与 None 比较建议用 `{sug}` 而不是 ==/!=")
                elif isinstance(comp.value, bool):
                    self._add(node, "info", "与布尔值直接 == 比较是多余的，建议直接用它做条件")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self._add(node, "warning", "裸 except 会吞掉所有异常（包括键盘中断），建议写明异常类型")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self._add(node, "info", "print 调试输出：本地调试没问题，正式提交前记得删掉")
        self.generic_visit(node)


class _Scope:
    def __init__(self, parent: "_Scope | None" = None):
        self.parent = parent
        self.defined: set[str] = set()
        self.globals: set[str] = set()  # 声明为 global 的名字

    def is_visible(self, name: str) -> bool:
        scope: _Scope | None = self
        while scope is not None:
            if name in scope.defined:
                return True
            scope = scope.parent
        return False


class _UndefinedNameChecker(ast.NodeVisitor):
    """保守的未定义名字检查：宁可漏报，不误报。"""

    def __init__(self, tree: ast.AST):
        self.tree = tree
        self.issues: list[Diagnostic] = []
        self.module_scope = _Scope()
        self.scope = self.module_scope

    def check(self) -> list[Diagnostic]:
        # 第一趟：收集模块级定义（顺序无关）
        for node in ast.iter_child_nodes(self.tree):
            self._collect_defs(node, self.module_scope)
        # 第二趟：检查引用
        self.visit(self.tree)
        return self.issues

    # ---- 定义收集 ----
    def _collect_defs(self, node: ast.AST, scope: _Scope):
        """把语句引入的名字登记进 scope。"""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.defined.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                self._bind_target(t, scope)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            self._bind_target(node.target, scope)
        elif isinstance(node, ast.Import):
            for a in node.names:
                scope.defined.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                scope.defined.add(a.asname or a.name)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            self._bind_target(node.target, scope)
            for child in node.body + node.orelse:
                self._collect_defs(child, scope)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars:
                    self._bind_target(item.optional_vars, scope)
            for child in node.body:
                self._collect_defs(child, scope)
        elif isinstance(node, ast.If):
            # if/else 两个分支里的赋值都可能生效，保守起见都收集
            for child in node.body + node.orelse:
                self._collect_defs(child, scope)
        elif isinstance(node, (ast.Try, ast.TryStar)):
            for child in node.body + node.orelse + node.finalbody:
                self._collect_defs(child, scope)
            for h in node.handlers:
                if h.name:
                    scope.defined.add(h.name)
                for child in h.body:
                    self._collect_defs(child, scope)
        elif isinstance(node, (ast.While,)):
            for child in node.body + node.orelse:
                self._collect_defs(child, scope)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.NamedExpr):
            self._bind_target(node.value.target, scope)

    def _bind_target(self, t: ast.AST, scope: _Scope):
        if isinstance(t, ast.Name):
            scope.defined.add(t.id)
        elif isinstance(t, (ast.Tuple, ast.List)):
            for e in t.elts:
                self._bind_target(e, scope)
        elif isinstance(t, ast.Starred):
            self._bind_target(t.value, scope)

    def _bind_args(self, args: ast.arguments, scope: _Scope):
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            scope.defined.add(a.arg)
        if args.vararg:
            scope.defined.add(args.vararg.arg)
        if args.kwarg:
            scope.defined.add(args.kwarg.arg)

    # ---- 引用检查 ----
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            if (
                node.id not in BUILTIN_NAMES
                and not self.scope.is_visible(node.id)
                # 函数内引用的名字可能被 global 声明到模块级，上面 is_visible 已覆盖
            ):
                self.issues.append(Diagnostic(
                    line=node.lineno, col=node.col_offset,
                    end_line=node.end_lineno or node.lineno,
                    end_col=node.end_col_offset or node.col_offset + len(node.id),
                    severity="warning",
                    message=f"`{node.id}` 可能未定义（检查拼写或是否忘记赋值/导入）",
                ))
        # 不 generic_visit：Name 没有子节点

    def visit_Global(self, node: ast.Global):
        # global 声明的名字视作模块级可见（若模块级已定义则没问题；没定义也会漏掉，保守放行）
        for n in node.names:
            self.scope.globals.add(n)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def _visit_function(self, node):
        # 默认参数与装饰器在当前作用域求值
        for d in list(node.args.defaults) + [x for x in node.args.kw_defaults if x]:
            self.visit(d)
        for dec in node.decorator_list:
            self.visit(dec)

        func_scope = _Scope(parent=self.scope)
        self._bind_args(node.args, func_scope)
        # 收集函数体内所有局部定义（顺序无关，保守）
        for stmt in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and stmt is not node:
                # 嵌套定义的名字属于当前函数作用域
                func_scope.defined.add(stmt.name)
        for stmt in node.body:
            self._collect_defs(stmt, func_scope)
        # comprehension / lambda 内部变量
        for sub in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(sub, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                for gen in sub.generators:
                    self._bind_target(gen.target, func_scope)
            elif isinstance(sub, ast.Lambda):
                self._bind_args(sub.args, func_scope)

        outer = self.scope
        self.scope = func_scope
        for stmt in node.body:
            self.visit(stmt)
        self.scope = outer

    def visit_ClassDef(self, node: ast.ClassDef):
        for dec in node.decorator_list:
            self.visit(dec)
        for base in node.bases:
            self.visit(base)
        class_scope = _Scope(parent=self.scope)
        for stmt in node.body:
            self._collect_defs(stmt, class_scope)
        outer = self.scope
        self.scope = class_scope
        for stmt in node.body:
            self.visit(stmt)
        self.scope = outer

    def visit_Lambda(self, node: ast.Lambda):
        lam_scope = _Scope(parent=self.scope)
        self._bind_args(node.args, lam_scope)
        outer = self.scope
        self.scope = lam_scope
        self.visit(node.body)
        self.scope = outer

    def _visit_comp(self, node):
        comp_scope = _Scope(parent=self.scope)
        for gen in node.generators:
            self._bind_target(gen.target, comp_scope)
        outer = self.scope
        self.scope = comp_scope
        for gen in node.generators:
            self.visit(gen.iter)
            for cond in gen.ifs:
                self.visit(cond)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self.scope = outer

    def visit_ListComp(self, node):
        self._visit_comp(node)

    def visit_SetComp(self, node):
        self._visit_comp(node)

    def visit_GeneratorExp(self, node):
        self._visit_comp(node)

    def visit_DictComp(self, node):
        self._visit_comp(node)
