# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-02-25  
**Scope:** Full repo

## Summary

- Total markers/phrases found: 33
- By category: NOTE (2), TODO (10), eventually (1), later (18), support for (1), we should (1)
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Add turn/run metrics display in run detail view

- **Rationale:** The UI fetches runs and turns but does not surface computed metrics, even though the API schemas include them.
- **Scope:** Small
- **Evidence:** `ui/types/api.generated.ts` includes `metrics` fields on turn/run schemas; `ui/lib/api/simulation.ts` `mapTurn()` ignores metrics; `ui/components/details/DetailsPanel.tsx` only renders feeds/actions.

#### Feature 2: Preselect metrics from default config when backend provides `metric_keys`

- **Rationale:** The MetricSelector supports selections, but default config mapping ignores `metric_keys`; a plan note calls out a future backend extension.
- **Scope:** Small
- **Evidence:** `ui/lib/api/simulation.ts` `getDefaultConfig()` returns only `num_agents/num_turns`; `docs/plans/2026-02-24_metrics_selector_ui_9f3a2b/metrics_selector_ui_34c8ca07.plan.md` notes mapping `metric_keys` to `metricKeys` once available.

#### Feature 3: Add agent search/filtering in agent lists (View agents + linkable agents)

- **Rationale:** Agent lists are paginated with load-more and can grow large; no search/filter currently exists in UI.
- **Scope:** Small
- **Evidence:** `ui/components/agents/AgentsView.tsx` and `ui/components/agents/CreateAgentView.tsx` render lists without filtering; `ui/hooks/useSimulationPageState.ts` uses `getAgents()` with `limit/offset` only.

### ML (3 features)

#### Feature 1: Support AI-generated posts in feeds

- **Rationale:** Feeds are currently constrained to Bluesky posts; comments indicate future support for AI-generated posts.
- **Scope:** Large
- **Evidence:** `simulation/core/models/feeds.py` notes only Bluesky posts are supported and AI-generated posts are a future addition.

#### Feature 2: Implement structured output support for Gemini/Groq providers

- **Rationale:** Gemini and Groq providers raise `NotImplementedError` for structured outputs, limiting parity with other providers.
- **Scope:** Small
- **Evidence:** `ml_tooling/llm/providers/gemini_provider.py` and `ml_tooling/llm/providers/groq_provider.py` both contain "revisit later" `NotImplementedError` stubs.

#### Feature 3: Add partial-result handling for batch completions

- **Rationale:** Batch LLM completions are currently all-or-nothing; partial result handling is a stated TODO.
- **Scope:** Medium
- **Evidence:** `ml_tooling/llm/llm_service.py` TODO on supporting partial results for batch completions.

### Backend (3 features)

#### Feature 1: Add pagination/filtering for `GET /simulations/runs`

- **Rationale:** The runs list endpoint returns all runs without limit/offset/status filters, which will not scale for large histories.
- **Scope:** Medium
- **Evidence:** `simulation/api/routes/simulation.py` `get_simulation_runs()` has no query params; `RunListItem` implies list-style use.

#### Feature 2: Include `metric_keys` in default config endpoint

- **Rationale:** The default config endpoint returns only `num_agents/num_turns`, but UI supports metric selection and plans call for default metric keys.
- **Scope:** Small
- **Evidence:** `simulation/api/schemas/simulation.py` `DefaultConfigSchema` lacks `metric_keys`; `simulation/api/routes/simulation.py` returns `DefaultConfigSchema` for `/simulations/config/default`.

#### Feature 3: Eliminate agent creation race condition

- **Rationale:** A TODO notes a race condition between checking and writing an agent record; should be addressed with transactional logic or DB constraints.
- **Scope:** Small
- **Evidence:** `simulation/api/services/agent_command_service.py` TODO about a race condition before the DB write context manager.

## Markers and phrases

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO  
**Context:**

```text
"""SQLite implementation of agent persona bio database adapter.

TODO: For caching or async, consider a caching layer around
read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).
"""
```text

**Original text:**

```text
TODO: For caching or async, consider a caching layer around
```

---

### File: `db/schema.py` (line 10)

**Type:** Feature idea  
**Context:**

```text
- Keep this schema aligned with what migrations produce at HEAD.
- The initial migration in this repo intentionally omits the
  `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
