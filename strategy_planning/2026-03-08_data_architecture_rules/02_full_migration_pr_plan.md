# Full Data Migration PR Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview

We should execute this migration as a sequence of narrow PRs that first establish the persistence contract, then add mutable `agent_*` seed-state tables, then introduce immutable `run_*` snapshots, and only then cut simulation startup and historical reads over to the new model. The key architectural rule is: `agent_*` is editable current state, `run_*` is frozen start-of-run state, and existing `likes` / `comments` / `follows` remain turn-event history. I agree with starting with `agent_*` first in spirit, but I would not land all seed tables and all runtime behavior in one PR. The dependency graph matters more than the prefix: `agent_follow_edges` can stand alone, but `agent_post_likes` and `agent_post_comments` only make sense once `agent_posts` exists and post identity is stable.

## Upstream Dependency: PR 172 First

Assume [PR #172](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/172) lands before this migration work. That PR does not change the core architecture proposed here, but it materially improves the post migration substrate:

1. `bluesky_feed_posts` becomes canonical `feed_posts`.
2. post identity becomes canonical `post_id` with `source` + `uri`, instead of using raw Bluesky URIs as the primary identifier.
3. `generated_feeds.post_uris` becomes `generated_feeds.post_ids`.

That means our post-seed migration should backfill `agent_posts` from `feed_posts` after PR 172, not directly from `bluesky_feed_posts`. Architecturally, nothing else changes: `feed_posts` remains an ingest/import catalog, while `agent_posts` becomes the editable pre-run seed-state source of truth.

## Feedback On "Do All `agent_*` First"

1. This is the right top-level direction because startup state must come from seed tables, not from turn-event tables.
2. I would not put all `agent_*` tables into one PR unless you are deliberately accepting a very large review surface. `agent_follow_edges` is low-risk and independent; initialized posts/likes/comments are a second dependency chain.
3. The biggest migration constraint is that counts are lossy. `user_agent_profile_metadata.follows_count`, `followers_count`, and `posts_count` do not tell us *which* edges or posts exist. We can backfill counts, but we cannot reconstruct concrete follows/likes/comments from counts alone.
4. Because of that, the migration should distinguish:
   - schema creation
   - deterministic backfill from existing row-level data
   - manual or imported population of newly modeled seed-state rows
5. With [PR #172](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/172) merged first, my recommendation is to treat `feed_posts` as the import/backfill source for `agent_posts`, but not as the long-term source of truth for initialized posts. If initialized posts matter to simulation startup, they need to live in `agent_posts`.
6. We should not cut runs over to live `agent_*` reads until `run_*` snapshot tables exist. Otherwise edits to current agent state will rewrite the apparent initial state of historical runs.

## Happy Flow

1. We codify the data-scope contract in `docs/RULES.md` and a new architecture doc so future schema changes cannot mix seed state, run snapshots, and turn events.
2. We add seed-state tables to `db/schema.py` and Alembic revisions under `db/migrations/versions/`:
   - `agent_follow_edges`
   - `agent_posts`
   - `agent_post_likes`
   - `agent_post_comments`
3. We add repositories/adapters under `db/repositories/` and `db/adapters/sqlite/` so the app can read and write seed state without touching run-event tables.
4. We backfill only what can be backfilled deterministically:
   - `agent_posts` from row-level imported `feed_posts` data after PR 172
   - summary counts from the new source-of-truth tables into `user_agent_profile_metadata`
5. We add run snapshot tables:
   - `run_agents`
   - `run_follow_edges`
   - `run_posts`
   - `run_post_likes`
   - `run_post_comments`
6. At run creation time, the backend snapshots selected agents plus their relevant `agent_*` state into `run_*`.
7. Simulation startup and history queries read `run_*` plus turn-event tables, while `agent_*` remains the editable source for future runs only.
8. Existing `likes`, `comments`, and `follows` keep their current meaning: append-only turn events tied to `run_id` and `turn_number`.

## Correctness Semantics For The Whole Migration

1. Historical runs must never derive behaviorally relevant state from live `agent_*` tables.
2. `agent_*` tables are mutable and represent "what exists before the next run starts."
3. `run_*` tables are immutable after run creation and represent "what existed when this run started."
4. Existing `likes`, `comments`, and `follows` remain immutable event logs and are not reused for initialized state.
5. `agent_post_likes` and `agent_post_comments` may only reference persistent seed posts in `agent_posts`.
6. Backfills must be idempotent. Re-running the migration or population command must not create duplicate rows or drift counts.
7. `user_agent_profile_metadata` remains a summary/cache table, not the source of truth for edges or posts.
8. We should explicitly accept that some initialized tables may begin partially populated or empty if there is no row-level source data to infer them from.

## Proposed PR Sequence

### Pre-PR: Merge PR 172

#### Pre-PR Goal

Land [PR #172](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/172) first so post storage is canonical before we start post-seed migration work.

#### Pre-PR Why it should go first

- It renames `bluesky_feed_posts` to `feed_posts`, which is a better long-term import substrate.
- It canonicalizes `post_id`, which gives the migration a stable dedupe/import key.
- It changes `generated_feeds` and post lookup APIs to `post_ids`, which aligns the rest of the system with post identity not being Bluesky-specific.

#### Pre-PR Effect on this migration plan

- `agent_follow_edges` work is largely unaffected.
- `agent_posts` backfill should read from `feed_posts`, not `bluesky_feed_posts`.
- `agent_post_likes` / `agent_post_comments` are still blocked on having row-level interaction source data; PR 172 does not change that limitation.
- Any docs or code in this plan that mention `bluesky_feed_posts` should now be read as `feed_posts` once PR 172 lands.

### PR 1: Codify Persistence Scopes And Migration Contracts

#### PR 1 Goal

Create the architectural contract before adding new tables so later PRs have a fixed target and reviewers can reject scope-mixing early.

#### PR 1 Likely files

- `docs/RULES.md`
- `docs/architecture/seed-state-run-snapshot-turn-events.md`
- `temp/2026-03-08_data_architecture_rules/02_full_migration_pr_plan.md`
- optionally `scripts/lint_schema_conventions.py`

#### PR 1 Scope

- Add a "Persistence scopes" section to `docs/RULES.md`.
- Document the canonical meanings of `agent_*`, `run_*`, and turn-event tables.
- Explicitly ban mixed-lifecycle tables that rely on nullable `run_id` / `turn_number` or `source = manual | simulation`.
- Define the migration contract for lossy vs non-lossy data:
  - counts can be preserved
  - row identities can only be migrated from row-level source data

#### PR 1 Correctness semantics

- No runtime behavior change.
- No schema change required yet, unless you also want lightweight schema linting in this PR.
- After this PR, any later proposal that tries to store initialized follows in `follows` should be considered incorrect by design.

#### PR 1 Notes

- This PR is small but high leverage. It will make the later reviews much faster.
- If you want to skip a docs-only PR, this content can be paired with PR 2, but I still recommend landing it first.

### PR 2: Introduce `agent_follow_edges` As The First Real Seed-State Table

#### PR 2 Goal

Add the simplest durable seed-state table first so we can validate the pattern for mutable current-state data before tackling posts and seeded interactions.

#### PR 2 New table

- `agent_follow_edges`

#### PR 2 Recommended columns

- `id`
- `follower_agent_id`
- `target_agent_id` nullable
- `target_handle`
- `target_kind`
- `created_at`
- `updated_at`
- optional provenance such as `created_by_app_user_id`

#### PR 2 Why this PR first

- Follows are independent edges.
- They do not require a seed post identity.
- They let us validate mutable `agent_*` CRUD, FK strategy, constraints, count synchronization, and UI/API shape.

#### PR 2 Likely files

- `db/schema.py`
- `db/migrations/versions/<new_revision>.py`
- `db/adapters/sqlite/follow_seed_adapter.py` or equivalent
- `db/repositories/agent_follow_repository.py`
- `simulation/api/services/...` for agent detail/edit flows
- tests under `tests/db/` and `tests/simulation/api/`

#### PR 2 Backfill stance

- Do **not** attempt to infer concrete follow edges from `user_agent_profile_metadata.follows_count` or `followers_count`.
- If there is no row-level import source, initialize this table empty and let it become the durable source of truth from this point forward.

#### PR 2 Correctness semantics

- `agent_follow_edges` is the source of truth for initialized follows.
- `user_agent_profile_metadata.follows_count` and `followers_count` are derived/cache values updated transactionally from edge writes.
- Existing `follows` remains unchanged and still means "follow actions emitted during a run turn."
- Historical run pages must still ignore `agent_follow_edges` until run snapshots exist.

#### PR 2 Notes

- If you want startup visibility early, this is the first PR that actually gives you a real, queryable initialized social graph.
- This PR should also settle whether external targets are supported on day one via `target_kind = agent | external_profile`.

### PR 3: Add Seed Posts And Seeded Post Interactions

#### PR 3 Goal

Create the remaining initialized social-state tables so startup can eventually include authored posts plus pre-existing likes/comments.

#### PR 3 New tables

- `agent_posts`
- `agent_post_likes`
- `agent_post_comments`

#### PR 3 Recommended dependency order inside the PR

1. `agent_posts`
2. `agent_post_likes`
3. `agent_post_comments`

#### PR 3 Suggested table semantics

`agent_posts`

- one row per persistent initialized post
- anchored by stable internal ID, not external URI alone
- include `agent_id`, text/body, authored timestamp, and import provenance from `feed_posts`

#### PR 3 Recommended `agent_posts` shape

- `id` as the internal primary key for seed-state usage
- `agent_id` as the internal FK to `agent.agent_id`
- `text` copied from `feed_posts.text`
- `authored_at` copied from imported `feed_posts.created_at`
- `created_at` as the seed-row creation timestamp
- `updated_at` as the seed-row update timestamp
- `source_post_id` nullable but populated for imported rows, copied from `feed_posts.post_id`
- `source` nullable but populated for imported rows, copied from `feed_posts.source`
- `source_uri` nullable but populated for imported rows, copied from `feed_posts.uri`
- `import_metadata_json` for non-seed provenance that is useful to preserve but should not become the source of truth for simulation state

#### PR 3 What should go in `import_metadata_json`

- imported `author_handle`
- imported `author_display_name`
- imported engagement counters such as `bookmark_count`, `like_count`, `quote_count`, `reply_count`, and `repost_count`

That split is intentional: post text and authored time are meaningful seed-state content, while author-display details and aggregate counters are import context and should not become the behavioral source of truth for initialized simulation data.

`agent_post_likes`

- one row per initialized like
- references `agent_posts`
- actor should be anchored by `agent_id`

`agent_post_comments`

- one row per initialized comment
- references `agent_posts`
- author should be anchored by `agent_id`

#### PR 3 Backfill stance

- `agent_posts` should be backfilled from `feed_posts` after [PR #172](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/172) for **all** rows whose `author_handle` maps to an internal `agent.handle`.
- `agent_post_likes` and `agent_post_comments` should only be backfilled if there is a real row-level import source. Do not synthesize them from aggregate counts.
- If the only available signal is aggregate counters on imported posts, preserve those only as informational import metadata, not as fake interaction rows.

#### PR 3 Correctness semantics

- Every initialized like/comment must point to a real `agent_posts` row.
- No seeded interaction row may target a run-created post.
- `user_agent_profile_metadata.posts_count` becomes derived from `agent_posts`, not the reverse.
- The `agent_posts` import from `feed_posts` must be idempotent and define a stable dedupe key. After PR 172, `feed_posts.post_id` is the natural upstream key to preserve as provenance.
- Importing all matching `feed_posts` rows means the backfill should be expressed as "all posts currently attributable to internal agents become initialized posts," not "some sampled subset."

#### PR 3 Notes

- This PR is where "all `agent_*` tables first" becomes fully true.
- I would keep runtime simulation behavior unchanged here. Land schema, repositories, and perhaps agent detail/query surfaces first.
- I would explicitly preserve import provenance on `agent_posts`, for example by storing upstream source metadata such as canonical imported `post_id`, `source`, or `uri`, so later re-import/reconciliation is deterministic.

### PR 4: Backfill, Reconciliation, And Dual-Read Safety

#### PR 4 Goal

Populate the new `agent_*` tables where possible, reconcile metadata counts, and make read paths safe while the system is still in transition.

#### PR 4 Scope

- Add backfill code or one-time migration scripts for deterministic sources.
- Recompute `user_agent_profile_metadata` from `agent_follow_edges` and `agent_posts`.
- Decide whether agent detail pages should:
  - read only new `agent_*` tables, or
  - temporarily dual-read with explicit precedence while backfill rolls out
- Use `feed_posts.post_id` as the idempotent import key so re-running the backfill updates or skips the same logical imported post instead of creating duplicates.

#### PR 4 Likely files

- `db/migrations/versions/<new_revision>.py` for data migration helpers if done in Alembic
- or a dedicated script under `scripts/`
- `simulation/api/services/agent_query_service.py`
- `db/repositories/feed_post_repository.py`
- repositories and adapters supporting count reconciliation
- verification tests

#### PR 4 Recommended migration rule

- Keep schema migrations focused on DDL where possible.
- If the backfill is non-trivial, prefer a dedicated idempotent script plus a documented operator runbook over embedding large data-copy logic directly in Alembic.

#### PR 4 Correctness semantics

- Re-running the backfill must leave row counts and derived counts unchanged.
- Missing row-level source data is not an error; fabricated rows are an error.
- During the transition, the app must have a deterministic precedence rule if both legacy and new sources exist.

#### PR 4 Notes

- This PR is where we need to be honest about the limits of migration. We can preserve *known rows* and *known counts*; we cannot recover edges or interactions that were never stored concretely.

### PR 5: Add Immutable Run Snapshot Tables

#### PR 5 Goal

Freeze startup state at run creation so historical behavior is stable even after agents are edited later.

#### PR 5 New tables

- `run_agents`
- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`

#### PR 5 Recommended `run_agents` shape

- `run_id`
- `agent_id`
- `handle_at_start`
- `display_name_at_start`
- `persona_bio_at_start`
- `followers_count_at_start`
- `follows_count_at_start`
- `posts_count_at_start`

#### PR 5 Scope

- Extend run creation/start flows so selected agents are persisted explicitly.
- Snapshot relevant `agent_*` rows into `run_*` in the same logical workflow as run creation.
- Keep existing turn-event persistence untouched.

#### PR 5 Likely files

- `db/schema.py`
- `db/migrations/versions/<new_revision>.py`
- run repositories/adapters under `db/repositories/` and `db/adapters/sqlite/`
- simulation start service(s) under `simulation/api/services/`
- engine/factory wiring if run startup currently lacks these dependencies

#### PR 5 Correctness semantics

- Snapshot creation is atomic from the application point of view: either the run and its initial snapshot exist together, or the run start fails.
- After creation, `run_*` rows are immutable.
- Later edits to `agent_*` must not mutate or reinterpret existing `run_*` rows.

#### PR 5 Notes

- This is the real boundary between "editable startup state" and "historical start state."
- I would not let simulation behavior depend on initialized follows/posts until this PR exists.

### PR 6: Cut Simulation Startup And History Reads Over To `run_*`

#### PR 6 Goal

Make the simulator and history queries consume the new snapshot model end-to-end.

#### PR 6 Scope

- On run start, feed initial state from `run_follow_edges`, `run_posts`, `run_post_likes`, and `run_post_comments`.
- Update history queries so run detail views read `run_*` plus turn-event tables.
- Keep `likes`, `comments`, and `follows` as append-only turn outputs.

#### PR 6 Likely files

- `simulation/api/services/run_query_service.py`
- simulation execution/start services
- repositories for reading `run_*`
- relevant schemas under `simulation/api/`
- integration tests proving historical isolation

#### PR 6 Correctness semantics

- A historical run rendered tomorrow must show the same initial state it had today, even if the user edits the agent afterward.
- The only state that evolves after run start is turn-event state and derived metrics.
- No run-history path should need to read live `agent_*` for behaviorally relevant information.

#### PR 6 Notes

- This is the PR where the new architecture becomes operational rather than just modeled.
- If there is any dual-read behavior left after PR 4, this PR should remove it.

### PR 7: Cleanup, Guardrails, And Optional Legacy Deprecations

#### PR 7 Goal

Remove ambiguity and lock in the model so the codebase does not regress.

#### PR 7 Scope

- Add schema-lint checks for scope boundaries.
- Add architecture tests if useful.
- Clarify the remaining role of import/catalog tables such as `feed_posts` and legacy tables such as `agent_bios`.
- Regenerate versioned DB schema docs.

#### PR 7 Likely files

- `scripts/lint_architecture.py`
- `scripts/lint_schema_conventions.py`
- `docs/db/...`
- `docs/RULES.md`

#### PR 7 Correctness semantics

- New development cannot accidentally reintroduce mixed-lifecycle tables.
- Legacy tables are either clearly import-only, clearly deprecated, or fully retired.

## Recommended First Cut

If you want the highest-value, lowest-risk start, I would implement the rollout in this order:

1. PR 1: architecture contract
2. PR 2: `agent_follow_edges`
3. PR 3: `agent_posts` + `agent_post_likes` + `agent_post_comments`
4. PR 5: `run_*` snapshot tables
5. PR 6: runtime cutover
6. PR 4 and PR 7 can be threaded alongside those where needed for backfill and guardrails

That ordering is slightly different from a purely chronological numbering because runtime cutover should wait until the snapshot model exists, while backfill mechanics can be developed in parallel as soon as the seed tables are introduced. The only prerequisite ahead of this sequence is [PR #172](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/172), which should land first.

## Open Decisions To Resolve Before Implementation

1. Do we want day-one support for external follow targets in `agent_follow_edges`, or only internal agent-to-agent follows?
2. Do initialized likes/comments need to support external actors or only internal agents?
3. Should data backfill live in Alembic revisions, dedicated idempotent scripts under `scripts/`, or both?
4. Do we want `run_posts` / `run_post_likes` / `run_post_comments` immediately, or should the first snapshot PR ship only `run_agents` + `run_follow_edges` and defer initialized post snapshots one PR later?

## Alternative Approaches

- **Alternative: one huge schema PR with all `agent_*` and `run_*` tables at once.**
  - Rejected because it mixes storage modeling, data migration, runtime cutover, and history semantics into one review.
- **Alternative: reuse existing `likes/comments/follows` with nullable `run_id` or a `source` enum.**
  - Rejected because it collapses editable seed state and immutable event history into one table family.
- **Alternative: infer initialized edges/interactions from counts.**
  - Rejected because counts are lossy and would create fabricated data.

## Manual Verification

- [ ] Read `db/schema.py` after each schema PR and confirm the new tables obey the intended scope: `agent_*` has no `run_id` or `turn_number`; `run_*` has `run_id`; turn-event tables keep non-null `turn_number`.
- [ ] Run `SIM_DB_PATH=/tmp/agent-sim-migration.sqlite uv run python -m alembic -c pyproject.toml upgrade head` and confirm Alembic reaches `head` without errors.
- [ ] Run `SIM_DB_PATH=/tmp/agent-sim-migration.sqlite uv run python -m alembic -c pyproject.toml current` and confirm the output shows the latest revision.
- [ ] If a PR includes backfill logic, run the backfill twice against the same DB and confirm row counts do not increase on the second run.
- [ ] Run focused repository tests after each PR, for example `uv run pytest tests/db -q`, plus any new service tests added for the PR.
- [ ] Run `uv run python scripts/generate_db_schema_docs.py --update` after migration changes and confirm the generated docs reflect the new tables.
- [ ] For the snapshot PR, create a run, edit an agent afterward, then re-read the run and confirm its initial state did not change.
- [ ] For the runtime cutover PR, verify that initialized follows/posts come from `run_*` at startup, while subsequent simulated actions still land in `follows`, `likes`, and `comments`.

## Bottom-Line Recommendation

Your instinct to start with `agent_*` is correct, but I would refine it to: start with the *independent* `agent_*` table first (`agent_follow_edges`), then add the *post-dependent* `agent_*` tables (`agent_posts`, `agent_post_likes`, `agent_post_comments`), and only then wire that seed state into immutable `run_*` snapshots. The most important correction to the rollout is that a "full migration" cannot mean "reconstruct every initialized row from counts"; for follows and seeded interactions, we only get real migrated rows where a row-level source already exists.
