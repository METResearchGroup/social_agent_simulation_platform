# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-03-08  
**Scope:** Targeted repo scan across `ui/`, `simulation/core/`, `ml_tooling/`, `simulation/api/`, and selected docs (`docs/RULES.md`, `docs/runbooks/`), excluding generated files (`node_modules`, `.venv`, lockfiles, and existing `docs/feature_ideas/` reports).

## Summary

- Total markers/phrases found: 14
- By category: TODO (6), NOTE (2), technical-debt phrase (6)
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Add JSON fallback editor for unsupported algorithm config fields

- **Rationale:** Algorithm config rendering currently hard-fails unsupported required schema fields, which blocks valid algorithm usage when schema includes shapes beyond primitive/string-enum/boolean/number.
- **Scope:** Small
- **Evidence:** `ui/components/form/config-schema.ts` maps unknown fields to `kind: 'unsupported'` and validation emits `Unsupported required config field schema`; `ui/components/form/AlgorithmSettingsSection.tsx` only renders an error message for unsupported fields.

#### Feature 2: Surface API failures as user-facing toasts instead of console-only logs

- **Rationale:** Key UI data flows (runs, agents, turns, run details, start run) still rely heavily on `console.error`, so users often only see stale/empty screens unless they open DevTools.
- **Scope:** Small
- **Evidence:** Repeated `console.error` paths in `ui/hooks/useSimulationPageState.ts` and `ui/components/form/ConfigForm.tsx` for failed fetches and submission errors.

#### Feature 3: Show persisted feed algorithm config in Run Parameters

- **Rationale:** Run Parameters UI has a component for algorithm config entries but currently loses config for persisted runs because API mapping deliberately sets `feedAlgorithmConfig: null`.
- **Scope:** Small
- **Evidence:** `ui/components/details/RunParametersBlock.tsx` has `AlgorithmConfigBlock`; `ui/lib/api/simulation.ts` comment at `getRunDetails` explicitly says `feedAlgorithmConfig` is forced to `null` due API schema shape.

### ML (3 features)

#### Feature 1: Generalize feed models beyond Bluesky-only posts

- **Rationale:** Core feed model explicitly documents Bluesky-only support and deferred handling for other content sources; this limits experimentation with synthetic/alternative social graphs.
- **Scope:** Large
- **Evidence:** `simulation/core/models/feeds.py` contains TODOs stating only Bluesky posts are currently supported and future extension is deferred.

#### Feature 2: Add capability-aware structured output fallback routing

- **Rationale:** Provider contract notes uneven structured-output support while provider implementations explicitly defer Gemini/Groq behavior; service should route or degrade gracefully per model capability.
- **Scope:** Large
- **Evidence:** `ml_tooling/llm/providers/base.py` docstring: structured outputs vary by provider; `ml_tooling/llm/providers/gemini_provider.py` and `ml_tooling/llm/providers/groq_provider.py` include "revisit later" placeholders.

#### Feature 3: Support pluggable metric bundles beyond hardcoded built-ins

- **Rationale:** Metric registration is statically compiled into `BUILTIN_METRICS`, which slows iteration and prevents easier domain-specific metric packs.
- **Scope:** Large
- **Evidence:** `simulation/core/metrics/defaults.py` defines fixed `BUILTIN_METRICS` and builds registries from that tuple only.

### Backend (3 features)

#### Feature 1: Return `feed_algorithm_config` in run details API

- **Rationale:** Backend run-details schema omits algorithm config, forcing UI to drop this data for persisted runs and reducing reproducibility/debuggability.
- **Scope:** Small
- **Evidence:** `simulation/api/schemas/simulation.py` `RunConfigDetail` includes `num_agents`, `num_turns`, `feed_algorithm`, `metric_keys` only; `ui/lib/api/simulation.ts` documents omission impact.

#### Feature 2: Add dedicated lightweight run-config endpoint

- **Rationale:** UI currently calls full run-details just to load config, while run-details API is broader (status, turns, metrics). A focused endpoint would reduce payload and coupling.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py` exposes only full `GET /simulations/runs/{run_id}`; `ui/lib/api/simulation.ts` maps only `run_id` + `config` and intentionally ignores other fields.

#### Feature 3: Add pagination/filtering to posts API for non-URI queries

- **Rationale:** Unfiltered post reads are hard-capped at 500 and only URI filtering exists; this constrains large-run inspection and incremental loading UX.
- **Scope:** Small
- **Evidence:** `simulation/api/services/run_query_service.py` has `MAX_UNFILTERED_POSTS = 500`; `get_posts_by_uris()` only supports URI list filtering today.

## Markers and phrases

### File: `simulation/api/services/agent_command_service.py` (line 33)

**Type:** TODO / Technical debt  
**Context:** Agent creation checks uniqueness before transaction, with documented race risk.

> \# TODO: that this can cause a slight race condition if we do this check

---

### File: `simulation/core/models/feeds.py` (line 1)

**Type:** TODO / Feature idea  
**Context:** Feed model scope is explicitly constrained to Bluesky posts.

> \# TODO: for now, we support only Bluesky posts being added to feeds.

---

### File: `simulation/core/models/feeds.py` (line 2)

**Type:** Feature idea / Deferred work  
**Context:** Follow-up work for adding non-current feed content is deferred.

> \# We'll revisit how to add AI-generated posts to feeds later on.

---

### File: `simulation/core/command_service.py` (line 398)

**Type:** TODO / Refactor  
**Context:** Logging ownership is in the wrong layer.

> \# TODO: this log should live within agent_factory.

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO / Feature idea  
**Context:** Batch completion behavior is all-or-nothing today.

> TODO: Consider supporting partial results for batch completions instead of

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO / Technical debt  
**Context:** UI still relies on ad-hoc console diagnostics for fetch failures.

> `/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */`

---

### File: `ui/lib/api/simulation.ts` (line 300)

**Type:** NOTE / API capability gap  
**Context:** UI intentionally drops run-details fields and nulls algorithm config because API doesn’t provide it in config schema.

> // NOTE: `getRunDetails` intentionally returns only `{ runId, config }`, where `config` is mapped via

---

### File: `simulation/api/routes/simulation.py` (line 352)

**Type:** Deferred work phrase  
**Context:** Current implementation keeps sync path and hints at later real-I/O evolution.

> \# Use to_thread for consistency with other async routes and to prepare for real I/O later.

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Deferred optimization  
**Context:** Run-level metric aggregation currently loads all turn metadata rows in memory.

> Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE / Architectural debt marker  
**Context:** Provider registry auto-registration location is a conscious tradeoff.

> \# NOTE: choosing to do this here instead of `__init__` so that we can use the

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Deferred work phrase  
**Context:** Gemini-specific behavior is intentionally postponed.

> "We'll revisit this later when actively working with Gemini models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Deferred work phrase  
**Context:** Groq-specific behavior is intentionally postponed.

> "We'll revisit this later when actively working with Groq models."

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Future improvement phrase  
**Context:** Production guidance calls out a later migration path off SQLite.

> With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 103)

**Type:** Future improvement phrase  
**Context:** Deployment runbook also captures deferred database scaling work.

> - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
