# Seed state vs run snapshots vs turn events

This document defines the **persistence scopes** used by the simulation platform. It exists to prevent a recurring failure mode: mixing editable “current state” data with immutable run history in one table family.

## Canonical scopes

### Seed state (current, editable)

Seed state is the mutable data that should still exist even when **no run exists**. It represents “what exists before the next run starts.”

- **Naming**: new seed-state tables use the `agent_*` prefix.
- **Lifecycle**: editable; changes affect only future runs.
- **Examples (current schema)**:
  - `agent`
  - `agent_persona_bios`
  - `user_agent_profile_metadata` (summary/cache; not the source of truth for edges/posts)

### Run snapshot (immutable after run creation)

A run snapshot is the frozen copy of the relevant seed state captured **at run creation**. It exists so historical reads and historical behavior are stable even if seed state changes later.

- **Naming**: new snapshot tables use the `run_*` prefix.
- **Lifecycle**: created atomically with run creation; immutable afterward.
- **Purpose**: historical runs must not be reinterpreted based on later edits.

### Turn events (append-only history)

Turn events are immutable per-turn outputs produced during a run. They represent “what happened during this run” and should never be edited to represent baseline state.

- **Naming**: new per-turn tables use the `turn_*` prefix.
- **Lifecycle**: append-only; writes are run-scoped; rows include non-null `run_id` and non-null `turn_number`.
- **Legacy-named turn-event tables (current schema)**:
  - `generated_feeds`
  - `likes`
  - `comments`
  - `follows`
  - `turn_metadata`
  - `turn_metrics`

## How the current schema maps to scopes

This document describes intended semantics, not table renames. The current table set in `db/schema.py` already spans multiple scopes:

- **Run identity and run-level summaries**:
  - `runs` (run identity/config/status)
  - `run_metrics` (run-level derived outputs)
- **Turn events**:
  - `turn_metadata`, `turn_metrics`
  - `generated_feeds`, `likes`, `comments`, `follows`
- **Seed state**:
  - `agent`, `agent_persona_bios`, `user_agent_profile_metadata`
- **Out-of-scope / supporting tables** (not governed by the `agent_*`/`run_*`/`turn_*` convention):
  - `app_users` (app/auth)
  - `bluesky_profiles`, `feed_posts`, `agent_bios` (ingest/enrichment/legacy seed substrate)

## Core contract rules

1. **Do not mix lifecycles inside one table.** If it should exist with no run, it is seed state. If it has `turn_number`, it is a turn event. If it must remain stable for history after edits, it must be snapshotted into `run_*` at run creation time.
2. **Historical reads must not consult live seed state for behaviorally relevant values.** History pages and run replays should be backed by `run_*` and turn-event tables.
3. **Do not overload event tables to store seed state.** The existing `likes/comments/follows` are turn events; they are not a place to store initialized “baseline” relationships.

## Explicit bans (reviewer-fast-fail)

The following patterns are incorrect by design and should be rejected in review:

- A mixed-lifecycle table that stores seed state and events together by making `run_id` or `turn_number` nullable.
- A single table re-used for baseline and events by adding a lifecycle-collapsing discriminator such as `source = manual | simulation`.

## Migration/backfill semantics (counts vs rows)

- **Counts are lossy**. Summary fields like `followers_count`, `follows_count`, `posts_count` are allowed as caches, but they do not imply the underlying row-level facts.
- **Row-level facts must come from row-level source data**. Follow edges, posts, likes, and comments may only be migrated/backfilled when there is row-level source data to infer them from. Do not synthesize interaction rows from aggregate counters.
