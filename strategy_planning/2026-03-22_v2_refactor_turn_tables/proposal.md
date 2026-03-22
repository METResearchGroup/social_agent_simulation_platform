---
name: Turn tables refactor proposal v2
overview: Update the March 19 turn-table refactor plan to reflect the now-complete agent_id migration stack, preserve current canonical ID and post-author contracts, and define a staged hard-cutover from legacy turn-event tables to a fully turn-scoped schema centered on turns and turn_posts.
---

# Turn Tables Refactor Proposal V2

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Preserve canonical `agent_id` / `author_agent_id` contracts already landed
- Do not reintroduce handle-keyed persistence or query semantics

## Overview

This is a revision of the original [March 19 turn-table proposal](../2026-03-19_refactor_turn_tables/proposal.md), rewritten after reviewing the current repo state at HEAD, the canonical identity migration plan in [March 20 agent_id migration proposal](../2026-03-20_agent_id_migration/proposal.md), the pre-closeout progress summary in [`CURRENT_PROGRESS_STATUS.md`](../../CURRENT_PROGRESS_STATUS.md), and the merged implementation stack in [PR #268](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/268), [PR #269](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/269), [PR #270](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/270), [PR #272](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/272), [PR #274](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/274), [PR #275](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/275), [PR #276](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/276), [PR #278](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/278), and [PR #281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281).

The core change in v2 is that the turn-table refactor can no longer be planned as a mostly mechanical naming cleanup that preserves handle-shaped action semantics. That assumption was reasonable on March 19, but it is stale now. The merged agent-ID epic completed the identity migration all the way through storage, runtime generation, repository boundaries, query hydration, API payloads, UI consumption, and milestone verification. The turn-table plan must therefore treat canonical `agent_id`, `target_agent_id`, and `author_agent_id` as fixed architectural inputs and must not reopen those decisions.

The other major v2 change is that the proposal now treats the transactional boundary as first-class work. Today, `generated_feeds` is still written before `SimulationPersistenceService.write_turn(...)`, which means a failed turn can leave feed rows behind without corresponding `turn_metadata`, metrics, or actions. The refactor should use this schema-cutover to fix that boundary and make every per-turn artifact a child of a canonical `turns` row persisted atomically.

## What Changed Since March 19

The original [March 19 turn-table proposal](../2026-03-19_refactor_turn_tables/proposal.md) still got several important things right:

- the repo still needs a hard cutover away from legacy turn-event names
- `generated_feeds -> turn_generated_feeds` should be in scope
- `turn_metadata -> turns` should become a real parent turn entity
- `turn_posts` is still the missing table that prevents fully representing authored activity during turns
- query hydration still needs a mixed `run_posts + turn_posts` story once `turn_posts` exists

But several assumptions are now obsolete because of the agent-ID migration:

- The March 19 proposal explicitly recommended not bundling handle-to-agent-id normalization into the turn-table epic. That recommendation has already been overtaken by [PR #272](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/272), [PR #274](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/274), [PR #275](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/275), [PR #276](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/276), [PR #278](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/278), and [PR #281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281).
- The March 19 proposal preserved `agent_handle` and `user_id` semantics for turn actions. That is no longer acceptable. Current persisted turn-action semantics are canonical `agent_id` and `target_agent_id`, and the query/API/UI boundary already expects that.
- The pre-#281 summary in [`CURRENT_PROGRESS_STATUS.md`](../../CURRENT_PROGRESS_STATUS.md) said the remaining work in the agent-ID epic was milestone verification and fixture cleanup. [PR #281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281) closed that gap. This means the turn-table refactor should build on a completed identity migration, not a partially finished one.

## Reviewed Implementation History

### Original planning inputs

- [March 19 turn-table proposal](../2026-03-19_refactor_turn_tables/proposal.md): first pass at the turn-table cleanup, before the identity migration finished.
- [March 20 agent_id migration proposal](../2026-03-20_agent_id_migration/proposal.md): repo-wide identity normalization plan that ultimately changed the correct target shape for turn tables.
- [`CURRENT_PROGRESS_STATUS.md`](../../CURRENT_PROGRESS_STATUS.md): useful review summary of the stack through [PR #278](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/278), but now stale because it intentionally excluded [PR #281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281).

### Merged PR stack and implications for this proposal

| PR | What landed | Why it matters for the turn-table refactor |
| --- | --- | --- |
| [#268](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/268) | Introduced `lib/agent_id.py` canonical helper and validator, plus `Agent` model guardrails. | Canonical `agent_id` is now a frozen contract, not a proposal-level option. |
| [#269](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/269) | Normalized new agent creation paths and local-dev seeds to canonical IDs. | New turn tables must assume canonical IDs are emitted on all creation paths. |
| [#270](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/270) | Rewrote existing agent PK/FK graph to canonical IDs. | Turn-table migrations must preserve the already-migrated identity graph, not invent a second mapping layer. |
| [#272](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/272) | Moved action/feed schema semantics to `agent_id` and `target_agent_id`. | Any new `turn_*` tables must preserve those exact semantics under new names. |
| [#274](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/274) | Moved runtime history and duplicate suppression to canonical actor keys. | The refactor must not reintroduce handle-keyed history or dedupe. |
| [#275](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/275) | Required `Post.author_agent_id` and added `feed_posts.author_agent_id` FK. | `turn_posts` should start with explicit `author_agent_id` from day one. |
| [#276](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/276) | Hardened repository and SQLite boundaries to reject non-canonical IDs. | New persistence layers should keep validation at repository/adapter boundaries and not add fallback resolution. |
| [#278](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/278) | Updated query/API/UI boundary to canonical `agent_id` keying for turns. | The turn-table refactor must preserve ID-keyed `TurnData` and `TurnSchema` contracts. |
| [#281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281) | Closed Phase 7 with head-state verification, canonical fixtures, and API persistence proof. | The identity migration is complete. This proposal should assume that work is done and stable. |

## Current State At HEAD

After reviewing the current codebase, the actual baseline is:

- `db/schema.py` still defines `turn_metadata`, `generated_feeds`, `likes`, `comments`, and `follows`.
- Those tables already use canonical `agent_id` and `target_agent_id` semantics where appropriate.
- `turn_metrics` already exists and is correctly named, but it is still not modeled as a child of a canonical `turns` parent.
- `simulation/core/services/query_service.py` already returns `TurnData` keyed by canonical `agent_id`, not by handle.
- `simulation/api/services/run_query_service.py` already serializes turn payloads keyed by canonical `agent_id`.
- `simulation/core/models/feeds.py` already treats `GeneratedFeed.agent_handle` as display-only metadata and `agent_id` as the persistence key.
- There is still no live `turn_posts` implementation in schema, migrations, repositories, adapters, or query logic.
- `feeds/feed_generator.py` still persists `generated_feeds` before `SimulationPersistenceService.write_turn(...)`, which leaves a real partial-persistence risk.
- `scripts/lint_schema_conventions.py` still blesses the legacy turn-event tables via `LEGACY_TURN_EVENT_TABLES`, so the linter remains aligned with the old state rather than the desired steady state.

## Desired Outcome

This epic should land the following end state:

- `turn_metadata` is replaced by `turns`, which becomes the canonical parent row for per-turn history within a run.
- `generated_feeds` is replaced by `turn_generated_feeds`.
- `likes`, `comments`, and `follows` are replaced by `turn_likes`, `turn_comments`, and `turn_follows`.
- `turn_metrics` remains, but now references `turns(run_id, turn_number)` as its direct parent rather than only `runs.run_id`.
- A new `turn_posts` table exists as the canonical persisted representation of posts authored during a run turn.
- Every turn-event table is a true child of `turns` via composite FK `(run_id, turn_number) -> turns(run_id, turn_number)`.
- Turn writes are atomic: `turns`, `turn_metrics`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and eventually `turn_posts` are persisted in one transaction.
- Query, API, and UI continue to use canonical `agent_id`, `target_agent_id`, and `author_agent_id` semantics without change at the logical contract boundary.
- Historical replay still uses `run_*` snapshots plus `turn_*` tables; it does not fall back to live seed-state rows for behaviorally relevant history.
- The schema linter and architecture docs stop treating legacy turn-event names as acceptable steady state.

## Architectural Calls To Freeze

These decisions should be treated as frozen before coding begins.

### 1. Canonical IDs stay canonical everywhere

This refactor must preserve the contracts established by [PR #268](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/268), [PR #272](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/272), [PR #274](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/274), [PR #275](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/275), [PR #276](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/276), [PR #278](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/278), and [PR #281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281):

- `GeneratedFeed` is keyed by canonical `agent_id`.
- turn actions are keyed by canonical `agent_id`.
- follows use canonical `target_agent_id`.
- posts use required `author_agent_id`.
- handles remain display metadata only.

This proposal must not add compatibility behavior that silently accepts handle-shaped values in new turn-event persistence paths.

### 2. `turns` becomes the canonical parent row

`turn_metadata` is currently the de facto turn parent, but only by convention. The target model is:

- `runs` is the parent of `turns`
- `turns` is the parent of all per-turn history tables
- every per-turn table stores non-null `run_id` and non-null `turn_number`
- every per-turn table references `turns(run_id, turn_number)` directly

This should apply to:

- `turn_metrics`
- `turn_generated_feeds`
- `turn_likes`
- `turn_comments`
- `turn_follows`
- `turn_posts`

### 3. Turn persistence must be atomic

The current split write path is a real architectural defect:

- `feeds/feed_generator.py` writes generated feeds separately
- `db/services/simulation_persistence_service.py` writes metadata, metrics, and actions later

The steady state must instead be:

- feed generation produces in-memory `GeneratedFeed` models only
- a single turn write bundle is handed to persistence
- persistence writes `turns`, metrics, feeds, actions, and optional turn posts in one transaction

This is not optional cleanup. It is part of making turn history a coherent unit.

### 4. `turn_generated_feeds.post_ids` remains the feed-visible post ID contract

The feed row still needs to carry the ordered feed-visible post identifiers shown to an agent during a turn. The correct contract is:

- `turn_generated_feeds.post_ids` stays the source of truth for feed ordering
- likes/comments continue to point at that same feed-visible post ID namespace
- the read path resolves those IDs in application logic

Recommended namespace:

- seeded run-start posts use `run_post_id`
- turn-authored posts use `turn_post_id`

This avoids a polymorphic FK while keeping one shared ID vocabulary.

### 5. `turn_posts` starts with explicit author identity

Because [PR #275](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/275) already established `author_agent_id` as mandatory for `Post`, the first version of `turn_posts` should include:

- `turn_post_id`
- `run_id`
- `turn_number`
- `author_agent_id`
- `author_handle_at_time`
- `author_display_name_at_time`
- `body_text`
- `created_at`
- generation metadata columns matching other generated-action rows

The new table should not inherit any old handle-derived author logic.

### 6. No mixed-lifecycle table tricks

The architecture docs in `docs/architecture/agents-turns-runs-data-model.md` and `docs/architecture/seed-state-run-snapshot-turn-events.md` remain correct:

- seed state lives in `Agent*`
- historical run-start truth lives in `Run*`
- append-only turn history lives in `Turn*`

Therefore:

- do not make `run_id` or `turn_number` nullable to collapse scopes
- do not reuse one table for baseline plus events
- do not use a `source = manual | simulation` discriminator to avoid the correct table split

### 7. Hard cutover, not a long-lived compatibility layer

There are no external clients that justify dual writes or indefinite old/new aliases. The recommended strategy is:

- create new turn tables
- copy legacy data
- update code to read/write only the new names
- remove legacy tables

Short-lived migration internals are fine. Long-lived compatibility reads are not.

## Invariants To Maintain

The following invariants must hold throughout the implementation:

- Every persisted agent-key column remains canonical 16-character lowercase hex where already required by the merged identity migration.
- `TurnData` and `TurnSchema` remain keyed by canonical `agent_id`.
- Historical reads do not consult live `agent_*` or `feed_posts` rows for behaviorally relevant values that should come from `run_*` or `turn_*`.
- `GeneratedFeed.agent_handle` and other handle fields remain display-only.
- `turn_generated_feeds.post_ids`, `turn_likes.post_id`, and `turn_comments.post_id` refer to the same feed-visible ID namespace.
- Duplicate suppression and action history remain keyed by canonical IDs.
- No per-turn artifact row may exist without a corresponding `turns` row.
- If a turn write fails, none of the turn's rows should be committed.

## Target Data Model

### `turns`

This replaces `turn_metadata` as the canonical parent turn row.

Recommended columns:

- `run_id` not null
- `turn_number` not null
- `total_actions` not null
- `created_at` not null

Recommended constraints:

- primary key on (`run_id`, `turn_number`)
- FK `run_id -> runs.run_id`
- check `turn_number >= 0`

### `turn_metrics`

Keep the existing name, but change the parent relationship.

Recommended columns:

- `run_id` not null
- `turn_number` not null
- `metrics` not null
- `created_at` not null

Recommended constraints:

- primary key on (`run_id`, `turn_number`)
- composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`

### `turn_generated_feeds`

This is the renamed form of `generated_feeds`.

Recommended columns:

- `feed_id` not null
- `run_id` not null
- `turn_number` not null
- `agent_id` not null
- `agent_handle` nullable or non-null display metadata, depending on current runtime guarantees
- `post_ids` not null
- `created_at` not null

Recommended constraints:

- primary key on (`agent_id`, `run_id`, `turn_number`)
- FK `agent_id -> agent.agent_id`
- composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`

### `turn_likes`

This is the renamed form of `likes`.

Recommended columns:

- `like_id`
- `run_id`
- `turn_number`
- `agent_id`
- `post_id`
- `created_at`
- `explanation`
- `model_used`
- `generation_metadata_json`
- `generation_created_at`

Recommended constraints:

- primary key on `like_id`
- unique on (`run_id`, `turn_number`, `agent_id`, `post_id`)
- composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`

### `turn_comments`

This is the renamed form of `comments`.

Recommended columns:

- `comment_id`
- `run_id`
- `turn_number`
- `agent_id`
- `post_id`
- `text`
- `created_at`
- `explanation`
- `model_used`
- `generation_metadata_json`
- `generation_created_at`

Recommended constraints:

- primary key on `comment_id`
- unique on (`run_id`, `turn_number`, `agent_id`, `post_id`)
- composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`

### `turn_follows`

This is the renamed form of `follows`.

Recommended columns:

- `follow_id`
- `run_id`
- `turn_number`
- `agent_id`
- `target_agent_id`
- `created_at`
- `explanation`
- `model_used`
- `generation_metadata_json`
- `generation_created_at`

Recommended constraints:

- primary key on `follow_id`
- unique on (`run_id`, `turn_number`, `agent_id`, `target_agent_id`)
- composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- check `agent_id != target_agent_id` if not already enforced elsewhere

### `turn_posts`

This is the new table that does not yet exist.

Recommended first-version columns:

- `turn_post_id`
- `run_id`
- `turn_number`
- `author_agent_id`
- `author_handle_at_time`
- `author_display_name_at_time`
- `body_text`
- `created_at`
- `explanation`
- `model_used`
- `generation_metadata_json`
- `generation_created_at`

Recommended constraints:

- primary key on `turn_post_id`
- composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)`
- composite FK (`run_id`, `author_agent_id`) -> `run_agents(run_id, agent_id)`
- index on (`run_id`, `turn_number`, `author_agent_id`)

### Non-goals for `turn_posts` v1

- no reply-thread hierarchy
- no quote/repost model
- no synthetic backfill of rows from aggregate counts
- no immediate requirement that `TurnAction.POST` ship in the same PR as the table

## The Biggest Risks

### 1. Partial turn persistence

The current split between `feeds/feed_generator.py` and `SimulationPersistenceService.write_turn(...)` is the highest-risk bug surface. A turn-table refactor that only renames tables but leaves that write split intact would miss one of the most important architectural defects in the area.

### 2. `turn_posts` without resolver support is dead schema

If `turn_posts` lands without updating the read path to resolve `run_post_id` and `turn_post_id` from one feed-visible namespace, the table will exist but the system will not be able to hydrate feeds or actions that reference it.

### 3. Reopening agent identity semantics would be a regression

The current turn/event stack already moved to canonical IDs. Any attempt to reintroduce handle-shaped action keys or author identity derivation would directly contradict the merged PR stack.

### 4. The rename blast radius is broad

The legacy turn-event names are embedded in:

- `db/schema.py`
- Alembic migrations and docs snapshots
- SQLite adapters and repositories
- architecture docs
- `scripts/lint_schema_conventions.py`
- tests and fixtures

This argues for a staged plan with explicit PR boundaries, not a single massive unreviewable branch.

## Overarching Delivery Strategy

Use a staged hard cutover:

1. Freeze contracts and write down the exact target architecture.
2. Introduce the new schema (`turns`, renamed turn-event tables, `turn_posts`) and migrate local/dev data.
3. Move turn persistence to one atomic write bundle.
4. Update repository and query paths to read/write only the new turn tables.
5. Add `turn_posts` read support and, optionally, write support.
6. Update linters/docs/tests so the new schema is the only accepted steady state.

The most important sequencing rule is:

- do not start `turn_posts` generation behavior until the feed-visible post ID contract and the mixed resolver are frozen and implemented

## Milestones, Deliverables, And Suggested PRs

The sections below are intentionally detailed enough that a follow-on planning agent can turn any single PR into a full `/create-implementation-plan` plan without needing to rediscover scope, contracts, or file ownership.

### Milestone 1 / PR 1: Freeze Contracts And Update Architecture Docs

Goal:

- lock the v2 architecture before any schema or runtime code changes begin

Why this PR exists:

- The original [March 19 turn-table proposal](../2026-03-19_refactor_turn_tables/proposal.md) predates the completed agent-ID migration stack.
- A small docs-first PR reduces interpretation risk for every later coding PR.
- This is the place to freeze whether `TurnAction.POST` is in scope now or explicitly deferred.

Exact files to inspect:

- `strategy_planning/2026-03-19_refactor_turn_tables/proposal.md`
- `strategy_planning/2026-03-20_agent_id_migration/proposal.md`
- `strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md`
- `CURRENT_PROGRESS_STATUS.md`
- `docs/architecture/agents-turns-runs-data-model.md`
- `docs/architecture/seed-state-run-snapshot-turn-events.md`
- `docs/RULES.md`

Exact files allowed to change:

- `strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md`
- `docs/architecture/agents-turns-runs-data-model.md`
- `docs/architecture/seed-state-run-snapshot-turn-events.md`
- optionally one new focused doc under `docs/architecture/` if the post-ID namespace contract needs its own home

Exact files forbidden to change:

- `db/schema.py`
- `db/migrations/versions/*`
- `simulation/**`
- `ui/**`

Required decisions to freeze in this PR:

- canonical `agent_id`, `target_agent_id`, and `author_agent_id` semantics are immutable inputs
- `turns` replaces `turn_metadata` as the canonical parent row
- `generated_feeds` must become `turn_generated_feeds`
- turn persistence must become atomic
- feed-visible post IDs use one shared namespace with `run_post_id` and `turn_post_id`
- `turn_posts` v1 shape is approved
- authored-post generation is either declared in-scope for PR 6 or explicitly deferred

Expected deliverables:

- docs updated so another agent can answer "what exactly are we building?" without re-reading the full PR history
- explicit non-goals recorded so later PRs do not sprawl
- if `TurnAction.POST` is deferred, that deferment is written down in plain language

Verification:

- `uv run python scripts/check_docs_metadata.py docs/architecture strategy_planning/2026-03-22_v2_refactor_turn_tables`
- Expected: passes if metadata is required for the changed docs set

Suggested PR title:

- `docs: freeze turn-table refactor v2 contracts`

### Milestone 2 / PR 2: Land The Schema And Migration Spine

Goal:

- introduce the new turn table family and migrate legacy data forward in one coherent schema pass

Why this PR exists:

- This is the irreversible schema foundation that all later runtime and query work depends on.
- It should remain focused on DDL and data movement, not query behavior or API shape.

Exact files to inspect:

- `db/schema.py`
- current relevant revisions in `db/migrations/versions/`
- `docs/db/LATEST.txt`
- `scripts/lint_schema_conventions.py`
- `tests/lint/test_lint_schema_conventions.py`

Exact files allowed to change:

- `db/schema.py`
- one or more new files in `db/migrations/versions/`
- `docs/db/*`
- `docs/db/LATEST.txt`
- migration-focused tests under `tests/db/` and `tests/scripts/migrations/`

Exact files forbidden to change:

- `simulation/core/services/query_service.py`
- `simulation/api/services/run_query_service.py`
- `feeds/feed_generator.py`
- `simulation/core/services/command_service.py`
- `ui/**`

Implementation detail to hand off:

- Create `turns`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and `turn_posts`.
- Preserve existing row semantics while moving from legacy table names to the new table family.
- Use create/copy/drop rather than relying purely on table rename so the end-state constraints and index names are intentional.
- Add composite FK (`run_id`, `turn_number`) -> `turns(run_id, turn_number)` for every turn-event table, including `turn_metrics`.
- Preserve canonical FK relationships already established by the agent-ID migration.
- Do not backfill fake `turn_posts` rows; leave it empty until a real write path exists.
- Keep downgrade policy consistent with the repo's current migration style; if downgrade is unsupported, say so explicitly in the revision docstring/comments.

Expected deliverables:

- new tables exist at head
- legacy turn-event data is copied into the new tables
- old tables are removed from `db/schema.py`
- docs/db snapshot matches the new head schema

Verification:

- `SIM_DB_PATH=/tmp/turn_tables_v2.sqlite uv run python -m alembic -c pyproject.toml upgrade head`
- `uv run pytest tests/db -k "turn or migration" -q`
- `uv run python scripts/generate_db_schema_docs.py --check`
- Expected: migration succeeds, targeted tests pass, docs check passes after snapshot update

Suggested PR title:

- `feat(db): introduce turns and turn_* history tables`

### Milestone 3 / PR 3: Make Turn Writes Atomic

Goal:

- remove the split write boundary so all per-turn artifacts are persisted in one transaction

Why this PR exists:

- This is the highest-value behavioral fix in the area.
- It should be reviewed separately from the migration because transaction-boundary bugs are easy to hide in a giant schema diff.

Exact files to inspect:

- `feeds/feed_generator.py`
- `db/services/simulation_persistence_service.py`
- `simulation/core/services/command_service.py`
- `db/repositories/interfaces.py`
- `db/repositories/generated_feed_repository.py`
- `db/adapters/sqlite/generated_feed_adapter.py`
- tests around feed generation and turn persistence

Exact files allowed to change:

- `feeds/feed_generator.py`
- `db/services/simulation_persistence_service.py`
- `simulation/core/services/command_service.py`
- `db/repositories/interfaces.py`
- `db/repositories/generated_feed_repository.py`
- `db/adapters/sqlite/generated_feed_adapter.py`
- directly related tests under `tests/feeds/`, `tests/simulation/core/`, and `tests/db/repositories/`

Exact files forbidden to change:

- `simulation/core/services/query_service.py`
- `simulation/api/services/run_query_service.py`
- `ui/**`
- unrelated adapters/repositories

Implementation detail to hand off:

- Change `feeds/feed_generator.py` so it only generates `GeneratedFeed` models and hydrated feed data; it should not commit DB writes itself.
- Introduce a single turn-write bundle API, either by extending `SimulationPersistenceService.write_turn(...)` or by adding a sibling method with a narrower, explicit contract.
- Persist `turns` first inside the transaction, then `turn_metrics`, then `turn_generated_feeds`, then action tables, and then `turn_posts` if present.
- Ensure failure in any write path rolls back all turn rows.
- Preserve the current in-memory return shape used by `SimulationCommandService._simulate_turn(...)`.

Expected deliverables:

- no feed row can exist for a turn without a corresponding `turns` row
- the feed generator no longer owns write side effects
- turn persistence remains DI-friendly and repository-driven

Verification:

- `uv run pytest tests/feeds/test_feed_generator.py tests/simulation/core/test_command_service.py tests/db/repositories/test_generated_feed_repository_integration.py -q`
- add or update one focused transactional regression test proving that a mid-write exception leaves no partial turn rows behind
- Expected: pass, including the rollback regression test

Suggested PR title:

- `fix(turns): persist feeds and actions atomically`

### Milestone 4 / PR 4: Cut Repositories And Read Paths Over To The New Turn Tables

Goal:

- make low-level reads and writes depend only on `turns` and the renamed `turn_*` tables

Why this PR exists:

- Once schema and transaction boundaries are ready, the remaining task is the mechanical but high-blast-radius repository/adapter rename.
- Keeping this isolated makes it easier to verify that logical query results do not change.

Exact files to inspect:

- `db/adapters/sqlite/generated_feed_adapter.py`
- `db/adapters/sqlite/like_adapter.py`
- `db/adapters/sqlite/comment_adapter.py`
- `db/adapters/sqlite/follow_adapter.py`
- `db/adapters/sqlite/run_adapter.py`
- `db/repositories/interfaces.py`
- `db/repositories/generated_feed_repository.py`
- `db/repositories/like_repository.py`
- `db/repositories/comment_repository.py`
- `db/repositories/follow_repository.py`
- `simulation/core/models/turns.py`
- `simulation/core/models/persisted_actions.py`
- `simulation/core/services/query_service.py`

Exact files allowed to change:

- the files listed above
- tightly related tests in `tests/db/`, `tests/simulation/core/`, and `tests/api/`

Exact files forbidden to change:

- `simulation/core/models/actions.py`
- `feeds/feed_generator.py`
- `ui/**`
- architecture docs unless a name reference is blocking tests

Implementation detail to hand off:

- Replace all live SQL references to `generated_feeds`, `likes`, `comments`, `follows`, and `turn_metadata` with their new table names.
- Keep logical contracts stable: `TurnData` should still be keyed by canonical `agent_id`; action payload models should still expose canonical IDs.
- Rename any repository method names or comments only when necessary to remove misleading legacy semantics.
- If there is a choice between broad interface churn and a thin translation layer inside repository implementations, prefer the smallest safe public interface change for this PR.

Expected deliverables:

- no runtime repository or adapter reads/writes the legacy turn-event tables
- query service behavior stays logically unchanged except for table source names
- tests continue to assert canonical-ID turn payloads

Verification:

- `uv run pytest tests/db/repositories/test_action_repositories_integration.py tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/api/test_simulation_run.py -q`
- Expected: all pass without reintroducing handle-keyed assumptions

Suggested PR title:

- `refactor(turns): rename repository and query paths to turn_* tables`

### Milestone 5 / PR 5: Add `turn_posts` Foundation And Mixed Post Resolution

Goal:

- introduce the missing turn-authored post store and make the read path understand both run-start and turn-authored posts

Why this PR exists:

- `turn_posts` is the missing structural capability, but it is separable from actual authored-post generation.
- This PR should establish the storage and hydration contract first.

Exact files to inspect:

- `simulation/core/models/posts.py`
- `simulation/core/services/query_service.py`
- `simulation/core/engine.py`
- `db/repositories/interfaces.py`
- `db/repositories/feed_post_repository.py`
- `db/adapters/sqlite/feed_post_adapter.py`
- run-post related repositories/adapters if a shared post resolver is needed
- tests covering feed hydration and post reads

Exact files allowed to change:

- the files listed above
- new `turn_post` repository/adapter/model files if that separation is cleaner than reusing `feed_post_*`
- query-focused tests under `tests/simulation/core/`, `tests/api/`, and `tests/db/repositories/`

Exact files forbidden to change:

- `simulation/core/models/actions.py`
- generation algorithms under `simulation/core/action_generators/`
- `ui/**`

Implementation detail to hand off:

- Add the `turn_posts` domain shape and persistence interfaces if they do not already exist from PR 2.
- Define one resolver path that accepts a list of feed-visible post IDs and returns hydrated posts from `run_posts` and `turn_posts`.
- Keep `author_agent_id` mandatory for turn-authored posts.
- Make `turn_generated_feeds.post_ids`, `turn_likes.post_id`, and `turn_comments.post_id` all rely on the same mixed-ID namespace.
- Do not yet add authored-post generation logic unless PR 6 is intentionally pulled forward.

Expected deliverables:

- `turn_posts` exists as a usable data source
- query hydration can resolve both `run_post_id` and `turn_post_id`
- feeds/actions referencing turn-authored posts will be readable once generation lands

Verification:

- `uv run pytest tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/db/repositories -k "post" -q`
- add targeted tests for mixed-ID hydration order and missing-ID behavior
- Expected: pass, with explicit coverage for `run_post_id` and `turn_post_id` in the same feed

Suggested PR title:

- `feat(turns): add turn_posts and mixed post hydration`

### Milestone 6 / PR 6: Optional Authored-Post Generation

Goal:

- if product wants it now, let agents author posts during turns and persist them through `turn_posts`

Why this PR exists:

- This is the first milestone that changes the behavior of turn execution itself rather than only storage and hydration.
- It should stay optional because it expands metrics, validation, history, and API semantics.

Exact files to inspect:

- `simulation/core/models/actions.py`
- `simulation/core/models/turns.py`
- `simulation/core/services/command_service.py`
- relevant generators in `simulation/core/action_generators/`
- action history / validator modules in `simulation/core/action_history/` and `simulation/core/action_policy/`
- `simulation/api/schemas/simulation.py`

Exact files allowed to change:

- the files listed above
- `turn_posts` repository/adapter files from PR 5
- tests directly covering turn execution and API payloads

Exact files forbidden to change:

- migration files from PR 2 unless a genuine schema hole is discovered
- unrelated UI screens beyond payload adaptation if schema changes require it

Implementation detail to hand off:

- Add `TurnAction.POST` only if this PR is in scope.
- Decide whether authored posts appear in the same turn's feeds immediately or only in subsequent turns; write that choice down explicitly.
- Update validation, action history, and duplicate-prevention logic to handle authored posts without disturbing like/comment/follow semantics.
- Persist generated turn posts through the same atomic turn-write path from PR 3.
- Update API serialization and tests only for the exact new behavior chosen.

Expected deliverables:

- authored posts can be generated, validated, persisted, and replayed
- turn totals and metrics include post counts if the product contract requires it
- no ambiguity remains about when a turn-authored post becomes feed-visible

Verification:

- `uv run pytest tests/simulation/core -k "post or turn" -q`
- `uv run pytest tests/api -k "turn or run_query" -q`
- Expected: pass with explicit coverage for authored-post generation and replay

Suggested PR title:

- `feat(turns): support authored posts during simulation turns`

Recommendation:

- keep this milestone optional unless product needs it immediately

### Milestone 7 / PR 7: Linter, Docs, And Verification Closeout

Goal:

- make the new steady state mechanically enforced and remove the repo's remaining acceptance of legacy turn-event names

Why this PR exists:

- Without this closeout, the code may work but the repo will still document and lint the old state as acceptable.
- This is the cleanup that prevents regression back to transitional naming.

Exact files to inspect:

- `scripts/lint_schema_conventions.py`
- `tests/lint/test_lint_schema_conventions.py`
- `docs/architecture/agents-turns-runs-data-model.md`
- `docs/architecture/seed-state-run-snapshot-turn-events.md`
- touched strategy/docs files
- targeted grep results for old table names in live code

Exact files allowed to change:

- the files listed above
- targeted tests/docs still referencing the old steady-state names

Exact files forbidden to change:

- core runtime logic unless a documentation/linter mismatch reveals a real bug
- `ui/**`

Implementation detail to hand off:

- remove the old turn-event table names from `LEGACY_TURN_EVENT_TABLES`
- update architecture docs so `turns` and the full `turn_*` family are described as present reality, not future TODO
- add final tests or verification helpers that fail if live runtime code still references the old turn-event tables
- keep historical references only in migration docs, archived proposals, or explicit before/after explanation

Expected deliverables:

- linter enforces the new steady state
- docs match `db/schema.py`
- repo-wide search shows no live runtime dependency on old turn-event names

Verification:

- `uv run pytest tests/lint/test_lint_schema_conventions.py -q`
- `rg "\\b(turn_metadata|generated_feeds|likes|comments|follows)\\b" db simulation tests docs scripts`
- `uv run ruff check .`
- Expected: lint test passes; remaining grep hits are migration-history or archival-doc references only

Suggested PR title:

- `docs/lint: close out turn-table refactor steady state`

## Proposed PR Sequence

1. PR 1: contract freeze and architecture docs
2. PR 2: schema/migration spine for `turns` and renamed turn-event tables
3. PR 3: transactional turn-write bundle
4. PR 4: repository and read-path cutover to new names
5. PR 5: `turn_posts` foundation and mixed post-resolution support
6. PR 6: optional authored-post generation
7. PR 7: linter/docs/final verification cleanup

If review bandwidth is tight, PR 2 and PR 3 may be combined, but only if all of the following are true:

- the migration and transaction-boundary diffs remain reviewable together
- rollback behavior is covered by focused regression tests
- the combined PR still does not pull query/API/UI changes into scope

## Happy Flow After Completion

1. A run is created and run-start truth is snapshotted into `run_agents`, `run_posts`, `run_post_likes`, `run_post_comments`, and `run_follow_edges`.
2. For turn `N`, the runtime generates feeds and actions in memory using canonical `agent_id` and `target_agent_id`.
3. The persistence layer writes one canonical `turns` row for `(run_id, turn_number)`.
4. In the same transaction, it writes `turn_metrics`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and any `turn_posts`.
5. Query hydration reconstructs turn history only from `turn_*` tables plus run-start snapshots.
6. `turn_generated_feeds.post_ids` may resolve to either `run_post_id` or `turn_post_id`, and the resolver handles both.
7. API and UI continue to receive ID-keyed turn payloads, with handles only as nested display metadata.

## Alternative Approaches Considered

### Alternative 1: Rename tables only, leave transaction split alone

Rejected because it would preserve a real consistency defect in turn persistence.

### Alternative 2: Keep current legacy names and only add `turn_posts`

Rejected because it leaves the repo in an intentionally transitional state and keeps the schema linter and architecture docs permanently inconsistent with the naming goal.

### Alternative 3: Include authored-post generation immediately

Possible, but not recommended by default. The safer path is:

- first land `turn_posts` schema plus resolver
- then add authored-post generation as a follow-up if needed

## Manual Verification

- Run targeted persistence and query tests:
  - `uv run pytest tests/db/repositories/test_action_repositories_integration.py tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py tests/simulation/core/test_command_service.py tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/api/test_simulation_run.py -q`
  - Expected: all pass.
- Run schema convention tests:
  - `uv run pytest tests/lint/test_lint_schema_conventions.py -q`
  - Expected: pass with no legacy turn-event exceptions required for the new steady state.
- Run migration on a fresh SQLite database:
  - `SIM_DB_PATH=/tmp/turn_tables_v2.sqlite uv run python -m alembic -c pyproject.toml upgrade head`
  - Expected: exit 0.
- Run schema docs verification if snapshots are updated:
  - `uv run python scripts/generate_db_schema_docs.py --check`
  - Expected: pass after regenerating docs.
- Search for legacy steady-state table references after the final PR:
  - `rg "\\b(turn_metadata|generated_feeds|likes|comments|follows)\\b" db simulation tests docs scripts`
  - Expected: references are limited to migration history, explicit before/after docs, or intentionally named compatibility notes. No live runtime code should depend on those tables.
- Run quality gates for touched code:
  - `uv run ruff check .`
  - `uv run pyright .`
  - Expected: no new failures from touched areas.

## Final Verification Checklist

- `db/schema.py` defines `turns`, `turn_metrics`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, and `turn_posts`.
- Every per-turn table references `turns(run_id, turn_number)`.
- Turn persistence is atomic across feeds, metrics, actions, and any turn posts.
- Query/API/UI still use canonical `agent_id`-keyed turn payloads.
- `turn_posts` either fully participates in mixed post resolution or is explicitly documented as foundation-only.
- The schema linter no longer encodes legacy turn-event names as accepted baseline.
- Architecture docs describe the same truth as `db/schema.py`.

## Bottom Line

The correct v2 plan is not "redo the March 19 refactor proposal with better wording." It is:

1. keep the original goal of hard-cutting legacy turn-event names
2. explicitly preserve the now-complete canonical ID architecture from [PR #268](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/268) through [PR #281](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/281)
3. make `turns` the real parent of all turn history
4. fix the feed/action transaction split while already touching the turn write path
5. add `turn_posts` with an explicit mixed post-ID resolution contract
6. finish with docs/linter/test verification so the repo stops treating the old table names as normal steady state

That gets the repo to a coherent turn-history model that matches the architecture docs, preserves the completed agent-ID work, and creates a safe foundation for authored-post support when needed.
