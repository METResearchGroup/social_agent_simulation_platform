---
description: Enforce class-based pytest tests by migrating module-level tests and adding a linter with pre-commit/CI gates (issue #195).
tags: [plan, testing, pytest, lint, ci, pre-commit]
---

# Issue #195: Enforce Class-Based Pytest Tests

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview
Migrate remaining module-level `test_*` functions to class-based pytest tests, then enforce the convention in pre-commit and CI so regressions fail fast.

## Happy Flow
1. Run `uv run python scripts/lint_python_testing_syntax_conventions.py` (see `scripts/lint_python_testing_syntax_conventions.py`) to detect module-level test functions under `tests/`.
2. If violations exist, refactor the listed modules under `tests/**/test_*.py` by moving `def test_*` into `class Test...:` blocks (fixtures and helpers remain at module scope).
3. Run `uv run pytest` to confirm the suite still passes.
4. Run `uv run pre-commit run --all-files` to ensure the new hook (`python_testing_syntax_conventions` in `.pre-commit-config.yaml`) passes.
5. Confirm GitHub Actions runs the dedicated job (`python_testing_syntax_conventions` in `.github/workflows/ci.yml`) to prevent regressions.

## Data Flow
1. Developer adds/edits tests under `tests/`.
2. Pre-commit and CI invoke `scripts/lint_python_testing_syntax_conventions.py` which AST-parses `tests/**/test_*.py`.
3. If any module-level `test_*` functions exist, the linter exits non-zero and prints file:line diagnostics.
4. After refactor, the linter prints `OK: no module-level test_* functions found` and exits `0`.

## Manual Verification
- [ ] `uv sync --extra test`
- [ ] `uv run python scripts/lint_python_testing_syntax_conventions.py`
  - Expected (after migration): exits `0` and prints `OK: no module-level test_* functions found`.
- [ ] `uv run pytest tests/lint/test_lint_python_testing_syntax_conventions.py`
- [ ] `uv run pytest`
- [ ] `uv run pre-commit run --all-files`

## Alternative Approaches
- Use Ruff plugin/custom rule: not chosen because it increases maintenance burden and provides less repo-specific diagnostics.
- Fold into `scripts/lint_architecture.py`: not chosen to avoid mixing unrelated lint concerns.
