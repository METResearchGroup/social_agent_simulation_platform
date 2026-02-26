# Agent Instructions (Repository Guide)

This file is for AI agents and humans working in this repo. It points to the canonical runbooks and captures a few repo-specific conventions so work stays consistent.

## Start here (docs)

- Documentation index: `docs/README.md`
- Repo rules + conventions: `docs/RULES.md`

If you’re unsure how to do something (local dev, deployment, linting, smoke tests), check `docs/runbooks/` before inventing new workflows.

## Docs metadata

- Every Markdown file under `docs/runbooks/` and `docs/plans/` must ship YAML front matter with `description` and `tags`. Run `uv run python scripts/check_docs_metadata.py [paths]` to verify any document locally—the default behavior targets `docs/runbooks/` and `docs/plans/`, but you can pass explicit files or directories (pre-commit hooks do this automatically). Missing metadata blocks fail the docs-metadata CI job and the new pre-commit hook, so rerun the script (or `uv run pre-commit run docs-metadata`) before landing doc changes.

## Local development (default)

Canonical runbooks:

- Local API dev: `docs/runbooks/LOCAL_DEVELOPMENT.md`
- Local auth options (bypass vs real OAuth): `docs/runbooks/LOCAL_DEV_AUTH.md`

Common commands (repo root):

- Install deps (Python): `uv sync --extra test`
- Run API (reload): `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
- Health check: `http://localhost:8000/health` (OpenAPI: `http://localhost:8000/docs`)

UI (Next.js) lives in `ui/`:

- Dev server: `cd ui && npm run dev`
- Lint (all): `cd ui && npm run lint:all`

### Local auth guidance (important)

Use `docs/runbooks/LOCAL_DEV_AUTH.md` for the authoritative steps.

- Auth bypass (local only):
  - Backend: set `DISABLE_AUTH=1` when starting the API.
  - Frontend: set `NEXT_PUBLIC_DISABLE_AUTH=true` in `ui/.env.local`.
- Do **not** enable these flags in production or commit them to the repo.

## Database + migrations (SQLite + Alembic)

Canonical reference: `db/migrations/README`

Key gotchas:

- Alembic config is in `pyproject.toml`; always run Alembic with `-c pyproject.toml`.
- DB location can be overridden via `SIM_DB_PATH` (path) or `SIM_DATABASE_URL` (SQLAlchemy URL, takes precedence).

## Quality gates (Python)

Canonical runbook: `docs/runbooks/PRE_COMMIT_AND_LINTING.md`

Preferred commands:

- Pre-commit (repo rule): `uv run pre-commit run --all-files`
- Ruff: `uv run ruff check .` and `uv run ruff format .`
- Pyright: `uv run pyright .`
- Tests: `uv run pytest`

### Writing Python tests

Use the canonical runbook when adding or updating Python tests:

- `docs/runbooks/CREATE_NEW_PYTHON_TESTS.md` (factories + Hypothesis + `uv run pytest`)

Smoke tests against a running server:

- Runbook: `docs/runbooks/SMOKE_TEST.md`
- Command: `SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py`

## Plans

Implementation plans live in `docs/plans/`.

## Architecture conventions (high-signal highlights)

See `docs/RULES.md` for the full set. A few that commonly matter during edits:

- Use **dependency injection** (avoid instantiating concrete infra inside business logic).
- Keep FastAPI routes **thin** (validation + dependency wiring + service call).
- Prefer **absolute imports**.
- Keep domain models (`simulation.core.models`) “pure” (no imports from `db/`, `feeds/`, `ai/`, etc.).
- Put interfaces next to implementations in `interfaces.py` at the package level (e.g. `feeds/interfaces.py`).
