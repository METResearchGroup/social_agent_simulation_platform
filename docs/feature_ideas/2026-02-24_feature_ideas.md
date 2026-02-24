# Feature Ideas and Technical Debt Scan

**Scan date:** 2026-02-24
**Scope:** Full repo

## Summary

- Total markers/phrases found: 113
- By category: TODO (26), FIXME (0), HACK (0), XXX (1), NOTE (45), OPTIMIZE (2), REFACTOR (18), Feature ideas (21)
- Proposed features: 3 UI, 3 ML, 3 backend

## Proposed features by area

### UI (3 features)

#### Feature 1: Surface run and turn metrics in Run Summary

- **Rationale:** Run responses already include per-run and per-turn metrics, but the UI types and views omit them. Exposing these metrics would make simulation output more informative without additional backend work.
- **Scope:** Small
- **Evidence:** simulation/api/schemas/simulation.py (RunDetailsResponse.run_metrics, TurnActionsItem.metrics); ui/components/details/RunSummary.tsx (no metrics section); ui/types/index.ts (Run lacks metrics fields)

#### Feature 2: Wire Create Agent history/link fields to API

- **Rationale:** Create Agent UI already collects comments, liked post URIs, and linked agents, but the submit payload drops these fields. Wiring them to the API would unlock richer agent initialization.
- **Scope:** Small
- **Evidence:** ui/components/agents/CreateAgentView.tsx (comments, likedPostUris, linkedAgentHandles collected; submit only sends handle/displayName/bio); simulation/api/schemas/simulation.py (CreateAgentRequest fast-follows comment)

#### Feature 3: Add live run updates to the UI

- **Rationale:** The UI state already reserves a channel for live per-run updates, but nothing populates it. Implementing polling or streaming would allow the turn timeline to update while a run is in progress.
- **Scope:** Large
- **Evidence:** ui/lib/run-selectors.ts (newRunTurns reserved for live per-run updates); ui/hooks/useSimulationPageState.ts (newRunTurns exists but is not populated)

### ML (3 features)

#### Feature: Support AI-generated posts in feeds

- **Rationale:** Feed models explicitly note that only Bluesky posts are supported and AI-generated posts are deferred. Extending the model would enable synthetic content in simulations.
- **Scope:** Large
- **Evidence:** simulation/core/models/feeds.py (TODO about only Bluesky posts; revisit AI-generated posts)

#### Feature: Implement structured output for Gemini and Groq providers

- **Rationale:** Gemini and Groq providers raise NotImplementedError for structured output and completion kwargs. Implementing these would unlock parity with other providers.
- **Scope:** Small
- **Evidence:** ml_tooling/llm/providers/gemini_provider.py (structured output NotImplemented); ml_tooling/llm/providers/groq_provider.py (structured output/kwargs NotImplemented)

#### Feature: Allow partial results for batch completions

- **Rationale:** LLM service notes that batch completions are all-or-nothing. Supporting partial results would improve resilience when some calls fail.
- **Scope:** Large
- **Evidence:** ml_tooling/llm/llm_service.py (TODO about partial results for batch completions)

### Backend (3 features)

#### Feature: Replace dummy run/turn/post queries with real persistence

- **Rationale:** Run list, turns, and posts are served from dummy fixtures. Implementing real DB-backed queries would make the API reflect actual runs.
- **Scope:** Large
- **Evidence:** simulation/api/services/run_query_service.py (list_runs_dummy, get_turns_for_run_dummy, get_posts_by_uris_dummy use DUMMY_* data)

#### Feature: Add pagination for agent listing

- **Rationale:** The agent query service notes that pagination may be needed and hints at a hydrate_agents helper. Adding pagination will keep the API scalable as agent counts grow.
- **Scope:** Small
- **Evidence:** simulation/api/services/agent_query_service.py (comment about helper and pagination)

#### Feature: Support CreateAgent fast-follow payloads

- **Rationale:** API schema documents fast-follows (comments, likedPostUris, linkedAgentHandles) but the backend ignores them today. Implementing them would unlock richer agent setup.
- **Scope:** Large
- **Evidence:** simulation/api/schemas/simulation.py (CreateAgentRequest fast-follows comment); simulation/api/services/agent_command_service.py (create_agent only handles handle/display_name/bio)

## Markers and phrases

### File: `db/adapters/base.py` (line 58)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                This write is idempotent: an existing row with the same run_id may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 157)

**Type:** NOTE

Context:

                          they raise.
            Note:
                The total_actions field is stored in the database as JSON with string keys
                (e.g., {"like": 5, "comment": 2}). Implementations should convert these

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 225)

**Type:** NOTE

Context:

            conn: Connection.
            Note:
                This write is idempotent: an existing row with the same (run_id,
                turn_number) may be replaced. Callers can safely retry or recompute;

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 256)

**Type:** NOTE

Context:

            conn: Connection.
            Note:
                This write is idempotent: an existing row with the same run_id may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 290)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                This write is idempotent: an existing row with the same handle may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 359)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                This write is idempotent: an existing row with the same URI may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 380)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                Each write is idempotent: an existing row with the same URI may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 469)

**Type:** NOTE

Context:

                          Implementations should document the specific exception types
                          they raise.
            Note:
                This method is used to hydrate generated feeds. Implementations should
                ensure that the post URIs are valid and that the feed posts are returned

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 498)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                This write is idempotent: an existing row with the same composite
                key (agent_handle, run_id, turn_number) may be replaced. Callers can

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 625)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                This write is idempotent: an existing row with the same handle may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 683)

**Type:** NOTE

Context:

                conn: Connection.
            Note:
                Idempotent: an existing row with the same agent_id may be replaced.
            """

Original text:

            Note:

---

### File: `db/adapters/base.py` (line 747)

**Type:** NOTE

Context:

                conn: Connection.
            Note:
                Idempotent: an existing row with the same agent_id may be replaced.
            """

Original text:

            Note:

---

### File: `db/adapters/sqlite/agent_bio_adapter.py` (line 3)

**Type:** TODO

Context:

    """SQLite implementation of agent persona bio database adapter.
    TODO: For caching or async, consider a caching layer around
    read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).
    """

Original text:

    TODO: For caching or async, consider a caching layer around

---

### File: `db/repositories/feed_post_repository.py` (line 95)

**Type:** NOTE

Context:

                ValueError: If uri is empty or if no feed post is found for the given URI
            Note:
                Pydantic validators only run when creating models. Since this method accepts a raw string
                parameter (not a BlueskyFeedPost model), we validate uri here.

Original text:

            Note:

---

