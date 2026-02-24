# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-02-24  
**Scope:** Full repo (excluding generated files and prior feature_ideas reports)

## Summary

- Total markers/phrases found: 35
- By category: TODO (11), NOTE (2), Feature idea (22)
- Proposed features: 2 UI, 1 ML, 1 backend

## Proposed features by area

### UI (2 features)

#### Feature 1: Surface run metrics in Run Summary

- **Rationale:** The backend already computes and returns run and turn metrics, but the UI summary only shows static run fields. Exposing metrics would make the summary more informative without changing core simulation logic.
- **Scope:** Small
- **Evidence:** `simulation/api/routes/simulation.py` exposes `/simulations/metrics`; `simulation/api/services/run_query_service.py` includes `run_metrics` in `RunDetailsResponse`; `ui/components/details/RunSummary.tsx` currently renders a fixed table without metrics.

#### Feature 2: Add feed-algorithm load error state + retry in ConfigForm

- **Rationale:** Feed algorithm list fetch failures are only logged to the console; users see a fallback option without any indication or retry path. A visible error state would reduce silent failures and align with other UI retry patterns.
- **Scope:** Small
- **Evidence:** `ui/components/form/ConfigForm.tsx` logs warnings/errors and falls back to a single option when `getFeedAlgorithms()` fails.

### ML (1 feature)

#### Feature: Support AI-generated posts in feeds

- **Rationale:** Feed generation currently assumes Bluesky posts only, but there is an explicit TODO to add AI-generated posts later. Enabling this would unlock richer simulation behavior and ML-driven content generation.
- **Scope:** Large
- **Evidence:** `simulation/core/models/feeds.py` notes that only Bluesky posts are supported and AI-generated posts should be added later.

### Backend (1 feature)

#### Feature: Make agent handle uniqueness checks atomic

- **Rationale:** Agent creation checks for existing handles before starting a transaction, which can allow race conditions. Moving the uniqueness check into the transaction or enforcing a unique DB constraint would eliminate that gap and provide consistent 409 conflicts.
- **Scope:** Small
- **Evidence:** `simulation/api/services/agent_command_service.py` has a TODO noting the race condition in the pre-transaction handle check.

## Markers and phrases

### File: `ui/components/form/ConfigForm.tsx` (line 153)

**Type:** TODO

**Context:**

```text
152:             >
153:               {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
154:               {algorithms.length === 0 ? (
```

**Original text:**

```text
              {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
```

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO

**Context:**

```text
198:             LLMException: Standardized internal exception (LiteLLM exceptions are converted)
199:             TODO: Consider supporting partial results for batch completions instead of
200:                 all-or-nothing error handling.
```

**Original text:**

```text
            TODO: Consider supporting partial results for batch completions instead of
```

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** Technical debt

**Context:**

```text
57: # Auto-register default providers on import
58: # NOTE: choosing to do this here instead of __init__ so that we can use the
59: # classmethods while assuming that the providers are already imported.
```

**Original text:**

```text
# NOTE: choosing to do this here instead of __init__ so that we can use the
```

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea

**Context:**

```text
60:         raise NotImplementedError(
61:             "We'll revisit this later when actively working with Groq models."
62:         )
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
73:         raise NotImplementedError(
74:             "We'll revisit this later when actively working with Groq models."
75:         )
```

**Original text:**

```text
            "We'll revisit this later when actively working with Groq models."
```

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea

**Context:**

```text
81:         raise NotImplementedError(
82:             "We'll revisit this later when actively working with Gemini models."
83:         )
```

**Original text:**

```text
            "We'll revisit this later when actively working with Gemini models."
```

---

### File: `tests/ml_tooling/llm/test_retry.py` (line 148)

**Type:** Feature idea

**Context:**

```text
147:     def test_retry_llm_completion_respects_max_retries(self):
148:         """Test that decorated function respects max_retries and eventually raises."""
149:         call_count = 0
```

**Original text:**

```text
        """Test that decorated function respects max_retries and eventually raises."""
```

---

### File: `tests/ml_tooling/llm/config/test_model_registry.py` (line 158)

**Type:** Feature idea

**Context:**

```text
157:         # Act
158:         # Default has temperature: 0.0, provider has it too, so we should get it
159:         result = model_config.get_kwarg_value("temperature")
```

**Original text:**

```text
        # Default has temperature: 0.0, provider has it too, so we should get it
```

---

### File: `simulation/core/command_service.py` (line 363)

**Type:** TODO

**Context:**

```text
362: 
363:         # TODO: this log should live within agent_factory.
364:         logger.info(
```

**Original text:**

```text
        # TODO: this log should live within agent_factory.
```

---

### File: `simulation/core/metrics/builtins/actions.py` (line 83)

**Type:** Feature idea

**Context:**

```text
82: 
83:     Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
84:     which loads all turn rows into memory. For large runs, consider replacing
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
```

**Original text:**

```text
# We'll revisit how to add AI-generated posts to feeds later on.
```

---

### File: `simulation/api/routes/simulation.py` (line 340)

**Type:** Feature idea

**Context:**

```text
339:     try:
340:         # Use to_thread for consistency with other async routes and to prepare for real I/O later.
341:         return await asyncio.to_thread(list_runs_dummy)
```

**Original text:**

```text
        # Use to_thread for consistency with other async routes and to prepare for real I/O later.
```

---

### File: `simulation/api/routes/simulation.py` (line 454)

**Type:** Feature idea

**Context:**

