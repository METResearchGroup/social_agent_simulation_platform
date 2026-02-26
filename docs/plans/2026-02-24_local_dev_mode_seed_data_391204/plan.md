---
description: Plan to enable LOCAL=true for auto auth bypass and forced dummy DB seeded from JSON fixtures.
tags: [plan, local, auth, seed, dev]
---

# LOCAL=true Local Dev Mode: Forced Dummy DB + Seed Fixtures

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Title
`LOCAL=true` Local Dev Mode: Forced Dummy DB + Auto Auth Bypass + Backend Seed Fixtures + Seed Update Runbook

## Plan Output Location (this change)
- Plan doc: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/plan.md`
- UI screenshots:
  - Before: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/before/`
  - After: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/after/`

## Overview
Introduce a single local dev mode flag (`LOCAL=true`) that makes local development “just work” by (1) bypassing auth in both backend and frontend automatically, and (2) forcing the backend to use a clearly-named local SQLite DB (`db/dev_dummy_data_db.sqlite`) populated from committed JSON seed fixtures (including runs with turn metrics + run metrics). Treat the JSON fixtures as the canonical seed source (edit fixtures directly; retire Python dummy data + generator script).

## Goals / Success Criteria
- `LOCAL=true` is the only required switch to:
  - bypass auth in backend + frontend (no Supabase setup, no `.env.local` edits required)
  - make the UI usable immediately with seeded runs/posts/feeds/agents and runs that include metrics
- Backend uses and clearly logs that it is using: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite`
- Seed data is deterministic, committed as JSON fixtures in backend, and loaded into the dummy DB automatically (seed-once policy).
- Seed fixture update workflow is documented and actionable (edit JSON fixtures directly; reset/reseed and verify).

## Non-Goals (this iteration)
- Persisting per-agent action-event rows (current DB schema does not store agent actions; we’ll return empty `agent_actions` in seeded `TurnSchema` for now).
- Production seeding (local only, with fail-fast guards).

## Locked Decisions
- `LOCAL=true` **always** forces the dummy DB file (`/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite`) even if `SIM_DB_PATH` is set; `SIM_DB_PATH` is ignored in local mode.
- When `SIM_DB_PATH` is provided but `LOCAL=true`, log a warning that `LOCAL` overrides it.
- Seeding policy: seed once when DB is unseeded/empty; preserve developer-modified dummy DB unless explicitly reset.
- Seed storage: JSON fixtures (committed) are canonical and edited directly (no generator script).

## Public Interfaces / Behavior Changes

### Environment variables
- Backend + Frontend
  - `LOCAL=true` (truthy values: `1|true|yes`, case-insensitive)
- Backend-only
  - `LOCAL_RESET_DB=1` (optional): deletes `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite` at startup and re-seeds

### Backend DB path behavior (forced in local mode)
- File: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/adapters/sqlite/sqlite.py`
- `get_db_path()` precedence:
  1. If `LOCAL=true`: return `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite` (always)
     - If `SIM_DB_PATH` is set, emit log warning: `LOCAL=true overrides SIM_DB_PATH; using db/dev_dummy_data_db.sqlite`
  2. Else if `SIM_DB_PATH` is set: use it
  3. Else: existing default `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/db.sqlite`

### Backend auth bypass behavior
- File: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/api/dependencies/auth.py`
- Treat `LOCAL=true` as equivalent to `DISABLE_AUTH=1` for bypass logic.
- Maintain (and extend) existing production guard so bypass cannot be enabled in production-like environments.