### File: `db/repositories/feed_post_repository.py` (line 115)

**Type:** NOTE

Context:

                ValueError: If author_handle is empty or None
            Note:
                Pydantic validators only run when creating models. Since this method accepts a raw string
                parameter (not a BlueskyFeedPost model), we validate author_handle here.

Original text:

            Note:

---

### File: `db/repositories/generated_bio_repository.py` (line 62)

**Type:** NOTE

Context:

                ValueError: If handle is empty or None
            Note:
                Pydantic validators only run when creating models. Since this method accepts a raw string
                parameter (not a GeneratedBio model), we validate handle here.

Original text:

            Note:

---

### File: `db/repositories/generated_feed_repository.py` (line 50)

**Type:** NOTE

Context:

                sqlite3.OperationalError: If database operation fails (from adapter)
            Note:
                This write is idempotent: an existing row with the same composite
                key (agent_handle, run_id, turn_number) may be replaced. Callers can

Original text:

            Note:

---

### File: `db/repositories/generated_feed_repository.py` (line 85)

**Type:** NOTE

Context:

                ValueError: If no feed is found for the given composite key (from adapter)
            Note:
                turn_number is validated by the function signature (int type), so it cannot be None.
                Pydantic validators only run when creating models. Since this method accepts raw string

Original text:

            Note:

---

### File: `db/repositories/generated_feed_repository.py` (line 121)

**Type:** NOTE

Context:

                ValueError: If agent_handle or run_id is empty
            Note:
                Pydantic validators only run when creating models. Since this method accepts raw string
                parameters (not a GeneratedFeed model), we validate agent_handle and run_id here.

Original text:

            Note:

---

### File: `db/repositories/interfaces.py` (line 198)

**Type:** NOTE

Context:

            """Write computed metrics for a specific run/turn.
            Note:
                This write is idempotent: an existing row with the same (run_id,
                turn_number) may be replaced. Callers can safely retry or recompute;

Original text:

            Note:

---

### File: `db/repositories/interfaces.py` (line 224)

**Type:** NOTE

Context:

            """Write computed metrics for a run.
            Note:
                This write is idempotent: an existing row with the same run_id may be
                replaced. Callers can safely retry or recompute; duplicate writes do

Original text:

            Note:

---

### File: `db/repositories/interfaces.py` (line 368)

**Type:** NOTE

Context:

                The created or updated GeneratedFeed object
            Note:
                This write is idempotent: an existing row with the same composite
                key (agent_handle, run_id, turn_number) may be replaced. Callers can

Original text:

            Note:

---

### File: `db/repositories/profile_repository.py` (line 62)

**Type:** NOTE

Context:

                ValueError: If handle is empty or None
            Note:
                Pydantic validators only run when creating models. Since this method accepts a raw string
                parameter (not a BlueskyProfile model), we validate handle here.

Original text:

            Note:

---

### File: `db/repositories/run_repository.py` (line 229)

**Type:** NOTE

Context:

                          specific exception types they raise.
            Note:
                TurnMetadata Pydantic model already validates that run_id is non-empty
                and turn_number is non-negative. This method validates:

Original text:

            Note:

---

### File: `db/schema.py` (line 10)

**Type:** Feature idea

Context:

    - Keep this schema aligned with what migrations produce at HEAD.
    - The initial migration in this repo intentionally omits the
      `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
    """

Original text:

      `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.

---

### File: `db/schema.py` (line 93)

**Type:** NOTE

