# Proposed PRs For Migration

This note is intentionally lighter-weight than a formal implementation plan. The goal here is to decide the next backend/database PRs needed to consolidate persistence around the architecture in:

- `temp/2026-03-08_data_architecture_rules/00_architecture_distinction_riff.md`
- `temp/2026-03-08_data_architecture_rules/01_existing_tables_and_proposed_taxonomy.md`

The core model remains:

- `agent_*` = mutable seed state
- `run_*` = immutable snapshot captured at run creation
- existing `likes` / `comments` / `follows` = immutable turn events

## Recommendation

I would not sequence this as "all `agent_*` first, then all `run_*`." For a backend/database-first migration, the cleaner rollout is vertical:

1. make runs persist the participants they actually used
2. add one seed-state domain
3. snapshot that domain into `run_*`
4. move historical/backend reads to the snapshot
5. repeat for the next domain

That keeps each PR behaviorally coherent and avoids a long period where new seed-state tables exist but historical runs still have no durable frozen state.

## Hard Rules For Every PR

- Do not mix seed state and run/turn state in one table with nullable `run_id` / `turn_number` or a `source` enum.
- Do not fabricate row-level follows, likes, comments, or posts from aggregate counts.
- Prefer `agent_id` as the internal relational anchor; treat `handle` as denormalized display data.
- Historical run reads must move toward `run_*` tables and away from live `agent_*` state.
- Existing `likes`, `comments`, and `follows` should keep their current semantics as turn-event logs.
- `user_agent_profile_metadata` should remain a summary/cache table, not a source of truth.

## Fixed Decisions For This Migration

- `agent_follow_edges` supports only internal agent-to-agent edges for now.
- `run_agents` should store denormalized `*_at_start` fields in the first version.
- seeded post migration is in scope now; this is not a follow-only migration.
- pre-run likes/comments are a required part of the backend/data model for this migration.
- row-level seed fixtures for seeded likes/comments should be created as part of the migration work so end-to-end behavior can be verified against realistic seeded state.

## Proposed PR Sequence

### PR 1: Codify The Persistence Contract

This PR establishes the rules that every following backend/schema PR will obey.

Include:

- architecture doc describing `agent_*` vs `run_*` vs turn-event scopes
- repo rules that explicitly ban mixed-lifecycle tables
- lightweight enforcement where practical, especially schema-convention checks

Why first:

- It prevents "just add a `source` field" drift before new tables land.
- It gives reviewers a crisp rule for rejecting scope-mixing.

If you do not want a docs/lint-only PR, fold this into PR 2. But the contract itself should still land before the first substantive schema change.

### PR 2: Persist Actual Run Membership With `run_agents`

This is the first backend/data correctness PR I would land.

Add:

- `run_agents`

Proposed schema:

- `run_id` not null, FK to `runs.run_id`
- `agent_id` not null, FK to `agent.agent_id`
- `selection_order` not null
- `handle_at_start` not null
- `display_name_at_start` not null
- `persona_bio_at_start` not null
- `followers_count_at_start` not null
- `follows_count_at_start` not null
- `posts_count_at_start` not null
- `created_at` not null

Recommended constraints:

- primary key on (`run_id`, `agent_id`)
- unique on (`run_id`, `selection_order`)
- immutable after insert

Why this comes early:

- Today a run knows `total_agents`, but not which agents actually participated.
- Even before any UI changes, the backend already chooses real agents for a run. That choice should be persisted.
- `run_agents` is the base snapshot table that later `run_follow_edges` and `run_posts` will hang off of.

Key rule:

- once a run is created, `run_agents` is immutable

### PR 3: Introduce `agent_follow_edges`

This is the first true seed-state table.

Add:

- `agent_follow_edges`

Proposed schema:

- `agent_follow_edge_id` primary key
- `follower_agent_id` not null, FK to `agent.agent_id`
- `target_agent_id` not null, FK to `agent.agent_id`
- `created_at` not null

Recommended constraints:

- unique on (`follower_agent_id`, `target_agent_id`)
- check constraint preventing self-follow if we want to ban self-edges at the DB layer

Why follows first:

