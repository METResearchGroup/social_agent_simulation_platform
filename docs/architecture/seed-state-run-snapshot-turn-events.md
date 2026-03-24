---
description: Persistence scopes for seed state, run snapshots, and turn events—naming, lifecycle, and the steady-state `turns` parent with `turn_*` history tables.
tags: [architecture, data-model, simulation, turns, runs]
---

# Seed state vs run snapshots vs turn events

This document defines the **persistence scopes** used by the simulation platform. It exists to prevent a recurring failure mode: mixing editable “current state” data with immutable run history in one table family.

**Steady state (current schema):** Per-turn history is stored under **`turns`** as the canonical parent row and **`turn_*`** tables for append-only outputs (`turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, `turn_metrics`, `turn_posts`). Post-ID rules (`run_post_id` vs `turn_post_id`) are summarized in [turn-feed-post-id-contract.md](turn-feed-post-id-contract.md). **`TurnAction.POST`** persists **`turn_posts`** in the same turn write as other artifacts; feed visibility for those posts starts in **the next turn** (strictly later `turn_number`).

Design history and the v2 migration narrative remain in [strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md](../../strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md) for before/after context only.

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

- **Naming (steady state):** per-turn tables use the `turn_*` prefix. The canonical parent is **`turns(run_id, turn_number)`**; child tables include `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, `turn_metrics`, and `turn_posts`.
- **Lifecycle**: append-only; writes are run-scoped; rows include non-null `run_id` and non-null `turn_number` where required; child tables reference `turns` via composite foreign keys.

**Historical naming (migrations / old docs only):** Before the cutover, some concepts used different table names (`turn_metadata`, `generated_feeds`, bare `likes`, `comments`, `follows`). Those names are **not** acceptable for new schema at HEAD; they may appear in migration files or archived planning as historical record.

## How the current schema maps to scopes

- **Run identity and run-level summaries**:
  - `runs` (run identity/config/status)
  - `run_metrics` (run-level derived outputs)
- **Turn history (steady-state names in `db/schema.py`)**:
  - `turns` (parent row per `(run_id, turn_number)`)
  - `turn_metrics`, `turn_generated_feeds`, `turn_likes`, `turn_comments`, `turn_follows`, `turn_posts`
- **Seed state**:
  - `agent`, `agent_persona_bios`, `user_agent_profile_metadata`
- **Out-of-scope / supporting tables** (not governed by the `agent_*`/`run_*`/`turn_*` convention):
  - `app_users` (app/auth)
  - `bluesky_profiles`, `feed_posts`, `agent_bios` (ingest/enrichment/legacy seed substrate)

## Core contract rules

1. **Do not mix lifecycles inside one table.** If it should exist with no run, it is seed state. If it has `turn_number`, it is a turn event. If it must remain stable for history after edits, it must be snapshotted into `run_*` at run creation time.
2. **Historical reads must not consult live seed state for behaviorally relevant values.** History pages and run replays should be backed by `run_*` and `turn_*` tables.
3. **Do not overload event tables to store seed state.** `turn_likes`, `turn_comments`, and `turn_follows` are turn events; they are not a place to store initialized “baseline” relationships.

## Explicit bans (reviewer-fast-fail)

The following patterns are incorrect by design and should be rejected in review:

- A mixed-lifecycle table that stores seed state and events together by making `run_id` or `turn_number` nullable.
- A single table re-used for baseline and events by adding a lifecycle-collapsing discriminator such as `source = manual | simulation`.

## Migration/backfill semantics (counts vs rows)

- **Counts are lossy**. Summary fields like `followers_count`, `follows_count`, `posts_count` are allowed as caches, but they do not imply the underlying row-level facts.
- **Row-level facts must come from row-level source data**. Follow edges, posts, likes, and comments may only be migrated/backfilled when there is row-level source data to infer them from. Do not synthesize interaction rows from aggregate counters.
