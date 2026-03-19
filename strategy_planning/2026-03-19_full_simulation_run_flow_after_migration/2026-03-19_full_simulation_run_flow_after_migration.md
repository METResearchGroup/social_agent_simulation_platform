# Full Simulation Run Flow After Migration

## Purpose

This note answers the question:

- assuming `strategy_planning/2026-03-08_data_architecture_rules/02_full_migration_pr_plan.md` is fully implemented
- and assuming `strategy_planning/2026-03-08_data_architecture_rules/02_proposed_prs_for_migration.md` is fully implemented

what is the complete end-to-end flow, across backend and frontend, for executing a simulation run, and what is still missing or unclear to make that flow truly complete?

This document is grounded in the current repository state as of 2026-03-19, then projects forward to the intended "post-migration" state.

## Recommended architecture-doc filename

If this gets promoted into `docs/architecture/`, use:

- `docs/architecture/end-to-end-simulation-run-flow.md`

## Executive summary

The codebase is already farther along than the migration notes might suggest:

- `run_agents` already exists
- `run_follow_edges` already exists
- `run_posts` already exists
- run creation already snapshots agent membership, follow edges, and posts at run start
- turn-time feed generation already reads run-scoped post snapshots, not live `feed_posts`

So if the goal is only:

- "can the backend execute and persist a synchronous run?"

the answer is effectively yes, subject to normal environment/setup issues.

If the real goal is:

- "can the product execute a full simulation run with correct seed-state semantics, correct historical replay semantics, and a trustworthy frontend experience?"

then the main missing pieces are:

- seeded likes/comments are still not modeled or snapshotted
- the public API does not expose full run-start snapshot data to the frontend
- the frontend still guesses run participants instead of using persisted `run_agents`
- the frontend still hydrates posts globally instead of run-scoped
- the public turns API still returns empty `agent_actions`
- there is still no settled UX for exact run participant selection, seed-state inspection/editing before run start, or presentation of baseline likes/comments

## Scope assumptions

This trace assumes the migration is complete in the architectural sense:

- mutable pre-run state lives in `agent_*`
- immutable start-of-run state lives in `run_*`
- per-turn actions remain in `generated_feeds`, `likes`, `comments`, `follows`, `turn_metadata`, and `turn_metrics`

This trace also assumes the post-migration data model includes all of:

- `agent_follow_edges`
- `agent_posts`
- `agent_post_likes`
- `agent_post_comments`
- `run_agents`
- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`

## What is already implemented today

### Backend/data

Already present in the current code:

- `runs`, `run_metrics`, `turn_metadata`, `turn_metrics`
- `run_agents`
- `run_follow_edges`
- `run_posts`
- `agent_follow_edges`
- `agent_posts`
- run creation snapshots participants, follow edges, and posts
- feed candidate generation is run-scoped through `run_posts`

Current key files:

- `db/schema.py`
- `simulation/core/command_service.py`
- `simulation/core/query_service.py`
- `simulation/core/factories/agent.py`
- `simulation/api/routes/runs.py`
- `simulation/api/services/run_execution_service.py`
- `simulation/api/services/run_query_service.py`

### Frontend

Already present in the current UI:

- a start-run form
- authenticated run creation via `POST /v1/simulations/run`
- run history sidebar
- run summary view
- per-turn view
- post hydration for displayed feed entries

Current key files:

- `ui/app/page.tsx`
- `ui/hooks/useSimulationPageState.ts`
- `ui/lib/api/simulation.ts`
- `ui/lib/run-selectors.ts`
- `ui/components/start/StartScreenView.tsx`
- `ui/components/details/DetailsPanel.tsx`
- `ui/components/details/RunSummary.tsx`
- `ui/components/details/AgentDetail.tsx`

## Full intended flow after migration

This section describes the full flow that should exist once the migration is complete.

### 1. App boot and initial UI hydration

When the app boots:

- backend startup initializes the DB and application dependencies in `simulation/api/main.py`
- local/dev mode may seed the DB through `simulation/local_dev/seed_loader.py`
- the UI loads:
  - default run config
  - run list
  - agent list
  - feed-algorithm options
  - metric options

Relevant files:

- `simulation/api/main.py`
- `simulation/api/context.py`
- `ui/app/page.tsx`
- `ui/hooks/useSimulationPageState.ts`
- `ui/lib/api/simulation.ts`

### 2. User prepares a run in the UI

In the intended post-migration world, run preparation should mean two separate things:

1. configure the run itself
2. choose the exact seed state that the run should start from

The run configuration already has a UI shape:

- `num_agents`
- `num_turns`
- `feed_algorithm`
- `feed_algorithm_config`
- `metric_keys`

But a fully correct post-migration flow likely also needs:

- exact run participant selection, or an explicitly documented server-side selection rule
- the ability to inspect the current seed state that will be snapshotted:
  - agent identity/bio/counts
  - follows
  - posts
  - pre-run likes
  - pre-run comments

If the product keeps implicit selection, then the UI must clearly communicate:

- how agents are chosen
- in what order
- whether the selection is deterministic or random

If the product moves to explicit selection, then the start-run request likely needs a new field such as:

- `selected_agent_ids`

This is not settled yet.

### 3. User clicks "Start Simulation"

The current UI submits the start form through:

- `ui/hooks/useSimulationPageState.ts`
- `ui/lib/api/simulation.ts`

to:

- `POST /v1/simulations/run`

The current request includes only configuration, not explicit participant membership.

In the intended end state, the request should represent whichever participant-selection contract the product chooses:

- either only config, with backend-owned participant selection
- or config plus explicit selected agents

### 4. Backend creates the run row

The backend route is:

- `simulation/api/routes/runs.py`

It delegates to:

- `simulation/api/services/run_execution_service.py::execute`
- `simulation/core/engine.py::SimulationEngine.execute_run`
- `simulation/core/command_service.py::SimulationCommandService.execute_run`

The first backend persistence step is:

- create the `runs` row

That row captures:

- `run_id`
- timestamps
- total turns
- total agents
- feed algorithm
- metric keys
- app user attribution
- initial status

### 5. Backend resolves the seed-state participants

The backend then determines the actual participating agents.

Current behavior:

- the default agent factory hydrates the full seed-state catalog
- it slices the first `num_agents`

Relevant files:

- `simulation/core/factories/agent.py`
- `simulation/core/seed_state.py`

The seed-state hydration source is:

- `agent`
- latest row in `agent_persona_bios`
- `user_agent_profile_metadata`

This is already close to the post-migration shape.

Important nuance:

- `simulation/core/factories/agent.py` still hydrates `SimulationAgent.posts` from live `feed_posts`

That is a lingering hybrid seam. It does not appear to drive run-scoped feed candidate generation anymore, but it is still architectural drift and should be removed if post-migration startup state is meant to come only from `agent_*` and `run_*`.

### 6. Backend snapshots all start-of-run state into `run_*`

This is the core migration boundary.

At run creation time, the backend should atomically snapshot:

- `run_agents`
- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`