Context:

        sa.Column("post_uris", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        # NOTE: This FK is applied by the second Alembic migration.
        sa.ForeignKeyConstraint(
            ["run_id"],

Original text:

        # NOTE: This FK is applied by the second Alembic migration.

---

### File: `docs/RULES.md` (line 61)

**Type:** Feature idea

Context:

    API design and rollout
    - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.
    Per-commit:

Original text:

    - Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.

---

### File: `docs/RULES.md` (line 67)

**Type:** TODO

Context:

    - Run all pre-commit hooks.
    - Follow ci.yml and run those commands (e.g., "ruff", "uv run pytest") and fix errors as needed.
    - ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.
    Testing:

Original text:

    - ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.

---

### File: `docs/RULES.md` (line 162)

**Type:** TODO

Context:

    - Prefer documenting intent at the boundary over leaving semantics to be inferred from implementation details.
    - Comment non-obvious design choices: If a choice is made for consistency, future-proofing, or maintainability rather than immediate benefit, add a short comment explaining why, so reviewers and future readers understand the intent.
    - When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.
    Persistence and model boundaries

Original text:

    - When adding infrastructure that may be extended later (caching, read replicas, async batch loaders), add short TODO: comments at the boundary (e.g. above batch-fetch calls or in adapter docstrings) to indicate where future extensions could be wired in.

---

### File: `docs/plans/2026-02-18_naive_llm_action_generators_887eadcb/plan.md` (line 181)

**Type:** Feature idea

Context:

    ## Alternative Approaches
    - **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
    - **Algorithm filename**: Initially `naive_llm_algorithm.py`; renamed to `algorithm.py` since folder already encodes the name.
    - **Env loading (e2e)**: Initially `load_dotenv()`; switched to `EnvVarsContainer` after merge of [PR #100](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/100).

Original text:

    - **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.

---

### File: `docs/plans/2026-02-19_feed_algorithm_frontend/unit_2_feed_algorithm_frontend_8547c724.plan.md` (line 4)

**Type:** TODO

Context:

    name: Feed Algorithm Frontend
    overview: "add feed algorithm selection to the ConfigForm, wire the frontend to the existing GET /v1/simulations/feed-algorithms endpoint, extend RunConfig and the submit flow with feedAlgorithm, and wire handleConfigSubmit to POST /v1/simulations/run."
    todos:
      - id: before-screenshots
        content: Capture before screenshots of ConfigForm to docs/plans/2026-02-19_feed_algorithm_frontend/images/before/

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_feed_algorithm_frontend/unit_2_feed_algorithm_frontend_8547c724.plan.md` (line 114)

**Type:** TODO

Context:

    ## Implementation Steps
    ### 1. Before screenshots (UI work – first todo)
    Capture the current Start/ConfigForm UI to `docs/plans/2026-02-19_feed_algorithm_frontend/images/before/`. Ensure the dev server is running and the start screen is visible.

Original text:

    ### 1. Before screenshots (UI work – first todo)

---

### File: `docs/plans/2026-02-19_feed_algorithm_frontend/unit_2_feed_algorithm_frontend_8547c724.plan.md` (line 156)

**Type:** NOTE

Context:

      - On error: set `runsError` (or equivalent) so the UI can show a retry or error message; do not add a fake run.
    - Ensure `config` passed to `handleConfigSubmit` includes `feedAlgorithm`. If omitted, default to `"chronological"` before calling `postRun`.
    - **Note**: Backend [RunResponse](simulation/api/schemas/simulation.py) does not include `created_at`; [Run](ui/types/index.ts) requires `createdAt`. For runs from `postRun`, derive `createdAt` as `new Date().toISOString()` (run was just created). [RunListItem](simulation/api/schemas/simulation.py) (from GET /runs) includes `created_at`; only `postRun`-created runs need the derived value.
    ### 6. RunConfig storage

Original text:

    - **Note**: Backend [RunResponse](simulation/api/schemas/simulation.py) does not include `created_at`; [Run](ui/types/index.ts) requires `createdAt`. For runs from `postRun`, derive `createdAt` as `new Date().toISOString()` (run was just created). [RunListItem](simulation/api/schemas/simulation.py) (from GET /runs) includes `created_at`; only `postRun`-created runs need the derived value.

---

### File: `docs/plans/2026-02-19_feed_algorithm_frontend/unit_2_feed_algorithm_frontend_8547c724.plan.md` (line 162)

**Type:** TODO

Context:

    - `runConfigs` stores full config including `feedAlgorithm`. Backend `RunConfigDetail` has `feed_algorithm`. No backend changes needed.
    ### 7. After screenshots (UI work – last todo)
    Capture the new ConfigForm with feed algorithm select to `docs/plans/2026-02-19_feed_algorithm_frontend/images/after/`.

Original text:

    ### 7. After screenshots (UI work – last todo)

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 2)

**Type:** REFACTOR

Context:

    ---
    name: Unit 1 Feed Algorithms Backend Refactor
    overview: Migrate feeds from the monolithic `feeds/feed_generator.py` + `feeds/algorithms.py` setup to a registry-based architecture mirroring `simulation/core/action_generators`, add algorithm metadata, and expose `GET /v1/simulations/feed-algorithms` for the frontend.
    todos:

Original text:

    name: Unit 1 Feed Algorithms Backend Refactor

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 4)

**Type:** TODO

Context:

    name: Unit 1 Feed Algorithms Backend Refactor
    overview: Migrate feeds from the monolithic `feeds/feed_generator.py` + `feeds/algorithms.py` setup to a registry-based architecture mirroring `simulation/core/action_generators`, add algorithm metadata, and expose `GET /v1/simulations/feed-algorithms` for the frontend.
    todos:
      - id: create-algorithms-package
        content: Create feeds/algorithms/ package (interfaces.py, validators.py, __init__.py)

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 14)

**Type:** REFACTOR

Context:

        content: Create feeds/algorithms/registry.py with get_registered_algorithms() and get_feed_generator()
        status: completed
      - id: refactor-feed-generator
        content: Refactor feeds/feed_generator.py to use registry, remove _FEED_ALGORITHMS
        status: completed

Original text:

      - id: refactor-feed-generator

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 15)

**Type:** REFACTOR

Context:

        status: completed
      - id: refactor-feed-generator
        content: Refactor feeds/feed_generator.py to use registry, remove _FEED_ALGORITHMS
        status: completed
      - id: update-validators-models

Original text:

        content: Refactor feeds/feed_generator.py to use registry, remove _FEED_ALGORITHMS

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 29)

**Type:** REFACTOR

Context:

    ---
    # Unit 1: Backend Refactor – Feeds Registry + Metadata
    ## Remember

Original text:

    # Unit 1: Backend Refactor – Feeds Registry + Metadata

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 49)

**Type:** REFACTOR

Context:

    ## Happy Flow
    1. **Run creation** – `RunRequest` (POST /v1/simulations/run) accepts `feed_algorithm`; [simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py) validates via `validate_feed_algorithm` from [simulation/core/validators.py](simulation/core/validators.py) (which will import from `feeds.algorithms.validators` after refactor).
    2. **Feed generation** – [feeds/feed_generator.py](feeds/feed_generator.py) calls `registry.get_feed_generator(feed_algorithm)` to obtain the algorithm, runs it on candidate posts, and persists `GeneratedFeed`.
    3. **Algorithm metadata** – `GET /v1/simulations/feed-algorithms` calls `feeds.algorithms.registry.get_registered_algorithms()` and returns JSON `[{id, display_name, description, config_schema}]`.

Original text:

    1. **Run creation** – `RunRequest` (POST /v1/simulations/run) accepts `feed_algorithm`; [simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py) validates via `validate_feed_algorithm` from [simulation/core/validators.py](simulation/core/validators.py) (which will import from `feeds.algorithms.validators` after refactor).

---

### File: `docs/plans/2026-02-19_feed_algorithms_unit1_backend_8b6b27/feed_algorithms_backend_refactor_8b6b27b2.plan.md` (line 105)

**Type:** REFACTOR

Context:

      - `FEED_ALGORITHMS: tuple[str, ...]` derived from registry keys for validators.
    ### 4. Refactor feed_generator
    - In [feeds/feed_generator.py](feeds/feed_generator.py): remove `_FEED_ALGORITHMS` and `from feeds.algorithms import generate_chronological_feed`.

Original text:

    ### 4. Refactor feed_generator

---

### File: `docs/plans/2026-02-19_log_route_completion_decorator_246801/plan.md` (line 3)

**Type:** REFACTOR

Context:

    ---
    name: Log Route Completion Decorator
    overview: Refactor the repetitive `log_route_completion` calls in simulation routes into a parameterized decorator that logs route completion after each handler returns, keeping routes thin and consolidating the logging pattern per docs/RULES.md.
    todos:
      - id: add-error-extractor

Original text:

    overview: Refactor the repetitive `log_route_completion` calls in simulation routes into a parameterized decorator that logs route completion after each handler returns, keeping routes thin and consolidating the logging pattern per docs/RULES.md.

---

### File: `docs/plans/2026-02-19_log_route_completion_decorator_246801/plan.md` (line 4)

**Type:** TODO

Context:

    name: Log Route Completion Decorator
    overview: Refactor the repetitive `log_route_completion` calls in simulation routes into a parameterized decorator that logs route completion after each handler returns, keeping routes thin and consolidating the logging pattern per docs/RULES.md.
    todos:
      - id: add-error-extractor
        content: Move _error_code_from_json_response to lib/request_logging.py

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_log_route_completion_decorator_246801/plan.md` (line 11)

**Type:** REFACTOR

Context:

        content: Implement log_route_completion_decorator in lib/request_logging.py
        status: completed
      - id: refactor-routes
        content: Apply decorator to all 5 routes and remove inline logging in simulation.py
        status: completed

Original text:

      - id: refactor-routes

---

### File: `docs/plans/2026-02-19_migrate_agents_backend/migrate_agents_backend.plan.md` (line 4)

**Type:** TODO

Context:

    name: Migrate Agents Backend
    overview: Migrate DUMMY_AGENTS from the frontend to the backend, adding GET /v1/simulations/agents and wiring useSimulationPageState to fetch agents via the API. No overlap with the posts migration—this plan touches only agents-related code.
    todos:
      - id: backend-schema
        content: Add AgentSchema to simulation/api/schemas/simulation.py

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 4)

**Type:** TODO

Context:

    name: Migrate Posts Backend
    overview: Migrate DUMMY_POSTS and getPostByUri from the frontend to the backend, adding GET /v1/simulations/posts?uris=... and wiring DetailsPanel to fetch posts via the API. No new functionality—only relocating mock data to the backend so the frontend uses the real API path.
    todos:
      - id: backend-schema
        content: Add PostSchema to simulation/api/schemas/simulation.py

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 233)

**Type:** NOTE

Context:

    ## Verification Results (2026-02-19)
    | Step | Status | Notes |
    | --- | --- | --- |
    | Backend tests | Passed | 13 tests (runs + posts) |

Original text:

    | Step | Status | Notes |

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 257)