### Frontend auth bypass behavior (automatic when local)
- File: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/next.config.ts`
- If `LOCAL=true`, inject `NEXT_PUBLIC_DISABLE_AUTH=true` into Next.js runtime env so `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/contexts/AuthContext.tsx` bypasses auth automatically.
- Fail-fast: if building with `NODE_ENV=production` and `LOCAL=true`, throw to prevent accidental insecure builds.

## Backend routes must be DB-backed (no more dummy routes for core UI flows)
Rewired these from `simulation/api/dummy_data.py` to DB reads so local mode validates real routes:
- `GET /v1/simulations/runs`
- `GET /v1/simulations/runs/{run_id}`
- `GET /v1/simulations/runs/{run_id}/turns`
- `GET /v1/simulations/posts`

All simulation agent reads now go through `GET /v1/simulations/agents` (DB-backed).

## Happy Flow (end-to-end with file references)
1. Developer starts backend with `LOCAL=true`.
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/adapters/sqlite/sqlite.py#get_db_path()` returns `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite` and logs override if `SIM_DB_PATH` was set.
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/api/main.py` lifespan runs:
     - `disallow_auth_bypass_in_production()` + `disallow_local_mode_in_production()` guards
     - `initialize_database()` (migrations targeted at the forced dummy DB)
     - `seed_local_db_if_needed(db_path=get_db_path())` (seed-once; writes fixtures into the dummy DB)
2. Developer starts frontend with `LOCAL=true`.
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/next.config.ts` injects `NEXT_PUBLIC_DISABLE_AUTH=true`.
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/contexts/AuthContext.tsx` bypasses auth and sets a mock dev user.
3. UI loads and hits real API routes:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/lib/api/simulation.ts#getRuns()` → backend returns seeded DB runs.
   - Selecting a run triggers `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/lib/api/simulation.ts#getTurnsForRun()` → backend returns `TurnSchema` built from DB `generated_feeds` (and empty `agent_actions`).
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/components/details/DetailsPanel.tsx` calls `getPosts(uris)` → backend returns posts from DB `bluesky_feed_posts`.
   - `GET /v1/simulations/runs/{run_id}` returns turn metrics + run metrics from DB (`turn_metrics`, `run_metrics`) so metrics-dependent UI changes can be tested.

## Data Model & Seed Fixtures (DB tables covered)
Seed fixtures cover at least:
- runs + status + metric_keys
- turn_metadata (so builtin metrics can compute)
- turn_metrics (precomputed)
- run_metrics (precomputed)
- generated_feeds (turn hydration for UI)
- bluesky_feed_posts (post hydration for UI)
- agent tables used by `/v1/simulations/agents` (so “View agents” works in local mode):
  - agent
  - agent_persona_bios
  - user_agent_profile_metadata

Fixture location (committed):
- `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/local_dev/seed_fixtures/*.json`

Dummy DB forced path:
- `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite`

## Implementation Steps (done)
1. Take **before** screenshots of UI happy flow:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/before/01-runs-list.png`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/before/02-run-summary.png`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/before/03-turn-detail.png`
2. Add local mode detection + production guard:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/lib/env_utils.py`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/local_dev/local_mode.py`
3. Force dummy DB in local mode + override logging and migration correctness:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/adapters/sqlite/sqlite.py`
4. Implement seed fixture loader (seed-once + reset flag):
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/local_dev/seed_loader.py`
   - Fixtures: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/local_dev/seed_fixtures/`
5. Wire seed loader into FastAPI startup:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/api/main.py`
6. Rewire routes to DB-backed reads (routes thin; services do the work):
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/api/routes/simulation.py`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/api/services/run_query_service.py`
7. Frontend: auto auth bypass from `LOCAL=true`:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/next.config.ts`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui/contexts/AuthContext.tsx`
8. Documentation:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/runbooks/UPDATE_SEED_DATA.md`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/runbooks/LOCAL_DEVELOPMENT.md`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/runbooks/LOCAL_DEV_AUTH.md`
9. Tests (pytest):
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/tests/local_dev/test_local_mode_seed.py`
10. Take **after** screenshots of UI happy flow:
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/after/01-runs-list.png`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/after/02-run-summary.png`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/after/03-turn-detail.png`
   - `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/plans/2026-02-24_local_dev_mode_seed_data_391204/images/after/04-seeded-run-metrics.png` (API response proof: seeded `run_metrics` + per-turn `metrics`)
11. Follow-up: retire Python dummy sources and seed generator (JSON fixtures canonical):
   - Remove: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/api/dummy_data.py`
   - Remove: `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/scripts/update_seed_data.py`
   - Remove `GET /v1/simulations/agents/mock` (no dummy/legacy endpoints)

## Manual Verification (checklist)
- Backend startup (local mode)
  - Install deps: `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && uv sync --extra test`
  - Start API: `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && LOCAL=true PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000`
  - Health check: open `http://localhost:8000/health` → expected `{"status":"ok"}`
  - Verify forced DB path:
    - `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && python -c "import os; os.environ['LOCAL']='true'; from db.adapters.sqlite.sqlite import get_db_path; print(get_db_path())"`
    - Expected output ends with: `/db/dev_dummy_data_db.sqlite`
  - Verify seeded runs:
    - `curl -s http://localhost:8000/v1/simulations/runs | jq 'length'` → expected `> 0`
  - Verify seeded metrics exist (pick a run id from runs list):
    - `curl -s http://localhost:8000/v1/simulations/runs/<RUN_ID> | jq '.run_metrics'` → expected non-null
- Frontend startup (local mode)
  - Start UI: `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui && LOCAL=true npm run dev`
  - Open `http://localhost:3000`
  - Confirm:
    - no sign-in screen
    - run history shows runs
    - selecting a run loads turns and posts without errors
- Reset & reseed
  - Stop backend
  - Restart with: `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && LOCAL=true LOCAL_RESET_DB=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000`
  - Confirm runs list matches deterministic fixtures again
- Tests
  - `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && uv run pytest`
    - Expected: `>= 571 passed, 2 skipped` (current observed: `575 passed, 2 skipped, 3 warnings in ~8s`)
- Optional quality gates
  - `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && uv run ruff check .` → expected `All checks passed!`
  - `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && uv run pyright .` → expected `0 errors, 0 warnings, 0 informations`
  - `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform/ui && npm run lint:all` → expected success (oxlint may emit warnings)

## `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/docs/runbooks/UPDATE_SEED_DATA.md` (required contents)
- When to update seed data (new API fields, new tables, new UI expectations, new metric keys)
- How to update fixtures (JSON is canonical):
  - Edit JSON fixtures directly in `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/simulation/local_dev/seed_fixtures/*.json`
  - Reset local dummy DB: restart backend with `LOCAL=true LOCAL_RESET_DB=1 ...` to force reseed
- How to validate:
  - run backend with `LOCAL=true` and verify endpoints
  - run `cd /Users/mark/.codex/worktrees/710f/agent_simulation_platform && uv run pytest`
- How to reset dummy DB:
  - `LOCAL=true LOCAL_RESET_DB=1 ...`
- Explicit statement: `LOCAL=true` always uses `/Users/mark/.codex/worktrees/710f/agent_simulation_platform/db/dev_dummy_data_db.sqlite` and ignores `SIM_DB_PATH`.

## Alternative Approaches Considered
- Commit a binary `seed.sqlite`: faster but poor diffs/review; rejected.
- Keep dummy API endpoints forever: doesn’t validate real DB/API wiring; rejected.
- Allow `SIM_DB_PATH` override in local mode: increases confusion; rejected in favor of forced dummy DB + explicit logs.

## Assumptions
- UI can proceed with empty `agent_actions` in turns until we add an action-event persistence table.
- Seed data volume is modest; for `GET /v1/simulations/posts` without `uris`, enforce a safe limit + deterministic sort (documented and tested).
