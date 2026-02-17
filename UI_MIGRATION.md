# UI Migration Plan: Frontend -> Simulation API

## Goal

Migrate the `ui/` frontend from local/dummy data to a backend-driven interface where:

- `simulation/` and `simulation/api/` are the source of truth for request/response contracts, run status semantics, and simulation-derived metrics.
- the UI acts primarily as a presentation layer over API responses.
- users can submit a simulation run (`num_agents`, `num_turns`) and immediately see real output.
- existing mock/stub screens remain visible during migration, but are clearly labeled as stubbed.
- the frontend is production-deployable on Vercel against the deployed simulation API.

This document is designed as a multi-PR implementation roadmap with explicit acceptance criteria.

---

## Locked Product Decisions

- **Backend source of truth**: `simulation/api/schemas/simulation.py` and related core models define contract semantics.
- **Initial user flow**: synchronous `POST /v1/simulations/run` execution, showing returned payload directly.
- **UI complexity (phase 1)**: keep UX simple and focused on run submission + response display.
- **Existing mock features**: retain current screens/components as placeholders, but clearly mark them as **stubbed/demo**.
- **Deployment topology**:
  - UI on Vercel.
  - API hosted separately (Railway deployment already established for backend).
- **Contract style in UI**: API DTOs use snake_case to match backend schema exactly (avoid unnecessary transformation layer early).

---

## Current State (What Already Exists)

### Backend/API (available now)

- `POST /v1/simulations/run`
  - accepts `num_agents`, optional `num_turns`, optional `feed_algorithm`.
  - returns `run_id`, `status`, `num_agents`, `num_turns`, `likes_per_turn`, `total_likes`, `error`.
- `GET /v1/simulations/runs/{run_id}`
  - returns run lifecycle timestamps, config, and turn-level aggregate action counts.
- Validation and status semantics are well-defined by Pydantic schemas and core models.

### Frontend/UI (current)

- Next.js app in `ui/` with a fully local state/dummy-data architecture.
- `app/page.tsx` creates synthetic runs on form submit (no API calls).
- `lib/dummy-data.ts` provides runs, turns, posts, and agents for display.
- UI types are local/camelCase and do not map 1:1 to backend API DTOs.
- No explicit API client, no environment-based API URL wiring, no CORS integration guidance, no Vercel deployment runbook for this integration.

---

## Key Gaps to Close

1. No shared/authoritative API DTO layer in `ui/`.
2. No HTTP client path from Config form to simulation API.
3. Run result screen is derived from dummy models instead of backend response schema.
4. Stubbed sections are not clearly labeled as non-source-of-truth.
5. No robust error handling UX for API validation/server errors.
6. No explicit environment/deployment wiring for Vercel -> backend API communication.
7. No frontend smoke/E2E checks for deployed integration path.

---

## Migration Principles

1. **Contract-first UI**: API response shape is displayed directly whenever practical.
2. **Additive and safe**: preserve current layout and components while progressively replacing data sources.
3. **Clear source boundaries**:
   - Backend truth: run config, status, likes per turn, totals, errors, turn action summaries.
   - UI-only/stubbed: agent profile cards, synthetic posts/feed internals until corresponding backend APIs exist.
4. **Observable behavior**: surface request states (loading/success/error) explicitly.
5. **Deployability from day one**: every merged PR should remain Vercel-compatible.

---

## Proposed Target Architecture (Phase 1: Real Run Submission + Display)

### Frontend domains

- `ui/types/api.ts`
  - API-facing DTO types mirroring backend schema names exactly.
- `ui/lib/api/simulations.ts`
  - typed client for:
    - `postSimulationRun()`
    - `getSimulationRunDetails()` (optional for phase 1 display, required for phase 2 turn sidebar).
- `ui/app/page.tsx` (or extracted feature container)
  - orchestrates form submit, fetch lifecycle, and result rendering.
- `ui/components/`
  - real-data components for run summary/result.
  - existing components retained with explicit stub labeling where not API-backed.

### Data ownership model

- **Backend-driven state**
  - current run request payload
  - run response payload
  - optional run details response payload
- **UI-only state**
  - selected tabs/sections
  - expanded/collapsed panels
  - local “show stubbed data” toggles (if retained)

---

## API Contract Mapping for UI

### Endpoint 1: Execute simulation run

- `POST /v1/simulations/run`

Request body:

```json
{
  "num_agents": 20,
  "num_turns": 10,
  "feed_algorithm": "chronological"
}
```

Response body:

```json
{
  "run_id": "run_2026_02_17-10:22:00_abc123",
  "status": "completed",
  "num_agents": 20,
  "num_turns": 10,
  "likes_per_turn": [
    { "turn_number": 0, "likes": 6 },
    { "turn_number": 1, "likes": 8 }
  ],
  "total_likes": 14,
  "error": null
}
```

