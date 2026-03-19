# Turn Tables Refactor Proposal

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread

## Overview

This epic should finish the next major cleanup in the persistence taxonomy: move the legacy runtime tables `likes`, `comments`, `follows`, and `generated_feeds` to explicit `turn_*` names, introduce `turn_posts`, and make runtime activity truly turn-scoped rather than merely run-scoped rows that also happen to carry a `turn_number`. The most important goal is not just cosmetic renaming. It is to make the lifecycle mechanically obvious in the schema and code, so every runtime artifact is a child of a canonical turn record and every turn belongs to exactly one run. Because there are no external clients to preserve yet, I recommend a hard cutover rather than a compatibility migration.

## Desired Outcome

- `db/schema.py` no longer defines legacy turn action tables named `likes`, `comments`, or `follows`; they become `turn_likes`, `turn_comments`, and `turn_follows`.
- `generated_feeds` is renamed to `turn_generated_feeds`.
- A new `turn_posts` table exists for posts authored during a run.
- Runtime artifacts are modeled as children of a canonical `turns` table, not just rows that duplicate `run_id` and `turn_number`.
- A run links to many turns, and turns link to many turn-scoped artifacts.
- The repository, adapter, model, service, and query layers use `turn_*` terminology end-to-end.
- Tests, fixtures, lints, docs, and migration scripts no longer depend on the legacy table names.
- Turn-time post hydration supports both run-start snapshot posts and turn-authored posts.
- The migration is one-way and clean: no dual-write, no long-lived aliases, no nullable mixed-lifecycle table tricks.

## Current State Review

The relevant current implementation is coherent, but it has an obvious naming seam:

- `db/schema.py` treats `likes`, `comments`, and `follows` as runtime event tables with `run_id` and `turn_number`, but they are not modeled as children of a first-class turn entity.
- `db/services/simulation_persistence_service.py` persists those tables transactionally from `write_turn(...)`.
- `db/adapters/sqlite/like_adapter.py`, `db/adapters/sqlite/comment_adapter.py`, and `db/adapters/sqlite/follow_adapter.py` read/write the legacy table names directly.
- `simulation/core/models/persisted_actions.py` still encodes the legacy row shapes as `PersistedLike`, `PersistedComment`, and `PersistedFollow`.
- `simulation/core/query_service.py` hydrates turn actions from those repositories.
- `generated_feeds` remains the feed table name even though it is semantically a turn table.
- `simulation/core/models/posts.py` and `simulation/core/engine.py` currently assume feed-visible post IDs resolve only from `run_posts`.
- `scripts/lint_schema_conventions.py` explicitly treats `likes`, `comments`, `follows`, and `generated_feeds` as legacy turn-event tables.

There is one especially important architectural gap:

- there is currently no persisted `turn_posts` concept
- therefore feed/query logic has no first-class way to represent "this post was created during turn N of run R"
- therefore turn actions can only point at run-start posts in a robust way today

## Main Recommendation

Treat this epic as **a hard cutover plus a turn-post foundation**, not as a broad semantic rewrite.

That means:

1. Introduce a canonical `turns` parent table by hard-cutting `turn_metadata` into a true turn entity.
2. Rename the legacy runtime tables and all codepaths that touch them, including `generated_feeds -> turn_generated_feeds`.
3. Introduce `turn_posts`.
4. Add the feed/query contract needed so `turn_posts` can be used safely.
5. Do **not** expand this same epic into a second major migration where all turn actions switch from handle-based identity to agent-ID-based identity unless you explicitly decide that bigger scope is worth it.

I would preserve the current `likes/comments/follows` payload semantics in this epic:

- `turn_likes`: keep `agent_handle` and `post_id`
- `turn_comments`: keep `agent_handle`, `post_id`, and `text`
- `turn_follows`: keep `agent_handle` and `user_id`

That keeps the rename mostly mechanical and minimizes regression risk in the already-working turn action pipeline.

For `turn_posts`, I would start stronger from day one:

- include `author_agent_id`
- include denormalized `author_handle_at_time`
- include denormalized `author_display_name_at_time`
- include the post body and created timestamp
- include generation metadata fields matching the other generated-action tables