**Type:** Feature idea

Context:

    - **Return-all vs batch:** Return-all `GET /v1/simulations/posts` would simplify the API but force the client to filter. MIGRATIONS.md recommends batch lookup; we adopt `?uris=...`.
    - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
    - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.

Original text:

    - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.

---

### File: `docs/plans/2026-02-19_migrate_posts_backend/plan.md` (line 258)

**Type:** Feature idea

Context:

    - **Return-all vs batch:** Return-all `GET /v1/simulations/posts` would simplify the API but force the client to filter. MIGRATIONS.md recommends batch lookup; we adopt `?uris=...`.
    - **Embed posts in turns response:** Could add full post objects to `TurnSchema` instead of just `post_uris`. That would duplicate posts across turns and bloat the response; separate endpoint keeps turns lean and allows independent post caching.
    - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.
    ---

Original text:

    - **Post query service module:** Could add `simulation/api/services/post_query_service.py` instead of extending `run_query_service`. For dummy data, a single service module is acceptable; RULES prefer minimal public APIs. We add `get_posts_by_uris_dummy` to `run_query_service` for consistency with `list_runs_dummy` and `get_turns_for_run_dummy`.

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 4)

**Type:** TODO

Context:

    name: Rate Limiting POST Paths
    overview: Add per-IP rate limiting to all POST routes using slowapi, with a stricter limit on POST /v1/simulations/run. Deployment is Railway with a single uvicorn worker; in-memory backend is sufficient. No per-user/tenant limits.
    todos:
      - id: add-slowapi-dep
        content: Add slowapi>=0.1.9 to pyproject.toml dependencies

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 94)

**Type:** NOTE

Context:

    Testing approach: Use `TestClient` with the same app. Use `_trigger_rate_limit` helper to reset the limiter and make 6 requests; tests assert on responses. The in-memory limiter keys by IP; use `X-Forwarded-For` header to simulate different clients. Mock the engine to avoid running real simulations.
    Note: slowapi resolves the limiter from `request.app.state.limiter`. Ensure the test app has the limiter configured before tests run.
    ---

Original text:

    Note: slowapi resolves the limiter from `request.app.state.limiter`. Ensure the test app has the limiter configured before tests run.

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 143)

**Type:** Feature idea

Context:

    - **fastapi-limiter:** Uses `Depends(RateLimiter(...))`. DI-based, no Redis. Chosen slowapi because it is more widely used and has Redis support when we scale to multiple workers.
    - **Custom middleware:** Full control but reinvents rate limiting logic; rejected for YAGNI.
    - **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.
    ---

Original text:

    - **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 149)

**Type:** NOTE

Context:

    ## Rule Compliance (review-rules)
    | Rule                    | Status | Notes                                                                        |
    | ----------------------- | ------ | ---------------------------------------------------------------------------- |
    | PLANNING_RULES          | pass   | Overview, Happy Flow, Manual Verification, alternatives, specificity present |

Original text:

    | Rule                    | Status | Notes                                                                        |

---

### File: `docs/plans/2026-02-19_rate_limiting_post_paths_847291/plan.md` (line 160)

**Type:** NOTE

Context:

    ## Plan Asset Storage
    Save this plan and any related assets (e.g. verification notes) in:
    ```text

Original text:

    Save this plan and any related assets (e.g. verification notes) in:

---

### File: `docs/plans/2026-02-19_security_headers_482917/plan.md` (line 4)

**Type:** TODO

Context:

    name: Security Headers Implementation
    overview: Add security headers middleware to the FastAPI backend to mitigate XSS, clickjacking, and MIME sniffing risks by setting X-Content-Type-Options, X-Frame-Options, and Strict-Transport-Security (when HTTPS) on all API responses.
    todos:
      - id: create-middleware
        content: Create lib/security_headers.py with SecurityHeadersMiddleware

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_security_headers_482917/plan.md` (line 124)

**Type:** Feature idea

Context:

    - **Per-route decorator**: Would require decorating every route; middleware is DRY and applies to all responses.
    - `**fastapi-security` or third-party package**: Adds a dependency for a simple middleware; custom middleware is minimal and matches existing patterns (e.g. `RequestIdMiddleware`).
    - **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
    - `**X-XSS-Protection`**: Deprecated in modern browsers; `X-Content-Type-Options: nosniff` and CSP provide better protection; not included.

Original text:

    - **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.

---

### File: `docs/plans/2026-02-19_user_created_agents_migration_246801/user-created_agents_migration_d0532522.plan.md` (line 4)

**Type:** TODO

Context:

    name: User-Created Agents Migration
    overview: Introduce a new agent data model (agent, agent_persona_bios, user_agent_profile_metadata) with repository/adapter pattern, then a one-off migration job to backfill from bluesky_profiles and the existing agent_bios table. This enables user-created agents and decouples agents from Bluesky.
    todos:
      - id: domain-models
        content: Add Agent, AgentBio, UserAgentProfileMetadata domain models and enums

Original text:

    todos:

---

### File: `docs/plans/2026-02-19_user_created_agents_migration_246801/user-created_agents_migration_d0532522.plan.md` (line 118)

**Type:** NOTE

