# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-02-25  
**Scope:** Full repo

## Summary

- Total markers/phrases found: 37
- By category: TODO (11), NOTE (3), Feature idea (23)
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Surface run status + timestamps in Run Detail

- **Rationale:** Run details already return status/started/completed timestamps, but UI drops them, so the run detail view lacks lifecycle context.
- **Scope:** Small
- **Evidence:** `simulation/api/schemas/simulation.py` (RunDetailsResponse includes status/created_at/started_at/completed_at), `ui/lib/api/simulation.ts` (getRunDetails intentionally omits fields), `ui/components/details/RunParametersBlock.tsx` (only shows config fields).

#### Feature 2: Add run status filtering in Run History

- **Rationale:** Runs already expose status, but the sidebar only lists all runs without any filter or grouping.
- **Scope:** Small
- **Evidence:** `ui/components/sidebars/RunHistorySidebar.tsx` (renders run.status per item), `ui/lib/api/simulation.ts` (Run mapping includes status).

#### Feature 3: Show feed-algorithm/metrics fetch errors inline

- **Rationale:** ConfigForm currently logs fetch failures to console only; a visible banner or inline warning would reduce confusion when APIs fail.
- **Scope:** Small
- **Evidence:** `ui/components/form/ConfigForm.tsx` (console.warn/console.error and TODO to switch to structured logging).

### ML (3 features)

#### Feature 1: Generalize feed algorithm inputs beyond Bluesky post types

- **Rationale:** Feed algorithms are coupled to Bluesky-specific post types, blocking other post sources or synthetic posts.
- **Scope:** Large
- **Evidence:** `feeds/algorithms/interfaces.py` (TODO to decouple from Bluesky-specific type).

#### Feature 2: Support non-Bluesky feed items in core feed models

- **Rationale:** Core feed models explicitly limit to Bluesky posts, which blocks multi-network or synthetic feed content.
- **Scope:** Large
- **Evidence:** `simulation/core/models/feeds.py` (TODO noting only Bluesky posts supported).

#### Feature 3: DB-side aggregation for run action totals metric

- **Rationale:** Metrics aggregation currently loads all turn metadata into memory; DB aggregation would scale better for large runs.
- **Scope:** Small
- **Evidence:** `simulation/core/metrics/builtins/actions.py` (Limitation comment recommending DB-side aggregation).

### Backend (3 features)

#### Feature 1: Persist and return agent actions in turn payloads

- **Rationale:** The turns endpoint returns empty `agent_actions`, which prevents UI from showing action details without extra sources.
- **Scope:** Large
- **Evidence:** `simulation/api/services/run_query_service.py` (note that agent_actions are not persisted and returned empty).

#### Feature 2: Add pagination/limits to `/simulations/posts`

- **Rationale:** Unfiltered post fetches are hard-capped server-side, but the API lacks a limit/offset for controlled paging.
- **Scope:** Small
- **Evidence:** `simulation/api/services/run_query_service.py` (MAX_UNFILTERED_POSTS cap), `simulation/api/routes/simulation.py` (posts endpoint only supports `uris`).

#### Feature 3: Include `feed_algorithm_config` in run details config

- **Rationale:** Run details omit `feed_algorithm_config`, so the UI cannot show the algorithm configuration used in a run.
- **Scope:** Small
- **Evidence:** `simulation/api/schemas/simulation.py` (RunConfigDetail lacks feed_algorithm_config), `ui/lib/api/simulation.ts` (maps feedAlgorithmConfig to null).

## Markers and phrases

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO
**Context:**

```text
1: """SQLite implementation of agent persona bio database adapter.
2: 
3: TODO: For caching or async, consider a caching layer around
4: read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).
5: """
```

**Original text:**

```text
TODO: For caching or async, consider a caching layer around
```

---

### File: `db/schema.py` (line 10)

**Type:** Feature idea
**Context:**

