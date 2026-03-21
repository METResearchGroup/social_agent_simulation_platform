---
name: agent-id-query-boundary
description: Canonical-ID-first read/query path, ID-keyed `/turns` API contract, and UI updates for agent ID migration completion.
tags:
  - planning
  - agent-id
  - api
  - query-service
  - openapi
  - ui
overview: Finish the remaining agent ID migration seam by making the read/query path canonical-ID-first, exposing canonical IDs in the `/simulations/runs/{run_id}/turns` API contract, and updating the typed UI consumer to handle ID-keyed turn payloads without regressing the run details experience.
todos:
  - id: capture-before-turns-ui
    content: Capture current run-details `/turns` happy-path screenshots into this plan folder’s `images/before/` before implementation begins.
    status: pending
  - id: freeze-turn-contract
    content: Freeze the internal `TurnData` and external `TurnSchema` contracts so feeds/actions are keyed by canonical `agent_id` and payload items carry explicit `agent_id` / `author_agent_id` / `target_agent_id` fields.
    status: pending
  - id: core-turndata-id-keying
    content: Update the core read path (`turn_data_hydration`, `query_service`, `TurnData`, core tests) so turn feeds/actions stay keyed by canonical IDs through hydration and query assembly.
    status: pending
  - id: api-turn-serializer
    content: Refactor the `/turns` API service and schemas to consume `engine.get_turn_data()`, serialize actions as well as feeds, and expose the ID-based contract with targeted API tests.
    status: pending
  - id: ui-contract-sync
    content: Regenerate OpenAPI artifacts and update the UI API mapper/details view so ID-keyed turn payloads still render correctly in the run details flow.
    status: pending
  - id: capture-after-turns-ui
    content: Capture updated run-details `/turns` happy-path screenshots into this plan folder’s `images/after/` after implementation and verification finish.
    status: pending
isProject: false
---

# Agent ID Query And API Boundary Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

