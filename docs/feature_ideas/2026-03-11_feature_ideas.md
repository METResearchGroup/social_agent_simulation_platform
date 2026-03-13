# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-03-11  
**Scope:** Active source + canonical docs (`ui/`, `simulation/core/`, `ml_tooling/`, `simulation/api/`, `feeds/`, `db/`, `docs/runbooks/`, `docs/RULES.md`), excluding generated/vendor artifacts and existing `docs/feature_ideas/` reports

## Summary

- Total markers/phrases found: 16
- By category: TODO (7), NOTE (2), future-improvement phrases (`later` / `consider` / `not yet supported`) (7)
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Add run timeline metadata to Run History cards

- **Rationale:** Run objects and run-detail payloads already carry timestamps (`created_at`, `started_at`, `completed_at`), but the sidebar currently renders only `runId`, counts, and `status`. Showing timestamps/duration would improve triage for long/failed runs.
- **Scope:** Small
- **Evidence:** `ui/components/sidebars/RunHistorySidebar.tsx` renders only status/counts (lines 156-164); `simulation/api/schemas/simulation.py` defines timestamp fields on `RunDetailsResponse` (lines 242-244).

#### Feature 2: Support richer feed-algorithm config field types in ConfigForm

- **Rationale:** Unsupported config schema types are currently surfaced as validation errors, which blocks required fields when algorithms expose non-primitive schema shapes.
- **Scope:** Small
- **Evidence:** `ui/components/form/AlgorithmSettingsSection.tsx` shows `Unsupported config field schema` (line 57); `ui/components/form/config-schema.ts` maps unknown fields to `kind: 'unsupported'` and errors on required unsupported fields (lines 141, 170-172).

#### Feature 3: Add agent sorting/filter chips by social stats

- **Rationale:** Agent objects expose `followers`, `following`, and `postsCount`, but current UI search is handle-only. Sorting/filter controls would make large agent sets easier to inspect.
- **Scope:** Small
- **Evidence:** `ui/components/details/AgentDetail.tsx` displays `followers/following/posts` (lines 62-72); sidebar search is currently only `Search by handle` (placeholder in `ui/components/sidebars/RunHistorySidebar.tsx`, line 219).

### ML (3 features)

#### Feature 1: Add personalized/batched candidate post retrieval for feed generation

- **Rationale:** Current feed generation loads all posts repeatedly and calls out optimization/personalization as future work; this is a clear scalability/performance debt marker.
- **Scope:** Large
- **Evidence:** `feeds/feed_generator.py` TODO says it currently loads all posts per agent and should optimize/personalize later (lines 73-74); `feeds/candidate_generation.py` TODO says loading all posts is only a first pass (lines 8-9).

#### Feature 2: Make per-post comment multiplicity configurable

- **Rationale:** The naive LLM comment generator currently dedupes by `post_id`, implicitly capping comments to one per post. Exposing this as policy/config enables richer behavior experiments.
- **Scope:** Small
- **Evidence:** `simulation/core/action_generators/comment/algorithms/naive_llm/algorithm.py` notes current behavior implies max one comment per post (line 103), then filters/dedupes by post ID (lines 104-108).

#### Feature 3: Add provider capability-aware fallback selection for model routing

- **Rationale:** Provider registry assumes a single provider supports a model; provider base indicates capabilities differ (structured output may be unsupported). Capability-aware fallback would reduce hard failures.
- **Scope:** Large
- **Evidence:** `ml_tooling/llm/providers/registry.py` explicitly assumes one provider per model (line 39); `ml_tooling/llm/providers/base.py` notes provider capability differences for structured output (lines 70-74).

### Backend (3 features)

#### Feature 1: Add `PATCH /simulations/agents/{handle}` for in-place profile updates