```text
8: - Keep this schema aligned with what migrations produce at HEAD.
9: - The initial migration in this repo intentionally omits the
10:   `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
11: """
12: 
```

**Original text:**

```text
`generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
```

---

### File: `db/schema.py` (line 94)

**Type:** NOTE
**Context:**

```text
92:     sa.Column("post_uris", sa.Text(), nullable=False),
93:     sa.Column("created_at", sa.Text(), nullable=False),
94:     # NOTE: This FK is applied by the second Alembic migration.
95:     sa.ForeignKeyConstraint(
96:         ["run_id"],
```

**Original text:**

```text
# NOTE: This FK is applied by the second Alembic migration.
```

---

### File: `docs/RULES.md` (line 62)

**Type:** Feature idea
**Context:**

```text
60: API design and rollout
61: 
62: - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
63: - For optional list fields where "no items" is a valid intent (e.g. metric_keys), prefer the contract omit the field for "none" and reject empty list in validation (raise with a message like "cannot be empty; omit the field if you don't want any"). That keeps "absent" and "present but empty" distinct and avoids ambiguous semantics.
64: 
```

**Original text:**

```text
- Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
```

---

### File: `docs/RULES.md` (line 69)

**Type:** TODO
**Context:**

```text
67: - Run all pre-commit hooks.
68: - Follow ci.yml and run those commands (e.g., "ruff", "uv run pytest") and fix errors as needed.
69: - ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.
70: 
71: Testing:
```

**Original text:**

```text
- ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.
```

---

### File: `docs/RULES.md` (line 165)

**Type:** TODO
**Context:**

```text
163: - Prefer documenting intent at the boundary over leaving semantics to be inferred from implementation details.
164: - Comment non-obvious design choices: If a choice is made for consistency, future-proofing, or maintainability rather than immediate benefit, add a short comment explaining why, so reviewers and future readers understand the intent.
165: - When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
166: 
167: Persistence and model boundaries
```

**Original text:**

```text
- When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
```

---

### File: `docs/plans/2026-02-18_naive_llm_action_generators_887eadcb/plan.md` (line 181)

**Type:** Feature idea
**Context:**

```text
179: ## Alternative Approaches
180: 
181: - **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
182: - **Algorithm filename**: Initially `naive_llm_algorithm.py`; renamed to `algorithm.py` since folder already encodes the name.
183: - **Env loading (e2e)**: Initially `load_dotenv()`; switched to `EnvVarsContainer` after merge of [PR #100](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/100).
```

**Original text:**

```text
- **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
```

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 257)

**Type:** Feature idea
**Context:**

```text
255: 
256: - **Return-all vs batch:** Return-all `GET /v1/simulations/posts` would simplify the API but force the client to filter. MIGRATIONS.md recommends batch lookup; we adopt `?uris=...`.
257: - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
258: - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
259: 
```

**Original text:**

```text
- **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
```

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 258)

**Type:** Feature idea
**Context:**

```text
256: - **Return-all vs batch:** Return-all `GET /v1/simulations/posts` would simplify the API but force the client to filter. MIGRATIONS.md recommends batch lookup; we adopt `?uris=...`.
257: - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
258: - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
259: 
260: ---
```

**Original text:**

```text
- **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
```

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 143)

**Type:** Feature idea
**Context:**

```text
141: - **fastapi-limiter:** Uses `Depends(RateLimiter(...))`. DI-based, no Redis. Chosen slowapi because it is more widely used and has Redis support when we scale to multiple workers.
142: - **Custom middleware:** Full control but reinvents rate limiting logic; rejected for YAGNI.
143: - **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.
144: 
145: ---
```

**Original text:**

```text
- **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.
```

---

### File: `docs/plans/2026-02-19_security_headers_482917/plan.md` (line 124)

**Type:** Feature idea
**Context:**

```text
122: - **Per-route decorator**: Would require decorating every route; middleware is DRY and applies to all responses.
123: - `**fastapi-security` or third-party package**: Adds a dependency for a simple middleware; custom middleware is minimal and matches existing patterns (e.g. `RequestIdMiddleware`).
124: - **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
125: - `**X-XSS-Protection`**: Deprecated in modern browsers; `X-Content-Type-Options: nosniff` and CSP provide better protection; not included.
126: 
```

**Original text:**

```text
- **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
```

---

### File: `docs/plans/2026-02-23_create_agent_tab_741a962a/create_agent_tab_741a962a.plan.md` (line 178)

**Type:** Feature idea
**Context:**

```text
176: - **Nested under View agents:** A "Create new" button within agents mode (like "Start New Run" under runs). Rejected: user requested a dedicated tab for clearer separation.
177: - **Separate route (e.g. /agents/create):** Rejected; toggle keeps a single-page flow consistent with View runs / View agents.
178: - **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.
179: 
180: ---
```

**Original text:**

```text
- **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.
```

---

### File: `docs/plans/2026-02-23_metrics_metadata_api_9c4e2a/plan.md` (line 148)

**Type:** Feature idea
**Context:**

```text
146: ## Alternative Approaches
147: 
148: - **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
149: - **Using MetricsRegistry:** The registry is built from `BUILTIN_METRICS` and used for computation. Listing metadata does not require the registry—iterating over `BUILTIN_METRICS` is simpler and avoids coupling the API to the registry's construction.
150: 
```

**Original text:**

```text
- **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
```

---

### File: `docs/plans/2026-02-24_metrics_selector_ui_9f3a2b/metrics_selector_ui_34c8ca07.plan.md` (line 131)

**Type:** Feature idea
**Context:**

```text
129: **File: [ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)** (getDefaultConfig)
130: 
131: - If the backend default config endpoint is later extended to return `metric_keys`, map it to `metricKeys` in the returned `RunConfig`. For Part 3, the endpoint may not include it; then `defaultConfig.metricKeys` is undefined and MetricSelector initializes to "all" once metrics load.
132: 
133: ### 6. After screenshots (UI)
```

**Original text:**

```text
- If the backend default config endpoint is later extended to return `metric_keys`, map it to `metricKeys` in the returned `RunConfig`. For Part 3, the endpoint may not include it; then `defaultConfig.metricKeys` is undefined and MetricSelector initializes to "all" once metrics load.
```

---

### File: `docs/plans/2026-02-24_run_params_display_4d5e6f/run_params_display_part_4_7ad4614e.plan.md` (line 166)

**Type:** Feature idea
**Context:**

```text
164: - **Fetch run details for every run in the list:** Would require N requests and more state; fetch-on-select keeps a single extra request when the user opens a run.
165: - **Display names in params block:** Would require passing `Metric[]` (e.g. from `getAvailableMetrics`) into the detail view or fetching metrics there and mapping key → display name. Part 4 ships with keys only; display names can be a follow-up.
166: - **Separate run-details state:** Keeping `runDetailsByRunId` only for the params block is possible; reusing `runConfigs` keeps one source of truth and allows reusing config for "edit/restart with same config" later.
167: 
168: ---
```

**Original text:**

```text
- **Separate run-details state:** Keeping `runDetailsByRunId` only for the params block is possible; reusing `runConfigs` keeps one source of truth and allows reusing config for "edit/restart with same config" later.
```

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Feature idea
**Context:**

```text
18: ## Workers
19: 
20: With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.
21: 
22: ## Timeouts
```

**Original text:**

```text
With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.
```

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 103)

**Type:** Feature idea
**Context:**

```text
101: - Keep worker count conservative with SQLite to reduce lock contention.
102: - Sync run requests can take time; configure client and platform timeouts accordingly.
103: - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
```

**Original text:**

```text
- For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
```

---

### File: `docs/weekly_updates/2026-02-16_2026-02-21.md` (line 8)

**Type:** Feature idea
**Context:**

```text
6: ## Scope of PRs
7: 
8: - Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
9: - Algorithms/Simulation: [Create the first liking algorithm (#56)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/56), [Create the first follow algorithm (#65)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/65), [Create the first commenting algorithm (#66)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/66), [Create a new composable metrics pipeline (#69)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/69), [Change default like algo to follow the same conventions as the default comment and follow algos (#80)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/80), [Migrate feed ranking algorithms to a registry pattern (#92)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/92)
10: - UI/Frontend: [refactor UI to more modularized components (#63)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/63), [Add loading/error UI in the sidebar and detail panels (#84)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/84), [Add feed algorithm selection to ConfigForm (#99)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/99)
```

**Original text:**

```text
- Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
```

---

### File: `feeds/algorithms/interfaces.py` (line 51)

**Type:** TODO
**Context:**

```text
49:         candidate_posts: list[
50:             BlueskyFeedPost
51:         ],  # TODO: decouple from Bluesky-specific type
52:         agent: SocialMediaAgent,
53:         limit: int,
```

**Original text:**

```text
],  # TODO: decouple from Bluesky-specific type
```

---

### File: `feeds/candidate_generation.py` (line 12)

**Type:** TODO
**Context:**

```text
10: 
11: 
12: # TODO: we can get arbitrarily complex with how we do this later
13: # on, but as a first pass it's easy enough to just load all the posts.
14: def load_posts() -> list[BlueskyFeedPost]:
```

**Original text:**

```text
# TODO: we can get arbitrarily complex with how we do this later
```

---

### File: `feeds/feed_generator.py` (line 70)

**Type:** TODO
**Context:**

```text
68:     feeds: dict[str, GeneratedFeed] = {}
69:     for agent in agents:
70:         # TODO: right now we load all posts per agent, but obviously
71:         # can optimize and personalize later to save on queries.
72:         feed = _generate_single_agent_feed(
```

**Original text:**

```text
# TODO: right now we load all posts per agent, but obviously
```

---

### File: `feeds/feed_generator.py` (line 71)

**Type:** Feature idea
**Context:**

```text
69:     for agent in agents:
70:         # TODO: right now we load all posts per agent, but obviously
71:         # can optimize and personalize later to save on queries.
72:         feed = _generate_single_agent_feed(
73:             agent=agent,
```

**Original text:**

```text
# can optimize and personalize later to save on queries.
```

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO
**Context:**

```text
197:         Raises:
198:             LLMException: Standardized internal exception (LiteLLM exceptions are converted)
199:             TODO: Consider supporting partial results for batch completions instead of
200:                 all-or-nothing error handling.
201:         """
```

**Original text:**

```text
TODO: Consider supporting partial results for batch completions instead of
```

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea
**Context:**

```text
80:         """Format Gemini's structured output format."""
81:         raise NotImplementedError(
82:             "We'll revisit this later when actively working with Gemini models."
83:         )
84: 
```

**Original text:**

```text
"We'll revisit this later when actively working with Gemini models."
```

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea
**Context:**

```text
59:         """Format Groq's structured output format."""
60:         raise NotImplementedError(
61:             "We'll revisit this later when actively working with Groq models."
62:         )
63: 
```

**Original text:**

```text
"We'll revisit this later when actively working with Groq models."
```

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 74)

**Type:** Feature idea
**Context:**

```text
72:         """Prepare Groq-specific completion kwargs."""
73:         raise NotImplementedError(
74:             "We'll revisit this later when actively working with Groq models."
75:         )
```

**Original text:**

```text
"We'll revisit this later when actively working with Groq models."
```

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE
**Context:**

```text
56: 
57: # Auto-register default providers on import
58: # NOTE: choosing to do this here instead of __init__ so that we can use the
59: # classmethods while assuming that the providers are already imported.
60: LLMProviderRegistry.register(OpenAIProvider)
```

**Original text:**

```text
# NOTE: choosing to do this here instead of __init__ so that we can use the
```

---

### File: `simulation/api/routes/simulation.py` (line 345)

**Type:** Feature idea
**Context:**

```text
343:     try:
344:         engine = request.app.state.engine
345:         # Use to_thread for consistency with other async routes and to prepare for real I/O later.
346:         return await asyncio.to_thread(list_runs, engine=engine)
347:     except Exception:
```

**Original text:**

```text
# Use to_thread for consistency with other async routes and to prepare for real I/O later.
```

---

### File: `simulation/api/services/agent_command_service.py` (line 58)

**Type:** TODO
**Context:**

```text
56:         )
57: 
58:     # TODO: that this can cause a slight race condition if we do this check
59:     # before the below context manager for writing the agent to the database.
60:     # This is a known issue, and we'll revisit this in the future.
```

**Original text:**

```text
# TODO: that this can cause a slight race condition if we do this check
```

---

### File: `simulation/core/command_service.py` (line 386)

**Type:** TODO
**Context:**

```text
384:         validate_duplicate_agent_handles(agents=agents)
385: 
386:         # TODO: this log should live within agent_factory.
387:         logger.info(
388:             "Created %d agents (requested: %d) for run %s",
```

**Original text:**

```text
# TODO: this log should live within agent_factory.
```

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Feature idea
**Context:**

```text
83:     """Aggregated action counts across all turns, by type.
84: 
85:     Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
86:     which loads all turn rows into memory. For large runs, consider replacing
87:     with DB-side aggregation (e.g. run_repo.aggregate_action_totals(run_id)
```

**Original text:**

```text
Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
```

---

### File: `simulation/core/models/feeds.py` (line 1)

**Type:** TODO
**Context:**

```text
1: # TODO: for now, we support only Bluesky posts being added to feeds.
2: # We'll revisit how to add AI-generated posts to feeds later on.
3: import uuid
```

**Original text:**

```text
# TODO: for now, we support only Bluesky posts being added to feeds.
```

---

### File: `simulation/core/models/feeds.py` (line 2)

**Type:** Feature idea
**Context:**

```text
1: # TODO: for now, we support only Bluesky posts being added to feeds.
2: # We'll revisit how to add AI-generated posts to feeds later on.
3: import uuid
4: 
```

**Original text:**

```text
# We'll revisit how to add AI-generated posts to feeds later on.
```

---

### File: `tests/ml_tooling/llm/config/test_model_registry.py` (line 158)

**Type:** Feature idea
**Context:**

```text
156: 
157:         # Act
158:         # Default has temperature: 0.0, provider has it too, so we should get it
159:         result = model_config.get_kwarg_value("temperature")
160: 
```

**Original text:**

```text
# Default has temperature: 0.0, provider has it too, so we should get it
```

---

### File: `tests/ml_tooling/llm/test_retry.py` (line 148)

**Type:** Feature idea
**Context:**

```text
146: 
147:     def test_retry_llm_completion_respects_max_retries(self):
148:         """Test that decorated function respects max_retries and eventually raises."""
149:         call_count = 0
150:         exception_instance = LLMTransientError("Rate limit exceeded")
```

**Original text:**

```text
"""Test that decorated function respects max_retries and eventually raises."""
```

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO
**Context:**

```text
189:               className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
190:             >
191:               {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
192:               {algorithms.length === 0 ? (
193:                 <option value="chronological">Chronological</option>
```

**Original text:**

```text
{/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
```

---

### File: `ui/lib/api/simulation.ts` (line 285)

**Type:** NOTE
**Context:**

```text
283: }
284: 
285: // NOTE: `getRunDetails` intentionally returns only `{ runId, config }`, where `config` is mapped via
286: // `mapRunDetailsConfig`. `mapRunDetailsConfig` intentionally sets `feedAlgorithmConfig` to null
287: // because `ApiRunConfigDetail` (RunConfigDetail) does not include `feed_algorithm_config`. Other
```

**Original text:**

```text
// NOTE: `getRunDetails` intentionally returns only `{ runId, config }`, where `config` is mapped via
```

---