This strikes the right balance:

- existing turn actions do not get a larger semantic rewrite than necessary
- the new table does not inherit avoidable ambiguity

## Critical Architectural Calls To Freeze Before Coding

### 1. Close the naming TODO and the scoping gap completely

The doc TODO says "migrate all Turn tables to use the `turn_*` nomenclature." Given the stated desired outcome, this epic should include `generated_feeds -> turn_generated_feeds` rather than leaving a single legacy turn-table name behind.

That means the target steady state is:

- `turns`
- `turn_generated_feeds`
- `turn_likes`
- `turn_comments`
- `turn_follows`
- `turn_posts`
- `turn_metrics`

This is the right call because:

- it removes the last ambiguous turn-table name in the schema
- it makes turn identity explicit instead of inferring it from duplicated columns
- it simplifies the linter and docs story
- it keeps the epic aligned with the literal architecture goal instead of requiring a cleanup chaser

### 2. Make runtime artifacts children of turns, not peers of runs

This is the most important behavioral change in the revised proposal.

I no longer recommend describing `turn_likes`, `turn_comments`, `turn_follows`, `turn_generated_feeds`, or `turn_posts` as "run-scoped tables with a `turn_number` column." They should be:

- turn-scoped tables
- children of a canonical `turns` row
- linked to the owning run through that turn

The practical DB rule should be:

- `runs` is the parent of `turns`
- `turns` is the parent of all runtime activity tables
- every runtime activity row still stores `run_id` and `turn_number`
- but referential integrity should be enforced via composite FK (`run_id`, `turn_number`) -> `turns`

This is the cleanest way to encode the invariant you want:

- runtime activity belongs to one turn
- turns belong to one run

### 3. Freeze the feed-visible post ID contract

This is the single most important design constraint for `turn_posts`.

Today:

- feed rows in `generated_feeds.post_ids` point at run-scoped seeded posts
- `simulation/core/models/posts.py::run_post_snapshot_to_post(...)` maps `run_post_id` into the feed-visible `Post.post_id`
- `simulation/core/query_service.py` resolves feed post IDs only from `run_posts`

Once `turn_posts` exists, likes/comments may need to target either:

- a seeded `run_post`
- a newly-authored `turn_post`

My recommendation is:

- keep `post_id` in `turn_likes` and `turn_comments` as a generic feed-visible identifier
- rename `generated_feeds` to `turn_generated_feeds` and keep `turn_generated_feeds.post_ids` as a list of the same generic feed-visible identifiers
- define the namespace as:
  - seeded posts use `run_post_id`
  - turn-authored posts use `turn_post_id`
- resolve those IDs in the service layer by checking `run_posts` and `turn_posts`

This means:

- no polymorphic FK at the database layer
- application/service-layer referential validation instead

That is acceptable here and is much cleaner than trying to force one FK across two physical tables.

### 4. Do not bundle handle-to-agent-id normalization into the rename unless you deliberately want a bigger epic

There is a tempting cleanup to make `turn_likes/comments/follows` join through `run_agents.agent_id` instead of handles. I would not do that by default in the same epic.

Reasons:

- it is not required to achieve the naming outcome
- it touches generators, action history, validators, fixtures, tests, and query hydration semantics
- it will make the migration harder to reason about than it needs to be

If you want that cleanup, make it an explicit follow-on PR after the rename lands.

## Proposed End-State Schema

### `turns`

This should become the canonical parent row for a turn within a run. I would achieve this via a hard cutover from `turn_metadata` rather than keeping `turn_metadata` as the long-term parent name.

Recommended columns:

- `run_id` not null
- `turn_number` not null
- `total_actions` not null
- `created_at` not null

Recommended constraints and indexes:

- FK `run_id -> runs.run_id`
- primary key on (`run_id`, `turn_number`)
- check `turn_number >= 0`

Important invariant:

- every runtime artifact row must reference an existing `turns` row
- the system should not persist runtime activity for a turn that does not exist as a first-class turn