Context:

    | Column         | Type   | Notes                                       |
    | -------------- | ------ | ------------------------------------------- |
    | agent_id       | PK     | Bluesky DID for sync_bluesky; UUID for user |

Original text:

    | Column         | Type   | Notes                                       |

---

### File: `docs/plans/2026-02-19_user_created_agents_migration_246801/user-created_agents_migration_d0532522.plan.md` (line 131)

**Type:** NOTE

Context:

    | Column             | Type | Notes                             |
    | ------------------ | ---- | --------------------------------- |
    | id                 | PK   | UUID                              |

Original text:

    | Column             | Type | Notes                             |

---

### File: `docs/plans/2026-02-19_user_created_agents_migration_246801/user-created_agents_migration_d0532522.plan.md` (line 144)

**Type:** NOTE

Context:

    | Column          | Type | Notes      |
    | --------------- | ---- | ---------- |
    | id              | PK   | UUID       |

Original text:

    | Column          | Type | Notes      |

---

### File: `docs/plans/2026-02-19_user_created_agents_migration_246801/user-created_agents_migration_d0532522.plan.md` (line 187)

**Type:** XXX

Context:

    ### 3. Alembic Migration
    **File:** `db/migrations/versions/xxxx_create_agent_tables.py`
    - `op.create_table("agent", ...)` with columns above

Original text:

    **File:** `db/migrations/versions/xxxx_create_agent_tables.py`

---

### File: `docs/plans/2026-02-20_feed_algorithms_typing_order_a1b2c3/feed_algorithms_typing_and_order_5131ff86.plan.md` (line 4)

**Type:** TODO

Context:

    name: Feed Algorithms Typing and Order
    overview: Strengthen feed algorithm contracts with typed return values (FeedAlgorithmResult), introduce a FeedAlgorithm ABC per RULES.md, and document ordering/determinism as part of the contract. This replaces raw dict returns, enforces ordering semantics, and aligns with action_generators patterns.
    todos: []
    isProject: false
    ---

Original text:

    todos: []

---

### File: `docs/plans/2026-02-23_create_agent_tab_741a962a/create_agent_tab_741a962a.plan.md` (line 4)

**Type:** TODO

Context:

    name: Create Agent Tab
    overview: Add a third "Create agent" tab alongside "View runs" and "View agents" that shows a create-agent form with handle, display name, bio, history (comments, likes), link-to-existing-profiles multi-select, a stubbed "Create AI-generated bio" button, and a no-op Submit button. UI-only; no backend integration.
    todos:
      - id: before-screenshots
        content: Capture before screenshots to docs/plans/2026-02-23_create_agent_tab_<hash>/images/before/

Original text:

    todos:

---

### File: `docs/plans/2026-02-23_create_agent_tab_741a962a/create_agent_tab_741a962a.plan.md` (line 178)

**Type:** Feature idea

Context:

    - **Nested under View agents:** A "Create new" button within agents mode (like "Start New Run" under runs). Rejected: user requested a dedicated tab for clearer separation.
    - **Separate route (e.g. /agents/create):** Rejected; toggle keeps a single-page flow consistent with View runs / View agents.
    - **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.
    ---

Original text:

    - **Profiles API for linking:** Backend has Bluesky profiles but no GET /profiles endpoint. Use existing `getAgents()` and label "Link to existing agents" for now; profiles API can be added later.

---

### File: `docs/plans/2026-02-23_db_test_fixtures_consolidation_56cf5a/plan.md` (line 13)

**Type:** REFACTOR

Context:

    ## Overview
    Add repository fixtures and `ensure_run_exists` to `tests/db/repositories/conftest.py`, remove all local `temp_db` definitions in favor of the root `temp_db` from `tests/conftest.py`, and refactor integration tests to use fixtures instead of in-test `create_sqlite_*_repository(transaction_provider=SqliteTransactionProvider())`. This eliminates ~80+ repeated setup lines across 10 test files.
    **Status:** Complete.

Original text:

    Add repository fixtures and `ensure_run_exists` to `tests/db/repositories/conftest.py`, remove all local `temp_db` definitions in favor of the root `temp_db` from `tests/conftest.py`, and refactor integration tests to use fixtures instead of in-test `create_sqlite_*_repository(transaction_provider=SqliteTransactionProvider())`. This eliminates ~80+ repeated setup lines across 10 test files.

---

### File: `docs/plans/2026-02-23_list_agents_batch_fetch_n1_a1b2c3/list_agents_batch_fetch_n1.plan.md` (line 3)

**Type:** REFACTOR

Context:

    ---
    name: list_agents N+1 batch fetch
    overview: Add batch read methods to AgentBioRepository and UserAgentProfileMetadataRepository, refactor list_agents() to use them (eliminating 1+2N queries down to 3), remove redundant sort, and add extension-point comments for future caching/async.
    todos:
      - id: interfaces

Original text:

    overview: Add batch read methods to AgentBioRepository and UserAgentProfileMetadataRepository, refactor list_agents() to use them (eliminating 1+2N queries down to 3), remove redundant sort, and add extension-point comments for future caching/async.

---

### File: `docs/plans/2026-02-23_list_agents_batch_fetch_n1_a1b2c3/list_agents_batch_fetch_n1.plan.md` (line 4)

**Type:** TODO

Context:

    name: list_agents N+1 batch fetch
    overview: Add batch read methods to AgentBioRepository and UserAgentProfileMetadataRepository, refactor list_agents() to use them (eliminating 1+2N queries down to 3), remove redundant sort, and add extension-point comments for future caching/async.
    todos:
      - id: interfaces
        content: Add get_latest_bios_by_agent_ids and get_metadata_by_agent_ids to db/repositories/interfaces.py

Original text:

    todos:

---

### File: `docs/plans/2026-02-23_list_agents_batch_fetch_n1_a1b2c3/list_agents_batch_fetch_n1.plan.md` (line 21)

**Type:** REFACTOR

Context:

        status: completed
      - id: service
        content: Refactor list_agents() in agent_query_service.py to batch-fetch, add _agent_to_schema, remove sort
        status: completed
      - id: verify

Original text:

        content: Refactor list_agents() in agent_query_service.py to batch-fetch, add _agent_to_schema, remove sort

---

### File: `docs/plans/2026-02-23_list_agents_batch_fetch_n1_a1b2c3/list_agents_batch_fetch_n1.plan.md` (line 41)

**Type:** REFACTOR

