"""Enforce repo conventions for Python test syntax under `tests/`.

Currently enforced:
- Pytest tests must not be defined as module-level `def test_*` functions; tests should
  live under `class Test...:` blocks. Fixtures and helper functions may remain at module
  scope.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    name: str


def _iter_python_test_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("test_*.py")))
        else:
            if p.name.startswith("test_") and p.suffix == ".py":
                files.append(p)
    # Deterministic output
    return sorted({f.resolve() for f in files})


def _find_module_level_test_functions(path: Path) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: list[Violation] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("test_"):
            violations.append(Violation(path=path, lineno=node.lineno, name=node.name))
    return violations


def main(argv: list[str]) -> int:
    raw_paths = argv[1:] if len(argv) > 1 else ["tests"]
    paths = [Path(p) for p in raw_paths]

    files = _iter_python_test_files(paths)
    all_violations: list[Violation] = []
    for f in files:
        all_violations.extend(_find_module_level_test_functions(f))

    if not all_violations:
        print("OK: no module-level test_* functions found")
        return 0

    for v in all_violations:
        rel = v.path
        try:
            rel = v.path.relative_to(Path.cwd())
        except ValueError:
            pass
        print(
            f"{rel}:{v.lineno} module-level test function '{v.name}' is not allowed; "
            "wrap in class Test...:"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