### `turn_generated_feeds`

This should remain semantically identical to the current `generated_feeds` table, but under an explicit turn-scoped name.

Recommended columns:

- `feed_id` not null
- `run_id` not null
- `turn_number` not null
- `agent_handle` not null
- `post_ids` not null
- `created_at` not null

Recommended constraints and indexes:

- FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- primary key on (`agent_handle`, `run_id`, `turn_number`)
- keep any existing read-path indexes that are still useful after rename

Important invariant:

- `post_ids` remains the canonical feed-visible post ID list consumed by the query layer
- the rename should not change feed row semantics, only lifecycle clarity

### `turn_likes`

Keep the current logical payload, just move it under the correct table name and constraint/index names.

Recommended columns:

- `like_id` primary key
- `run_id` not null
- `turn_number` not null
- `agent_handle` not null
- `post_id` not null
- `created_at` not null
- `explanation` nullable
- `model_used` nullable
- `generation_metadata_json` nullable
- `generation_created_at` nullable

Recommended constraints and indexes:

- FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- check `turn_number >= 0`
- unique on (`run_id`, `turn_number`, `agent_handle`, `post_id`)
- covering index on (`run_id`, `turn_number`, `agent_handle`)

### `turn_comments`

Recommended columns:

- `comment_id` primary key
- `run_id` not null
- `turn_number` not null
- `agent_handle` not null
- `post_id` not null
- `text` not null
- `created_at` not null
- `explanation` nullable
- `model_used` nullable
- `generation_metadata_json` nullable
- `generation_created_at` nullable

Recommended constraints and indexes:

- FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- check `turn_number >= 0`
- unique on (`run_id`, `turn_number`, `agent_handle`, `post_id`)
- covering index on (`run_id`, `turn_number`, `agent_handle`)

### `turn_follows`

Recommended columns:

- `follow_id` primary key
- `run_id` not null
- `turn_number` not null
- `agent_handle` not null
- `user_id` not null
- `created_at` not null
- `explanation` nullable
- `model_used` nullable
- `generation_metadata_json` nullable
- `generation_created_at` nullable

Recommended constraints and indexes:

- FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- check `turn_number >= 0`
- unique on (`run_id`, `turn_number`, `agent_handle`, `user_id`)
- covering index on (`run_id`, `turn_number`, `agent_handle`)

### `turn_posts`

Recommended first-version columns:

- `turn_post_id` primary key
- `run_id` not null
- `turn_number` not null
- `author_agent_id` not null
- `author_handle_at_time` not null
- `author_display_name_at_time` not null
- `body_text` not null
- `created_at` not null
- `explanation` nullable
- `model_used` nullable
- `generation_metadata_json` nullable
- `generation_created_at` nullable

Recommended constraints and indexes:

- FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- FK (`run_id`, `author_agent_id`) -> `run_agents(run_id, agent_id)`
- check `turn_number >= 0`
- index on (`run_id`, `turn_number`, `author_agent_id`)
- index on (`run_id`, `author_handle_at_time`)

Important first-version non-goals:

- no reply-thread hierarchy yet
- no quote/repost semantics yet
- no attempt to backfill historical authored-turn posts unless a real row-level source exists

## Robust Migration Strategy

### Recommended migration shape

Use **create new tables -> copy data -> switch code -> drop old tables**.

I do **not** recommend a bare `ALTER TABLE ... RENAME TO ...` as the primary plan.

Why:

- you will likely want new constraint names and index names anyway
- you may want to introduce `turn_posts` in the same schema pass
- SQLite table renames are convenient, but they leave you with a less intentional result if the goal is a clean end-state schema

Recommended Alembic approach:

1. Create `turns`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and `turn_posts`.
2. Copy legacy data:
   - `INSERT INTO turns (...) SELECT ... FROM turn_metadata`
   - `INSERT INTO turn_generated_feeds (...) SELECT ... FROM generated_feeds`
   - `INSERT INTO turn_likes (...) SELECT ... FROM likes`
   - `INSERT INTO turn_comments (...) SELECT ... FROM comments`
   - `INSERT INTO turn_follows (...) SELECT ... FROM follows`