Context:

    ## Overview
    [simulation/api/services/agent_query_service.py](simulation/api/services/agent_query_service.py) currently performs 1 + 2N DB queries for N agents: one for `list_all_agents()`, then per-agent calls to `get_latest_agent_bio()` and `get_by_agent_id()`. This plan adds batch methods to the bio and metadata repositories, refactors `list_agents()` to batch-fetch once, removes the redundant `sorted()` (since `list_all_agents()` already orders by handle), and adds comments marking extension points for caching or async batching.
    ---

Original text:

    [simulation/api/services/agent_query_service.py](simulation/api/services/agent_query_service.py) currently performs 1 + 2N DB queries for N agents: one for `list_all_agents()`, then per-agent calls to `get_latest_agent_bio()` and `get_by_agent_id()`. This plan adds batch methods to the bio and metadata repositories, refactors `list_agents()` to batch-fetch once, removes the redundant `sorted()` (since `list_all_agents()` already orders by handle), and adds comments marking extension points for caching or async batching.

---

### File: `docs/plans/2026-02-23_list_agents_batch_fetch_n1_a1b2c3/list_agents_batch_fetch_n1.plan.md` (line 174)

**Type:** REFACTOR

Context:

    ---
    ### 6. Refactor agent_query_service
    **File:** [simulation/api/services/agent_query_service.py](simulation/api/services/agent_query_service.py)

Original text:

    ### 6. Refactor agent_query_service

---

### File: `docs/plans/2026-02-23_metrics_metadata_api_9c4e2a/plan.md` (line 148)

**Type:** Feature idea

Context:

    ## Alternative Approaches
    - **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.
    - **Using MetricsRegistry:** The registry is built from `BUILTIN_METRICS` and used for computation. Listing metadata does not require the registry—iterating over `BUILTIN_METRICS` is simpler and avoids coupling the API to the registry's construction.

Original text:

    - **Optional service layer:** Logic could live in `simulation.api.services.metrics_query_service`. The feed-algorithms endpoint keeps logic in the route module with a private helper. For consistency and minimal scope, we keep the same pattern; a service can be extracted later if needed.

---

### File: `docs/plans/2026-02-23_view_agents_feature_a1b2c3/view_agents_feature_32a5c45b.plan.md` (line 4)

**Type:** TODO

Context:

    name: View Agents Feature
    overview: Add a top-left "View runs" | "View agents" toggle. When "View agents" is active, show an agent list sidebar and main-area agent detail (reusing AgentDetail with metadata, Feed, Liked Posts, Comments). Uses existing GET /v1/simulations/agents; Feed/Likes/Comments show empty in agent-only context.
    todos:
      - id: before-screenshots
        content: Capture before screenshots to docs/plans/2026-02-23_view_agents_feature_a1b2c3/images/before/

Original text:

    todos:

---

### File: `docs/plans/agents_backend_and_view_integration_0b63a071.plan.md` (line 4)

**Type:** TODO

Context:

    name: Agents Backend and View Integration
    overview: Implement backend persistence for agent creation (POST) and real-DB listing (GET), wire the Create Agent form to POST, switch View agents to real data, and preserve mock runs by introducing a mock agents endpoint for run-detail context. Uses atomic transactions, server-side handle normalization, and leaves comments/likes/linked-agents as fast-follows.
    todos: []
    isProject: false
    ---

Original text:

    todos: []

---

### File: `docs/plans/agents_backend_and_view_integration_0b63a071.plan.md` (line 188)

**Type:** NOTE

Context:

      - Integration: POST agent, then GET /agents includes it.
    ### 12. Fast-follow notes
    Add a short note in code or docs for future work:

Original text:

    ### 12. Fast-follow notes

---

### File: `docs/plans/agents_backend_and_view_integration_0b63a071.plan.md` (line 190)

**Type:** NOTE

Context:

    ### 12. Fast-follow notes
    Add a short note in code or docs for future work:
    - Accept and persist `comments` (list of `{ text, postUri }`)

Original text:

    Add a short note in code or docs for future work:

---

### File: `docs/runbooks/HOW_TO_CREATE_NEW_METRIC.md` (line 97)

**Type:** NOTE

Context:

    ```
    Notes:
    - Your metric’s output is **nested under its key**; the output itself is the value (`{ "foo": 1 }`).

Original text:

    Notes:

---

### File: `docs/runbooks/PRE_COMMIT_AND_LINTING.md` (line 37)

**Type:** REFACTOR

Context:

    ## complexipy (cognitive complexity)
    [complexipy](https://github.com/rohaquinlop/complexipy) reports **cognitive complexity** per function and module: how hard code is to follow (nesting, control flow), not just branch count. Use it to find good refactor targets.
    - **Run:** `uv run complexipy .` or `uv run complexipy path/to/file.py`. CI runs it only on changed Python files.

Original text:

    [complexipy](https://github.com/rohaquinlop/complexipy) reports **cognitive complexity** per function and module: how hard code is to follow (nesting, control flow), not just branch count. Use it to find good refactor targets.

---

### File: `docs/runbooks/PRE_COMMIT_AND_LINTING.md` (line 40)

**Type:** REFACTOR

Context:

    - **Run:** `uv run complexipy .` or `uv run complexipy path/to/file.py`. CI runs it only on changed Python files.
    - **Interpret:** Higher scores mean more complex code. Focus refactors on high-complexity functions.
    - **Optional threshold:** `uv run complexipy . --max-complexity-allowed 10` (exits non-zero if any function exceeds the limit).
    - **Config:** You can add `[tool.complexipy]` in `pyproject.toml` for excludes or defaults if the tool supports it; otherwise use CLI flags. CI treats complexipy as diagnostic (no threshold by default) so the build stays green while you review the report.

Original text:

    - **Interpret:** Higher scores mean more complex code. Focus refactors on high-complexity functions.

---

### File: `docs/runbooks/PRODUCTION_DEPLOYMENT.md` (line 20)

**Type:** Feature idea

Context:

    ## Workers
    With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.
    ## Timeouts

Original text:

    With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 42)

**Type:** NOTE

Context:

    ```
    Notes:
    - `SIM_DB_PATH` is read by the app at runtime and is the recommended SQLite path override for Railway.

Original text:

    Notes:

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 99)

**Type:** NOTE

Context:

    ```
    ## Operational Notes
    - Keep worker count conservative with SQLite to reduce lock contention.

Original text:

    ## Operational Notes

---

### File: `docs/runbooks/RAILWAY_DEPLOYMENT.md` (line 103)

**Type:** Feature idea

Context:

    - Keep worker count conservative with SQLite to reduce lock contention.
    - Sync run requests can take time; configure client and platform timeouts accordingly.
    - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.

Original text:

    - For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.

---

### File: `docs/runbooks/UI_DEPLOYMENT.md` (line 24)

**Type:** NOTE

Context:

    ```
    Notes:
    - This creates `ui/.vercel/` (already gitignored).

