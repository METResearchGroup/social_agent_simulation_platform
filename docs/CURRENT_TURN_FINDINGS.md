# Current turn / start-run flow — findings

This document captures how a new simulation run is executed end-to-end today, why the UI can show **0 / N** completed turns and **Invalid Date** on a failed run, and options for **turn-in-progress** and **step-at-a-time** simulation. It is intended as a reference for the next round of product and API work.

## Evaluation criteria (for comparing approaches)

- **Debuggability**: Can you see why a turn behaved as it did (feeds, actions, state)?
- **UX responsiveness**: Does the UI stay usable during long runs?
- **Implementation cost**: Changes to API, engine, DB, and UI.
- **Determinism & replay**: Same inputs → same outcomes; reproducible bugs.
- **Failure semantics**: Partial progress, retries, and clear error surfaces.

---

## Trace: what happens when you start a new run

### 1. UI

`StartScreenView` calls `onSubmit` → `handleConfigSubmit` in `useSimulationPageState`, which calls `postRun(config)`. On success it prepends the run to local state, selects it, and sets the view to summary (`selectedTurn: 'summary'`).

### 2. HTTP

`POST /v1/simulations/run` is handled in a worker thread (`asyncio.to_thread`) so the async event loop is not blocked while the simulation runs.

The handler requires `request.state.current_app_user` and passes `created_by_app_user_id` into the execution layer.

### 3. Run execution (`run_execution_service.execute`)

- Builds `RunConfig` from the request (with defaults for missing fields).
- Calls `engine.execute_run(run_config, created_by_app_user_id=...)`.
- On `SimulationRunFailure` **with** a `run_id`, returns HTTP **200** with `RunResponse` status **FAILED**, partial turn summaries when available, and an `error` payload.
- On failure **without** `run_id` (run creation failed), surfaces as `ApiRunCreationFailedError` → **500** `RUN_CREATION_FAILED`.

### 4. Engine / command service (`SimulationCommandService.execute_run`)

Rough order:

1. **Create run** row; set status to **RUNNING**.
2. **Create agents** for the run.
3. **Snapshot** initial state (agents, follow edges, posts, likes, comments as applicable).
4. **Preload** action history from snapshots (follows, likes, comments).
5. **`simulate_turns`** in a loop: `turn_number` from `0` to `total_turns - 1`. Each turn generates feeds and runs per-agent actions; metrics and turn metadata are persisted as implemented in `simulate_turn` / persistence.
6. **Collect and write run-level metrics**; return the `Run` on success.

On **any** exception after run creation, status is set to **FAILED** and `SimulationRunFailure` is raised with the `run_id` so the API can return partial results.

### 5. UI: completed turns and “0 / N”

`completedTurns` in the run summary is **not** derived from the `POST` response’s embedded turn list alone. It is computed from **turn payloads** loaded into client state: `getCompletedTurnsCount` → `getAvailableTurns` → keys in `newRunTurns[runId]` or **`fallbackTurns[runId]`** (from `GET /v1/simulations/runs/{run_id}/turns`).

`newRunTurns` is reserved for live updates but is **not** currently populated from the `postRun` response. So until turns are fetched successfully, the count can remain **0** even if the POST returned turn summaries.

A **failed** run that **persists no turn rows** correctly shows **0 / N** completed turns.

### 6. “Invalid Date” for Created At

The summary uses `new Date(run.createdAt).toLocaleString()`. If `created_at` from the list or detail API is not a string `Date` can parse (e.g. missing timezone or non-ISO format), the UI shows **Invalid Date**. This should be verified against the actual API payload for `RunListItem.created_at` / `RunResponse.created_at`.

### 7. Quick improvement (pre-stepping work)

Surfacing **`error`** from a failed `RunResponse` in the UI, and/or merging **POST response turns** into `newRunTurns` for the selected run, would make failed and partial runs easier to understand without waiting for a separate turns fetch.

---

## Options: turn-in-progress and step-at-a-time simulation

### Option A — Synchronous run + richer in-flight UI (no stepping API)