3. Leave `turn_posts` empty unless the PR also introduces write-path support.
4. Update application code to read/write only `turn_*`.
5. Drop `turn_metadata`, `generated_feeds`, `likes`, `comments`, and `follows` in the same migration series once tests pass.

Because you are fine with breaking changes and there are no external clients yet, I would avoid:

- dual writes
- runtime fallback reads from both old and new tables
- view-based compatibility layers

### Data preservation rules

- Preserve all existing rows in `generated_feeds`, `likes`, `comments`, and `follows` when migrating local/dev databases.
- Do not invent `turn_posts` rows.
- Do not rewrite existing action payload semantics during the rename.

### Transactionality

The current `SimulationPersistenceService.write_turn(...)` already treats a turn write as atomic. Preserve that invariant:

- create the `turns` row first inside the transaction
- if a turn write fails, there should not be a partial turn where `turns` exists but child artifacts do not
- if `turn_posts` is added to the write path, it must be written in the same transaction as `turns`, `turn_metrics`, and the rest of the turn actions

## Things To Watch Out For

### 1. `turn_posts` is not useful unless query hydration changes too

Today these files assume feed-visible posts come only from `run_posts`:

- `simulation/core/query_service.py`
- `simulation/core/engine.py`
- `simulation/core/models/posts.py`

If you add `turn_posts` but do not add a resolver that can hydrate `run_posts + turn_posts`, the new table exists but cannot actually participate in feeds or action lookups.

### 2. `TurnAction` currently has no `POST`

`simulation/core/models/actions.py` currently defines:

- `LIKE`
- `COMMENT`
- `FOLLOW`

If this epic includes actual authored-post generation, you must also add:

- `TurnAction.POST`

and then update:

- `simulation/core/models/turns.py`
- `simulation/core/command_service.py`
- `simulation/api/schemas/simulation.py`
- tests that assert turn action totals

If this epic is only laying the `turn_posts` foundation, leave `POST` out for now and document that the table is intentionally unused until the post-generation follow-up lands.

### 3. Action history is keyed to the current identifiers

`simulation/core/action_history/interfaces.py` and `simulation/core/action_history/recording.py` currently store:

- likes/comments by `post_id`
- follows by `user_id`

That is compatible with the recommended plan, but it means you should **not** silently switch identifier semantics mid-epic.

### 4. The API read path is already behind the core query layer

`simulation/api/services/run_query_service.py::get_turns_for_run(...)` still returns empty `agent_actions`. The lower-level `simulation/core/query_service.py` can hydrate actions, but the API service does not currently expose them in that endpoint.

That is not caused by this epic, but it matters for review:

- a successful rename/migration does not automatically improve the external turn-details API
- if you want the epic to feel complete at product level, you may want one PR that uses the core query path to surface real persisted turn actions

### 5. Feed rename has broad blast radius

Renaming `generated_feeds` to `turn_generated_feeds` is the right move, but it touches more than the other table renames because feed reads and local-dev fixtures depend on it directly.

Areas to watch closely:

- generated feed adapters and repositories
- seed loader fixtures
- API read services and tests
- any docs that refer to `generated_feeds` as current truth

## Happy Flow

1. A run is created and seed-state data is snapshotted into `run_agents`, `run_follow_edges`, `run_posts`, `run_post_likes`, and `run_post_comments` in `simulation/core/command_service.py`.
2. During a turn, `simulation/core/command_service.py` generates turn outputs and `db/services/simulation_persistence_service.py` writes the canonical `turns` row, `turn_metrics`, and the `turn_*` child rows in one transaction.
3. If authored-turn posts are enabled, `turn_posts` rows are created in that same transaction before downstream likes/comments reference their `turn_post_id`.
4. `turn_generated_feeds.post_ids` remains the feed-visible post ID list, but those IDs may now resolve to either `run_posts` or `turn_posts`.
5. `simulation/core/query_service.py` hydrates feed posts by resolving the mixed ID set across `run_posts` and `turn_posts`, then hydrates `turn_likes`, `turn_comments`, and `turn_follows` for the requested turn.
6. The UI/API sees a consistent model: run-start posts come from `run_*`, runtime artifacts come from `turn_*`, and every runtime artifact is reached through a turn that belongs to a run.