"""
```text

**Original text:**

```text
  `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
```

---

### File: `db/schema.py` (line 94)

**Type:** NOTE  
**Context:**

```text
    sa.Column("post_uris", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    # NOTE: This FK is applied by the second Alembic migration.
    sa.ForeignKeyConstraint(
        ["run_id"],
```text

**Original text:**

```text
    # NOTE: This FK is applied by the second Alembic migration.
```

---

### File: `docs/RULES.md` (line 62)

**Type:** Feature idea  
**Context:**

```text
API design and rollout

- Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
- For optional list fields where "no items" is a valid intent (e.g. metric_keys), prefer the contract omit the field for "none" and reject empty list in validation (raise with a message like "cannot be empty; omit the field if you don't want any"). That keeps "absent" and "present but empty" distinct and avoids ambiguous semantics.
```text

**Original text:**

```text
- Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
```

---

### File: `docs/RULES.md` (line 69)

**Type:** TODO  
**Context:**

```text
- Run all pre-commit hooks.
- Follow ci.yml and run those commands (e.g., "ruff", "uv run pytest") and fix errors as needed.
- ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.

Testing:
```text

**Original text:**

```text
- ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.
```

---

### File: `docs/RULES.md` (line 165)

**Type:** Feature idea  
**Context:**

```text
- Prefer documenting intent at the boundary over leaving semantics to be inferred from implementation details.
- Comment non-obvious design choices: If a choice is made for consistency, future-proofing, or maintainability rather than immediate benefit, add a short comment explaining why, so reviewers and future readers understand the intent.
- When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.

Persistence and model boundaries
```text

**Original text:**

```text
- When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
```

---

### File: `docs/plans/2026-02-18_naive_llm_action_generators_887eadcb/plan.md` (line 181)

**Type:** Feature idea  
**Context:**

```text
## Alternative Approaches

- **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
- **Algorithm filename**: Initially `naive_llm_algorithm.py`; renamed to `algorithm.py` since folder already encodes the name.
- **Env loading (e2e)**: Initially `load_dotenv()`; switched to `EnvVarsContainer` after merge of [PR #100](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/100).
```text

**Original text:**

```text
- **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
```

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 143)

**Type:** Feature idea  
**Context:**

```text
- **fastapi-limiter:** Uses `Depends(RateLimiter(...))`. DI-based, no Redis. Chosen slowapi because it is more widely used and has Redis support when we scale to multiple workers.
- **Custom middleware:** Full control but reinvents rate limiting logic; rejected for YAGNI.
- **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.

---
```text

**Original text:**

```text
- **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.
```

---

### File: `docs/plans/2026-02-19_security_headers_482917/plan.md` (line 124)

**Type:** Feature idea  
**Context:**

```text
- **Per-route decorator**: Would require decorating every route; middleware is DRY and applies to all responses.
- `**fastapi-security` or third-party package**: Adds a dependency for a simple middleware; custom middleware is minimal and matches existing patterns (e.g. `RequestIdMiddleware`).
- **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
- `**X-XSS-Protection`**: Deprecated in modern browsers; `X-Content-Type-Options: nosniff` and CSP provide better protection; not included.
```text

**Original text:**

```text
- **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
```

---

### File: `docs/plans/2026-02-23_create_agent_tab_741a962a/create_agent_tab_741a962a.plan.md` (line 178)

**Type:** Feature idea  
**Context:**

```text
- **Nested under View agents:** A "Create new" button within agents mode (like "Start New Run" under runs). Rejected: user requested a dedicated tab for clearer separation.
- **Separate route (e.g. /agents/create):** Rejected; toggle keeps a single-page flow consistent with View runs / View agents.
- **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.

---
```text

**Original text:**

```text
- **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.
```

---

### File: `docs/plans/2026-02-23_metrics_metadata_api_9c4e2a/plan.md` (line 148)

**Type:** Feature idea  
**Context:**

```text
## Alternative Approaches

- **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
- **Using MetricsRegistry:** The registry is built from `BUILTIN_METRICS` and used for computation. Listing metadata does not require the registry—iterating over `BUILTIN_METRICS` is simpler and avoids coupling the API to the registry's construction.
```text

**Original text:**

```text
- **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
```

---

### File: `docs/plans/2026-02-24_metrics_selector_ui_9f3a2b/metrics_selector_ui_34c8ca07.plan.md` (line 131)

**Type:** Feature idea  
**Context:**

```text
**File: [ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)** (getDefaultConfig)

- If the backend default config endpoint is later extended to return `metric_keys`, map it to `metricKeys` in the returned `RunConfig`. For Part 3, the endpoint may not include it; then `defaultConfig.metricKeys` is undefined and MetricSelector initializes to "all" once metrics load.

### 6. After screenshots (UI)
```text

**Original text:**

```text
- If the backend default config endpoint is later extended to return `metric_keys`, map it to `metricKeys` in the returned `RunConfig`. For Part 3, the endpoint may not include it; then `defaultConfig.metricKeys` is undefined and MetricSelector initializes to "all" once metrics load.
```

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Feature idea  
**Context:**

```text
## Workers

With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

## Timeouts
```text

**Original text:**

```text
With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.
```

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 103)

**Type:** Feature idea  
**Context:**

```text
- Keep worker count conservative with SQLite to reduce lock contention.
- Sync run requests can take time; configure client and platform timeouts accordingly.
- For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
```text

**Original text:**

```text
- For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
```

---

### File: `docs/weekly_updates/2026-02-16_2026-02-21.md` (line 8)

**Type:** Feature idea  
**Context:**

```text
## Scope of PRs

- Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
- Algorithms/Simulation: [Create the first liking algorithm (#56)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/56), [Create the first follow algorithm (#65)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/65), [Create the first commenting algorithm (#66)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/66), [Create a new composable metrics pipeline (#69)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/69), [Change default like algo to follow the same conventions as the default comment and follow algos (#80)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/80), [Migrate feed ranking algorithms to a registry pattern (#92)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/92)
- UI/Frontend: [refactor UI to more modularized components (#63)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/63), [Add loading/error UI in the sidebar and detail panels (#84)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/84), [Add feed algorithm selection to ConfigForm (#99)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/99)
```text

**Original text:**

```text
- Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
```

---

### File: `feeds/algorithms/interfaces.py` (line 51)

**Type:** TODO  
**Context:**

```text
        candidate_posts: list[
            BlueskyFeedPost
        ],  # TODO: decouple from Bluesky-specific type
        agent: SocialMediaAgent,
        limit: int,
```text

**Original text:**

```text
        ],  # TODO: decouple from Bluesky-specific type
```

---

### File: `feeds/candidate_generation.py` (line 12)

**Type:** TODO  
**Context:**

```text


# TODO: we can get arbitrarily complex with how we do this later
# on, but as a first pass it's easy enough to just load all the posts.
def load_posts() -> list[BlueskyFeedPost]:
```text

**Original text:**

```text
# TODO: we can get arbitrarily complex with how we do this later
```

---

### File: `feeds/feed_generator.py` (line 70)

**Type:** TODO  
**Context:**

```text
    feeds: dict[str, GeneratedFeed] = {}
    for agent in agents:
        # TODO: right now we load all posts per agent, but obviously
        # can optimize and personalize later to save on queries.
        feed = _generate_single_agent_feed(
```text

**Original text:**

```text
        # TODO: right now we load all posts per agent, but obviously
```

---

### File: `feeds/feed_generator.py` (line 71)

**Type:** Feature idea  
**Context:**

```text
    for agent in agents:
        # TODO: right now we load all posts per agent, but obviously
        # can optimize and personalize later to save on queries.
        feed = _generate_single_agent_feed(
            agent=agent,
```text

**Original text:**

```text
        # can optimize and personalize later to save on queries.
```

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO  
**Context:**

```text
        Raises:
            LLMException: Standardized internal exception (LiteLLM exceptions are converted)
            TODO: Consider supporting partial results for batch completions instead of
                all-or-nothing error handling.
        """
