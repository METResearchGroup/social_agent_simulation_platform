# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-02-21  
**Scope:** Full repo

## Summary

- Total markers/phrases found: 25
- By category: TODO (8), NOTE (2), Feature idea (10), Technical debt (5)
- Proposed features: 2 UI, 1 ML, 1 backend
- Skipped ambiguous phrase matches in tests (2):
  - `tests/ml_tooling/llm/config/test_model_registry.py:158` ("we should get it")
  - `tests/ml_tooling/llm/test_retry.py:148` ("eventually raises")

## Proposed features by area

### UI (2 features)

#### Feature 1: Render algorithm-specific config inputs in ConfigForm
- **Rationale:** Feed algorithms expose `config_schema`, but the UI only renders a single select + description. This blocks algorithm-specific tuning in the start form.
- **Scope:** Small
- **Evidence:** `feeds/algorithms/interfaces.py` defines `FeedAlgorithmMetadata.config_schema`; `ui/types/index.ts` includes `FeedAlgorithm.configSchema`; `ui/components/form/ConfigForm.tsx` only renders the select and description.

#### Feature 2: Show post previews for comment actions in AgentDetail
- **Rationale:** Comment actions currently show only `postUri`, even though posts are already fetched for the turn. Displaying the post content would make agent behavior easier to interpret.
- **Scope:** Small
- **Evidence:** `ui/components/details/AgentDetail.tsx` renders comment actions as `Comment on post: {action.postUri}`; `ui/components/details/DetailsPanel.tsx` already loads `postsByUri` for the current turn.

### ML (1 feature)

#### Feature: Add AI-generated posts to feeds
- **Rationale:** Feeds are currently limited to Bluesky posts; the code explicitly calls out adding AI-generated posts later.
- **Scope:** Large
- **Evidence:** `simulation/core/models/feeds.py` TODO notes only Bluesky posts are supported and AI-generated posts are deferred.

### Backend (1 feature)

#### Feature: Replace dummy run/turn/agent/post queries with real persistence
- **Rationale:** The API routes use dummy data services for runs, turns, agents, and posts, with comments suggesting later replacement. This limits real-world usage and API fidelity.
- **Scope:** Large
- **Evidence:** `simulation/api/routes/simulation.py` uses `list_runs_dummy`, `get_turns_for_run_dummy`, `list_agents_dummy`, `get_posts_by_uris_dummy`; `simulation/api/services/run_query_service.py` returns dummy data.

## Markers and phrases

### File: `simulation/main.py` (line 14)

**Type:** TODO  
**Context:** File-level note about CLI entrypoint migration.

> # TODO: This file will be deprecated in favor of `simulation/cli/main.py` in future PR

---

### File: `feeds/candidate_generation.py` (line 11)

**Type:** TODO  
**Context:** Candidate post loading strategy is intentionally simple for now.

> # TODO: we can get arbitrarily complex with how we do this later
> # on, but as a first pass it's easy enough to just load all the posts.

---

### File: `db/schema.py` (line 10)

**Type:** Technical debt  
**Context:** Docstring notes a delayed FK migration.

> `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.

---

### File: `db/schema.py` (line 93)

**Type:** NOTE  
**Context:** FK applied by a later migration.

> # NOTE: This FK is applied by the second Alembic migration.

---

### File: `feeds/feed_generator.py` (line 64)

**Type:** TODO  
**Context:** Feed generation loads all posts per agent; optimization deferred.

> # TODO: right now we load all posts per agent, but obviously
> # can optimize and personalize later to save on queries.

---

### File: `feeds/algorithms/interfaces.py` (line 50)

**Type:** TODO  
**Context:** Feed algorithm interface is Bluesky-specific.

> ],  # TODO: decouple from Bluesky-specific type

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO  
**Context:** Batch completions are all-or-nothing.

> TODO: Consider supporting partial results for batch completions instead of
>     all-or-nothing error handling.

---

### File: `docs/RULES.md` (line 61)

**Type:** Feature idea  
**Context:** Future async/job-based API guidance.

> - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.

---

### File: `docs/RULES.md` (line 67)

**Type:** Technical debt  
**Context:** Process note referencing TODO items.

> - ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE  
**Context:** Auto-registration location rationale.

> # NOTE: choosing to do this here instead of __init__ so that we can use the
> # classmethods while assuming that the providers are already imported.

---

### File: `simulation/core/models/feeds.py` (line 1)

**Type:** TODO  
**Context:** AI-generated posts deferred.

> # TODO: for now, we support only Bluesky posts being added to feeds.
> # We'll revisit how to add AI-generated posts to feeds later on.

---

### File: `ui/components/form/ConfigForm.tsx` (line 72)

**Type:** TODO  
**Context:** Logging is console-only.

> {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}

---

### File: `simulation/core/command_service.py` (line 355)

**Type:** TODO  
**Context:** Logging location refactor.

> # TODO: this log should live within agent_factory.

---

### File: `simulation/api/routes/simulation.py` (line 250)

**Type:** Technical debt  
**Context:** Sync dummy data call, future real I/O.

> # Use to_thread for consistency with other async routes and to prepare for real I/O later.

---

### File: `simulation/api/routes/simulation.py` (line 316)

**Type:** Technical debt  
**Context:** Sync dummy data call, future real I/O.

> # Use to_thread for consistency with other async routes and to prepare for real I/O later.

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea  
**Context:** Structured output formatting deferred.

> "We'll revisit this later when actively working with Gemini models."

---

### File: `simulation/core/metrics/builtins/actions.py` (line 83)

**Type:** Technical debt  
**Context:** In-memory aggregation is a scalability limitation.

> Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
> which loads all turn rows into memory. For large runs, consider replacing
> with DB-side aggregation (e.g. run_repo.aggregate_action_totals(run_id)
> returning dict[TurnAction, int], or MetricsSqlExecutor with a SQL GROUP BY
> on turn metadata).

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea  
**Context:** Structured output formatting deferred.

> "We'll revisit this later when actively working with Groq models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 74)

**Type:** Feature idea  
**Context:** Completion kwargs for Groq provider deferred.

> "We'll revisit this later when actively working with Groq models."

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 101)

**Type:** Feature idea  
**Context:** Server DB migration planned for later phase.

> - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Feature idea  
**Context:** Server DB migration planned for later phase.

> With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

---

### File: `docs/plans/2026-02-19_security_headers_482917/plan.md` (line 124)

**Type:** Feature idea  
**Context:** CSP header deferred.

> - **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 143)

**Type:** Feature idea  
**Context:** Edge/proxy rate limiting deferred.

> - **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 257)

**Type:** Feature idea  
**Context:** Alternative response shape for turns.

> - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 258)

**Type:** Feature idea  
**Context:** Alternative service module organization.

> - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.