Review of `[strategy_planning/2026-03-20_agent_id_migration/proposal.md](strategy_planning/2026-03-20_agent_id_migration/proposal.md)` plus merged PRs [#268](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/268), [#269](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/269), [#270](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/270), [#272](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/272), [#274](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/274), [#275](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/275), and [#276](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/276) shows the storage/runtime migration is largely complete. The remaining seam is the read/query boundary: `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` still converts canonical IDs back to handles too early, `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)` bypasses that path and still returns feed-only turn payloads with empty actions, `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)` does not expose canonical IDs cleanly, and the typed UI consumer under `ui/` still assumes handle-keyed turn maps. This unit should finish that boundary end-to-end.

## Review Findings

- `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`: `SimulationQueryService.get_turn_data()` hydrates canonical `agent_id` and `target_agent_id`, but then re-buckets `feeds` and `actions` by `handle_at_start` instead of preserving canonical keys.
- `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)`: `get_turns_for_run()` still calls `engine.read_feeds_for_turn()` directly, never hydrates actions, and hardcodes `agent_actions={}`.
- `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`: `FeedSchema` omits `agent_id`, `PostSchema` omits `author_agent_id`, and `AgentActionSchema` still uses ambiguous `user_id` instead of `target_agent_id`.
- `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)` and `[ui/components/details/DetailsPanel.tsx](ui/components/details/DetailsPanel.tsx)`: the client assumes `TurnSchema.agent_feeds` and `TurnSchema.agent_actions` are keyed by handle, so an ID-keyed API contract requires mapper/component adjustments in the same unit.

## Happy Flow

1. `[simulation/core/utils/turn_data_hydration.py](simulation/core/utils/turn_data_hydration.py)` hydrates persisted likes/comments/follows into generated action models using only persisted `agent_id` / `target_agent_id`; no IDs are derived from handles.
2. `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` assembles a `[TurnData](simulation/core/models/turns.py)` object whose `feeds` and `actions` maps are keyed by canonical `agent_id`, while hydrated `Post`, `GeneratedFeed`, and generated action payloads still carry display handles as nested fields where needed.
3. `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)` calls `engine.get_turn_data()` for each persisted turn, preserves empty-turn metadata behavior, and serializes an ID-keyed `[TurnSchema](simulation/api/schemas/simulation.py)` that exposes `agent_id`, `author_agent_id`, and `target_agent_id` explicitly.
4. `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)` consumes the regenerated OpenAPI contract, maps ID-keyed turn payloads without assuming map keys equal handles, and `[ui/components/details/DetailsPanel.tsx](ui/components/details/DetailsPanel.tsx)` renders feeds/actions by using nested display fields rather than object-key equality.

## Serial Coordination Spine

1. Capture baseline screenshots of the run details happy path into this plan folder’s `images/before/`.
2. Freeze the internal and external turn contracts before parallel work starts.
3. Land the core read-path packet first, because it defines the canonical `TurnData` shape that the API serializer consumes.
4. Land the API serializer/contract packet next and confirm backend tests pass before touching generated client artifacts.
5. Land the UI contract-sync packet last, regenerate OpenAPI artifacts, and verify the run details screen still works against the new ID-keyed response.
6. Capture post-change screenshots into this plan folder’s `images/after/`.

## Interface Or Contract Freeze

- Internal contract in `[simulation/core/models/turns.py](simulation/core/models/turns.py)`:
  - `TurnData.feeds: dict[str, list[Post]]` keyed by canonical `agent_id`
  - `TurnData.actions: dict[str, list[GeneratedLike | GeneratedComment | GeneratedFollow]]` keyed by canonical `agent_id`
- API contract in `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`:
  - `FeedSchema` must include `agent_id` and `agent_handle`
  - `PostSchema` must include `author_agent_id` and `author_handle`
  - `AgentActionSchema` must include `agent_id`, `agent_handle`, `post_id`, `target_agent_id`, `type`, `created_at`; remove `user_id`
  - `TurnSchema.agent_feeds` and `TurnSchema.agent_actions` are keyed by canonical `agent_id`
- Compatibility rule: display handles remain in payload values, not in key semantics.
- Empty-turn rule: `/turns` must continue returning entries for persisted turn metadata even if a turn has no feeds/actions yet.
- OpenAPI rule: because the API contract changes, regenerate and commit `[ui/openapi.json](ui/openapi.json)`, `[ui/types/api.generated.ts](ui/types/api.generated.ts)`, and `[ui/types/generated.ts](ui/types/generated.ts)` per `[docs/runbooks/UPDATE_SCHEMAS.md](docs/runbooks/UPDATE_SCHEMAS.md)`.

## Parallel Task Packets

### Packet A: Core Read Path

Task ID: `core-turndata-id-keying`

Objective: make the core read/hydration path preserve canonical IDs all the way through `TurnData` assembly.

Why this is parallelizable: after the contract freeze, this packet owns only core query-layer files and core tests.

Files to inspect:

- `[simulation/core/utils/turn_data_hydration.py](simulation/core/utils/turn_data_hydration.py)`
- `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`
- `[simulation/core/models/turns.py](simulation/core/models/turns.py)`
- `[tests/simulation/core/test_query_service.py](tests/simulation/core/test_query_service.py)`

Files allowed to change:

- `[simulation/core/utils/turn_data_hydration.py](simulation/core/utils/turn_data_hydration.py)`
- `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`
- `[simulation/core/models/turns.py](simulation/core/models/turns.py)`
- `[tests/simulation/core/test_query_service.py](tests/simulation/core/test_query_service.py)`

Files forbidden to change:

- `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)`
- `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`
- Anything under `ui/`

Preconditions:

- Contract freeze completed.

Dependency tasks:

- `freeze-turn-contract`

Required contracts and invariants:

- `TurnData` maps are keyed by canonical `agent_id` only.
- Hydration must not derive IDs from handles.
- Action ordering remains deterministic: likes/comments by `post_id` then row id; follows by `target_agent_id` then `follow_id`.

Implementation steps:

1. Update `[simulation/core/models/turns.py](simulation/core/models/turns.py)` docstrings/type comments so `feeds` and `actions` explicitly mean `agent_id`-keyed maps.
2. Keep `[simulation/core/utils/turn_data_hydration.py](simulation/core/utils/turn_data_hydration.py)` as the sole read-side source of `agent_id` / `target_agent_id`; only change it if a serializer-facing helper or assertion is missing.
3. In `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`, stop converting `feed.agent_id` and persisted action `row.agent_id` into handle-based keys; store `feeds_dict` and `actions_dict` by canonical `agent_id`.
4. Preserve stale-handle protection by keeping display handles inside payload values, not in the parent dict keys.
5. Update `[tests/simulation/core/test_query_service.py](tests/simulation/core/test_query_service.py)` to assert canonical-ID keys, action hydration for like/comment/follow, and immunity to stale `GeneratedFeed.agent_handle` drift.

Verification commands:

- `uv run pytest tests/simulation/core/test_query_service.py -q`

Expected outputs:

- All query-service tests pass.
- No assertions rely on handle-keyed `TurnData` maps anymore.

Done when:

- `SimulationQueryService.get_turn_data()` returns canonical-ID-keyed `feeds` and `actions`.
- Core tests explicitly assert `agent_id` keys and `target_agent_id` follow payloads.

Coordinator review checklist:

- Confirm there is no `_handle_for_agent_id(... )`-driven rebucketing left in `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`.
- Confirm tests cover both stale `agent_handle` drift and action hydration.

### Packet B: API Serializer And Backend Contract

Task ID: `api-turn-serializer`

Objective: route the `/turns` endpoint through the canonical query path and publish the explicit ID-first API contract.

Why this is parallelizable: after the contract freeze, this packet owns only API schemas/services/tests.

Files to inspect:

- `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)`
- `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`
- `[simulation/api/routes/runs.py](simulation/api/routes/runs.py)`
- `[tests/api/test_run_query_service.py](tests/api/test_run_query_service.py)`
- `[tests/api/test_simulation_run.py](tests/api/test_simulation_run.py)`

Files allowed to change:

- `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)`
- `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`
- `[tests/api/test_run_query_service.py](tests/api/test_run_query_service.py)`
- `[tests/api/test_simulation_run.py](tests/api/test_simulation_run.py)`

Files forbidden to change:

- `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`
- `[simulation/core/models/turns.py](simulation/core/models/turns.py)`
- Anything under `ui/`

Preconditions:

- Contract freeze completed.
- Packet A merged or at least available for integration against the frozen `TurnData` contract.

Dependency tasks:

- `freeze-turn-contract`
- `core-turndata-id-keying`

Required contracts and invariants:

- `/v1/simulations/runs/{run_id}/turns` must expose actions as well as feeds.
- `TurnSchema` maps are keyed by canonical `agent_id`.
- Empty-turn metadata entries must still be returned with empty maps.
- No serializer code should call `engine.read_feeds_for_turn()` directly for turn payload assembly.

Implementation steps:

1. Refactor `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)` so `get_turns_for_run()` calls `engine.get_turn_data()` for each persisted turn.
2. Add a serializer helper that converts `TurnData` into `[TurnSchema](simulation/api/schemas/simulation.py)` while preserving empty-turn behavior when `engine.get_turn_data()` returns `None`.
3. Update `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`:
  - `FeedSchema`: add `agent_id`
  - `PostSchema`: add `author_agent_id`
  - `AgentActionSchema`: add `agent_id` and `target_agent_id`; remove `user_id`
  - `TurnSchema`: document that `agent_feeds` / `agent_actions` are keyed by canonical `agent_id`
4. Add focused tests in `[tests/api/test_run_query_service.py](tests/api/test_run_query_service.py)` for action serialization, empty-turn handling, and run-not-found behavior.
5. Strengthen `[tests/api/test_simulation_run.py](tests/api/test_simulation_run.py)` so the route-level assertions validate ID-keyed maps and actual action/feed payload fields instead of only checking top-level keys.

Verification commands:

- `uv run pytest tests/api/test_run_query_service.py tests/api/test_simulation_run.py -q`

Expected outputs:

- `/turns` API tests pass.
- Action payloads are no longer empty by construction.
- The API contract explicitly includes canonical identity fields.

Done when:

- `get_turns_for_run()` no longer rebuilds turn payloads from raw feed reads.
- `simulation/api/schemas/simulation.py` exposes `agent_id`, `author_agent_id`, and `target_agent_id`.
- API tests prove ID-keyed response semantics and empty-turn compatibility.

Coordinator review checklist:

- Confirm there is no remaining `agent_actions={}` hardcode in `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)`.
- Confirm `AgentActionSchema.user_id` is fully removed from backend schemas/tests.

### Packet C: OpenAPI And UI Consumer Sync

Task ID: `ui-contract-sync`

Objective: regenerate typed API artifacts and adapt the run-details UI to the new ID-keyed turn payload.

Why this is parallelizable: this packet is isolated to generated contract artifacts plus the UI turn consumer after the backend contract is frozen.

Files to inspect:

- `[ui/openapi.json](ui/openapi.json)`
- `[ui/types/api.generated.ts](ui/types/api.generated.ts)`
- `[ui/types/generated.ts](ui/types/generated.ts)`
- `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`
- `[ui/components/details/DetailsPanel.tsx](ui/components/details/DetailsPanel.tsx)`
- `[docs/runbooks/UPDATE_SCHEMAS.md](docs/runbooks/UPDATE_SCHEMAS.md)`

Files allowed to change:

- `[ui/openapi.json](ui/openapi.json)`
- `[ui/types/api.generated.ts](ui/types/api.generated.ts)`
- `[ui/types/generated.ts](ui/types/generated.ts)`
- `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`
- `[ui/components/details/DetailsPanel.tsx](ui/components/details/DetailsPanel.tsx)`

Files forbidden to change:

- Backend Python files
- Unrelated UI components outside the run-details turn view unless a compile error forces a narrowly-scoped fix

Preconditions:

- Before screenshots captured.
- Packet B merged so OpenAPI generation reflects the final backend contract.

Dependency tasks:

- `capture-before-turns-ui`
- `api-turn-serializer`

Required contracts and invariants:

- Generated artifacts must be regenerated, not hand-edited.
- The UI must not assume object keys equal handles anymore.
- Existing run-details rendering must continue to work for feed-only turns and action-bearing turns.

Implementation steps:

1. Regenerate API artifacts exactly as documented in `[docs/runbooks/UPDATE_SCHEMAS.md](docs/runbooks/UPDATE_SCHEMAS.md)`: `cd ui && npm run generate:api`.
2. Update `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`:
  - `mapFeed()` to expose `agentId`
  - `mapPost()` to expose `authorAgentId`
  - `mapAction()` to expose `agentId` and `targetAgentId`
  - `mapTurn()` to handle `agent_feeds` / `agent_actions` keyed by canonical `agent_id`
3. Update `[ui/components/details/DetailsPanel.tsx](ui/components/details/DetailsPanel.tsx)` so participating-agent lookup and feed/action selection rely on nested `agentHandle` / `agentId` data rather than matching dict keys to handles.
4. Keep UI scope narrow: no unrelated layout changes, no route changes, no new view components unless compile/runtime behavior forces them.

Verification commands:

- `cd ui && npm run generate:api`
- `cd ui && npm run check:api`
- `cd ui && npx tsc --noEmit`

Expected outputs:

- Generated artifacts update cleanly.
- `check:api` passes with no drift.
- TypeScript compile succeeds with the new turn contract.

Done when:

- Generated artifacts are committed and match the backend schema.
- `simulation.ts` no longer references `user_id`.
- `DetailsPanel` does not depend on handle-keyed turn maps.

Coordinator review checklist:

- Confirm generated files were produced by the script, not hand-edited.
- Confirm the run-details view can still find feeds/actions for a run agent when the parent map keys are canonical IDs.

## Integration Order

1. Capture `images/before/` screenshots.
2. Freeze the `TurnData` and `TurnSchema` contracts.
3. Merge Packet A and rerun core query tests.
4. Merge Packet B and rerun API tests.
5. Merge Packet C, regenerate OpenAPI artifacts, and rerun UI checks.
6. Run final backend + UI verification.
7. Capture `images/after/` screenshots.

## Manual Verification

- Backend core:
  - `uv run pytest tests/simulation/core/test_query_service.py -q`
  - Expected: canonical-ID-keyed turn-data tests pass.
- Backend API:
  - `uv run pytest tests/api/test_run_query_service.py tests/api/test_simulation_run.py -q`
  - Expected: `/turns` endpoint returns actions plus explicit ID fields with ID-keyed maps.
- Focused regression sweep:
  - `uv run pytest tests/simulation/core/test_command_service.py tests/feeds/test_feed_generator.py -q`
  - Expected: no regressions in adjacent runtime/feed behavior.
- Backend lint/type safety for touched files:
  - `uv run ruff check simulation/core/services/query_service.py simulation/core/models/turns.py simulation/api/services/run_query_service.py simulation/api/schemas/simulation.py tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/api/test_simulation_run.py`
  - Expected: no new lint failures.
- OpenAPI and UI type sync:
  - `cd ui && npm run generate:api`
  - `cd ui && npm run check:api`
  - `cd ui && npx tsc --noEmit`
  - Expected: generated artifacts update, drift check passes, TypeScript compile passes.
- Browser/manual happy path:
  - Start API: `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
  - Start UI: `cd ui && npm run dev`
  - Open the run-details page for a run that includes at least one turn with feeds and at least one persisted action.
  - Click a turn in the sidebar and verify the agent cards still render feeds/actions correctly.
  - Inspect the `/v1/simulations/runs/{run_id}/turns` response in DevTools and confirm `agent_feeds` / `agent_actions` are keyed by canonical `agent_id`, while each payload item still carries display handles.
  - Save before/after screenshots into this plan folder’s `images/before/` and `images/after/` directories.

## Final Verification

- Confirm no remaining handle-keyed rebucketing in `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`.
- Confirm no direct `engine.read_feeds_for_turn()` turn-assembly path remains in `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)`.
- Confirm backend schemas no longer expose `user_id` for turn actions.
- Confirm generated files `[ui/openapi.json](ui/openapi.json)`, `[ui/types/api.generated.ts](ui/types/api.generated.ts)`, and `[ui/types/generated.ts](ui/types/generated.ts)` are updated together.
- Confirm the run-details UI still renders the happy path using the new ID-keyed API response.

## Alternative Approaches

- Chosen: expose canonical IDs now and update the typed UI consumer in the same unit.
  - Reason: this completes the contract cleanup instead of leaving a second translation seam at the API boundary.
- Not chosen: keep the current handle-keyed `/turns` response and only fix internals.
  - Reason: it would preserve ambiguous API semantics, defer OpenAPI cleanup, and keep the frontend dependent on a handle-keyed boundary that the rest of the migration is eliminating.