```text

**Original text:**

```text
            TODO: Consider supporting partial results for batch completions instead of
```

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea  
**Context:**

```text
        """Format Gemini's structured output format."""
        raise NotImplementedError(
            "We'll revisit this later when actively working with Gemini models."
        )
```text

**Original text:**

```text
            "We'll revisit this later when actively working with Gemini models."
```

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea  
**Context:**

```text
        """Format Groq's structured output format."""
        raise NotImplementedError(
            "We'll revisit this later when actively working with Groq models."
        )
```text

**Original text:**

```text
            "We'll revisit this later when actively working with Groq models."
```

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 74)

**Type:** Feature idea  
**Context:**

```text
        """Prepare Groq-specific completion kwargs."""
        raise NotImplementedError(
            "We'll revisit this later when actively working with Groq models."
        )
```text

**Original text:**

```text
            "We'll revisit this later when actively working with Groq models."
```

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE  
**Context:**

```text

# Auto-register default providers on import
# NOTE: choosing to do this here instead of __init__ so that we can use the
# classmethods while assuming that the providers are already imported.
LLMProviderRegistry.register(OpenAIProvider)
```text

**Original text:**

```text
# NOTE: choosing to do this here instead of __init__ so that we can use the
```

---

### File: `simulation/api/routes/simulation.py` (line 345)

**Type:** Feature idea  
**Context:**

```text
    try:
        engine = request.app.state.engine
        # Use to_thread for consistency with other async routes and to prepare for real I/O later.
        return await asyncio.to_thread(list_runs, engine=engine)
    except Exception:
```text

**Original text:**

```text
        # Use to_thread for consistency with other async routes and to prepare for real I/O later.
```

---

### File: `simulation/api/services/agent_command_service.py` (line 58)

**Type:** TODO  
**Context:**

```text
        )

    # TODO: that this can cause a slight race condition if we do this check
    # before the below context manager for writing the agent to the database.
    # This is a known issue, and we'll revisit this in the future.
```text

**Original text:**

```text
    # TODO: that this can cause a slight race condition if we do this check
```

---

### File: `simulation/core/command_service.py` (line 377)

**Type:** TODO  
**Context:**

```text
        validate_duplicate_agent_handles(agents=agents)

        # TODO: this log should live within agent_factory.
        logger.info(
            "Created %d agents (requested: %d) for run %s",
```text

**Original text:**

```text
        # TODO: this log should live within agent_factory.
```

---

### File: `simulation/core/metrics/builtins/actions.py` (line 85)

**Type:** Feature idea  
**Context:**

```text
    """Aggregated action counts across all turns, by type.

    Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
    which loads all turn rows into memory. For large runs, consider replacing
    with DB-side aggregation (e.g. run_repo.aggregate_action_totals(run_id)
```text

**Original text:**

```text
    Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
```

---

### File: `simulation/core/models/feeds.py` (line 1)

**Type:** TODO  
**Context:**

```text
# TODO: for now, we support only Bluesky posts being added to feeds.
# We'll revisit how to add AI-generated posts to feeds later on.
import uuid
```text

**Original text:**

```text
# TODO: for now, we support only Bluesky posts being added to feeds.
```

---

### File: `simulation/core/models/feeds.py` (line 2)

**Type:** Feature idea  
**Context:**

```text
# TODO: for now, we support only Bluesky posts being added to feeds.
# We'll revisit how to add AI-generated posts to feeds later on.
import uuid
```text

**Original text:**

```text
# We'll revisit how to add AI-generated posts to feeds later on.
```

---

### File: `tests/ml_tooling/llm/config/test_model_registry.py` (line 158)

**Type:** Feature idea  
**Context:**

```text

        # Act
        # Default has temperature: 0.0, provider has it too, so we should get it
        result = model_config.get_kwarg_value("temperature")
```text

**Original text:**

```text
        # Default has temperature: 0.0, provider has it too, so we should get it
```

---

### File: `tests/ml_tooling/llm/test_retry.py` (line 148)

**Type:** Feature idea  
**Context:**

```text

    def test_retry_llm_completion_respects_max_retries(self):
        """Test that decorated function respects max_retries and eventually raises."""
        call_count = 0
        exception_instance = LLMTransientError("Rate limit exceeded")
```text

**Original text:**

```text
        """Test that decorated function respects max_retries and eventually raises."""
```

---

### File: `ui/components/form/ConfigForm.tsx` (line 191)

**Type:** TODO  
**Context:**

```text
              className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
            >
              {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
              {algorithms.length === 0 ? (
                <option value="chronological">Chronological</option>
```text

**Original text:**

```text
              {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
```

---
