# Feature Ideas and Technical Debt Scan (De-duplicated)

**Scan date:** 2026-02-25  
**Scope:** Full repo, with de-duplication against existing `docs/feature_ideas/*.md`

## Summary

- New unique markers/phrases found: 0
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Deep-link selected run/turn/agent via URL params

- **Rationale:** Selection state (`selectedRunId`, `selectedTurn`, `selectedAgentHandle`, `viewMode`) lives only in React state, so the UI can’t be deep-linked/bookmarked and reload loses context.
- **Scope:** Small
- **Evidence:** `ui/hooks/useSimulationPageState.ts` holds selection state and exposes handlers, but there is no router/search-param sync (router usage appears only in auth callback at `ui/app/auth/callback/page.tsx`).

#### Feature 2: Show run timestamps in Run History items

- **Rationale:** Run list items already include `createdAt` (and the API returns timestamps), but the sidebar renders only `runId`, counts, and status; timestamps are critical for quickly finding the right run.
- **Scope:** Small
- **Evidence:** `ui/lib/api/simulation.ts` maps `created_at -> createdAt` for `getRuns()`, but `ui/components/sidebars/RunHistorySidebar.tsx` does not display `run.createdAt`.

#### Feature 3: Add a “Posts” browse panel backed by `GET /simulations/posts`

- **Rationale:** The UI already has `PostCard` and an API client for `getPosts()` (including an unfiltered fetch); exposing a lightweight browse/search view would make it easier to inspect the underlying post corpus outside of a specific run/turn.
- **Scope:** Small
- **Evidence:** `ui/lib/api/simulation.ts` `getPosts()` supports calling without URIs; `simulation/api/routes/simulation.py` exposes `GET /simulations/posts`; UI already renders posts via `ui/components/posts/PostCard.tsx` and fetches posts in `ui/components/details/DetailsPanel.tsx`.

### ML (3 features)

#### Feature 1: Add per-run random seeding for reproducible simulations

- **Rationale:** Several action generators use module-level randomness, so two runs with identical config can diverge; reproducibility is important for experiments and debugging.
- **Scope:** Medium
- **Evidence:** Random policies call `random.random()` directly (e.g. `simulation/core/action_generators/like/algorithms/random_simple.py`), and `simulation/core/models/runs.py` `RunConfig` has no seed field.

#### Feature 2: Support per-run action-generator algorithm selection

- **Rationale:** The action-generator registry already supports choosing algorithms (and has multiple implementations), but defaults are resolved via a global `config.yaml`, not a per-run configuration; per-run selection enables comparative experiments without editing repo config.
- **Scope:** Large
- **Evidence:** `simulation/core/action_generators/registry.py` accepts an optional `algorithm` and delegates to `simulation/core/action_generators/config.py` (`config.yaml`) when omitted; `simulation/core/models/runs.py` `RunConfig` does not expose action-generator choices.

#### Feature 3: Allow per-run LLM model selection for naive LLM generators

- **Rationale:** Naive LLM action generators always use the default model, even though the LLM service supports specifying a model; making model selection per-run enables controlled comparisons and cost/perf tuning.
- **Scope:** Medium
- **Evidence:** `ml_tooling/llm/llm_service.py` supports `structured_completion(..., model=...)` but `simulation/core/action_generators/*/algorithms/naive_llm/algorithm.py` calls `structured_completion` without a model parameter.

### Backend (3 features)

#### Feature 1: Validate `feed_algorithm_config` server-side using the algorithm `config_schema`

- **Rationale:** The UI validates algorithm config client-side, but the API accepts `feed_algorithm_config` without schema validation; server-side validation prevents invalid configs (and supports non-UI clients).
- **Scope:** Medium
- **Evidence:** `simulation/api/schemas/simulation.py` `RunRequest.feed_algorithm_config` has no validator; feed algorithms expose `config_schema` via `feeds/algorithms/interfaces.py` and the API surfaces it via `GET /simulations/feed-algorithms` in `simulation/api/routes/simulation.py`.

#### Feature 2: Add `GET /simulations/agents/{handle}` for agent detail retrieval

- **Rationale:** The API provides list/create endpoints for agents, but no detail endpoint; a handle-based read API enables deep-linking and avoids fetching pages of agents just to display one.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py` defines `GET /simulations/agents` and `POST /simulations/agents`, but no per-handle route; `ui/hooks/useSimulationPageState.ts` only loads agents via paginated `getAgents()`.

#### Feature 3: Add `GET /simulations/runs/{run_id}/export` to download a run bundle

- **Rationale:** Clients currently need multiple calls to reconstruct a run’s full payload (details + turns + posts); an export endpoint would simplify analysis workflows and enable easy sharing/archiving of a run snapshot.
- **Scope:** Medium
- **Evidence:** Separate endpoints exist for run details (`GET /simulations/runs/{run_id}`), turns (`GET /simulations/runs/{run_id}/turns`), and posts (`GET /simulations/posts`) in `simulation/api/routes/simulation.py`.

## Markers and phrases

No new unique marker/phrase matches were found after de-duplicating against existing reports in `docs/feature_ideas/`.