Keep a single `POST /simulations/run` that completes all turns in one request; improve UX via streaming, polling run status during execution, or better post-hoc error display.

| Pros | Cons |
|------|------|
| Minimal API change if you only improve failure/telemetry after the fact | Still one long HTTP request unless transport changes |
| Same execution path as today | True “one turn at a time” user control needs a different model |
| Fewer concurrency concerns around half-finished runs | Hard to pause or inspect between turns from the client |

**Opinion:** Good for short runs and clearer errors; weak for interactive stepping.

---

### Option B — Explicit step API (e.g. `POST /runs/{id}/step`)

Create run + initial state, return immediately; each subsequent request advances exactly one turn (or a bounded batch).

| Pros | Cons |
|------|------|
| Natural fit for “next turn” and a structured turn-in-progress panel | Requires a clear run lifecycle (`pending`, `running`, `paused`, `completed`, `failed`) |
| Per-step timeouts and cancellation | More tests: partial runs, double-clicks, retries, crash mid-turn |
| Clear mapping from UI to server | Many round trips for large N unless you also offer “run all” |

**Opinion:** Strongest fit for interactive debugging and reviewing each turn.

---

### Option C — Async job queue + polling

`POST` enqueues work; client polls until terminal state; worker may support pause-after-each-turn internally.

| Pros | Cons |
|------|------|
| Scales to long runs without holding connections | Worker/queue ops and deployment complexity |
| UI can show progress from persisted DB | Step UX still needs pause points or a step API |
| | Harder local dev without queue stubs |

**Opinion:** Best when production scale and reliability dominate.

---

### Option D — Hybrid: run all + replay from persisted turns

Keep bulk execution, but treat step-at-a-time **review** as **replay** from stored artifacts (feeds, actions), not re-execution.

| Pros | Cons |
|------|------|
| Deterministic review of what already happened | Not equivalent to live stepping through an incomplete run unless partial state exists |
| Cheaper than re-invoking heavy logic per click | Needs complete turn payloads |

**Opinion:** Pairs well after Option B or a full run; combine with B for “live then replay.”

### Recommendation

For **turn-in-progress** plus **simulate one turn at a time**, prefer **Option B** (explicit step endpoint + state machine), optionally complemented later by **Option D** for analysis.

#### Reconsideration criteria

- If the API cannot change soon: Option A plus fix `created_at` parsing and surface `error` on failed runs.
- If runs become too heavy for synchronous HTTP: Option C with pause points or the same persistence layer as Option B.

---

## Critical questions to answer before building

1. **Execution model**: Is one turn a user-triggered mutation, a scheduled job, or replay-only?
2. **Atomicity**: On failure mid-turn, persist nothing, partial turn, or a diagnostic row?
3. **Concurrency**: Can two clients advance the same run? (Likely single-writer or lock.)
4. **Determinism**: Explicit seeds and frozen agent selection for support reproduction?
5. **UI semantics for “in progress”**: Spinner only vs phased UI (feeds → actions → metrics)?
6. **Backward compatibility**: Must `POST /simulations/run` remain “run all” for scripts and tests?

---

## How to verify success

- **API**: OpenAPI and tests for states and any step endpoint; idempotency or `expected_turn` guards.
- **Engine**: Tests for stop/resume; turn metadata and metrics sets stay consistent (see turn-data consistency checks in run execution).
- **UI**: Manual flow — step through 10 turns; refresh mid-run; failed turn shows error without opaque 0/N.
- **E2E**: API tests mirroring create → step → assert persistence (patterns in `tests/api/`).
- **Observability**: Structured logs per `run_id` + `turn_number`.

---

## Key code references

- UI submit and state: `ui/hooks/useSimulationPageState.ts` (`handleConfigSubmit`, `completedTurnsCount`).
- Turn resolution: `ui/lib/run-selectors.ts` (`getTurnsForRun`, `getCompletedTurnsCount`).
- API route: `simulation/api/routes/runs.py` (`_execute_simulation_run`).
- Execution and failure response: `simulation/api/services/run_execution_service.py`.
- Run loop: `simulation/core/services/command_service.py` (`execute_run`, `simulate_turns`).
