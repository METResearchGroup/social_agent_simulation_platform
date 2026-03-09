# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-03-07  
**Scope:** Full repo (excluding generated/vendor artifacts and prior `docs/feature_ideas/*` reports)

## Summary

- Total markers/phrases found: 24
- By category: TODO (10), NOTE (3), later/revisit/optimization phrases (11), FIXME (0), HACK (0), XXX (0), OPTIMIZE (0), REFACTOR (0)
- Proposed features: 9 (UI: 3, ML: 3, backend: 3)
- Ambiguous matches skipped: `ui/package-lock.json` `LGPL-3.0-or-later` license strings, code-token false positive `if missing:` in migration code.

## Proposed features by area

### UI (3 features)

#### Feature 1: Enable AI-generated bio drafting in Create Agent form

- **Rationale:** The UI explicitly exposes a non-functional "Create AI-generated bio (coming soon)" action. Implementing this closes a visible UX gap and aligns with existing `generated_bio` fields in API/UI models.
- **Scope:** Small
- **Evidence:** `ui/components/agents/CreateAgentView.tsx` has a button with `onClick={() => {}}` and label `Create AI-generated bio (coming soon)` (lines 103-109).

#### Feature 2: Add run search and status filters in Run History

- **Rationale:** The sidebar supports agent search but provides no equivalent filtering for runs, making large run lists hard to navigate.
- **Scope:** Small
- **Evidence:** `ui/components/sidebars/RunHistorySidebar.tsx` renders `SearchInput` only when `viewMode !== 'runs'` (lines 214-223) while runs are rendered as an unfiltered map in `runListContent()`.

#### Feature 3: Cache post lookups across turns in turn detail view

- **Rationale:** Turn detail refetches posts on every turn change, even when post URIs overlap, which adds avoidable latency and request volume.
- **Scope:** Small
- **Evidence:** `ui/components/details/DetailsPanel.tsx` recomputes `postUris` from `currentTurn` and calls `getPosts(postUris)` in `useEffect` for each turn selection (lines 132-174).

### ML (3 features)

#### Feature 1: Add DB-side aggregation for run action metrics

- **Rationale:** Current run-level action totals pull all turn metadata into memory; this does not scale for large runs.
- **Scope:** Large
- **Evidence:** `simulation/core/metrics/builtins/actions.py` documents: `Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata ... consider replacing with DB-side aggregation` (lines 85-87).

#### Feature 2: Expose per-action generator selection in run configuration

- **Rationale:** Core supports multiple algorithms per action type (`random_simple`, `naive_llm`) but API run config only allows feed algorithm selection, leaving action-generator experimentation inaccessible.
- **Scope:** Large
- **Evidence:** `simulation/core/action_generators/registry.py` defines algorithm factories for like/comment/follow (lines 72-88), `simulation/core/action_generators/config.yaml` sets per-action defaults, while `simulation/api/schemas/simulation.py` `RunRequest` has no action-generator fields (lines 25-29).

#### Feature 3: Implement persistent action history store

- **Rationale:** Action de-dup tracking is currently in-memory only, so process restarts lose prior action memory and reduce consistency for longer or resumed workloads.
- **Scope:** Large
- **Evidence:** `simulation/core/action_history/stores.py` only provides `InMemoryActionHistoryStore` backed by in-process dict/set state (lines 8-20).

### Backend (3 features)

#### Feature 1: Return persisted agent actions from turns API

- **Rationale:** Turns API currently drops actions even though core query paths can hydrate likes/comments/follows; this leaves UI action views incomplete.
- **Scope:** Large
- **Evidence:** `simulation/api/services/run_query_service.py` states `agent_actions are currently not persisted ... returns an empty agent_actions mapping` and sets `agent_actions={}` (lines 47-48, 75). `simulation/core/query_service.py` already hydrates per-agent actions from repositories (lines 117-149).

#### Feature 2: Add single-turn endpoint to avoid full-run turn payload fetches