## Interface Or Contract Freeze

Freeze these contracts before parallel implementation starts:

1. `turns` is the canonical parent row for a turn within a run.
2. Every runtime artifact table must carry non-null `run_id` and `turn_number` and FK to `turns(run_id, turn_number)`.
3. `turn_generated_feeds.post_ids` remains the canonical feed-visible post ID list.
4. `turn_likes.post_id` and `turn_comments.post_id` reference that same feed-visible ID namespace.
5. Seeded feed-visible post IDs remain `run_post_id`.
6. Turn-authored feed-visible post IDs become `turn_post_id`.
7. This epic does not change the meaning of `turn_follows.user_id`; it remains the followed handle/identifier used by current generators.
8. This epic hard-cuts all repository/adapter/model code to the `turn_*` table names; no old/new compatibility mode remains after merge.

## Serial Coordination Spine

### S1. Freeze the scope and contracts

Objective: freeze `turns` as the canonical runtime parent, freeze `generated_feeds -> turn_generated_feeds` as required scope, and freeze the feed-visible post ID contract.

Files to inspect:

- `docs/architecture/agents-turns-runs-data-model.md`
- `docs/architecture/seed-state-run-snapshot-turn-events.md`
- `db/schema.py`
- `simulation/core/models/posts.py`
- `simulation/core/models/actions.py`
- `simulation/core/models/turns.py`

Done when:

- the proposal decisions above are accepted
- the team knows `turns` is the canonical parent row for runtime activity
- the team knows `generated_feeds -> turn_generated_feeds` is part of this epic
- the team knows whether `turn_posts` is schema-only or includes a write path

### S2. Land the DB migration spine

Objective: create the new turn-scoped tables and move local/dev data safely.

Files to inspect:

- `db/schema.py`
- `db/migrations/versions/*.py`

Done when:

- `turns`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and `turn_posts` exist at HEAD
- legacy data copies successfully
- old tables are removed if the hard cutover is part of the same migration

### S3. Integrate and verify

Objective: merge the parallel packets below in order and run the final verification set.

## Parallel Task Packets

### P1. Persistence rename packet

Task ID: `P1-turn-action-persistence`

Objective: rename the existing runtime persistence layer into turn-scoped tables hanging off `turns`, including `turn_generated_feeds`, without changing action semantics.

Why parallelizable:

- this packet can focus on adapters/repositories/models once the schema contract is frozen
- it does not need to own query hydration or docs

Exact files to inspect:

- `db/adapters/base.py`
- `db/adapters/sqlite/generated_feed_adapter.py`
- `db/adapters/sqlite/like_adapter.py`
- `db/adapters/sqlite/comment_adapter.py`
- `db/adapters/sqlite/follow_adapter.py`
- `db/repositories/interfaces.py`
- `db/repositories/generated_feed_repository.py`
- `db/repositories/like_repository.py`
- `db/repositories/comment_repository.py`
- `db/repositories/follow_repository.py`
- `simulation/core/models/persisted_actions.py`
- `db/services/simulation_persistence_service.py`
- `simulation/core/models/turns.py`

Exact files allowed to change:

- the files listed above

Exact files forbidden to change:

- `simulation/core/query_service.py`
- `simulation/core/engine.py`
- `simulation/api/services/run_query_service.py`
- any docs files

Preconditions:

- S1 complete
- table names and constraint names frozen

Dependency tasks:

- S2 for final verification against migrated schema

Required contracts and invariants:

- no behavior change beyond table names
- runtime artifacts are children of `turns`
- `write_turn(...)` remains transactional
- row payloads keep current semantics

Implementation steps:

