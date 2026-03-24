---
description: Release guardrails — local reset E2E in CI, startup logging, runbook updates.
tags: [deployment, ci, e2e, sqlite, observability, runbooks]
---

# Release guardrails, observability, and mandatory local reset E2E

## Overview

After deploy-bootstrap and shared fixture seeding are in place, this work **codifies** how releases are verified and makes regressions visible: documentation carries a single checklist operators can follow, logs answer “which DB,” “which revision,” and “did reset/seed run,” and **CI** runs an **end-to-end** check that mirrors production data setup: **fresh SQLite → Alembic → fixture seed → real HTTP server → contract smoke**. The E2E uses a **temporary** `SIM_DB_PATH` (not the developer `LOCAL=true` dummy file) so it is safe for parallel CI and does not require `LOCAL=true`.

**Explicitly out of scope:** a pre-commit hook for this E2E (too slow and noisy per team preference). Developers run `uv run pytest tests/api/test_simulation_local_reset_e2e.py` locally when touching the relevant surface area.

## Happy Flow

1. **Disposable DB reset (test setup):** In a pytest module, set `SIM_DB_PATH` to a path under `tmp_path`, ensure `LOCAL` is unset, delete the SQLite cluster, call `initialize_database()` then `seed_database_from_fixtures_if_needed(db_path=...)`—same logical sequence as `simulation/bootstrap/railway.py` after file removal (without Railway marker/env).
2. **Start real server:** Spawn `uvicorn simulation.api.main:app` via `subprocess` with `PYTHONPATH`, `DISABLE_AUTH=1`, `SIM_DB_PATH`, ephemeral port. Poll `GET /health` until 200 or timeout.
3. **HTTP assertions:** `GET /health`, `/v1/simulations/metrics`, `/v1/simulations/feed-algorithms`, `/v1/simulations/runs` (nonempty lists, 200), then run detail + turns for first `run_id` (align assertions with fixture content; fix fixtures if red).
4. **Teardown:** Terminate uvicorn subprocess cleanly.
5. **Manual operator path:** Document `LOCAL=true` + `LOCAL_RESET_DB=1` from `docs/runbooks/UPDATE_SEED_DATA.md` for human exploration; E2E does not wipe `db/dev_dummy_data_db.sqlite`.
6. **Logging:** INFO logs for resolved DB path, Alembic revision after init, seed/bootstrap path taken (no secrets).

## Data Flow

- Test → temp filesystem (`SIM_DB_PATH`) → `initialize_database` (Alembic) → `seed_database_from_fixtures_if_needed` → subprocess `uvicorn` → loopback HTTP client → assertions.

## Manual Verification

- `uv run pytest tests/api/test_simulation_local_reset_e2e.py -q` passes locally.
- `uv run pytest tests/api/test_simulation_smoke.py -q` still skips without `SIMULATION_API_URL`.
- `uv run pytest` full suite green when the default CI matrix skips E2E (use dedicated workflow for E2E on relevant paths).
- `uv run python scripts/check_docs_metadata.py` on edited `docs/runbooks/*.md`.
- Manual: `LOCAL=true LOCAL_RESET_DB=1` + uvicorn; curl health, metrics, feed-algorithms, runs; fix fixtures if empty.
- Confirm a PR that **only** changes excluded paths does not run the E2E job (if using path filters), and a PR touching `simulation/**` does run it.

## Implementation notes (this PR)

- **CI:** `.github/workflows/ci-e2e.yml` — path filters on `pull_request`; full run on `push` to `main`/`master`; `workflow_dispatch`; weekly `schedule`. Env `RUN_LOCAL_RESET_E2E=1` enables the E2E test under GitHub Actions.
- **Test skip in matrix:** `tests/api/test_simulation_local_reset_e2e.py` skips when `GITHUB_ACTIONS=true` and `RUN_LOCAL_RESET_E2E` is unset, so `uv run pytest` in the default matrix does not start uvicorn.