- **Rationale:** Agent API currently supports create/list/delete but not update; editing bio/display name requires delete/recreate workflows.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py` defines POST/GET/DELETE for `/simulations/agents` (lines 117, 135, 175) with no PATCH endpoint.

#### Feature 2: Include `feed_algorithm_config` in run-details config response

- **Rationale:** UI currently sets `feedAlgorithmConfig` to `null` because API run-details config omits it, losing reproducibility for algorithm settings.
- **Scope:** Small
- **Evidence:** `simulation/api/schemas/simulation.py` `RunConfigDetail` lacks `feed_algorithm_config` (lines 122-129); `ui/lib/api/simulation.ts` comment says it intentionally sets `feedAlgorithmConfig` to `null` due missing backend field (lines 303-305, 312).

#### Feature 3: Add pagination for `/simulations/posts` unfiltered reads

- **Rationale:** Unfiltered post fetches are hard-capped server-side (`MAX_UNFILTERED_POSTS`), which can silently truncate large datasets; explicit pagination/cursor APIs would make behavior deterministic.
- **Scope:** Large
- **Evidence:** `simulation/api/services/run_query_service.py` notes unfiltered calls return only up to `MAX_UNFILTERED_POSTS` (lines 102, 106); route currently exposes `/simulations/posts` without pagination params (`simulation/api/routes/simulation.py`, lines 241-256).

## Markers and phrases

### File: `feeds/feed_generator.py` (line 73)

**Type:** TODO  
**Context:** Feed generation loop

**Original text:**

```text
# TODO: right now we load all posts per agent, but obviously
```

---

### File: `feeds/feed_generator.py` (line 74)

**Type:** Future improvement phrase (`optimize`, `later`)  
**Context:** Follow-up line for feed-generation TODO

**Original text:**

```text
# can optimize and personalize later to save on queries.
```

---

### File: `feeds/candidate_generation.py` (line 8)

**Type:** TODO  
**Context:** Candidate post loading strategy

**Original text:**

```text
# TODO: we can get arbitrarily complex with how we do this later
```

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO  
**Context:** Batch completion error-handling docs

**Original text:**

```text
TODO: Consider supporting partial results for batch completions instead of
```

---

### File: `simulation/api/services/agent_command_service.py` (line 33)

**Type:** TODO  
**Context:** Handle uniqueness check before transaction

**Original text:**

```text
# TODO: that this can cause a slight race condition if we do this check
```

---

### File: `simulation/core/command_service.py` (line 398)

**Type:** TODO  
**Context:** Agent creation logging location

**Original text:**

```text
# TODO: this log should live within agent_factory.
```

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO  
**Context:** Feed algorithm selector options render

**Original text:**

```text
{/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
```

---

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO  
**Context:** Module docstring for adapter extension points

**Original text:**

```text
TODO: For caching or async, consider a caching layer around
```

---

### File: `simulation/api/services/run_query_service.py` (line 47)

**Type:** NOTE  
**Context:** Turn payload assembly docs

**Original text:**

```text
Note: agent_actions are currently not persisted in SQLite. This endpoint returns
```

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Future improvement phrase (`revisit later`)  
**Context:** Metric implementation docstring

**Original text:**

```text
Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
```

---

### File: `simulation/core/metrics/builtins/actions.py` (line 86)

**Type:** Future improvement phrase (`consider`)  
**Context:** Metric implementation docstring

**Original text:**

```text
which loads all turn rows into memory. For large runs, consider replacing
```

---

### File: `simulation/api/routes/simulation.py` (line 356)

**Type:** Future improvement phrase (`later`)  
**Context:** Runs list route implementation

**Original text:**

```text
# Use to_thread for consistency with other async routes and to prepare for real I/O later.
```

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Future improvement phrase (`later`)  
**Context:** Structured output support

**Original text:**

```text
"We'll revisit this later when actively working with Gemini models."
```

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Future improvement phrase (`later`)  
**Context:** Structured output support

**Original text:**

```text
"We'll revisit this later when actively working with Groq models."
```

---

### File: `simulation/api/schemas/simulation.py` (line 144)

**Type:** Feature idea phrase (`not yet supported`)  
**Context:** Create-agent request docs

**Original text:**

```text
Fast-follows (not yet supported):
```

---

### File: `ui/lib/api/simulation.ts` (line 302)

**Type:** NOTE  
**Context:** Run-details API mapping

**Original text:**

```text
// NOTE: `getRunDetails` intentionally returns only `{ runId, config }`, where `config` is mapped via
```

---