### Endpoint 2: Fetch run details (optional phase 1, required phase 2)

- `GET /v1/simulations/runs/{run_id}`

Used to drive real turn history data later (`turns[*].total_actions`) and reduce dependence on dummy turn scaffolding.

---

## UX Behavior Requirements (Target)

### Must-have (phase 1)

1. User sets `num_agents` and `num_turns`.
2. User submits run.
3. UI shows loading state.
4. UI renders real response:
   - run ID
   - status
   - configured agents/turns
   - likes-per-turn list/table
   - total likes
   - error payload (if status is failed or request-level error occurs)

### Keep but mark stubbed

- historical run sidebar rows not backed by backend list endpoint.
- agent-level drill-down cards based on `dummy-data`.
- per-post/per-feed details.
- any turn timeline entries not sourced from `GET /v1/simulations/runs/{run_id}`.

**Labeling requirement:** every non-backend-derived panel must include visible “Stubbed (demo data)” copy.

---

## Multi-PR Delivery Plan

Each PR should be independently mergeable and production-safe.

## PR 1 - Frontend API contract scaffolding

### PR 1 Scope

- Add API DTO types in `ui/types/api.ts` that mirror backend schemas.
- Add shared API error typing and parser utilities.
- Add config/env utility for `NEXT_PUBLIC_API_URL`.
- Add minimal docs block in `ui/README.md` for required env vars.

### PR 1 Acceptance Criteria

- DTOs represent current backend response/request fields exactly.
- Missing `NEXT_PUBLIC_API_URL` fails fast with clear developer error messaging.
- `npm run lint` and TypeScript checks pass.

---

## PR 2 - Simulation API client layer

### PR 2 Scope

- Add `ui/lib/api/simulations.ts` with:
  - `postSimulationRun(request)`
  - `getSimulationRunDetails(runId)` (optional immediate usage)
- Centralize fetch behavior:
  - JSON headers
  - timeout handling strategy
  - safe parsing for non-2xx responses into typed UI errors.

### PR 2 Acceptance Criteria

- API client functions are unit-tested with mocked fetch.
- Error mapping is deterministic for 422/500/network failures.
- No component performs ad-hoc raw fetch to simulation endpoints.

---

## PR 3 - Replace Config submit flow with real POST integration

### PR 3 Scope

- Update `ConfigForm` submit path to call API via parent container.
- Remove synthetic run creation on submit in `app/page.tsx`.
- Add loading/disabled state for submit button.
- Render backend response in a new real-data result view (or refactor existing summary component).

### PR 3 Acceptance Criteria

- Submitting form triggers real `POST /v1/simulations/run`.
- UI renders returned `run_id`, `status`, `num_agents`, `num_turns`, `likes_per_turn`, `total_likes`.
- Failure states are visible and actionable (retry).

---

## PR 4 - Real run result screen hardening

### PR 4 Scope

- Improve status messaging for:
  - completed run
  - failed run with partial results
  - request validation errors
  - infrastructure/network errors
- Add copy explaining synchronous nature and expected wait behavior.
- Add resilient empty-state handling when payload arrays are empty.

### PR 4 Acceptance Criteria

- All major status branches are handled with explicit UI copy.
- Error payload fields (`code`, `message`, `detail`) are displayed when present.
- UX remains functional under slow API response scenarios.

---

## PR 5 - Stub boundary clarity pass

### PR 5 Scope

- Add visual labels/badges to all non-API-backed panels.
- Update section titles/tooltips to state whether data source is “Simulation API” or “Stubbed demo data”.
- Prevent accidental mixing of real and dummy fields in same metric card without annotation.

### PR 5 Acceptance Criteria

- Every stubbed panel is clearly labeled.
- No primary run-result metric is sourced from dummy data.
- Product/engineering review confirms clarity to users/testers.

---

## PR 6 - Real turn history integration (GET run details)

### PR 6 Scope

- Integrate `GET /v1/simulations/runs/{run_id}` after successful run submission.
- Drive Turn History sidebar from real `turns` array when available.
- Show aggregate action counts per turn from API response.
- Keep deeper agent/post details stubbed unless backend data supports it.

### PR 6 Acceptance Criteria

- Turn list reflects backend response ordering and counts.
- If details fetch fails, base run result still renders from POST response.
- Clear fallback messaging for unavailable detail data.

---

## PR 7 - Session-level run history (frontend persistence)

### PR 7 Scope

- Replace static dummy run history with real session history:
  - store successful/failed run responses in client state (and optional localStorage).
- Allow selecting prior session runs for summary display.
- Clearly distinguish “session history” from durable backend run history (until list endpoint exists).

### PR 7 Acceptance Criteria

