# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-03-18  
**Scope:** Targeted repo scan across `ui/`, `simulation/core/`, `ml_tooling/`, `simulation/api/`, plus high-signal docs (`docs/RULES.md`, `docs/runbooks/`) and DB/scripts (`db/`, `scripts/`), excluding generated/history-heavy artifacts (for example `node_modules`, `.venv`, `ui/package-lock.json`, `docs/feature_ideas/`, `docs/plans/`, `strategy_planning/`).

## Summary

- Total markers/phrases found: 24
- By category: TODO (9), NOTE (3), future-improvement / feature-gap phrases (12)
- Proposed features: 3 UI, 3 ML, 3 backend
- Ambiguous matches skipped: `db/migrations/versions/f0e1d2c3b4a5_enforce_app_user_identity_not_null.py:29` (`if missing:` matched phrase pattern but is not a feature/debt marker)

## Proposed features by area

### UI (3 features)

#### Feature 1: Add seed-state follow graph editor in Agent Detail

- **Rationale:** The backend already supports listing/creating/deleting seed-state follow edges, but the UI has no API wrappers or views for this workflow.
- **Scope:** Large
- **Evidence:** `simulation/api/routes/simulation.py` exposes `GET/POST/DELETE /simulations/agents/{handle}/follows...` routes; `ui/lib/api/simulation.ts` has no follow-edge client methods; `ui/components/details/AgentDetail.tsx` renders metadata/feed/actions but no follow-edge management.

#### Feature 2: Add JSON fallback editor for unsupported algorithm config schema fields

- **Rationale:** Config schemas that normalize to `kind: 'unsupported'` currently block required fields with no editable fallback, preventing use of richer algorithm configs.
- **Scope:** Small
- **Evidence:** `ui/components/form/config-schema.ts` emits `kind: 'unsupported'` and validation errors for required unsupported fields; `ui/components/form/AlgorithmSettingsSection.tsx` only shows an error message (`Unsupported config field schema...`) with no input path.

#### Feature 3: Add explicit metadata-load health UI on Start form

- **Rationale:** Feed algorithm / metric loading failures currently log to console and silently fall back; users do not get actionable UI feedback.
- **Scope:** Small
- **Evidence:** `ui/components/form/ConfigForm.tsx` logs `console.warn`/`console.error` for metadata fetch failures and uses fallback options; inline TODO says to switch from console-only handling.

### ML (3 features)

#### Feature 1: Add provider capability contract for structured output and completion kwargs

- **Rationale:** Provider methods currently rely on `NotImplementedError` stubs, which makes unsupported paths runtime failures rather than explicit capability negotiation.
- **Scope:** Large
- **Evidence:** `ml_tooling/llm/providers/gemini_provider.py` and `ml_tooling/llm/providers/groq_provider.py` raise `NotImplementedError` for structured output/kwargs paths; `ml_tooling/llm/llm_service.py` calls provider hooks generically.

#### Feature 2: Make Gemini safety settings configurable via model config registry

- **Rationale:** Gemini safety settings are hardcoded defaults; model-level or environment-specific tuning is not configurable through existing YAML model config layering.
- **Scope:** Small
- **Evidence:** `ml_tooling/llm/providers/gemini_provider.py` hardcodes `DEFAULT_GEMINI_SAFETY_SETTINGS`; `ml_tooling/llm/config/model_registry.py` already supports hierarchical per-provider/per-model kwargs.

#### Feature 3: Add follow-graph drift metrics (run-start snapshot vs turn follow actions)

- **Rationale:** The system snapshots follow edges at run start and records follow actions by turn, but built-in metrics currently only cover action totals, not graph-evolution metrics.
- **Scope:** Large
- **Evidence:** `simulation/core/models/run_follow_edges.py` defines immutable run-start follow snapshots; `simulation/core/command_service.py` snapshots and preloads follow history; `simulation/core/metrics/defaults.py` currently registers only action-count metrics.

### Backend (3 features)

#### Feature 1: Add lightweight run-config endpoint (`GET /simulations/runs/{run_id}/config`)

- **Rationale:** The frontend currently needs only run config but must call a heavier run-details contract and then intentionally drop fields client-side.
- **Scope:** Small
- **Evidence:** `simulation/api/services/run_query_service.py` returns full `RunDetailsResponse` (`status`, `turns`, `run_metrics`, etc.); `ui/lib/api/simulation.ts` NOTE documents deliberate omission of those fields from `getRunDetails` mapping.

#### Feature 2: Add cache validators (ETag/Cache-Control) for metadata endpoints