Original text:

    Notes:

---

### File: `docs/runbooks/UI_DEPLOYMENT.md` (line 73)

**Type:** NOTE

Context:

    ```
    ## Reproducibility notes
    - `ui/package-lock.json` is committed and CI uses `npm ci` to ensure deterministic installs.

Original text:

    ## Reproducibility notes

---

### File: `docs/runbooks/UPDATE_SCHEMAS.md` (line 22)

**Type:** REFACTOR

Context:

      running.
    You typically do **not** need regeneration for UI-only refactors that do not touch the
    API contract.

Original text:

    You typically do **not** need regeneration for UI-only refactors that do not touch the

---

### File: `docs/weekly_updates/2026-02-16_2026-02-21.md` (line 8)

**Type:** Feature idea

Context:

    ## Scope of PRs
    - Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
    - Algorithms/Simulation: [Create the first liking algorithm (#56)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/56), [Create the first follow algorithm (#65)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/65), [Create the first commenting algorithm (#66)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/66), [Create a new composable metrics pipeline (#69)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/69), [Change default like algo to follow the same conventions as the default comment and follow algos (#80)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/80), [Migrate feed ranking algorithms to a registry pattern (#92)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/92)
    - UI/Frontend: [refactor UI to more modularized components (#63)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/63), [Add loading/error UI in the sidebar and detail panels (#84)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/84), [Add feed algorithm selection to ConfigForm (#99)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/99)

Original text:

    - Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)

---

### File: `docs/weekly_updates/2026-02-16_2026-02-21.md` (line 10)

**Type:** REFACTOR

Context:

    - Backend/API: [Catch-all PR for fixing dependency flows (#46)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/46), [Create a centralized LLMService (#51)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/51), [Add scaffolding for FastAPI app (#52)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/52), [Add API support for list_turn_metadata (#53)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/53), [Update failure propagation model for partial-result API (#54)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/54), [Add sync simulation endpoint (#55)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/55), [Add improved logging and telemetry (#58)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/58), [Add run lookup endpoint (#60)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/60), [Improve fetch error handling and structured API errors (#85)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/85), [Add log route completion decorator (#89)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/89)
    - Algorithms/Simulation: [Create the first liking algorithm (#56)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/56), [Create the first follow algorithm (#65)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/65), [Create the first commenting algorithm (#66)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/66), [Create a new composable metrics pipeline (#69)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/69), [Change default like algo to follow the same conventions as the default comment and follow algos (#80)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/80), [Migrate feed ranking algorithms to a registry pattern (#92)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/92)
    - UI/Frontend: [refactor UI to more modularized components (#63)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/63), [Add loading/error UI in the sidebar and detail panels (#84)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/84), [Add feed algorithm selection to ConfigForm (#99)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/99)
    - Full-stack integration: [Connect UI and backend so that runs and turns are fetched from the backend (#67)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/67), [Connect UI and backend so posts are fetched from the backend (#86)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/86), [Connect UI and backend so agents are fetched from the backend (#87)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/87), [Connect UI and backend so default config is fetched from the backend (#90)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/90)
    - Infra/DevOps/Tooling: [Add Oxlint and react-doctor (#64)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/64), [Deploy app to Railway (#59)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/59), [Deploy UI to Vercel (#68)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/68), [Create daily Cursor QA job, run via Github Actions (#78)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/78), [Add action generator YAML config (#79)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/79), [turn off daily Cursor QA job (#82)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/82), [Update Docker to remove nonroot user (#95)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/95), [Add centralized env vars loader (lib/load_env_vars.py) (#100)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/100)

Original text:

    - UI/Frontend: [refactor UI to more modularized components (#63)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/63), [Add loading/error UI in the sidebar and detail panels (#84)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/84), [Add feed algorithm selection to ConfigForm (#99)](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/99)

---

### File: `feeds/algorithms/interfaces.py` (line 51)

**Type:** TODO

Context:

            candidate_posts: list[
                BlueskyFeedPost
            ],  # TODO: decouple from Bluesky-specific type
            agent: SocialMediaAgent,
            limit: int,

Original text:

            ],  # TODO: decouple from Bluesky-specific type

---

### File: `feeds/candidate_generation.py` (line 12)

**Type:** TODO

Context:

    # TODO: we can get arbitrarily complex with how we do this later
    # on, but as a first pass it's easy enough to just load all the posts.
    def load_posts() -> list[BlueskyFeedPost]:

Original text:

    # TODO: we can get arbitrarily complex with how we do this later

---

### File: `feeds/feed_generator.py` (line 70)

**Type:** TODO

Context:

        feeds: dict[str, GeneratedFeed] = {}
        for agent in agents:
            # TODO: right now we load all posts per agent, but obviously
            # can optimize and personalize later to save on queries.
            feed = _generate_single_agent_feed(

Original text:

            # TODO: right now we load all posts per agent, but obviously

---

### File: `feeds/feed_generator.py` (line 71)

**Type:** OPTIMIZE

Context:

        for agent in agents:
            # TODO: right now we load all posts per agent, but obviously
            # can optimize and personalize later to save on queries.
            feed = _generate_single_agent_feed(
                agent=agent,

Original text:

            # can optimize and personalize later to save on queries.

---

### File: `ml_tooling/llm/exceptions.py` (line 97)

**Type:** NOTE

Context:

            Internal LLMException with appropriate category
        Note:
            The original exception is preserved via exception chaining (__cause__)
            for debugging purposes while maintaining clean retry logic.

Original text:

        Note:

---

### File: `ml_tooling/llm/llm_service.py` (line 31)

**Type:** NOTE

Context:

                        If True, does not suppress LiteLLM logs (uses LiteLLM defaults).
            Note: Providers are initialized lazily when first used to avoid
            requiring API keys for all providers when only one is needed.
            """

Original text:

            Note: Providers are initialized lazily when first used to avoid

---

### File: `ml_tooling/llm/llm_service.py` (line 106)

**Type:** NOTE

Context:

            # Prepare completion kwargs using provider-specific logic
            # Note: messages is passed as placeholder empty list here, will be set by caller
            completion_kwargs = provider.prepare_completion_kwargs(
                model=model,

Original text:

            # Note: messages is passed as placeholder empty list here, will be set by caller

---

### File: `ml_tooling/llm/llm_service.py` (line 199)

**Type:** TODO

Context:

            Raises:
                LLMException: Standardized internal exception (LiteLLM exceptions are converted)
                TODO: Consider supporting partial results for batch completions instead of
                    all-or-nothing error handling.
            """

Original text:

                TODO: Consider supporting partial results for batch completions instead of

---

### File: `ml_tooling/llm/providers/gemini_provider.py` (line 82)

**Type:** Feature idea

Context:

            """Format Gemini's structured output format."""
            raise NotImplementedError(
                "We'll revisit this later when actively working with Gemini models."
            )

Original text:

                "We'll revisit this later when actively working with Gemini models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 61)

**Type:** Feature idea

Context:

            """Format Groq's structured output format."""
            raise NotImplementedError(
                "We'll revisit this later when actively working with Groq models."
            )

Original text:

                "We'll revisit this later when actively working with Groq models."

---

### File: `ml_tooling/llm/providers/groq_provider.py` (line 74)

**Type:** Feature idea

Context:

            """Prepare Groq-specific completion kwargs."""
            raise NotImplementedError(
                "We'll revisit this later when actively working with Groq models."
            )

Original text:

                "We'll revisit this later when actively working with Groq models."

---

### File: `ml_tooling/llm/providers/registry.py` (line 58)

**Type:** NOTE

Context:

    # Auto-register default providers on import
    # NOTE: choosing to do this here instead of __init__ so that we can use the
    # classmethods while assuming that the providers are already imported.
    LLMProviderRegistry.register(OpenAIProvider)

Original text:

    # NOTE: choosing to do this here instead of __init__ so that we can use the

---

### File: `simulation/api/dummy_data.py` (line 229)

**Type:** REFACTOR

Context:

            author_display_name="Bob Martinez",
            author_handle="@bob.tech",
            text="Refactored a legacy component today. It's like archaeology—carefully removing layers to discover the original intent. Satisfying when it all clicks.",
            bookmark_count=28,
            like_count=134,

Original text:

            text="Refactored a legacy component today. It's like archaeology—carefully removing layers to discover the original intent. Satisfying when it all clicks.",

---

### File: `simulation/api/routes/simulation.py` (line 340)

**Type:** Feature idea

Context:

        """Fetch run summaries and convert unexpected failures to HTTP responses."""
        try:
            # Use to_thread for consistency with other async routes and to prepare for real I/O later.
            return await asyncio.to_thread(list_runs_dummy)
        except Exception:

Original text:

            # Use to_thread for consistency with other async routes and to prepare for real I/O later.

---

### File: `simulation/api/routes/simulation.py` (line 454)

**Type:** Feature idea

Context:

        """Fetch run turns and convert known failures to HTTP responses."""
        try:
            # Use to_thread for consistency with other async routes and to prepare for real I/O later.
            return await asyncio.to_thread(get_turns_for_run_dummy, run_id=run_id)
        except RunNotFoundError as e:

Original text:

            # Use to_thread for consistency with other async routes and to prepare for real I/O later.

---

### File: `simulation/api/services/agent_command_service.py` (line 58)

**Type:** TODO

Context:

            )
        # TODO: that this can cause a slight race condition if we do this check
        # before the below context manager for writing the agent to the database.
        # This is a known issue, and we'll revisit this in the future.

Original text:

        # TODO: that this can cause a slight race condition if we do this check

---

### File: `simulation/core/command_service.py` (line 363)

**Type:** TODO

Context:

            validate_duplicate_agent_handles(agents=agents)
            # TODO: this log should live within agent_factory.
            logger.info(
                "Created %d agents (requested: %d) for run %s",

Original text:

            # TODO: this log should live within agent_factory.

---

### File: `simulation/core/metrics/builtins/actions.py` (line 83)

**Type:** Feature idea

Context:

        """Aggregated action counts across all turns, by type.
        Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,
        which loads all turn rows into memory. For large runs, consider replacing
        with DB-side aggregation (e.g. run_repo.aggregate_action_totals(run_id)

Original text:

        Limitation (revisit later): compute() uses deps.run_repo.list_turn_metadata,

---

### File: `simulation/core/models/feeds.py` (line 1)

**Type:** TODO

Context:

    # TODO: for now, we support only Bluesky posts being added to feeds.
    # We'll revisit how to add AI-generated posts to feeds later on.
    import uuid

Original text:

    # TODO: for now, we support only Bluesky posts being added to feeds.

---

### File: `simulation/core/models/feeds.py` (line 2)

**Type:** Feature idea

Context:

    # TODO: for now, we support only Bluesky posts being added to feeds.
    # We'll revisit how to add AI-generated posts to feeds later on.
    import uuid

Original text:

    # We'll revisit how to add AI-generated posts to feeds later on.

---

### File: `tests/db/repositories/test_generated_bio_repository_integration.py` (line 155)

**Type:** NOTE

Context:

            assert retrieved_bio.handle == "update.bsky.social"
            assert retrieved_bio.generated_bio == "Updated bio text with more information"
            # Note: created_at will be the updated timestamp since we use INSERT OR REPLACE
        def test_get_generated_bio_returns_none_for_nonexistent_handle(

Original text:

            # Note: created_at will be the updated timestamp since we use INSERT OR REPLACE

---

### File: `tests/db/repositories/test_profile_repository_integration.py` (line 243)

**Type:** NOTE

Context:

            repo = profile_repo
            # Note: Bluesky handles typically don't have special chars, but test edge cases
            profile = BlueskyProfile(
                handle="user-name.bsky.social",

Original text:

            # Note: Bluesky handles typically don't have special chars, but test edge cases

---

### File: `tests/ml_tooling/llm/config/test_model_registry.py` (line 158)

**Type:** Feature idea

Context:

            # Act
            # Default has temperature: 0.0, provider has it too, so we should get it
            result = model_config.get_kwarg_value("temperature")

Original text:

            # Default has temperature: 0.0, provider has it too, so we should get it

---

### File: `tests/ml_tooling/llm/test_retry.py` (line 148)

**Type:** Feature idea

Context:

        def test_retry_llm_completion_respects_max_retries(self):
            """Test that decorated function respects max_retries and eventually raises."""
            call_count = 0
            exception_instance = LLMTransientError("Rate limit exceeded")

Original text:

            """Test that decorated function respects max_retries and eventually raises."""

---

### File: `ui/README.md` (line 23)

**Type:** OPTIMIZE

Context:

    You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.
    This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.
    ## Learn More

Original text:

    This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

---

### File: `ui/components/form/ConfigForm.tsx` (line 153)

**Type:** TODO

Context:

                  className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                >
                  {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
                  {algorithms.length === 0 ? (
                    <option value="chronological">Chronological</option>

Original text:

                  {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}

---
