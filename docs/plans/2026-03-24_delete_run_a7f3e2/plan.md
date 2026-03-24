---
name: Delete run feature
description: "Add DELETE /v1/simulations/runs/{run_id} with transactional SQLite cleanup, Run Summary Delete run + confirm, and state reset to the start screen."
tags: [plan, api, ui, runs, delete, sqlite, openapi]
overview: "Add a persisted **delete run** capability end-to-end: a new `DELETE` API that removes a run and all dependent SQLite rows in a single transaction, plus UI controls in the Run Summary header (next to **Export Run**) with confirmation, then clear selection so the app returns to the same default “no run selected” view as **Start New Run**."
todos:
  - id: be-delete-api
    content: Implement transactional DB delete + SimulationEngine.delete_run + DELETE /v1/simulations/runs/{run_id} + pytest
    status: pending
  - id: openapi-regen
    content: Run cd ui && npm run generate:api after route exists
    status: pending
  - id: fe-delete-ui
    content: deleteRun client, RunSummary Delete + confirm, handleDeleteRun clears state like handleStartNewRun
    status: pending
  - id: plan-screenshots
    content: Capture before/after UI screenshots to docs/plans/2026-03-24_delete_run_a7f3e2/images/{before,after}/
    status: pending
isProject: false
---

# Delete run (API + UI)

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- UI changes: agent captures **before/after** screenshots to `docs/plans/2026-03-24_delete_run_a7f3e2/images/before/` and `.../images/after/` (implementation phase; no README delegating screenshots to the user)

## Overview

Users need to remove simulation runs from storage and from the UI. Today the API exposes list/get for runs (`[simulation/api/routes/runs.py](simulation/api/routes/runs.py)`) but **no delete**; the Run Summary header in `[ui/components/details/RunSummary.tsx](ui/components/details/RunSummary.tsx)` only has **Export Run**. This work adds a transactional DB delete, a `DELETE /v1/simulations/runs/{run_id}` endpoint, a thin API client, and a **Delete run** control with confirmation. On success, the client clears `selectedRunId` / `selectedTurn` like `[handleStartNewRun](ui/hooks/useSimulationPageState.ts)` so `[isStartScreen](ui/hooks/useSimulationPageState.ts)` becomes true and `[page.tsx](ui/app/page.tsx)` shows `[StartScreenView](ui/app/page.tsx)` again.

## Happy Flow

1. User selects a run in `[RunHistorySidebar](ui/components/sidebars/RunHistorySidebar.tsx)`; `selectedRunId` is set (`[useSimulationPageState](ui/hooks/useSimulationPageState.ts)`).
2. On the **Summary** tab, the right-hand details panel renders `[RunSummary](ui/components/details/RunSummary.tsx)`, which shows **Export Run** and the new **Delete run** (top-right, same flex row).
3. User clicks **Delete run** → confirmation dialog (same pattern as agent delete: `[window.confirm](ui/components/agents/AgentsView.tsx)` unless you introduce a shared modal component).
4. On confirm, the UI calls `DELETE /v1/simulations/runs/{run_id}` (new helper in `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`, following `[fetchJson](ui/lib/api/simulation.ts)` / auth headers).
5. Backend route in `[simulation/api/routes/runs.py](simulation/api/routes/runs.py)` resolves the engine from `request.app.state.deps.engine`, validates `run_id`, and invokes a new **delete** operation that loads the run, enforces **ownership** when `runs.app_user_id` is set (compare to `request.state.current_app_user.id`; return **403** with a stable `error.code` if mismatch), deletes dependent rows in FK-safe order inside **one transaction**, then deletes the `runs` row. Return **204 No Content** on success; **404** with `RUN_NOT_FOUND` if missing (reuse `[ApiRunNotFoundError](simulation/api/errors.py)` / `[error_response](simulation/api/routes/_helpers.py)` patterns used by GET run).
6. On **204**, the hook removes the run from local `runs` state, prunes per-run caches (`runConfigs`, `fallbackTurns`, `turnsLoadingByRunId`, `turnsErrorByRunId`, `runDetailsLoadingByRunId`, `runDetailsErrorByRunId`, refs such as `loadedTurnsRunIdsRef` / `turnsFetchInFlightRef` for that id), then sets `selectedRunId` to `null` and `selectedTurn` to `null` — matching `**handleStartNewRun`** (`[useSimulationPageState.ts` lines 478–481](ui/hooks/useSimulationPageState.ts)).
7. Main area shows `StartScreenView` again (`isStartScreen: selectedRunId === null`).

