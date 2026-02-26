"""Architecture linter for dependency injection and layering rules.

This script enforces DI-related rules from docs/RULES.md as mechanically-checkable
guards in pre-commit and CI.

Output format (one per violation):
  path:line:col [PY-x] message
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

COMPOSITION_ROOT_PREFIXES: tuple[str, ...] = (
    "simulation/core/factories/",
    "simulation/api/main.py",
    "db/",
    "jobs/",
    "simulation/local_dev/",
    "tests/",
)

INTERFACE_FILE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "db/adapters/base.py",
        "ml_tooling/llm/providers/base.py",
        "tests/factories/base.py",
    }
)

DEPENDENCY_NAME_SUFFIXES: tuple[str, ...] = (
    "_repo",
    "_provider",
    "_adapter",
    "_service",
    "_client",
    "_executor",
)

DEPENDENCY_MODULE_PREFIXES: tuple[str, ...] = (
    "db.",
    "feeds.",
    "ml_tooling.",
)

PY8_PATH_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Orchestration layer is allowed to compose services.
        "simulation/core/engine.py",
    }
)


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    col: int
    rule: str
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}:{self.col} [{self.rule}] {self.message}"


def _is_composition_root(path: str) -> bool:
    p = path.replace("\\", "/")
    if p in {"simulation/api/main.py"}:
        return True
    return any(p.startswith(prefix) for prefix in COMPOSITION_ROOT_PREFIXES)


def _is_in_core_non_factory(path: str) -> bool:
    p = path.replace("\\", "/")
    if not p.startswith("simulation/core/"):
        return False
    return not p.startswith("simulation/core/factories/")


def _posix(path: str) -> str:
    return path.replace("\\", "/")


def _dependency_shaped_name(name: str) -> bool:
    return any(name.endswith(suffix) for suffix in DEPENDENCY_NAME_SUFFIXES)


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def _callee_name(call: ast.Call) -> str | None:
    fn = call.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


def _git_ls_files_py() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "*.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return [f for f in files if not _posix(f).startswith("docs/plans/")]


@dataclass
class ImportTable:
    # Maps local name -> fully-qualified symbol, e.g. AgentRepository -> db.repositories.interfaces.AgentRepository
    symbols: dict[str, str]
    # Maps local module alias -> fully-qualified module, e.g. sqlite -> sqlite3
    modules: dict[str, str]


def _build_import_table(tree: ast.AST) -> ImportTable:
    symbols: dict[str, str] = {}
    modules: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[-1]
                modules[local] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            module = node.module
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                symbols[local] = f"{module}.{alias.name}"
    return ImportTable(symbols=symbols, modules=modules)


def _iter_function_params(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterable[ast.arg]:
    args = fn.args
    for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
        yield a


def _arg_default_map(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, ast.AST | None]:
    """Return param name -> default node (or None if no default)."""
    args = fn.args
    positional = list(args.posonlyargs) + list(args.args)
    defaults = list(args.defaults)
    mapping: dict[str, ast.AST | None] = {}

    # Align trailing defaults to positional args.
    if defaults:
        for arg, default in zip(positional[-len(defaults) :], defaults, strict=True):
            mapping[arg.arg] = default

    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
        mapping[arg.arg] = default

    return mapping


def _is_none_literal(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _optional_union_members(annotation: ast.expr) -> list[ast.expr] | None:
    """Return union members if annotation is a PEP604 union, else None."""

    # For PEP 604 unions: A | B is ast.BinOp(BitOr).
    def flatten(n: ast.expr) -> list[ast.expr] | None:
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            left = flatten(n.left)
            right = flatten(n.right)
            if left is None or right is None:
                return None
            return left + right
        return [n]

    members = flatten(annotation)
    if members is None or len(members) < 2:
        return None
    return members


def _is_optional_annotation(
    annotation: ast.expr, imports: ImportTable
) -> tuple[bool, list[ast.expr]]:
    """Return (is_optional, non_none_types)."""
    union = _optional_union_members(annotation)
    if union is not None:
        non_none = [m for m in union if not _is_none_literal(m)]
        is_opt = len(non_none) != len(union)
        return (is_opt, non_none)

    # typing.Optional[T] or Optional[T]
    if isinstance(annotation, ast.Subscript):
        value = annotation.value
        if isinstance(value, ast.Name):
            name = value.id
            resolved = imports.symbols.get(name, name)
            if (
                resolved.endswith(".Optional")
                or resolved == "Optional"
                or name == "Optional"
            ):
                inner = annotation.slice
                if isinstance(inner, ast.Tuple):
                    types = list(inner.elts)
                else:
                    types = [inner]
                return (True, types)
        if isinstance(value, ast.Attribute) and value.attr == "Optional":
            inner = annotation.slice
            if isinstance(inner, ast.Tuple):
                types = list(inner.elts)
            else:
                types = [inner]
            return (True, types)

        # Union[T, None]
        if isinstance(value, ast.Name):
            name = value.id
            resolved = imports.symbols.get(name, name)
            if resolved.endswith(".Union") or resolved == "Union" or name == "Union":
                inner = annotation.slice
                elts: list[ast.expr]
                if isinstance(inner, ast.Tuple):
                    elts = list(inner.elts)
                else:
                    elts = [inner]
                non_none = [e for e in elts if not _is_none_literal(e)]
                is_opt = len(non_none) != len(elts)
                return (is_opt, non_none)
        if isinstance(value, ast.Attribute) and value.attr == "Union":
            inner = annotation.slice
            elts = list(inner.elts) if isinstance(inner, ast.Tuple) else [inner]
            non_none = [e for e in elts if not _is_none_literal(e)]
            is_opt = len(non_none) != len(elts)
            return (is_opt, non_none)

    return (False, [annotation])


def _attribute_name_parts(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        parent = _attribute_name_parts(node.value)
        if parent:
            return parent + [node.attr]
        return [node.attr]
    return []


def _annotation_type_names(annotation: ast.expr) -> list[str]:
    """Extract full dotted type names from an annotation expression."""
    names: list[str] = []

    def visit(n: ast.expr) -> None:
        if isinstance(n, ast.Name):
            names.append(n.id)
        elif isinstance(n, ast.Attribute):
            parts = _attribute_name_parts(n)
            if parts:
                names.append(".".join(parts))
        elif isinstance(n, ast.Subscript):
            visit(n.value)
            slice_node = n.slice
            if isinstance(slice_node, ast.Tuple):
                for e in slice_node.elts:
                    visit(e)
            else:
                visit(slice_node)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            visit(n.left)
            visit(n.right)
        elif isinstance(n, ast.Tuple):
            for e in n.elts:
                visit(e)
        elif isinstance(n, ast.Call):
            visit(n.func)
            for arg in n.args:
                visit(arg)
        else:
            for child in ast.iter_child_nodes(n):
                if isinstance(child, ast.expr):
                    visit(child)

    visit(annotation)
    return names


def _resolve_dotted_name(name: str, imports: ImportTable) -> str:
    if "." in name:
        root, rest = name.split(".", 1)
        module_base = imports.modules.get(root)
        if module_base:
            return f"{module_base}.{rest}"
    symbol = imports.symbols.get(name)
    if symbol:
        return symbol
    return name


def _resolved_modules_for_type_names(
    type_names: Iterable[str], imports: ImportTable
) -> set[str]:
    modules: set[str] = set()
    for name in type_names:
        resolved = _resolve_dotted_name(name, imports)
        if "." in resolved:
            modules.add(resolved.rsplit(".", 1)[0])
        else:
            modules.add(resolved)
    return modules


def _looks_like_dependency_by_module(
    imports: ImportTable, annotation: ast.expr
) -> bool:
    type_names = _annotation_type_names(annotation)
    modules = _resolved_modules_for_type_names(type_names, imports)
    return any(
        any(m.startswith(prefix) for prefix in DEPENDENCY_MODULE_PREFIXES)
        for m in modules
    )


def _find_py5_interfaces(
    path: str, tree: ast.AST, imports: ImportTable
) -> list[Violation]:
    p = _posix(path)
    if p.startswith("tests/"):
        return []
    if p.endswith("/interfaces.py") or p.endswith("interfaces.py"):
        return []
    if p in INTERFACE_FILE_ALLOWLIST:
        return []

    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            # ABC via Name('ABC') or Attribute(abc, 'ABC')
            if isinstance(base, ast.Name) and base.id == "ABC":
                violations.append(
                    Violation(
                        path=path,
                        line=node.lineno,
                        col=node.col_offset + 1,
                        rule="PY-5",
                        message=(
                            f"Interface '{node.name}' must live in interfaces.py "
                            f"(or allowlisted base interface module)."
                        ),
                    )
                )
                break
            if isinstance(base, ast.Attribute) and base.attr == "ABC":
                violations.append(
                    Violation(
                        path=path,
                        line=node.lineno,
                        col=node.col_offset + 1,
                        rule="PY-5",
                        message=(
                            f"Interface '{node.name}' must live in interfaces.py "
                            f"(or allowlisted base interface module)."
                        ),
                    )
                )
                break
            # Protocol via Name('Protocol') or Attribute(typing, 'Protocol')
            if isinstance(base, ast.Name) and base.id == "Protocol":
                violations.append(
                    Violation(
                        path=path,
                        line=node.lineno,
                        col=node.col_offset + 1,
                        rule="PY-5",
                        message=(
                            f"Interface '{node.name}' must live in interfaces.py "
                            f"(or allowlisted base interface module)."
                        ),
                    )
                )
                break
            if isinstance(base, ast.Attribute) and base.attr == "Protocol":
                violations.append(
                    Violation(
                        path=path,
                        line=node.lineno,
                        col=node.col_offset + 1,
                        rule="PY-5",
                        message=(
                            f"Interface '{node.name}' must live in interfaces.py "
                            f"(or allowlisted base interface module)."
                        ),
                    )
                )
                break

    return violations


def _find_py7_module_level_wiring(path: str, tree: ast.Module) -> list[Violation]:
    if _is_composition_root(path):
        return []
    violations: list[Violation] = []

    def is_banned_call(call: ast.Call) -> tuple[bool, str]:
        callee = _callee_name(call)
        if callee is None:
            return (False, "")
        if callee == "SqliteTransactionProvider":
            return (True, callee)
        if callee.startswith("create_sqlite_"):
            return (True, callee)
        if callee == "get_llm_service":
            return (True, callee)
        if re.match(r"^SQLite.+Adapter$", callee):
            return (True, callee)
        return (False, callee)

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value if isinstance(node, ast.AnnAssign) else node.value
            if isinstance(value, ast.Call):
                banned, callee = is_banned_call(value)
                if banned:
                    violations.append(
                        Violation(
                            path=path,
                            line=node.lineno,
                            col=node.col_offset + 1,
                            rule="PY-7",
                            message=(
                                f"Module-level wiring via '{callee}(...)' is not allowed "
                                "outside composition roots."
                            ),
                        )
                    )

        # Also catch `x: T = call()` in AnnAssign above.

    return violations


def _find_py3_factory_only_defaults(
    path: str, tree: ast.AST, imports: ImportTable
) -> list[Violation]:
    if _is_composition_root(path):
        return []
    violations: list[Violation] = []

    # Pattern 1: x = x or call(...)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr]
            value: ast.AST | None
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
                value = node.value
            else:
                targets = [node.target]
                value = node.value
            if value is None:
                continue

            for target in targets:
                if not isinstance(target, (ast.Name, ast.Attribute)):
                    continue
                target_name = target.id if isinstance(target, ast.Name) else target.attr

                if isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or):
                    # Look for: <name> or <call> with same name.
                    has_same_name = any(
                        isinstance(v, ast.Name) and v.id == target_name
                        for v in value.values
                    )
                    has_call = any(isinstance(v, ast.Call) for v in value.values)
                    if (
                        has_same_name
                        and has_call
                        and _dependency_shaped_name(target_name)
                    ):
                        violations.append(
                            Violation(
                                path=path,
                                line=node.lineno,
                                col=node.col_offset + 1,
                                rule="PY-3",
                                message=(
                                    "Dependency fallback defaulting is not allowed outside "
                                    "composition roots; require the dependency and default it "
                                    "only in factories."
                                ),
                            )
                        )

                # Pattern 2: target = x if x is not None else call(...)
                if isinstance(value, ast.IfExp) and isinstance(value.test, ast.Compare):
                    cmp = value.test
                    if (
                        isinstance(cmp.left, ast.Name)
                        and len(cmp.ops) == 1
                        and isinstance(cmp.ops[0], ast.IsNot)
                        and len(cmp.comparators) == 1
                        and _is_none_literal(cmp.comparators[0])
                    ):
                        dep_name = cmp.left.id
                        if (
                            _dependency_shaped_name(dep_name)
                            and isinstance(value.body, ast.Name)
                            and value.body.id == dep_name
                            and isinstance(value.orelse, ast.Call)
                        ):
                            violations.append(
                                Violation(
                                    path=path,
                                    line=node.lineno,
                                    col=node.col_offset + 1,
                                    rule="PY-3",
                                    message=(
                                        "Dependency fallback defaulting is not allowed outside "
                                        "composition roots; require the dependency and default it "
                                        "only in factories."
                                    ),
                                )
                            )

    # Pattern 3: if x is None: x = call(...)
    class IfVisitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:  # noqa: N802
            if (
                isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.Is)
                and len(node.test.comparators) == 1
                and _is_none_literal(node.test.comparators[0])
            ):
                dep_name = node.test.left.id
                if _dependency_shaped_name(dep_name):
                    for stmt in node.body:
                        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                            target = (
                                stmt.targets[0]
                                if isinstance(stmt, ast.Assign)
                                else stmt.target
                            )
                            value = (
                                stmt.value
                                if isinstance(stmt, ast.Assign)
                                else stmt.value
                            )
                            if (
                                isinstance(target, ast.Name)
                                and target.id == dep_name
                                and isinstance(value, ast.Call)
                            ):
                                violations.append(
                                    Violation(
                                        path=path,
                                        line=stmt.lineno,
                                        col=stmt.col_offset + 1,
                                        rule="PY-3",
                                        message=(
                                            "Dependency fallback defaulting is not allowed outside "
                                            "composition roots; require the dependency and default it "
                                            "only in factories."
                                        ),
                                    )
                                )
            self.generic_visit(node)

    IfVisitor().visit(tree)
    return violations


def _find_py6_optional_infra_deps(
    path: str, tree: ast.AST, imports: ImportTable
) -> list[Violation]:
    if _is_composition_root(path):
        return []
    violations: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        default_map = _arg_default_map(node)
        for arg in _iter_function_params(node):
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                continue
            default = default_map.get(arg.arg)
            if not _is_none_literal(default):
                continue

            is_optional, non_none_types = _is_optional_annotation(
                arg.annotation, imports
            )
            if not is_optional:
                continue

            looks_like_dep = _dependency_shaped_name(
                arg.arg
            ) or _looks_like_dependency_by_module(imports, arg.annotation)
            if not looks_like_dep:
                continue

            violations.append(
                Violation(
                    path=path,
                    line=arg.lineno,
                    col=arg.col_offset + 1,
                    rule="PY-6",
                    message=(
                        f"Optional dependency '{arg.arg}: {_safe_unparse(arg.annotation)} = None' "
                        "is not allowed outside composition roots; require the dependency and "
                        "apply defaults only in factories."
                    ),
                )
            )

    return violations


def _find_py8_service_to_service_in_core(
    path: str, tree: ast.AST, imports: ImportTable
) -> list[Violation]:
    if _posix(path) in PY8_PATH_ALLOWLIST:
        return []
    if not _is_in_core_non_factory(path):
        return []
    violations: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        default_map = _arg_default_map(node)
        for arg in _iter_function_params(node):
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                continue

            # Only care about dependency-shaped params.
            if not _dependency_shaped_name(arg.arg):
                continue

            is_optional, non_none = _is_optional_annotation(arg.annotation, imports)
            # PY-8 is about type edges, not optionality; check all non-None types.
            type_names: list[str] = []
            for t in non_none:
                type_names.extend(_annotation_type_names(t))

            for type_name in type_names:
                if not type_name.endswith("Service"):
                    continue
                resolved = imports.symbols.get(type_name)
                if resolved is None:
                    continue
                mod = resolved.rsplit(".", 1)[0]
                if mod.startswith("simulation.core.") or mod.startswith(
                    "simulation.api.services."
                ):
                    violations.append(
                        Violation(
                            path=path,
                            line=arg.lineno,
                            col=arg.col_offset + 1,
                            rule="PY-8",
                            message=(
                                f"Service-to-service injection in core is not allowed: "
                                f"param '{arg.arg}: {type_name}'. Depend on ports "
                                "(*Repository/*Provider/*Adapter) and orchestrate at a higher layer."
                            ),
                        )
                    )
                    break

            # Silence unused default_map for future extension.
            _ = default_map

    return violations


def _find_py9_concrete_infra_type_hints(
    path: str, tree: ast.AST, imports: ImportTable
) -> list[Violation]:
    if _is_composition_root(path):
        return []
    violations: list[Violation] = []

    def is_concrete_infra_type_name(type_name: str) -> bool:
        if type_name.startswith(("Sqlite", "SQLite")):
            return True
        if type_name.endswith("Adapter") and "SQLite" in type_name:
            return True
        return False

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for arg in _iter_function_params(node):
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                continue
            if not _dependency_shaped_name(arg.arg):
                continue
            is_optional, non_none = _is_optional_annotation(arg.annotation, imports)
            _ = is_optional
            type_names: list[str] = []
            for t in non_none:
                type_names.extend(_annotation_type_names(t))
            concrete = [n for n in type_names if is_concrete_infra_type_name(n)]
            if concrete:
                violations.append(
                    Violation(
                        path=path,
                        line=arg.lineno,
                        col=arg.col_offset + 1,
                        rule="PY-9",
                        message=(
                            f"Concrete infra types not allowed in dependency annotations: "
                            f"param '{arg.arg}: {_safe_unparse(arg.annotation)}' "
                            f"(concrete: {', '.join(sorted(set(concrete)))})."
                        ),
                    )
                )

    return violations


def lint_file(path: str, source: str) -> tuple[int, list[Violation]]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        v = Violation(
            path=path,
            line=getattr(e, "lineno", 1) or 1,
            col=(getattr(e, "offset", 0) or 0) + 1,
            rule="PY-LINT",
            message=f"Failed to parse file: {e.msg}",
        )
        return (1, [v])

    imports = _build_import_table(tree)
    violations: list[Violation] = []

    if isinstance(tree, ast.Module):
        violations.extend(_find_py7_module_level_wiring(path, tree))

    violations.extend(_find_py3_factory_only_defaults(path, tree, imports))
    violations.extend(_find_py5_interfaces(path, tree, imports))
    violations.extend(_find_py6_optional_infra_deps(path, tree, imports))
    violations.extend(_find_py8_service_to_service_in_core(path, tree, imports))
    violations.extend(_find_py9_concrete_infra_type_hints(path, tree, imports))

    return (0, violations)


def main(argv: list[str]) -> int:
    _ = argv
    files = _git_ls_files_py()
    all_violations: list[Violation] = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            all_violations.append(
                Violation(
                    path=path,
                    line=1,
                    col=1,
                    rule="PY-LINT",
                    message=f"Failed to read file: {e}",
                )
            )
            continue
        _, violations = lint_file(path, source)
        all_violations.extend(violations)

    if all_violations:
        for v in sorted(
            all_violations,
            key=lambda x: (PurePosixPath(_posix(x.path)), x.line, x.col, x.rule),
        ):
            print(v.format())
        return 1

    print(f"OK ({len(files)} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