```text
453:     try:
454:         # Use to_thread for consistency with other async routes and to prepare for real I/O later.
455:         return await asyncio.to_thread(get_turns_for_run_dummy, run_id=run_id)
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
57: 
58:     # TODO: that this can cause a slight race condition if we do this check
59:     # before the below context manager for writing the agent to the database.
```

**Original text:**

```text
    # TODO: that this can cause a slight race condition if we do this check
```

---

### File: `docs/RULES.md` (line 61)

**Type:** Feature idea

**Context:**

```text
60: 
61: - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
62: 
```

**Original text:**

```text
- Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
```

---

### File: `docs/RULES.md` (line 67)

**Type:** TODO

**Context:**

```text
66: - Follow ci.yml and run those commands (e.g., "ruff", "uv run pytest") and fix errors as needed.
67: - ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.
68: 
```

**Original text:**

```text
- ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.
```

---

### File: `docs/RULES.md` (line 162)

**Type:** TODO

**Context:**

```text
161: - Comment non-obvious design choices: If a choice is made for consistency, future-proofing, or maintainability rather than immediate benefit, add a short comment explaining why, so reviewers and future readers understand the intent.
162: - When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
163: 
```

**Original text:**

```text
- When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
```

---

### File: `docs/plans/2026-02-19_security_headers_482917/plan.md` (line 124)

**Type:** Feature idea

**Context:**

```text
123: - `**fastapi-security` or third-party package**: Adds a dependency for a simple middleware; custom middleware is minimal and matches existing patterns (e.g. `RequestIdMiddleware`).
124: - **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
125: - `**X-XSS-Protection`**: Deprecated in modern browsers; `X-Content-Type-Options: nosniff` and CSP provide better protection; not included.
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
177: - **Separate route (e.g. /agents/create):** Rejected; toggle keeps a single-page flow consistent with View runs / View agents.
178: - **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.
179: 
```

**Original text:**

```text
- **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.
```

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 143)

**Type:** Feature idea

**Context:**

```text
142: - **Custom middleware:** Full control but reinvents rate limiting logic; rejected for YAGNI.
143: - **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.
144: 
```

**Original text:**

```text
- **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.
```

---

### File: `docs/plans/2026-02-18_naive_llm_action_generators_887eadcb/plan.md` (line 181)

**Type:** Feature idea

**Context:**

```text
180: 
181: - **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
182: - **Algorithm filename**: Initially `naive_llm_algorithm.py`; renamed to `algorithm.py` since folder already encodes the name.
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
256: - **Return-all vs batch:** Return-all `GET /v1/simulations/posts` would simplify the API but force the client to filter. MIGRATIONS.md recommends batch lookup; we adopt `?uris=...`.
257: - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
258: - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
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
257: - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
258: - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
259: 
```

**Original text:**

```text
- **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
```

---

### File: `docs/plans/2026-02-23_metrics_metadata_api_9c4e2a/plan.md` (line 148)

**Type:** Feature idea

**Context:**

```text
147: 
148: - **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
149: - **Using MetricsRegistry:** The registry is built from `BUILTIN_METRICS` and used for computation. Listing metadata does not require the registry—iterating over `BUILTIN_METRICS` is simpler and avoids coupling the API to the registry's construction.
```

**Original text:**

```text
- **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
```

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Feature idea

**Context:**

```text
19: 
20: With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.
21: 
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
7: 
8: - Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
9: - Algorithms/Simulation: [Create the first liking algorithm (#56)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/56), [Create the first follow algorithm (#65)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/65), [Create the first commenting algorithm (#66)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/66), [Create a new composable metrics pipeline (#69)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/69), [Change default like algo to follow the same conventions as the default comment and follow algos (#80)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/80), [Migrate feed ranking algorithms to a registry pattern (#92)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/92)
```

**Original text:**

```text
- Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
```

---

### File: `feeds/candidate_generation.py` (line 12)

**Type:** TODO

**Context:**

```text
11: 
12: # TODO: we can get arbitrarily complex with how we do this later
13: # on, but as a first pass it's easy enough to just load all the posts.
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
69:     for agent in agents:
70:         # TODO: right now we load all posts per agent, but obviously
71:         # can optimize and personalize later to save on queries.
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
70:         # TODO: right now we load all posts per agent, but obviously
71:         # can optimize and personalize later to save on queries.
72:         feed = _generate_single_agent_feed(
```

**Original text:**

```text
        # can optimize and personalize later to save on queries.
```

---

### File: `feeds/algorithms/interfaces.py` (line 51)

**Type:** TODO

**Context:**

```text
50:             BlueskyFeedPost
51:         ],  # TODO: decouple from Bluesky-specific type
52:         agent: SocialMediaAgent,
```

**Original text:**

```text
        ],  # TODO: decouple from Bluesky-specific type
```

---

### File: `db/schema.py` (line 10)

**Type:** Feature idea

**Context:**

```text
9: - The initial migration in this repo intentionally omits the
10:   `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
11: """
```

**Original text:**

```text
  `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
```

---

### File: `db/schema.py` (line 93)

**Type:** Technical debt

**Context:**

```text
92:     sa.Column("created_at", sa.Text(), nullable=False),
93:     # NOTE: This FK is applied by the second Alembic migration.
94:     sa.ForeignKeyConstraint(
```

**Original text:**

```text
    # NOTE: This FK is applied by the second Alembic migration.
```

---

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO

**Context:**

```text
2: 
3: TODO: For caching or async, consider a caching layer around
4: read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).
```

**Original text:**

```text
TODO: For caching or async, consider a caching layer around
```

---
