# Proposed fixes: prod breakage, deployment skew, and deterministic SQLite (Proposal A)

This document captures the **initial problem**, **diagnosis**, and **chosen direction (Proposal A)** from the March 2026 investigation, including the requirement to **always reuse the JSON fixtures** under `simulation/local_dev/seed_fixtures/`.

---

## 1. Initial problem (symptoms)

Observed on the production UI ([Vercel](https://ui-iota-eight.vercel.app/)) against the production API ([Railway](https://agent-simulation-platform-production.up.railway.app)):

- **404** on `GET /v1/simulations/metrics`
- **404** on `GET /v1/simulations/feed-algorithms`
- **404** / “Run not found” when loading run details for a sample run such as `run_2025-01-17T08:20:00`
- Console: `Failed to fetch metrics: ApiError: {"detail":"Not Found"}` (same shape for feed algorithms)
- **Frontend crash:** `Uncaught TypeError: n.postIds is not iterable` (minified bundle; corresponds to UI code that iterates `feed.postIds` after mapping API feeds)

The user also suspected **SQLite drift** in prod (ephemeral or partially migrated DB, out of sync with expectations).

---

## 2. Diagnosis

### 2.1 Deployment / contract skew (primary)

The live backend’s OpenAPI at `/openapi.json` was inspected and showed an **older API contract** than the current repository and UI:

- Routes **`/v1/simulations/metrics`** and **`/v1/simulations/feed-algorithms`** were **missing** from the published OpenAPI — so **404s are literal “route not implemented”**, not missing seed rows. Those endpoints are **code-defined** and do not depend on database content.
- Turn payloads used **`post_uris`** in `FeedSchema`, while the current UI expects **`post_ids`** (mapped in `ui/lib/api/simulation.ts` as `postIds: apiFeed.post_ids`). That mismatch explains **`postIds is not iterable`** when the client maps `undefined` or wrong-shaped JSON.
- **Inconsistency on the same run id:** `GET /v1/simulations/runs` listed `run_2025-01-17T08:20:00`, but **`GET /v1/simulations/runs/{run_id}`** could return **404** while **`GET /v1/simulations/runs/{run_id}/turns`** still returned data — indicating an **older or inconsistent backend build/state**, not a single clear “SQLite only” story.

**Conclusion:** The dominant issue is **frontend/backend version skew** (Vercel UI newer than Railway API, or wrong API URL on Vercel). **Resetting SQLite alone does not fix missing routes.**

### 2.2 SQLite and seeding (secondary but real)

In the current codebase:

- **Auto-seeding** from fixtures runs only when **`LOCAL=true`** (see `simulation/api/main.py` lifespan: `seed_local_db_if_needed` after `initialize_database`).
- **Production** runs **`initialize_database()`** (Alembic to head) but **does not** automatically load `simulation/local_dev/seed_fixtures/` unless we add an explicit prod policy.
- Local seed policy is **seed-once** keyed by fixture digest (`local_seed_meta.fixtures_sha256` in `simulation/local_dev/seed_loader.py`); changing fixtures requires **`LOCAL_RESET_DB=1`** locally — that is a **developer** workflow, not Railway’s default.

So: **SQLite can drift or be empty/partial** on prod (volume issues, old migrations, manual edits). That can cause **missing runs** or odd list vs detail behavior **once** the API version matches the repo. It does **not** explain **404 on metrics/feed-algorithms**.

### 2.3 Mapping to code (reference)

- Metadata routes (current repo): `simulation/api/routes/metadata.py` — `GET /simulations/metrics`, `GET /simulations/feed-algorithms` (mounted under `/v1` in `simulation/api/main.py`).
- Lifespan: `simulation/api/main.py` — local-only seed after migrations.
- Seed loader + fixtures: `simulation/local_dev/seed_loader.py`, directory `simulation/local_dev/seed_fixtures/`.
- SQLite path: `db/adapters/sqlite/sqlite.py` — `SIM_DB_PATH` in non-local mode; Railway runbook recommends a persistent volume (e.g. `SIM_DB_PATH=/data/db.sqlite`) — see `docs/runbooks/RAILWAY_DEPLOYMENT.md`.

---

## 3. Chosen direction: **Proposal A**

**Proposal A — Ship parity first, then deterministic prod data (`reset_on_deploy`)**

1. **Single release unit:** Deploy **the same Git revision** to Vercel (UI) and Railway (API). No long-lived mismatch between “UI build” and “API build.”
2. **Short term:** Fix **deployment skew** so the UI and API speak the **same contract** (OpenAPI matches generated/types and runtime behavior).
3. **Prod data:** Implement **`reset_on_deploy`**: on each **deploy**, recreate or clear the SQLite file, run migrations, then **seed from the canonical JSON fixtures** under `simulation/local_dev/seed_fixtures/`.
4. **Tradeoff:** User-created records in prod are **lost on every deploy**; the demo stays **consistent** and aligned with committed fixtures.

**Fixture requirement (explicit):** Always reuse the **existing JSON fixtures** under `simulation/local_dev/seed_fixtures/` (same source as local mode), invoked via the existing loader (`seed_local_db_if_needed` or a thin wrapper that calls the same `_load_fixtures` / insert path) so local and prod demo data stay **one source of truth**.

---

## 4. Step-by-step implementation plan (Proposal A)

### Phase 1 — Fix skew (do this first)

1. Pick a **single Git ref** (e.g. `main` at commit SHA or release tag) as **production**.
2. **Redeploy Railway** from that ref so `/openapi.json` includes:
   - `GET /v1/simulations/metrics`
   - `GET /v1/simulations/feed-algorithms`
   - `FeedSchema` / turns using **`post_ids`** (or UI updated if you intentionally keep old names — current repo uses `post_ids`).
3. **Redeploy Vercel** from the **same ref**.
4. Confirm **Vercel env:** `NEXT_PUBLIC_SIMULATION_API_URL` points to the **canonical** Railway URL (no stale preview or old service).
5. **Smoke-check** (browser or curl):
   - `GET /health` → 200
   - `GET /v1/simulations/metrics` → 200 + JSON array
   - `GET /v1/simulations/feed-algorithms` → 200 + JSON array
   - Pick a seeded `run_id` from `GET /v1/simulations/runs` and verify `GET /v1/simulations/runs/{run_id}` and `.../turns` both succeed and UI loads without `postIds` errors.

### Phase 2 — `reset_on_deploy` + fixtures (prod)

1. **Entrypoint script** (recommended) used by Docker/Railway instead of bare `uvicorn`:
   - On **deploy** (see note below on “deploy vs restart”):
     - Remove SQLite file at `SIM_DB_PATH` (or empty all app tables if you prefer truncate — file delete is simpler for SQLite).
     - Run **`initialize_database()`** / `alembic upgrade head` (same as today).
     - Call seeding that loads **`simulation/local_dev/seed_fixtures/*.json`** via the same code path as local (`seed_local_db_if_needed` or refactor to `seed_db_from_fixtures(db_path=..., fixtures_dir=FIXTURES_DIR)` with **no** `LOCAL=true` requirement for the loader itself — only for “which DB path” if you currently gate behavior).
   - Start **`uv run uvicorn simulation.api.main:app ...`** as today (`Dockerfile` `CMD`).

2. **Deploy detection (Railway):** Prefer resetting only when the **deployment id** or **git SHA** changes (e.g. compare `RAILWAY_DEPLOYMENT_ID` or `GIT_COMMIT` to a small marker file on the volume such as `/data/.last_deploy_id`) so **random restarts** do not wipe the DB. If you accept wiping on every process start, you can simplify — at the cost of surprise data loss on restarts.

3. **Idempotency:** After `reset_on_deploy`, seed should run on an **empty** DB; the existing digest logic in `seed_local_db_if_needed` can remain (first run seeds; digest stored). Alternatively, for prod-only, **always** run full seed after file delete (simplest).

4. **Environment variables:** Keep `SIM_DB_PATH` on the persistent volume path documented in `docs/runbooks/RAILWAY_DEPLOYMENT.md`. Add a clear flag e.g. `SEED_ON_START=1` or `RESET_DB_ON_DEPLOY=1` so prod behavior is explicit.

5. **Security / local:** Do **not** enable prod reset flags in local dev; keep `LOCAL=true` + `LOCAL_RESET_DB=1` for developer resets per `docs/runbooks/UPDATE_SEED_DATA.md`.

### Phase 3 — Regression prevention

1. **Extend smoke tests** (`tests/api/test_simulation_smoke.py` or a new prod-oriented test) to assert:
   - `GET /v1/simulations/metrics` — 200
   - `GET /v1/simulations/feed-algorithms` — 200
   - Optional: one seeded run id has consistent list / details / turns
2. **CI or scheduled job:** Run `SIMULATION_API_URL=<prod> uv run pytest -m smoke ...` after deploy (optional).
3. **Release checklist:** “Deploy API + UI from same SHA”; “OpenAPI spot-check”; “Smoke URLs.”

---

## 5. Operational notes

- **SQLite on Railway:** Use a **volume** and a stable `SIM_DB_PATH`; with Proposal A, the file is **recreated on deploy** (after deploy-id check if implemented), not on every page load.
- **Why not “reset on refresh”:** Browser refresh is not a reliable or safe lifecycle boundary; use **deploy** or controlled **startup** behavior.
- **Postgres migration (later):** Replacing SQLite does not remove the need for **deploy parity**; seed strategy (`reset_on_deploy` vs `seed_if_empty`) still applies.

---

## 6. Summary

| Issue | Cause | Fix under Proposal A |
|--------|--------|-------------------------|
| 404 on metrics / feed-algorithms | **Old API build** (routes absent) | Deploy **current** API; align with UI ref |
| `postIds is not iterable` | **Schema mismatch** (`post_uris` vs `post_ids`) | Same alignment + correct OpenAPI/types |
| Run list vs run details inconsistency | **Old/inconsistent backend or DB** | Align deploys; then **`reset_on_deploy`** + fixtures |
| Desire for deterministic demo | SQLite + no prod seed | **`reset_on_deploy`** + **`simulation/local_dev/seed_fixtures/`** |

This file is the working agreement for **Proposal A** and **fixture reuse**; implementation tasks should reference it in PR descriptions.

---

## 7. Planning handoff for follow-up PRs

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread

### Overview

We are fixing the production failure in two layers: first by eliminating **UI/API deployment skew**, then by making production SQLite **deterministic on deploy** using the already-committed JSON fixtures in `simulation/local_dev/seed_fixtures/`. The PRs below are intentionally sliced so later AI agents can plan and implement them with low ambiguity, clear verification, and tight file ownership boundaries.

### Happy Flow

1. A single Git SHA is chosen for release and deployed to both Railway and Vercel, so the UI and API share the same runtime contract. Relevant files: `Dockerfile`, `railway.json`, `docs/runbooks/RAILWAY_DEPLOYMENT.md`, `docs/runbooks/UI_DEPLOYMENT.md`.
2. The backend starts against the configured SQLite path, runs Alembic to head, and exposes the current API contract including `/v1/simulations/metrics`, `/v1/simulations/feed-algorithms`, and turn feeds with `post_ids`. Relevant files: `simulation/api/main.py`, `simulation/api/routes/metadata.py`, `simulation/api/routes/runs.py`, `ui/lib/api/simulation.ts`, `ui/types/api.generated.ts`.
3. Production deploy bootstrap detects a new deploy, resets the SQLite file for the demo environment, reruns migrations, and seeds from `simulation/local_dev/seed_fixtures/` using the shared seed logic rather than a prod-only fork. Relevant files: `simulation/local_dev/seed_loader.py`, `db/adapters/sqlite/sqlite.py`, `Dockerfile`, new bootstrap script(s).
4. Smoke tests and release checks verify the deployed API shape and the seeded sample data end to end. Relevant files: `tests/api/test_simulation_smoke.py`, deployment runbooks, optional release helper scripts.

### Alternative approaches

- We chose **Proposal A (`reset_on_deploy`)** over `seed_if_empty` because the goal is a **deterministic demo** and the accepted tradeoff is losing user-created prod records on each deploy.
- We chose to **reuse `simulation/local_dev/seed_fixtures/`** rather than introduce a separate prod fixture set because one canonical fixture source reduces drift between local and prod.
- We chose a **multi-PR rollout** instead of one large PR so that deploy skew, seed reuse, and reset-on-deploy bootstrap can be reviewed and verified independently.

### Interface or Contract Freeze

The following contracts and invariants are frozen unless a later document explicitly supersedes this one:

- Production UI and production API must deploy from the **same Git SHA or release tag**.
- The canonical demo seed source is **only** `simulation/local_dev/seed_fixtures/`.
- The backend contract expected by the UI includes:
  - `GET /v1/simulations/metrics`
  - `GET /v1/simulations/feed-algorithms`
  - Turn feed payloads with `post_ids`, not `post_uris`
- Local-dev behavior must remain intact:
  - `LOCAL=true` continues to force the local dummy DB
  - `LOCAL_RESET_DB=1` remains the explicit local reset workflow
- Production reset behavior must be **deploy-bound**, not browser-refresh-bound.
- No PR in this sequence should introduce a second seed source, a second prod-only fixture directory, or ad hoc SQL seed data outside the shared loader path.

### Serial Coordination Spine

1. PR 1: release parity and contract verification guardrails
2. PR 2: shared fixture seeding extraction for local and prod reuse
3. PR 3: Railway/demo reset-on-deploy bootstrap
4. PR 4: post-deploy verification, release checklist, and observability guardrails

### Parallel Task Packets (PR candidates)

#### PR 1 — Release parity and contract verification

- Objective: Ensure production UI and production API deploy from the same ref and fail verification if the live API contract is older than the UI expects.
- Why this is first: It fixes the **current outage class** immediately and prevents shipping a newer UI against an older backend.
- Success looks like:
  - Railway prod serves `/v1/simulations/metrics` and `/v1/simulations/feed-algorithms`.
  - Turn payloads consumed by the UI include `post_ids`.
  - The release process explicitly checks that Vercel and Railway reference the same Git SHA or release tag.
  - Smoke verification catches contract skew before or immediately after deploy.
- Files to inspect:
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - `docs/runbooks/UI_DEPLOYMENT.md`
  - `tests/api/test_simulation_smoke.py`
  - `ui/lib/api/simulation.ts`
  - `ui/types/api.generated.ts`
  - `simulation/api/routes/metadata.py`
  - `simulation/api/routes/runs.py`
- Files allowed to change:
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - `docs/runbooks/UI_DEPLOYMENT.md`
  - `docs/runbooks/PRODUCTION_DEPLOYMENT.md`
  - `tests/api/test_simulation_smoke.py`
  - Optional small helper script under `scripts/`
- Files forbidden to change:
  - `simulation/local_dev/seed_fixtures/**`
  - `simulation/local_dev/seed_loader.py`
  - `db/migrations/**`
  - UI component files under `ui/components/**`
- Invariants to maintain:
  - Do not change seeding behavior in this PR.
  - Do not change SQLite schema.
  - Do not change runtime API payload shape unless required to reflect already-merged backend code in the current repo.
- Verification path:
  - `uv run pytest tests/api/test_simulation_smoke.py -q`
    - Expected: local test file passes or skips cleanly when `SIMULATION_API_URL` is unset.
  - Manual deploy verification:
    - `curl -sS https://agent-simulation-platform-production.up.railway.app/health`
      - Expected output: `{"status":"ok"}`
    - `curl -sS https://agent-simulation-platform-production.up.railway.app/v1/simulations/metrics`
      - Expected: JSON array, HTTP 200
    - `curl -sS https://agent-simulation-platform-production.up.railway.app/v1/simulations/feed-algorithms`
      - Expected: JSON array, HTTP 200
  - Browser verification:
    - Open [the Vercel app](https://ui-iota-eight.vercel.app/), click a seeded sample run, confirm no `postIds` crash and no 404s for metadata routes in devtools.
- Done when:
  - Deploy docs describe a same-ref release flow.
  - Smoke tests cover the missing-route regression class.
  - Production passes the three curl checks above.

#### PR 2 — Shared fixture seeding extraction

- Objective: Refactor the current local-only seeding implementation into a shared, reusable fixture-seeding path that can be invoked by both local mode and production bootstrap.
- Why this is parallelizable: It is self-contained in the seeding layer and should not depend on the deploy bootstrap mechanics from PR 3.
- Success looks like:
  - There is one shared seed function that accepts `db_path` and `fixtures_dir`.
  - Local mode still behaves exactly as before.
  - Production can call the same shared seed path without requiring `LOCAL=true`.
  - The only fixture source remains `simulation/local_dev/seed_fixtures/`.
- Files to inspect:
  - `simulation/local_dev/seed_loader.py`
  - `simulation/api/main.py`
  - `tests/local_dev/test_local_mode_seed.py`
  - `db/adapters/sqlite/sqlite.py`
- Files allowed to change:
  - `simulation/local_dev/seed_loader.py`
  - `simulation/api/main.py`
  - `tests/local_dev/test_local_mode_seed.py`
  - New tests under `tests/local_dev/` or `tests/api/`
- Files forbidden to change:
  - `simulation/local_dev/seed_fixtures/**`
  - `Dockerfile`
  - `railway.json`
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - `ui/**`
- Invariants to maintain:
  - Local mode remains seed-once unless `LOCAL_RESET_DB=1` is used.
  - The fixture digest behavior for local mode remains intact unless deliberately wrapped, not removed.
  - No second fixture directory or prod-only JSON snapshots are introduced.
  - No change to API route behavior in this PR.
- Verification path:
  - `uv run pytest tests/local_dev/test_local_mode_seed.py -q`
    - Expected: passing tests covering idempotent local seed behavior
  - If a new shared helper is added, add focused tests and run:
    - `uv run pytest tests/local_dev -q`
      - Expected: all local-dev seed tests pass
- Done when:
  - The code has a clearly reusable seed entry point for non-local callers.
  - Existing local seed tests still pass.
  - The shared path is documented in code comments/docstrings well enough for PR 3 to consume without reinterpretation.

#### PR 3 — Railway reset-on-deploy bootstrap

- Objective: Add production bootstrap logic that resets the demo SQLite DB on deploy, reruns migrations, and seeds from the shared fixture path before starting the API.
- Why this must follow PR 2: It depends on the shared fixture seeding path and should not reinvent or duplicate seed logic.
- Success looks like:
  - On a new deploy, the Railway service recreates or clears the SQLite DB at `SIM_DB_PATH`.
  - Migrations run to head.
  - Seed data from `simulation/local_dev/seed_fixtures/` is loaded successfully.
  - Random process restarts do not accidentally wipe data if deploy-id detection is implemented.
- Files to inspect:
  - `Dockerfile`
  - `railway.json`
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - `simulation/api/main.py`
  - `db/adapters/sqlite/sqlite.py`
  - Shared seed entry point introduced in PR 2
- Files allowed to change:
  - `Dockerfile`
  - `railway.json`
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - New bootstrap script(s) under `scripts/` or similar
  - Minimal targeted changes in `simulation/api/main.py` only if needed for startup integration
- Files forbidden to change:
  - `simulation/local_dev/seed_fixtures/**`
  - `ui/**`
  - `tests/api/test_simulation_smoke.py` except for extremely small command/reference updates
  - `db/migrations/**`
- Invariants to maintain:
  - Reset policy is deploy-bound, not request-bound.
  - Local mode semantics must not change.
  - The API must still start normally when reset flags are disabled.
  - No ad hoc SQL seeding outside the shared seed path.
- Verification path:
  - Local bootstrap dry run against a temp DB:
    - `SIM_DB_PATH=/tmp/agent-sim-reset.sqlite PYTHONPATH=. uv run python -c "from db.adapters.sqlite.sqlite import initialize_database; initialize_database(); from simulation.local_dev.seed_loader import seed_local_db_if_needed; seed_local_db_if_needed(db_path='/tmp/agent-sim-reset.sqlite')"`
      - Expected: completes without exception and creates a populated SQLite file
  - Container/startup verification:
    - Start the service with the new bootstrap entrypoint and `SIM_DB_PATH` pointed at a disposable path
    - `curl -sS http://localhost:8000/health`
      - Expected output: `{"status":"ok"}`
    - `curl -sS http://localhost:8000/v1/simulations/runs`
      - Expected: JSON array including seeded sample runs
- Done when:
  - A deploy bootstrap exists and is documented.
  - The bootstrap uses the shared fixture path, not duplicated logic.
  - Local disposable-path verification passes.

#### PR 4 — Release checklist, observability, and final verification guardrails

- Objective: Add the final operational guardrails so skew or seed/reset regressions are visible immediately during release and post-deploy checks.
- Why this is last: It should codify the behavior after PRs 1–3 have stabilized.
- Success looks like:
  - Release docs contain a concise same-SHA checklist for UI + API deploys.
  - There is a documented verification path for confirming seeded runs and metadata routes after deploy.
  - Startup or deploy logs clearly show the DB path, Alembic revision, and whether seeding/reset happened.
- Files to inspect:
  - `docs/runbooks/PRODUCTION_DEPLOYMENT.md`
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - `docs/runbooks/UI_DEPLOYMENT.md`
  - `simulation/api/main.py`
  - `db/adapters/sqlite/sqlite.py`
- Files allowed to change:
  - `docs/runbooks/PRODUCTION_DEPLOYMENT.md`
  - `docs/runbooks/RAILWAY_DEPLOYMENT.md`
  - `docs/runbooks/UI_DEPLOYMENT.md`
  - Minimal logging additions in `simulation/api/main.py` or `db/adapters/sqlite/sqlite.py`
- Files forbidden to change:
  - `simulation/local_dev/seed_fixtures/**`
  - `ui/**`
  - `db/migrations/**`
  - `simulation/local_dev/seed_loader.py` unless a logging hook is strictly required and already agreed
- Invariants to maintain:
  - Docs must match the actual release path from PRs 1–3.
  - Logging must not leak secrets or auth tokens.
  - This PR should not change business logic or data shape.
- Verification path:
  - `uv run pytest tests/api/test_simulation_smoke.py -q`
    - Expected: passes or skips cleanly locally
  - Manual doc verification:
    - Follow the updated runbooks step by step in a disposable environment and ensure each command is executable as written.
  - Post-deploy verification:
    - Confirm logs show migration/seeding/reset status.
    - Confirm seeded sample run opens successfully in the UI.
- Done when:
  - Operators can perform a release and verify it without relying on tribal knowledge.
  - Logs make it obvious whether a new deploy reset and reseeded the DB.

### Integration Order

1. Merge PR 1 first to stop the current class of prod breakage.
2. Merge PR 2 second so there is one shared seed path.
3. Merge PR 3 third to wire shared seeding into the Railway deploy lifecycle.
4. Merge PR 4 last to codify release and post-deploy verification once the implementation is settled.

### Final Verification

- Local code verification:
  - `uv run pytest tests/local_dev/test_local_mode_seed.py tests/api/test_simulation_smoke.py -q`
    - Expected: all relevant tests pass; smoke tests may skip when no live URL is set
- Local server verification:
  - `PYTHONPATH=. uv run uvicorn simulation.api.main:app --port 8000`
  - `curl -sS http://localhost:8000/health`
    - Expected output: `{"status":"ok"}`
- Production verification:
  - `curl -sS https://agent-simulation-platform-production.up.railway.app/v1/simulations/metrics`
    - Expected: HTTP 200 JSON array
  - `curl -sS https://agent-simulation-platform-production.up.railway.app/v1/simulations/feed-algorithms`
    - Expected: HTTP 200 JSON array
  - `curl -sS https://agent-simulation-platform-production.up.railway.app/v1/simulations/runs`
    - Expected: seeded sample runs present
  - Open [the Vercel app](https://ui-iota-eight.vercel.app/), click a seeded sample run, and confirm:
    - no `postIds` crash
    - no route 404s for metadata endpoints
    - run details and turns render correctly

### Recommended detailed-plan folders

When a future agent expands any one PR into a full implementation plan, store that plan under:

- `docs/plans/2026-03-24_release_parity_prod_contract_<hash>/`
- `docs/plans/2026-03-24_shared_fixture_seeding_<hash>/`
- `docs/plans/2026-03-24_reset_on_deploy_bootstrap_<hash>/`
- `docs/plans/2026-03-24_release_guardrails_prod_verification_<hash>/`