```mermaid
sequenceDiagram
  participant UI as RunSummary
  participant API as FastAPI
  participant Eng as SimulationEngine
  participant DB as SQLite
  UI->>API: DELETE /v1/simulations/runs/{run_id}
  API->>Eng: delete_run(run_id, app_user_id)
  Eng->>DB: BEGIN; delete children; delete runs; COMMIT
  DB-->>Eng: ok
  Eng-->>API: void
  API-->>UI: 204
  UI->>UI: filter runs, clear selection, prune caches
```



## Interface or contract freeze

- **HTTP:** `DELETE /v1/simulations/runs/{run_id}` → **204** empty body on success.
- **Errors:** Same envelope as existing routes: `404` + `RUN_NOT_FOUND`; **403** + e.g. `RUN_FORBIDDEN` if `app_user_id` on the run does not match the current user (when `app_user_id` is non-null). Invalid id: `400` + `INVALID_RUN_ID` (consistent with GET).
- **Engine:** `SimulationEngine.delete_run(run_id: str, *, deleted_by_app_user_id: str | None) -> None` (or pass `AppUser` from the route) — raises domain/not-found/forbidden exceptions mapped in the route.
- **OpenAPI:** Regenerate `[ui/openapi.json](ui/openapi.json)` and `[ui/types/api.generated.ts](ui/types/api.generated.ts)` via `[ui/package.json](ui/package.json)` `npm run generate:api` after the FastAPI route exists.

## Serial coordination spine

1. **Inventory FK graph** from Alembic migrations under `[db/migrations/versions/](db/migrations/versions/)` (tables referencing `runs.run_id` and any **child-before-parent** ordering, e.g. `run_post_`* referencing `run_posts`, `run_agents` before `run_follow_edges`, metrics tables, `turns`, generated feed/action tables, etc.). Produce an explicit ordered `DELETE` list (and/or one module such as `db/services/run_deletion_service.py` used only for this operation).
2. Implement **transactional** deletion (SQLite: `PRAGMA foreign_keys=ON`; use existing `[TransactionProvider](db/repositories/run_repository.py)` patterns).
3. Wire `**delete_run`** through `[SimulationEngine](simulation/core/engine.py)` / `[SimulationQueryService](simulation/core/services/query_service.py)` or a small dedicated service (prefer **not** bloating `[SimulationCommandService](simulation/core/services/command_service.py)` unless that is already the home for mutations).
4. Add FastAPI route + tests in `[tests/api/](tests/api/)` (mirror style of `[tests/api/test_run_query_service.py](tests/api/test_run_query_service.py)` / `[tests/api/test_simulation_run.py](tests/api/test_simulation_run.py)`).
5. Regenerate OpenAPI and add `deleteRun(runId)` in `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`.
6. Extend `[useSimulationPageState](ui/hooks/useSimulationPageState.ts)` with `handleDeleteRun` (or pass callback from page) and export it; update `[page.tsx](ui/app/page.tsx)` / `[RunDetailContext](ui/components/run-detail/RunDetailContext.tsx)` if the button must live below `RunSummary` — **minimal change:** add optional `onDeleteRun` to `RunSummary` props supplied from context or page wiring.
7. **Manual / agent verification** (below).

## Parallel task packets

Parallelism is intentionally limited: the **OpenAPI types** block frontend work until the route exists. After the route is merged:


| ID   | Objective                                                                         | Depends on                 |
| ---- | --------------------------------------------------------------------------------- | -------------------------- |
| BE-1 | DB + engine + `DELETE` route + `uv run pytest` for API and repository/integration | Contract freeze            |
| FE-1 | `deleteRun` client, `RunSummary` UI + state cleanup + `cd ui && npm run lint:all` | BE-1 + regenerated OpenAPI |


If two developers work in parallel before BE-1 lands, FE-1 can use a **temporary** local type for `deleteRun` only if the team accepts a follow-up regen commit (not ideal).

### Packet BE-1 (backend)