- **Rationale:** API returns all turns at once (`dict[str, TurnSchema]`), which can become heavy as run size grows; a turn-scoped endpoint would reduce payload and UI latency.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py` exposes only `GET /simulations/runs/{run_id}/turns` for full per-turn payload maps (lines 237-251).

#### Feature 3: Add async simulation run job API with polling/status endpoints

- **Rationale:** Run execution is synchronous today; introducing job-based execution would better support longer workloads and concurrency.
- **Scope:** Large
- **Evidence:** `simulation/api/routes/simulation.py` describes `POST /simulations/run` as `Execute a synchronous simulation run.` (lines 182-188). `docs/RULES.md` explicitly recommends adding async/job APIs later for scale (line 62).

## Markers and phrases

### File: `db/schema.py` (line 10)

**Type:** Feature idea  
**Context:** Schema docstring describes deferred FK rollout.

> `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.

---

### File: `db/schema.py` (line 112)

**Type:** NOTE  
**Context:** Inline migration caveat in table definition.

> \# NOTE: This FK is applied by the second Alembic migration

---

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO  
**Context:** Adapter docstring flags scaling extension point.

> TODO: For caching or async, consider a caching layer around
> read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).

---

### File: `feeds/feed_generator.py` (line 73)

**Type:** TODO  
**Context:** Feed construction currently over-fetches.

> \# TODO: right now we load all posts per agent, but obviously

---

### File: `feeds/feed_generator.py` (line 74)

**Type:** Feature idea  
**Context:** Follow-up comment on personalization and query efficiency.

> \# can optimize and personalize later to save on queries

---

### File: `feeds/candidate_generation.py` (line 8)

**Type:** TODO  
**Context:** Candidate generation intentionally simple for now.

> \# TODO: we can get arbitrarily complex with how we do this later

---

### File: `feeds/algorithms/interfaces.py` (line 51)

**Type:** TODO  
**Context:** Algorithm interface still tied to Bluesky model type.

> ],  # TODO: decouple from Bluesky-specific type

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO  
**Context:** Batch completion error policy extension point.

> TODO: Consider supporting partial results for batch completions instead of
> all-or-nothing error handling.

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE  
**Context:** Provider registration location rationale.

> \# NOTE: choosing to do this here instead of **init** so that we can use the

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea  
**Context:** Structured-output support intentionally deferred.

> "We'll revisit this later when actively working with Gemini models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea  
**Context:** Structured-output support intentionally deferred.

> "We'll revisit this later when actively working with Groq models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 74)

**Type:** Feature idea  
**Context:** Groq completion kwargs implementation intentionally deferred.

> "We'll revisit this later when actively working with Groq models."

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Technical debt  
**Context:** Metric implementation documents memory-scaling limitation.

> Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
> which loads all turn rows into memory.

---

### File: `simulation/core/models/feeds.py` (line 1)

**Type:** TODO  
**Context:** Feed model explicitly scoped to one post source.

> \# TODO: for now, we support only Bluesky posts being added to feeds

---

### File: `simulation/core/models/feeds.py` (line 2)

**Type:** Feature idea  
**Context:** Follow-on expansion called out inline.

> \# We'll revisit how to add AI-generated posts to feeds later on

---

### File: `simulation/core/command_service.py` (line 398)

**Type:** TODO  
**Context:** Logging responsibility boundary noted for refactor.

> \# TODO: this log should live within agent_factory

---

### File: `simulation/api/services/agent_command_service.py` (line 33)

**Type:** TODO  
**Context:** Known race condition in create path.

> \# TODO: that this can cause a slight race condition if we do this check
>
> \# before the below context manager for writing the agent to the database

---

### File: `simulation/api/routes/simulation.py` (line 332)

**Type:** Feature idea  
**Context:** Route implementation anticipates future async/real I/O concerns.

> \# Use to_thread for consistency with other async routes and to prepare for real I/O later

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO  
**Context:** UI error handling currently relies on console logs.

> {/*Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging.*/}

---

### File: `ui/lib/api/simulation.ts` (line 285)

**Type:** NOTE  
**Context:** Client intentionally drops most run-details payload fields.

> // NOTE: `getRunDetails` intentionally returns only `{ runId, config }`, where `config` is mapped via

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Feature idea  
**Context:** Deployment guidance signals scaling migration path.

> With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 103)

**Type:** Feature idea  
**Context:** Railway runbook reiterates DB scaling migration.

> - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.

---

### File: `docs/RULES.md` (line 62)

**Type:** Feature idea  
**Context:** API design convention captures deferred async job architecture.

> - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.

---

### File: `docs/RULES.md` (line 169)

**Type:** TODO  
**Context:** Repo rule encourages explicit extension points for future infra work.

> - When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