Today, the backend already snapshots:

- `run_agents`
- `run_follow_edges`
- `run_posts`

through:

- `simulation/core/command_service.py::snapshot_run_initial_state`
- `snapshot_run_agents`
- `snapshot_run_follow_edges`
- `snapshot_run_posts`

In the fully migrated state, this same transaction should also snapshot:

- `agent_post_likes` -> `run_post_likes`
- `agent_post_comments` -> `run_post_comments`

The correctness rule is:

- either the run row and all required snapshots exist together
- or run startup fails

### 7. Backend seeds in-memory action history with baseline state

Before simulating turns, the backend must preload baseline state into whatever in-memory history/action-suppression mechanism is used during the run.

Today, this already exists for follows:

- `simulation/core/command_service.py::preload_follow_history_from_snapshots`

This is important because it ensures agents do not immediately re-follow relationships that already existed at run start.

In the fully migrated state, the same idea must also exist for:

- baseline likes
- baseline comments

Otherwise the model is incomplete: the DB may know that a like/comment existed at run start, but the turn logic may still behave as if the action never happened before.

This preload path for likes/comments does not appear to exist yet.

### 8. Turn 0 feed generation uses run-scoped initial content

For each turn:

- feed generation runs
- candidate posts are loaded
- candidates are filtered
- actions are generated
- actions are validated
- turn outputs are persisted

The critical post-migration invariant is:

- turn-time feed generation must read the frozen run-start post snapshot, not live global post state

The current backend already does this through:

- `feeds/candidate_generation.py`
- `simulation/core/models/posts.py::run_post_snapshot_to_post`

This is one of the strongest signs that the backend is already partly migrated in practice.

### 9. Each turn persists only turn-event outputs

Once the run starts, only turn-event state should grow.

Per turn, the backend persists:

- `generated_feeds`
- `likes`
- `comments`
- `follows`
- `turn_metadata`
- `turn_metrics`

Relevant write path:

- `db/services/simulation_persistence_service.py`

This part of the architecture is already conceptually aligned with the migration rules.

### 10. Run completion persists final run-level outputs

After the last turn:

- run metrics are computed
- `run_metrics` is persisted
- `runs.status` is updated to `completed`

On mid-run failure:

- the run is marked `failed`
- partial turn data may still exist
- the API may still return a 200 with `status = failed` if the run row exists

This behavior is already implemented.

### 11. Frontend transitions from start screen to run detail

After a successful `POST /v1/simulations/run`:

- the UI prepends the new run into local run state
- selects the new run
- moves into the run detail view

Current files:

- `ui/hooks/useSimulationPageState.ts`
- `ui/app/page.tsx`

However, the current frontend throws away most of the backend response and only keeps:

- `runId`
- `createdAt`
- `totalTurns`
- `totalAgents`
- `status`

That means it is not using rich return data such as:

- turn summaries
- run metrics
- error detail

So even after the backend is fully migrated, the frontend contract is still too thin for a truly rich run experience.

### 12. Frontend loads run detail and turn detail

Today, selecting a run triggers:

- `GET /v1/simulations/runs/{run_id}`
- `GET /v1/simulations/runs/{run_id}/turns`

Then, for turn detail, the UI collects post IDs from feeds/actions and calls:

- `GET /v1/simulations/posts?post_ids=...`

In the fully correct migrated state, this should be interpreted as two separate read layers:

1. run-start snapshot layer
2. per-turn event layer

The UI should be able to render:

- who was in the run at start
- what follow graph existed at start
- what posts existed at start
- what likes/comments existed at start
- then, for each turn, what happened next

That means the frontend eventually needs snapshot-aware data, not only run summary plus turns.

### 13. Historical replay must read `run_*` plus turn events

This is the most important historical-correctness requirement.

A run detail page must never derive behaviorally relevant start state from live editable seed tables.

It should reconstruct history using:

- `run_agents`
- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`
- `generated_feeds`
- `likes`
- `comments`
- `follows`
- `turn_metadata`
- `turn_metrics`
- `run_metrics`

That is the durable interpretation contract for a historical run.

## What is still missing on the backend

### 1. Seeded likes/comments are still absent

I do not see implemented support for:

- `agent_post_likes`
- `agent_post_comments`
- `run_post_likes`
- `run_post_comments`

This is the biggest backend data-model gap relative to the migration plans.

Without these tables and repositories:

- pre-run likes/comments cannot exist as first-class state
- runs cannot fully snapshot initialized engagement
- historical replay is incomplete

### 2. No baseline likes/comments preload logic exists

Even after the tables are added, the run executor still needs something analogous to:

- `preload_follow_history_from_snapshots`

for:

- likes
- comments

Otherwise turn-time validators and candidate filters can mis-handle already-existing interactions.

### 3. Public run-history APIs do not expose full snapshot state

The internal model is stronger than the public API.

The current public API does not appear to expose:

- `run_agents`
- `run_follow_edges`
- `run_posts`
- any future `run_post_likes`
- any future `run_post_comments`

So the backend may have correct persisted data, but the frontend still cannot consume it.

### 4. The public turns API still drops actions

`simulation/api/services/run_query_service.py::get_turns_for_run` currently returns:

- `agent_feeds`
- `agent_actions = {}`

even though deeper query logic can hydrate actions from persisted tables.

This is a major API-layer gap because a "full run view" needs:

- likes
- comments
- follows

per agent, per turn.

### 5. Posts API is not run-scoped at the route contract

The service layer already has a `run_id` concept in `get_posts_by_ids(...)`, but the public route:

- `simulation/api/routes/posts.py`

does not expose `run_id`.

That means the frontend cannot explicitly ask:

- "give me these posts as they existed in this run"

and instead is forced into global post hydration.

### 6. Participant selection contract is still unclear

The backend today chooses the first `num_agents` from the hydrated seed catalog.

That may be acceptable for a temporary internal tool, but for a true end-to-end product flow it remains unclear whether the final contract should be:

- deterministic first N
- random N
- explicit selected agents
- some filtered/sampled server-side strategy

This directly affects:

- request schema
- snapshot semantics
- UI affordances
- reproducibility

### 7. Exogenous posts are still an unresolved edge case

`snapshot_run_posts` explicitly assumes that run-start posts belong to agents participating in the run.

That excludes a future world where agents see posts from:

- non-participating agents
- external profiles
- imported catalog-only actors

That may be acceptable for now, but it remains an architectural limitation.

## What is still missing on the frontend

### 1. The UI does not show actual run participants

Today, `ui/lib/run-selectors.ts::getRunAgents` infers run agents by slicing the first `N` globally loaded agents.

That is not historically correct.

A post-migration frontend needs actual `run_agents` data from the backend.

### 2. Post hydration is still global, not run-scoped

The frontend currently calls:

- `getPosts(postIds)`

with no `run_id`.

That is unsafe for a historical run viewer because post lookup should be anchored to:

- `run_posts`

when the IDs being rendered are run-scoped IDs.

### 3. The frontend throws away rich run response data

After `POST /v1/simulations/run`, the frontend stores only a narrow run summary.

It does not preserve:

- returned turn summaries
- returned metrics
- failure detail

This makes the UI less capable than the backend API already is.

### 4. There is no frontend model for baseline snapshot state

Even if the backend fully implements:

- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`