- Follows are the simplest seed-state graph.
- They do not depend on seed posts.
- They let us validate the mutable `agent_*` pattern without pulling in post identity yet.

Important constraints:

- `agent_follow_edges` becomes the source of truth for editable pre-run follows
- for now, every edge is internal agent-to-agent; no external-profile targets yet
- `follows` remains the run-turn event log
- `user_agent_profile_metadata.follows_count` and `followers_count` become derived/cache values

### PR 4: Snapshot Follows Into `run_follow_edges`

Once follow seed state exists, freeze it at run creation.

Add:

- `run_follow_edges`

Scope:

- snapshot follow edges for agents participating in a run
- connect them to `run_agents`
- make backend/history code use `run_follow_edges` when asking what the run started with
- cut follow-related backend reads over in this PR, not later in one giant cleanup PR

Proposed schema:

- `run_id` not null, FK to `runs.run_id`
- `follower_agent_id` not null
- `target_agent_id` not null
- `created_at` not null

Recommended constraints:

- primary key on (`run_id`, `follower_agent_id`, `target_agent_id`)
- follower and target agents should both belong to `run_agents` for that `run_id`

Why this is a separate PR:

- it closes the correctness loop for follows
- it avoids a limbo state where current seed follows exist but historical runs still depend on live tables

Key rule:

- historical run behavior must never be derived from current `agent_follow_edges`

### PR 5: Introduce `agent_posts`

This is the next seed-state domain after follows.

Add:

- `agent_posts`

Recommended semantics:

- one row per persistent pre-run post
- anchored by an internal seed-state ID
- linked to `agent_id`
- preserves import provenance from the upstream post-ingest substrate without making that ingest table the source of truth

Proposed source-of-truth columns:

- `agent_post_id` primary key
- `agent_id` not null, FK to `agent.agent_id`
- `body_text` not null
- `published_at` not null
- `created_at` not null
- `updated_at` not null

Proposed import-provenance columns:

- `source_post_id` nullable
- `source` nullable
- `source_uri` nullable
- `imported_author_handle` nullable
- `imported_author_display_name` nullable
- `import_metadata_json` nullable

How I would draw the line:

- source of truth is only the data that defines the seeded post the simulator should start from: author, content, and authored time
- provenance is anything needed for backfill, dedupe, reconciliation, or audit, but not needed to define the seeded post itself

Recommended constraints:

- partial unique constraint on (`source`, `source_post_id`) when `source_post_id` is not null
- index on (`agent_id`, `published_at`)

Why this is its own PR:

- post identity is more complex than follows
- it is the prerequisite for any initialized likes/comments
- it is where idempotent backfill/import rules matter most

Backfill rule:

- only backfill concrete posts from concrete row-level source data attributable to internal agents
- do not infer posts from `posts_count`

Backfill finding from `simulation/local_dev/seed_fixtures/`:

- `bluesky_feed_posts.json` contains row-level post data with `author_handle`, `created_at`, `text`, and `uri`
- `agents.json` lets us map those author handles to internal `agent_id` values
- so local-dev seed data can support deterministic backfill for `agent_posts`
- the fixture data does not provide a separate row-level seed-post identity beyond `uri`, so before canonical `post_id` lands the practical dedupe key is upstream `uri`

Fixture/testing work to include:

- if needed, normalize local-dev post fixtures so seeded post backfill is deterministic in tests
- ensure fixture posts are attributable to internal agents so `agent_posts` population can be exercised end-to-end

### PR 6: Snapshot Posts Into `run_posts`

After live seed posts exist, freeze the initial post set at run creation.

Add:

- `run_posts`

Scope:

- snapshot initialized posts for the agents in `run_agents`
- make backend/history code read `run_posts` for start-of-run post state
- cut post-related backend reads over in this PR, not later in one giant cleanup PR

Why this matters:

- without this snapshot, editing or re-importing current `agent_posts` rewrites the apparent initial state of old runs

Proposed schema:

