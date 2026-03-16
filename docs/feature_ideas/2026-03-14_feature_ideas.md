# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-03-14  
**Scope:** Full repo scan (excluding generated/vendor artifacts and prior `docs/feature_ideas/` reports)

## Summary

- Total markers/phrases found: 18
- By category: TODO (9), NOTE (1), future-improvement phrases (7), feature-gap phrase (1)
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Implement downloadable run export from Run Summary

- **Rationale:** The UI already exposes an "Export Run" action, but it only logs JSON to the browser console instead of producing a shareable artifact.
- **Scope:** Small
- **Evidence:** `ui/components/details/RunSummary.tsx:40-45` sets export state and `console.log(...)`; `ui/components/details/RunSummary.tsx:51-57` renders the Export button.

#### Feature 2: Add URL deep-linking for selected run and turn

- **Rationale:** Run/turn selection state is fully in React state and not reflected in URL params, so refresh/share loses context and prevents linkable troubleshooting views.
- **Scope:** Small
- **Evidence:** `ui/hooks/useSimulationPageState.ts:101-105` stores `viewMode`, `selectedRunId`, `selectedTurn` in component state; `ui/hooks/useSimulationPageState.ts:469-476` mutates selection via setters only (no router/query-state synchronization).

#### Feature 3: Replace console-only client errors with user-visible toasts + structured telemetry

- **Rationale:** Multiple fetch failures are only written to console, which makes production debugging and user feedback weak.
- **Scope:** Small
- **Evidence:** `ui/hooks/useSimulationPageState.ts:464-465` and `:517-519` log failures with `console.error`; `ui/components/form/ConfigForm.tsx:56-63` and `:82-93` log API failures/warnings, and `ui/components/form/ConfigForm.tsx:191` has TODO to switch to structured logging.

### ML (3 features)

#### Feature 1: Add deterministic simulation seed support for random action generators

- **Rationale:** Random-simple generators rely on process-global randomness with no run-level seed, making experiments difficult to reproduce exactly.
- **Scope:** Large
- **Evidence:** `simulation/core/action_generators/like/algorithms/random_simple.py:86-88` uses `random.random()`; `simulation/core/action_generators/comment/algorithms/random_simple.py:118-120` samples comment text via random roll; comparable random calls exist in follow generator.

#### Feature 2: Externalize random-simple generator hyperparameters into config

- **Rationale:** Core behavior knobs (probabilities, top-k, text pool) are hardcoded constants, limiting experimentability and requiring code deploys for tuning.
- **Scope:** Large
- **Evidence:** `simulation/core/action_generators/like/algorithms/random_simple.py:19-27` hardcodes scoring/probability constants; `simulation/core/action_generators/comment/algorithms/random_simple.py:19-33` hardcodes probability and comment text templates.

#### Feature 3: Add strict validation diagnostics for action-generator config loading

- **Rationale:** Invalid/missing config silently degrades to empty config/fallback defaults; this hides configuration errors in ML behavior.
- **Scope:** Small
- **Evidence:** `simulation/core/action_generators/config.py:19-30` returns `{}` when config file is missing or invalid and caches it; `simulation/core/action_generators/config.py:12-16` defines silent fallback algorithms per action.

### Backend (3 features)

#### Feature 1: Add `GET /simulations/runs/{run_id}/export` for single-call run artifact download

- **Rationale:** Export currently requires stitching run metadata, turns, and posts on the client; a backend export endpoint would produce a stable artifact for debugging and sharing.
- **Scope:** Large
- **Evidence:** Existing routes expose separate reads (`/simulations/runs/{run_id}`, `/simulations/runs/{run_id}/turns`, `/simulations/posts`) in `simulation/api/routes/simulation.py:234-273`; UI export action is currently a console log in `ui/components/details/RunSummary.tsx:40-45`.

#### Feature 2: Add run-scoped post hydration endpoint (e.g., `/simulations/runs/{run_id}/turns/{turn_number}/posts`)