the current UI has no presentation model for:

- "state at run start"

Open UX question:

- should baseline state appear in Summary?
- in a dedicated Initial State tab?
- as a pseudo "Turn 0"?

This needs explicit product definition.

### 5. No UI exists yet for pre-run seed-state likes/comments editing or inspection

The migration plans make pre-run likes/comments part of the backend architecture, but the current UI does not provide a settled flow for:

- viewing seed posts
- viewing seed follows
- viewing seed likes
- viewing seed comments
- editing that state before starting a run

Some strategy notes propose this direction, but it is not yet an implemented frontend flow.

### 6. Exact participant selection UX is not implemented

There is an earlier strategy note proposing a future "Select Agents" flow:

- `strategy_planning/2026-02-26_interface_updates/PROPOSED_START_SIMULATION_FLOW.md`

But today the run form still submits only:

- `numAgents`

So the frontend cannot yet control exact run membership.

### 7. There is no real progress UX

The current run flow is synchronous and the UI does not have a richer progress model such as:

- streaming updates
- polling until completion
- partial-turn live refresh

This is not strictly required for a synchronous run, but if runs become longer or asynchronous later, this will matter.

## What remains unclear even after the migration plans

These are design questions that the migration plans do not fully settle.

### 1. What exactly is the run-start request contract?

Options include:

- config only
- config plus selected agent IDs
- config plus a selection mode such as random/custom

This must be made explicit.

### 2. How should seeded likes/comments affect behavior?

Questions:

- do seeded likes/comments count toward duplicate-suppression only?
- do they affect metrics from the very start of the run?
- do they influence feed ranking?
- do they appear as baseline state only, or are they also rendered in replay in a special way?

### 3. How should initial state be rendered in the UI?

Options include:

- a Summary section
- an "Initial State" tab
- a synthetic "Turn 0"

The storage model alone does not answer this.

### 4. Is agent selection deterministic, random, or user-driven?

This affects reproducibility and testing.

Today the backend effectively uses deterministic ordering from the seed catalog, but that seems more like a placeholder than a product decision.

### 5. Are external actors in scope?

The migration notes narrowed some domains to internal-only first, but longer-term questions remain:

- can agents follow external profiles?
- can seeded likes/comments come from external actors?
- can run-start posts belong to non-run actors?

### 6. How will non-local environments populate seeded likes/comments?

The strategy notes correctly say row-level seed fixtures are needed for local verification.

But there is still a broader operational question:

- outside local fixtures, what is the real source of truth for initial likes/comments?

Possible answers include:

- manual UI entry
- import pipeline
- both

That should be documented.

## The most important end-to-end blockers

If I reduce everything down to the shortest list of blockers for a trustworthy full simulation-run product flow, they are:

1. Implement seeded likes/comments plus run snapshots for them.
2. Expose run-start snapshot data through public APIs.
3. Expose fully hydrated per-turn actions through public APIs.
4. Make post lookup explicitly run-scoped in the frontend/backend contract.
5. Stop the frontend from inferring run participants and instead feed it real `run_agents`.
6. Decide and implement the final run-participant-selection contract.
7. Decide how baseline state is rendered in the UI.

## Concrete end-state API/data contract I would expect

For the product to feel complete, I would expect the frontend to have access to something close to:

- `POST /v1/simulations/run`
  - accepts run config
  - optionally accepts explicit participant selection
  - returns run summary and maybe initial turn summaries
- `GET /v1/simulations/runs`
  - list view
- `GET /v1/simulations/runs/{run_id}`
  - run summary
  - run config
  - run metrics
  - actual run participants
  - maybe initial-state summary counts
- `GET /v1/simulations/runs/{run_id}/initial-state`
  - run agents
  - run follow edges
  - run posts
  - run post likes
  - run post comments
- `GET /v1/simulations/runs/{run_id}/turns`
  - fully hydrated per-turn feeds and actions
- `GET /v1/simulations/posts?run_id=...&post_ids=...`
  - run-scoped hydration

The exact endpoint shape can vary, but the frontend needs equivalent information somewhere.

## Bottom line

The backend already has the skeleton of the correct architecture for a full run:

- seed state
- run snapshots
- turn events

But it is not yet complete enough to support the full intended product flow.

The single biggest backend gap is:

- no seeded likes/comments snapshot model yet

The single biggest frontend gap is:

- it still cannot render a run from authoritative run snapshot data

The single biggest unresolved product question is:

- how users choose the exact participants and seed state for a run before clicking "Start Simulation"

Until those three areas are resolved, the system can execute runs, but it cannot yet present a fully trustworthy, fully migrated, end-to-end simulation-run experience.