1. Introduce the `turns` parent model and make the write path persist it as the canonical turn row.
2. Rename adapter SQL statements to `turn_generated_feeds`, `turn_likes`, `turn_comments`, and `turn_follows`.
3. Rename any constraint/index assumptions in adapter tests if needed.
4. Rename repository docstrings and model comments to "turn actions" rather than legacy names.
5. Keep method signatures stable unless a wider naming refactor is deliberately approved.
6. Update the persistence service wiring to use the renamed tables through the same repository interfaces and parent `turns` row.

Exact verification commands:

- `uv run pytest tests/db/repositories/test_action_repositories_integration.py`
- `uv run pytest tests/db/repositories/test_generated_feed_repository.py`
- `uv run pytest tests/simulation/core/test_command_service.py`

Expected outputs from verification:

- both test modules pass
- generated-feed repository tests pass
- persisted action rows round-trip through the renamed tables

Done-when checklist:

- adapters no longer reference `generated_feeds`, `likes`, `comments`, or `follows`
- runtime artifact writes cannot occur without a `turns` row
- repositories still pass integration tests
- no transactional regression in turn persistence

Coordinator review checklist:

- confirm no query-layer logic was changed here
- confirm no identifier semantics changed here

### P2. `turn_posts` schema and resolver packet

Task ID: `P2-turn-posts-foundation`

Objective: introduce `turn_posts` as a child of `turns` and add the resolver primitives needed for mixed run-post / turn-post hydration.

Why parallelizable:

- it can proceed mostly independently once the ID contract is frozen
- it does not need to own legacy action-table renames

Exact files to inspect:

- `db/schema.py`
- `db/migrations/versions/*.py`
- `simulation/core/models/posts.py`
- `simulation/core/engine.py`
- `simulation/core/query_service.py`
- `db/repositories/interfaces.py`

Exact files allowed to change:

- the files listed above
- new `turn_post` repository/adapter/model files if created

Exact files forbidden to change:

- existing like/comment/follow generator algorithm files
- UI files under `ui/`

Preconditions:

- S1 complete

Dependency tasks:

- none for schema work
- P1 not required unless shared interfaces are changed

Required contracts and invariants:

- feed-visible post IDs remain opaque IDs shared by feeds and action tables
- `turn_posts` is a child of `turns`
- resolver supports both `run_posts` and `turn_posts`
- no synthetic backfill of `turn_posts`

Implementation steps:

1. Add `turn_posts` to `db/schema.py` with composite FK to `turns`.
2. Add the Alembic migration that creates `turn_posts`.
3. Add repository and adapter interfaces for reading turn posts by ID and by run/turn.
4. Add a post resolver in `simulation/core/query_service.py` and `simulation/core/engine.py` that can hydrate mixed IDs from `run_posts` and `turn_posts`.
5. If this PR includes write-path support, add insert methods too; if not, keep write APIs out until the generation packet lands.

Exact verification commands:

- `uv run pytest tests/lint/test_lint_schema_conventions.py`
- `uv run pytest tests/simulation/core/test_query_service.py`

Expected outputs from verification:

- schema linter passes
- query tests prove mixed-ID resolution works or is at least ready for turn-post reads

Done-when checklist:

- `turn_posts` exists in schema and migrations
- a resolver path exists for turn-authored posts
- no query path assumes only `run_posts`

Coordinator review checklist:

- confirm post ID contract is exactly the frozen one
- confirm the PR does not silently change run-post semantics

### P3. Query/API exposure packet

Task ID: `P3-turn-read-surface`

Objective: make turn-read code clearly depend on `turns` plus `turn_*` child tables, including `turn_generated_feeds`, and, if desired, expose persisted actions through the API service.

Why parallelizable:

- it can work against the repository interfaces after P1/P2 contracts are stable

Exact files to inspect:

- `simulation/core/query_service.py`
- `simulation/core/utils/turn_data_hydration.py`
- `simulation/api/services/run_query_service.py`
- `simulation/api/schemas/simulation.py`

Exact files allowed to change:

- the files listed above

Exact files forbidden to change:

- database migrations
- low-level adapters

Preconditions:

- P1 complete
- P2 complete if `turn_posts` should participate in query hydration

Dependency tasks:

- P1
- P2 for mixed post resolution

