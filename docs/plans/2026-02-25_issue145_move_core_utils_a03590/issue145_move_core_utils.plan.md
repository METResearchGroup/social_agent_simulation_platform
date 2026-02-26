---
name: Issue #145 — Relocate simulation.core utilities into simulation/core/utils/
overview: "Relocate simulation/core/{exceptions,validators,handle_utils}.py into simulation/core/utils/ and update all internal imports accordingly. This is a pure refactor (no behavioral changes) but is an intentional breaking change for external consumers because we will not keep backwards-compatible shims at the old import paths."
todos:
  - id: plan-assets-dir
    content: Create plan assets folder `docs/plans/2026-02-25_issue145_move_core_utils_a03590/` and save this plan.
    status: completed
  - id: move-modules
    content: Move `simulation/core/{exceptions,validators,handle_utils}.py` into `simulation/core/utils/` using `git mv`.
    status: completed
  - id: update-imports
    content: Update all internal imports from `simulation.core.{exceptions,validators,handle_utils}` to `simulation.core.utils.{exceptions,validators,handle_utils}`.
    status: completed
  - id: update-exports-docs
    content: Update `simulation/core/__init__.py` exports and update `db/exceptions.py` docstring to reference new paths.
    status: completed
  - id: verification
    content: Run `uv sync --extra test`, `uv run ruff check .`, `uv run pyright .`, and `uv run pytest` (targeted then full). Ensure `rg` finds no remaining old imports.
    status: completed
isProject: false
---

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview
We will relocate three general-purpose modules—`simulation/core/exceptions.py`, `simulation/core/validators.py`, and `simulation/core/handle_utils.py`—into the existing package `simulation/core/utils/`, then update all internal import sites to the new module paths. This is a pure refactor (no behavioral changes), but it is an intentional breaking change for any external consumers importing the old paths since we will not keep backwards-compatible shims.

## Public API / interface changes (breaking)
- Removed import paths (no shims kept):
  - `simulation.core` + `.exceptions` -> `simulation.core.utils.exceptions`
  - `simulation.core` + `.validators` -> `simulation.core.utils.validators`
  - `simulation.core` + `.handle_utils` -> `simulation.core.utils.handle_utils`
- `simulation/core/__init__.py` will be updated to re-export `SimulationError` / `InsufficientAgentsError` from the new location.

## Happy Flow
1. Callers that previously did `from simulation.core` + `.exceptions import RunNotFoundError` now import from `simulation.core.utils.exceptions`.
2. Callers that previously did `from simulation.core` + `.validators import validate_run_id` (and `validate_turn_number`) now import from `simulation.core.utils.validators`.
3. Callers that previously did `from simulation.core` + `.handle_utils import normalize_handle` now import from `simulation.core.utils.handle_utils`.
4. The moved modules keep identical symbol names/behavior; only module locations change.
5. All tests and typechecks pass, and `rg` shows no remaining imports from the old module paths.

## Manual Verification
- `cd /Users/mark/.codex/worktrees/266e/agent_simulation_platform`
- `uv sync --extra test`
- `uv run ruff check .`
- `uv run pyright .`
- `uv run pytest tests/test_validation_decorators.py -v`
- `uv run pytest tests/simulation/core/test_command_service.py -v`
- `uv run pytest tests/db/repositories/test_run_repository.py -v`
- `uv run pytest`
- `rg -n "simulation\\.core\\.(exceptions|validators|handle_utils)" -S .` (expect: 0 matches)

## Alternative approaches
- Keep shims at `simulation/core/{exceptions,validators,handle_utils}.py` re-exporting from `simulation/core/utils/*`: rejected because this change is intended to break old import paths and avoid duplication.