- `run_post_id` primary key
- `run_id` not null, FK to `runs.run_id`
- `agent_post_id` not null
- `author_agent_id` not null
- `author_handle_at_start` not null
- `author_display_name_at_start` not null
- `body_text_at_start` not null
- `published_at_start` not null
- `source_post_id_at_start` nullable
- `source_at_start` nullable
- `source_uri_at_start` nullable
- `created_at` not null

Recommended constraints:

- unique on (`run_id`, `agent_post_id`)
- index on (`run_id`, `author_agent_id`, `published_at_start`)

### PR 7: Add Seeded Likes And Snapshot Them

Pre-run likes are in scope for this migration, and they should ship separately from comments.

Add:

- `agent_post_likes`
- `run_post_likes`

Why this comes after posts:

- likes only make sense once seed posts already exist
- post identity must be stable before seeded like rows can be correct

Scope:

- add live seed-state like tables anchored to `agent_posts`
- add immutable run-snapshot like tables anchored to `run_posts`
- cut like-related backend reads over in this PR
- add row-level local-dev seed fixtures for seeded likes so end-to-end tests can verify the happy path with real initialized like rows

Proposed schema for `agent_post_likes`:

- `agent_post_like_id` primary key
- `agent_post_id` not null, FK to `agent_posts.agent_post_id`
- `liker_agent_id` not null, FK to `agent.agent_id`
- `created_at` not null

Recommended constraints:

- unique on (`agent_post_id`, `liker_agent_id`)

Proposed schema for `run_post_likes`:

- `run_post_like_id` primary key
- `run_id` not null, FK to `runs.run_id`
- `run_post_id` not null, FK to `run_posts.run_post_id`
- `liker_agent_id` not null
- `liker_handle_at_start` not null
- `created_at` not null

Recommended constraints:

- unique on (`run_post_id`, `liker_agent_id`)
- index on (`run_id`, `liker_agent_id`)

Backfill rule:

- backfill only from real row-level interaction data if such a source exists
- if row-level interaction backfill is incomplete, leave gaps explicit rather than manufacturing rows from counters

Non-negotiable rule:

- never synthesize initialized like rows from aggregate counters

Backfill finding from `simulation/local_dev/seed_fixtures/`:

- there is no `likes.json` or equivalent row-level like fixture
- `bluesky_feed_posts.json` only contains aggregate `like_count`
- `generated_feeds.json` shows which posts appeared in generated run feeds, not who liked them
- so local-dev seed fixtures do not provide a concrete row-level source for backfilling `agent_post_likes`

Fixture plan:

- add a new row-level seed fixture file for likes under `simulation/local_dev/seed_fixtures/`
- seed likes should reference posts that also exist in the seeded post dataset
- seed likes should use internal agent identities so they exercise the same relational model as `agent_post_likes`
- tests should cover fixture load -> `agent_post_likes` population -> `run_post_likes` snapshot -> backend read path

### PR 8: Add Seeded Comments And Snapshot Them

Pre-run comments are also in scope, but they should ship separately from likes.

Add:

- `agent_post_comments`
- `run_post_comments`

Why separate from likes:

- comments carry more payload than likes
- they deserve their own review surface, validation rules, and backfill discussion
- splitting them keeps each PR narrower and easier to reason about

Scope:

- add live seed-state comment tables anchored to `agent_posts`
- add immutable run-snapshot comment tables anchored to `run_posts`
- cut comment-related backend reads over in this PR
- add row-level local-dev seed fixtures for seeded comments so end-to-end tests can verify initialized comment state

Proposed schema for `agent_post_comments`:

- `agent_post_comment_id` primary key
- `agent_post_id` not null, FK to `agent_posts.agent_post_id`
- `author_agent_id` not null, FK to `agent.agent_id`
- `body_text` not null
- `published_at` not null
- `created_at` not null
- `updated_at` not null

Recommended constraints:

- index on (`agent_post_id`, `published_at`)
- index on (`author_agent_id`, `published_at`)

Proposed schema for `run_post_comments`:

- `run_post_comment_id` primary key
- `run_id` not null, FK to `runs.run_id`
- `run_post_id` not null, FK to `run_posts.run_post_id`
- `author_agent_id` not null
- `author_handle_at_start` not null
- `body_text_at_start` not null
- `published_at_start` not null
- `created_at` not null