- **Why parallelizable:** Self-contained Python surface.
- **Inspect:** `[db/repositories/run_repository.py](db/repositories/run_repository.py)`, `[db/repositories/interfaces.py](db/repositories/interfaces.py)`, `[simulation/core/engine.py](simulation/core/engine.py)`, `[simulation/api/routes/runs.py](simulation/api/routes/runs.py)`.
- **May change:** New deletion helper module under `db/`, `RunRepository` / SQLite adapter if delete is implemented at repo layer, `simulation/core/`, `simulation/api/`, `tests/api/`, `tests/db/` as needed.
- **Forbidden:** Unrelated refactors in `ui/`.
- **Preconditions:** Contract freeze above.
- **Steps:** Implement ordered deletes + transaction; add `delete_run` on engine; register route; add tests proving run disappears from `GET /v1/simulations/runs` and `GET` returns 404 after delete.
- **Verify:** `uv run pytest tests/api/...` and targeted db integration tests; `uv run ruff check` on touched files.

### Packet FE-1 (frontend)

- **Depends on:** BE-1 + `npm run generate:api`.
- **Inspect:** `[RunSummary.tsx](ui/components/details/RunSummary.tsx)`, `[DetailsPanel.tsx](ui/components/details/DetailsPanel.tsx)`, `[useSimulationPageState.ts](ui/hooks/useSimulationPageState.ts)`, `[page.tsx](ui/app/page.tsx)`.
- **May change:** `ui/lib/api/simulation.ts`, `ui/components/details/RunSummary.tsx`, `ui/hooks/useSimulationPageState.ts`, `ui/app/page.tsx`, optionally `[RunDetailContext.tsx](ui/components/run-detail/RunDetailContext.tsx)` to thread `onDeleteRun`.
- **Forbidden:** Backend Python files.
- **Verify:** `cd ui && npm run lint:all`; manual click-through (below).

## Integration order

1. BE-1 (persistence + API + tests).
2. `cd ui && npm run generate:api`.
3. FE-1 (client + UI + hook).
4. Full verification checklist.

## Alternative approaches

- **CASCADE FKs in a new migration:** Would simplify deletes but touches many migrations/constraints and risks unintended mass deletes; **explicit transactional delete** is clearer and easier to audit for a single-run operation.
- **Soft delete (`deleted_at`):** Avoids heavy physical deletes but complicates every query; **not YAGNI** unless product requires recovery.
- **Confirmation UI:** `window.confirm` matches `[AgentsView](ui/components/agents/AgentsView.tsx)`; a modal would be nicer but adds scope — start with `confirm` unless design requires otherwise.

## Specificity notes

- **Default view:** Identical to no selection: `selectedRunId === null`, `selectedTurn === null`, `viewMode === 'runs'` — do **not** switch to agents tab; mirror `handleStartNewRun`.
- **Export placement:** **Delete run** sits in the same header row as **Export Run** in `[RunSummary.tsx](ui/components/details/RunSummary.tsx)` (only visible on Summary). If product later requires delete while viewing a turn, add a second entry point in `[RunDetailView](ui/components/run-detail/RunDetailView.tsx)` (out of scope unless requested).
- **Docs metadata:** If you add a runbook snippet for `DELETE`, follow `[docs/RULES.md](docs/RULES.md)` / `scripts/check_docs_metadata.py` (only if you touch `docs/runbooks/`).

## Manual verification

**Backend**

- `uv run pytest` (at least new delete tests + existing API tests).
- `curl -X DELETE -H "Authorization: Bearer …" http://localhost:8000/v1/simulations/runs/<run_id> -i` → `204`, then `GET` same id → `404`.

**Frontend**

- `DISABLE_AUTH=1` / `NEXT_PUBLIC_DISABLE_AUTH=true` per [LOCAL_DEV_AUTH](docs/runbooks/LOCAL_DEV_AUTH.md); start API and `cd ui && npm run dev`.
- Select a run → Summary → **Delete run** → cancel → run still there.
- **Delete run** → confirm → run disappears from sidebar, main pane shows start screen (same as before selecting a run).
- Regenerate API types: `cd ui && npm run generate:api` and ensure `git diff` for `openapi.json` / `api.generated.ts` is intentional.

**Plan assets (implementation phase)**

- Before screenshots: `docs/plans/2026-03-24_delete_run_a7f3e2/images/before/` (run selected, Summary visible, Export visible).
- After screenshots: `docs/plans/2026-03-24_delete_run_a7f3e2/images/after/` (start screen, run removed from list).

## Final verification

- No orphan rows for deleted `run_id` (spot-check SQLite or integration test asserts counts).
- Unauthorized user cannot delete another user’s run when `app_user_id` is set (403 test).