Required contracts and invariants:

- runtime artifacts are hydrated through `turns` and `turn_*` tables
- API responses stay deterministic
- no fallback reads from legacy table names

Implementation steps:

1. Update core query hydration to read `turns`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, and `turn_follows`.
2. Keep persisted action -> generated action conversion behavior identical.
3. Optionally replace the empty `agent_actions={}` response in `simulation/api/services/run_query_service.py` with real hydrated actions if you want the product-facing API to benefit from the epic.

Exact verification commands:

- `uv run pytest tests/simulation/core/test_query_service.py`
- `uv run pytest tests/api/test_run_query_service.py`

Expected outputs from verification:

- turn data hydration tests pass
- API service tests pass

Done-when checklist:

- no read path references legacy action tables
- turn action hydration still sorts deterministically

Coordinator review checklist:

- confirm API behavior change, if any, is intentional and documented

### P4. Tests, lint, and docs packet

Task ID: `P4-docs-tests-guardrails`

Objective: update guardrails and documentation so the repo no longer treats runtime artifacts as run-scoped rows and no longer treats `generated_feeds/likes/comments/follows` as the accepted baseline.

Why parallelizable:

- this packet should not need to touch core runtime code once contracts are frozen

Exact files to inspect:

- `scripts/lint_schema_conventions.py`
- `tests/lint/test_lint_schema_conventions.py`
- `docs/architecture/agents-turns-runs-data-model.md`
- `docs/architecture/seed-state-run-snapshot-turn-events.md`
- strategy docs that mention legacy event names

Exact files allowed to change:

- the files listed above
- targeted tests referencing the old table names

Exact files forbidden to change:

- core runtime implementation files

Preconditions:

- S1 complete

Dependency tasks:

- none for docs/lints

Required contracts and invariants:

- docs match the actual schema at HEAD
- schema linter no longer encodes stale legacy assumptions for legacy turn table names

Implementation steps:

1. Remove `generated_feeds`, `likes`, `comments`, and `follows` from the legacy turn-table allowlist in `scripts/lint_schema_conventions.py`.
2. Add or update linter rules so runtime artifact tables must include non-null `run_id` and `turn_number`.
3. Update architecture docs to describe `turns`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and `turn_posts`.
4. Update tests to assert the new schema convention behavior.

Exact verification commands:

- `uv run pytest tests/lint/test_lint_schema_conventions.py`

Expected outputs from verification:

- schema convention tests pass
- docs and lints describe the same truth as `db/schema.py`

Done-when checklist:

- docs no longer describe `likes/comments/follows` as the expected steady state
- the schema linter would fail if someone reintroduced a new legacy-named turn table

Coordinator review checklist:

- confirm docs consistently use `turn_generated_feeds`

## Integration Order

1. S1 contract freeze
2. S2 migration spine
3. P1 persistence rename
4. P2 `turn_posts` schema/resolver
5. P3 query/API exposure
6. P4 docs/tests/guardrails
7. S3 final verification

## Proposed PR Plan

### PR 1: Freeze the turn-event contract

Scope:

- update architecture docs
- freeze `turns` as the canonical per-run turn entity
- freeze `generated_feeds -> turn_generated_feeds` as required
- document the feed-visible post ID contract for `turn_posts`

Why first:

- this prevents a half-implemented `turn_posts` design
- it keeps later PRs mechanical instead of interpretive

### PR 2: Introduce `turns` and hard-cut `generated_feeds/likes/comments/follows` to `turn_generated_feeds/turn_likes/turn_comments/turn_follows`

Scope:

- hard-cut `turn_metadata -> turns`
- Alembic migration using create/copy/drop
- `db/schema.py`
- adapters, repositories, persistence service
- feed repository/adapters and local-dev fixtures that read/write generated feeds
- tests for action repository round-trips and turn writes

Why separate:

- this is the highest-value nomenclature cleanup
- it is where the runtime scoping invariant becomes real
- it is mechanically testable
- it avoids mixing rename work with new turn-post behavior

### PR 3: Introduce `turn_posts` and mixed post-resolution support