- New runs appear in run history immediately after submission.
- Refresh behavior is deterministic (if localStorage enabled, restores correctly).
- Labels indicate this is not full server-side historical listing.

---

## PR 8 - UI test coverage and smoke automation

### PR 8 Scope

- Add component/integration tests for:
  - form submit flow
  - loading and error states
  - result rendering
  - stub labels visibility
- Add smoke script/runbook for local + deployed verification.

### PR 8 Acceptance Criteria

- CI runs frontend tests for core migration paths.
- Smoke test checklist is documented and repeatable.
- Regressions in submit/result path are caught by tests.

---

## PR 9 - Vercel deployment readiness

### PR 9 Scope

- Configure Vercel project for `ui/` root.
- Document required env vars in deployment docs:
  - `NEXT_PUBLIC_API_URL`
- Validate production build settings and runtime assumptions.
- Confirm CORS requirements for backend origin(s).

### PR 9 Acceptance Criteria

- Vercel deployment succeeds from main branch.
- Deployed UI can call deployed simulation API successfully.
- Environment setup is documented for preview + production.

---

## PR 10 - Post-launch observability and operational polish

### PR 10 Scope

- Add lightweight client-side telemetry/events for:
  - run submit started/completed/failed
  - latency bands
  - failure code categories
- Add runbook notes for triaging frontend/backend integration failures.
- Capture known limitations and follow-up backlog items.

### PR 10 Acceptance Criteria

- Team can distinguish API error vs network/CORS vs UI regression quickly.
- Operational notes are sufficient for on-call/debugging.
- Migration limitations and future scope are explicitly tracked.

---

## Testing Strategy by Layer

### Unit tests

- API DTO parsing and normalization utilities.
- API client response/error mapping.
- Pure view model formatting (status labels, empty states).

### Component tests

- `ConfigForm` validation + submit disabled/loading behavior.
- Run result component rendering for completed/failed payloads.
- Stubbed label visibility.

### Integration tests

- page-level flow: submit -> loading -> result.
- simulated backend failures (422/500/network timeout).
- optional: submit -> fetch details -> render turn summary.

### Deployed smoke tests

- Vercel URL loads.
- form submission reaches backend.
- successful run displays `run_id` and `total_likes`.
- failure response path displays error payload.

---

## Deployment and Environment Plan

### Local

- UI: `npm run dev` in `ui/`.
- API: run backend service locally with `/v1` routes available.
- Env: `NEXT_PUBLIC_API_URL` points to local backend origin.

### Preview (Vercel)

- Preview deployments use preview backend URL.
- Validate CORS for preview origin(s).

### Production

- Production Vercel env uses production API URL.
- Rollout checklist includes endpoint health check + manual submit test.

---

## CORS and Networking Requirements

Backend must allow browser requests from:

- local development origin (e.g., `http://localhost:3000`)
- Vercel preview domains
- Vercel production domain

Without explicit CORS support in API middleware, browser calls from the deployed UI will fail despite healthy server endpoints.

---

## Suggested Repo Structure Additions

```text
ui/
  types/
    api.ts
  lib/
    api/
      simulations.ts
    config/
      env.ts
  docs/
    runbooks/
      UI_SMOKE_TEST.md   (optional)
```

---

## Risks and Mitigations

1. **Contract drift between backend and UI**
   - Mitigation: API-mirrored DTOs + PR checklist requiring schema sync review.
2. **Ambiguity from mixed real/dummy data**
   - Mitigation: mandatory stub badges and data-source labeling.
3. **CORS misconfiguration in deployed environments**
   - Mitigation: explicit origin allowlist and pre-deploy smoke tests.
4. **Slow synchronous runs degrade UX**
   - Mitigation: loading states, timeout messaging, future migration path to async APIs.
5. **Insufficient integration test coverage**
   - Mitigation: prioritize submit/result/error path tests before broad UI enhancements.

---

## Definition of Done (Final State)

The UI migration is complete when:

1. Frontend submits real simulation runs to `POST /v1/simulations/run`.
2. Frontend displays backend run output as the primary source of truth.
3. Stubbed sections are clearly labeled and never masquerade as real backend data.
4. Optional run details are fetched from `GET /v1/simulations/runs/{run_id}` for turn-level summary.
5. Vercel deployment is stable with documented environment and CORS requirements.
6. Core submit/result/error flows are covered by automated tests and smoke runbooks.

---

## Implementation Notes for PR Authors

- Keep PRs narrow and testable; avoid mixing major refactors with behavior changes.
- Prefer additive migration over deleting legacy components early.
- Treat backend schema as the canonical contract; avoid silent field remapping unless necessary.
- If a UI panel still relies on dummy data, label it in the component itself (not just in docs).
- Preserve accessibility and keyboard behavior while introducing async/loading states.