Recommended constraints:

- index on (`run_id`, `run_post_id`, `published_at_start`)
- index on (`run_id`, `author_agent_id`, `published_at_start`)

Backfill rule:

- backfill only from real row-level comment data if such a source exists
- if row-level comment backfill is incomplete, leave gaps explicit rather than manufacturing rows from counters

Non-negotiable rule:

- never synthesize initialized comment rows from aggregate counters

Backfill finding from `simulation/local_dev/seed_fixtures/`:

- there is no `comments.json` or equivalent row-level comment fixture
- `bluesky_feed_posts.json` only contains aggregate `reply_count`
- `generated_feeds.json` does not encode authored comments
- so local-dev seed fixtures do not provide a concrete row-level source for backfilling `agent_post_comments`

Fixture plan:

- add a new row-level seed fixture file for comments under `simulation/local_dev/seed_fixtures/`
- seed comments should reference posts that also exist in the seeded post dataset
- seed comments should use internal agent identities and realistic comment bodies/timestamps
- tests should cover fixture load -> `agent_post_comments` population -> `run_post_comments` snapshot -> backend read path

### PR 9: Final Cleanup And Guardrails

This PR is now smaller because concern-by-concern backend cutover should happen during PRs 4, 6, 7, and 8.

Include:

- removal of any leftover temporary dual-read logic
- stronger lints/guardrails around scope boundaries
- explicit documentation of legacy table roles

The practical outcome should be:

- current editable state lives in `agent_*`
- historical start state lives in `run_*`
- per-turn outcomes live in existing event tables

## Why This Ordering Is Better Than "All `agent_*` First"

The strongest reason is historical correctness.

If we add all seed-state tables first but delay snapshots, then for a while we have:

- new current-state representations
- no frozen historical counterpart
- pressure for backend reads to look at live `agent_*`

That is exactly the period where history can get muddled.

The vertical sequence above avoids that by finishing one semantic slice at a time:

1. current-state table exists
2. run snapshot exists
3. backend reads for that concern can become snapshot-based

Then move on to the next concern.

## What I Would Treat As The Mandatory Backend-First Migration

If the goal is "consolidate our data representations before more UI/product work," I would consider these mandatory:

1. PR 1: persistence contract
2. PR 2: `run_agents`
3. PR 3: `agent_follow_edges`
4. PR 4: `run_follow_edges`
5. PR 5: `agent_posts`
6. PR 6: `run_posts`
7. PR 7: `agent_post_likes` plus `run_post_likes`, including row-level likes fixtures
8. PR 8: `agent_post_comments` plus `run_post_comments`, including row-level comments fixtures
9. PR 9: final cleanup and guardrails

## Main Call I Would Make

The most important sequencing decision is this:

- land `run_agents` earlier than we might have originally expected

That is the foundational run-snapshot table, and it is useful even before any user-facing "Select Agents" work exists. Once the backend persists actual run membership, the rest of the migration has a much cleaner place to attach frozen start-of-run state.

## Decisions Now Locked In

1. `agent_follow_edges` is internal-only for now, so `target_agent_id` should be required in the initial version.
2. `run_agents` should include denormalized `*_at_start` fields in its first shipped schema.
3. Seeded posts are part of the core migration, not a later add-on.
4. Pre-run likes/comments are a required part of the migration and should be modeled in both `agent_*` and `run_*`.
5. Likes and comments should ship as separate PRs.
6. Backend cutover should happen concern-by-concern as each snapshot layer lands.
7. Row-level seed fixtures for seeded likes/comments should be added as part of the migration so end-to-end verification is straightforward.

## Remaining Design Questions

1. For `agent_posts`, are reply/thread fields out of scope for the first version, or do we need seeded thread structure immediately?
2. Do we want the new row-level likes/comments fixture files to anchor by `agent_id`, by handle, or by an import-friendly hybrid shape that gets resolved during fixture load?
3. Do we want `run_follow_edges` to duplicate denormalized handles, or is agent-id-only sufficient because `run_agents` already stores handle snapshots?