Scope:

- `turn_posts` schema
- repository/adapter/model support
- composite FK from `turn_posts` to `turns`
- mixed `run_posts + turn_posts` resolution in `simulation/core/query_service.py` and `simulation/core/engine.py`

Why separate:

- `turn_posts` is the only part of this epic that creates a new semantic domain
- it deserves its own review surface

### PR 4: Optional authored-post generation support

Scope:

- only if you actually want agents to author posts during turns now
- add `TurnAction.POST`
- add generated-post model/generator/persistence wiring
- make feeds and action totals aware of newly-authored posts

Why optional:

- the table and resolver can land before generation behavior
- if you do not need authored-turn posts yet, this PR can be deferred cleanly

## Alternative Approaches

### Alternative 1: bare table renames with `ALTER TABLE`

Pros:

- shorter migration

Cons:

- less intentional end-state DDL
- awkward constraint/index naming cleanup
- less flexibility if the same migration also introduces `turn_posts`

Why I do not recommend it:

- you want a robust cleanup, not just the minimum DDL trick

### Alternative 2: rename plus agent-ID normalization in one epic

Pros:

- stronger relational model

Cons:

- much larger blast radius
- more regression risk
- harder to review

Why I do not recommend it:

- it mixes a nomenclature refactor with a semantics refactor

### Alternative 3: leave `turn_posts` for later

Pros:

- smaller immediate scope

Cons:

- misses the opportunity to define the turn-post identity contract while already working through the turn-event cleanup
- leaves the architecture doc TODO only partially addressed

Why I do not recommend it:

- if this is your next large epic, `turn_posts` belongs in the plan now

## Manual Verification

- [ ] Run the targeted database and persistence tests:
  `uv run pytest tests/db/repositories/test_action_repositories_integration.py tests/simulation/core/test_command_service.py tests/simulation/core/test_query_service.py tests/lint/test_lint_schema_conventions.py`
  Expected result: all tests pass with no references to legacy `generated_feeds/likes/comments/follows` tables and with runtime artifacts hanging off `turns`.
- [ ] Run the API query-service tests if PR 3 changes the API surface:
  `uv run pytest tests/api/test_run_query_service.py`
  Expected result: turn details still serialize deterministically.
- [ ] Run repo-level static checks for touched files:
  `uv run ruff check .`
  Expected result: no new lint failures in touched code.
- [ ] Run type checking if interfaces or schemas changed materially:
  `uv run pyright .`
  Expected result: no new type errors in turn persistence/query code.
- [ ] Verify the migration on a fresh SQLite database:
  `SIM_DB_PATH=/tmp/turn_tables_refactor.db uv run alembic -c pyproject.toml upgrade head`
  Expected result: migration succeeds and the DB contains `turns`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and `turn_posts`.
- [ ] If old local/dev data must be preserved, test migration from a pre-epic database snapshot and confirm action row counts match before and after copy.

## Final Verification

- Schema at HEAD reflects the intended steady state.
- Runtime artifacts are modeled as children of `turns`, and `turns` are children of `runs`.
- Runtime write paths no longer mention `generated_feeds/likes/comments/follows`.
- Runtime read paths no longer mention `generated_feeds/likes/comments/follows`.
- The `turn_posts` contract is either fully wired or explicitly documented as foundation-only.
- The architecture docs describe `turn_generated_feeds` as the steady-state feed table.

## Bottom Line

The cleanest way to do this is:

1. hard-cut `likes/comments/follows` to `turn_likes/turn_comments/turn_follows`
2. hard-cut `generated_feeds` to `turn_generated_feeds`
3. hard-cut `turn_metadata` into a canonical `turns` parent so runtime artifacts are truly turn-scoped
4. introduce `turn_posts` with a frozen feed-visible post ID contract
5. update query hydration so posts can resolve from both `run_posts` and `turn_posts`
6. keep the bigger handle-to-agent-id cleanup out of scope unless you intentionally choose to expand the epic

That gets you a robust, reviewable migration with clear PR boundaries and without carrying the legacy table names deeper into the next phase of the system.