- **Rationale:** Turn detail currently computes post IDs client-side and issues separate post lookups; backend hydration would reduce client fan-out and simplify detail rendering.
- **Scope:** Large
- **Evidence:** `simulation/api/routes/simulation.py:241-256` supports posts lookup only by `post_ids`; `ui/components/details/DetailsPanel.tsx:136-158` derives post IDs from turn payload and calls `getPosts(postIds)`.

#### Feature 3: Add `GET /simulations/agents/{handle}` for direct agent lookup

- **Rationale:** API currently supports list/create/delete but no single-agent read endpoint, which blocks direct links and forces list-query workflows for all agent detail views.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py:117-186` defines POST/GET-list/DELETE for agents with no GET-by-handle route; UI selection state is handle-based (`ui/hooks/useSimulationPageState.ts:102-104`) and would benefit from direct fetch semantics.

## Markers and phrases

### File: `feeds/feed_generator.py` (line 73)

**Type:** TODO  
**Context:** Feed generation loop

> `# TODO: right now we load all posts per agent, but obviously`

---

### File: `feeds/feed_generator.py` (line 74)

**Type:** Future improvement phrase (`optimize`, `later`)  
**Context:** Continuation of feed-generation TODO

> `# can optimize and personalize later to save on queries.`

---

### File: `feeds/candidate_generation.py` (line 8)

**Type:** TODO  
**Context:** Candidate loading strategy note

> `# TODO: we can get arbitrarily complex with how we do this later`

---

### File: `simulation/api/services/agent_command_service.py` (line 33)

**Type:** TODO  
**Context:** Pre-transaction handle-existence check

> `# TODO: that this can cause a slight race condition if we do this check`

---

### File: `simulation/core/command_service.py` (line 398)

**Type:** TODO  
**Context:** Ownership of agent-creation log

> `# TODO: this log should live within agent_factory.`

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO  
**Context:** Feed algorithm select option rendering

> `{/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}`

---

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO  
**Context:** Adapter module docstring extension point

> `TODO: For caching or async, consider a caching layer around`

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO  
**Context:** Batch completion error model

> `TODO: Consider supporting partial results for batch completions instead of`

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Future improvement phrase (`revisit later`)  
**Context:** Run metric implementation limitation

> `Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,`

---

### File: `simulation/core/metrics/builtins/actions.py` (line 86)

**Type:** Future improvement phrase (`consider`)  
**Context:** Scaling note for run metrics aggregation

> `which loads all turn rows into memory. For large runs, consider replacing`

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Future improvement phrase (`later`)  
**Context:** Structured-output support stub

> `"We'll revisit this later when actively working with Gemini models."`

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Future improvement phrase (`later`)  
**Context:** Structured-output support stub

> `"We'll revisit this later when actively working with Groq models."`

---

### File: `simulation/api/schemas/simulation.py` (line 144)

**Type:** Feature gap phrase (`not yet supported`)  
**Context:** Create-agent request documentation

> `Fast-follows (not yet supported):`

---

### File: `simulation/api/services/run_query_service.py` (line 47)

**Type:** NOTE  
**Context:** Turn payload contract note

> `Note: agent_actions are currently not persisted in SQLite. This endpoint returns`

---

### File: `simulation/api/routes/simulation.py` (line 356)

**Type:** Future improvement phrase (`later`)  
**Context:** Runs list execution model

> `# Use to_thread for consistency with other async routes and to prepare for real I/O later.`

---

### File: `db/schema.py` (line 10)

**Type:** Future improvement phrase (`later`)  
**Context:** Schema migration sequencing note

> `` `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.``

---

### File: `scripts/lint_schema_conventions.py` (line 19)

**Type:** TODO  
**Context:** Legacy table cleanup list (seed state)

> `# TODO: Delete these legacy tables once migration renames/replaces them.`

---

### File: `scripts/lint_schema_conventions.py` (line 29)

**Type:** TODO  
**Context:** Legacy table cleanup list (turn events)

> `# TODO: Delete these legacy tables once migration renames/replaces them.`

---
