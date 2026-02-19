---
description: Pre-commit hooks and code quality tools (Ruff, Pyright, complexipy) for Python.
tags: [pre-commit, linting, ruff, pyright, complexipy, code-quality]
---

# Pre-commit and Linting Runbook

This runbook covers pre-commit hooks and code quality tools (Ruff, Pyright, complexipy).

## Pre-commit

Install hooks so Ruff, complexipy, and pyright run before each commit:

```bash
pre-commit install
```

Run on all files:

```bash
pre-commit run --all-files
```

## Ruff (lint and format)

- **Lint:** `uv run ruff check .` (use `--fix` to auto-fix where possible).
- **Format:** `uv run ruff format .` (or `ruff format --check` for CI).

## Pyright (type checking)

```bash
uv run pyright .
```

## complexipy (cognitive complexity)

[complexipy](https://github.com/rohaquinlop/complexipy) reports **cognitive complexity** per function and module: how hard code is to follow (nesting, control flow), not just branch count. Use it to find good refactor targets.

- **Run:** `uv run complexipy .` or `uv run complexipy path/to/file.py`. CI runs it only on changed Python files.
- **Interpret:** Higher scores mean more complex code. Focus refactors on high-complexity functions.
- **Optional threshold:** `uv run complexipy . --max-complexity-allowed 10` (exits non-zero if any function exceeds the limit).
- **Config:** You can add `[tool.complexipy]` in `pyproject.toml` for excludes or defaults if the tool supports it; otherwise use CLI flags. CI treats complexipy as diagnostic (no threshold by default) so the build stays green while you review the report.