- **Rationale:** Feed algorithm and metric metadata are read-mostly and fetched repeatedly, but endpoints currently return fresh responses each time.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py` has metadata routes (`/simulations/feed-algorithms`, `/simulations/metrics`, `/simulations/config/default`); `simulation/api/services/metadata_service.py` returns registry-derived static metadata.

#### Feature 3: Add bulk seed-state follow mutation endpoint for setup workflows

- **Rationale:** Existing follow-edge APIs are single-edge operations; a UI editor/import workflow would require many sequential requests.
- **Scope:** Large
- **Evidence:** `simulation/api/routes/simulation.py` currently exposes one-at-a-time follow create/delete endpoints; `simulation/api/services/agent_follows_command_service.py` logic is edge-level and can be composed into batched operations.

## Markers and phrases

### File: `docs/RULES.md` (line 62)

**Type:** Feature idea  
**Context:** Rule notes future async/job API expansion.

> - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.

---

### File: `docs/RULES.md` (line 69)

**Type:** TODO  
**Context:** Process rule referencing TODO completion.

> - ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.

---

### File: `docs/RULES.md` (line 169)

**Type:** TODO / future improvement phrase  
**Context:** Rule explicitly recommends TODO markers for future infra extensibility.

> - When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.

---

### File: `db/schema.py` (line 10)

**Type:** Feature idea (future migration follow-up)  
**Context:** Schema doc notes deferred FK migration step.

> `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.

---

### File: `db/schema.py` (line 171)

**Type:** NOTE  
**Context:** Inline schema note on migration sequencing.

> \# NOTE: This FK is applied by the second Alembic migration

---

### File: `scripts/lint_schema_conventions.py` (line 19)

**Type:** TODO  
**Context:** Legacy table cleanup marker.

> \# TODO: Delete these legacy tables once migration renames/replaces them

---

### File: `scripts/lint_schema_conventions.py` (line 29)

**Type:** TODO  
**Context:** Legacy table cleanup marker (second table constant).

> \# TODO: Delete these legacy tables once migration renames/replaces them

---

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO / feature idea  
**Context:** Module docstring flags future caching/async layer.

> TODO: For caching or async, consider a caching layer around
> read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO  
**Context:** Batch completion error-handling limitation in docstring.

> TODO: Consider supporting partial results for batch completions instead of
> all-or-nothing error handling.

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE  
**Context:** Registry initialization-order note.

> \# NOTE: choosing to do this here instead of `__init__` so that we can use the

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea (future provider support)  
**Context:** Explicit deferred structured-output implementation.

> "We'll revisit this later when actively working with Gemini models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea (future provider support)  
**Context:** Explicit deferred structured-output implementation.

> "We'll revisit this later when actively working with Groq models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 74)

**Type:** Feature idea (future provider support)  
**Context:** Explicit deferred completion-kwargs implementation.

> "We'll revisit this later when actively working with Groq models."

---

### File: `simulation/api/services/agent_command_service.py` (line 37)

**Type:** TODO / technical debt  
**Context:** Known race condition before transactional write.

> \# TODO: that this can cause a slight race condition if we do this check

---

### File: `simulation/api/services/agent_command_service.py` (line 39)

**Type:** Feature idea (future fix)  
**Context:** Follow-up sentence for the race-condition TODO.

> \# This is a known issue, and we'll revisit this in the future

---

### File: `simulation/api/routes/simulation.py` (line 457)

**Type:** Future improvement phrase  
**Context:** Route implementation note preparing for eventual real I/O.

> \# Use to_thread for consistency with other async routes and to prepare for real I/O later

---

### File: `simulation/core/command_service.py` (line 448)

**Type:** TODO / refactor marker  
**Context:** Logging ownership debt note.

> \# TODO: this log should live within agent_factory

---

### File: `simulation/core/factories/agent.py` (line 103)

**Type:** Future-improvement context  
**Context:** Comment anchors current behavior to later snapshot FK needs.

> \# Build agents from seed state so later run snapshots can FK back to
>
> \# the selected `agent.agent_id` rows

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Feature idea / optimization debt  
**Context:** Metric docstring identifies memory-scaling limitation and future DB aggregation path.

> Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
> which loads all turn rows into memory. For large runs, consider replacing
> with DB-side aggregation (e.g. run_repo.aggregate_action_totals(run_id)
> returning dict[TurnAction, int], or MetricsSqlExecutor with a SQL GROUP BY
> on turn metadata).

---

### File: `simulation/core/models/run_follow_edges.py` (line 13)

**Type:** Feature idea (historical-state extension)  
**Context:** Model docs emphasize no tracking of post-snapshot mutable changes.

> track later changes to `agent_follow_edges`.

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO  
**Context:** UI comment acknowledges console-only error handling debt.

> {/*Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging.*/}

---

### File: `ui/lib/api/simulation.ts` (line 302)

**Type:** NOTE / feature-gap marker  
**Context:** Client intentionally discards fields from run-details response.

> // NOTE: `getRunDetails` intentionally returns only `{ runId, config }`, where `config` is mapped via
> // `mapRunDetailsConfig`. `mapRunDetailsConfig` intentionally sets `feedAlgorithmConfig` to null
> // because `ApiRunConfigDetail` (RunConfigDetail) does not include `feed_algorithm_config`. Other
> // fields available on `ApiRunDetailsResponse` (status, turns, run_metrics, etc.) are deliberately
> // omitted in this PR scope to avoid callers assuming they’re available without a separate fetch.

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Future improvement phrase  
**Context:** Deployment guidance defers DB migration for concurrency scaling.

> With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 103)

**Type:** Future improvement phrase  
**Context:** Deployment runbook calls out later-phase DB migration.

> - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
