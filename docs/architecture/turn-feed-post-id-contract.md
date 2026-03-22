---
description: Feed-visible post ID namespace for turn feeds and actions—run_post_id vs turn_post_id and application-level resolution (no polymorphic FK).
tags: [architecture, data-model, simulation, turns, feeds]
---

# Turn feed and post ID contract

This document freezes how **feed-visible post identifiers** work for turn-scoped feeds and actions. Normative detail and sequencing live in [strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md](../../strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md) (**Architectural Calls To Freeze**, **Frozen contract**).

## Shared namespace

These fields refer to the **same** feed-visible ID vocabulary (ordering and action targets must agree):

- `turn_generated_feeds.post_ids` (ordered list)
- `turn_likes.post_id`
- `turn_comments.post_id`

There is **no** polymorphic foreign key from those columns to mixed tables. Instead, the application resolves each ID to a hydrated post using the split below.

## Resolution: `run_post_id` vs `turn_post_id`

- **`run_post_id`:** Identifies a post that comes from the **run-start snapshot** (`run_posts` and the frozen baseline copied at run creation). These IDs point at immutable run-scoped post rows.
- **`turn_post_id`:** Identifies a post **authored during a turn** and stored in **`turn_posts`** once that table exists. Same conceptual ID shape as other feed-visible IDs, but resolved against `turn_posts` rather than `run_posts`.

Readers (feed hydration, action display, replay) implement **one resolver** that accepts feed-visible IDs and loads from `run_posts`, `turn_posts`, or both as needed. Mixed `run_posts` + `turn_posts` hydration is required for the system to interpret feeds and actions once `turn_posts` exists; see the strategy proposal’s milestones on mixed post resolution.

## Non-goals

- Persisting authored posts during turns (`TurnAction.POST` **generation**) is **deferred** to a later implementation slice; this contract defines IDs and resolution only.

## Related docs

- [agents-turns-runs-data-model.md](agents-turns-runs-data-model.md) — `Agent*`, `Run*`, and `Turn*` taxonomy
- [seed-state-run-snapshot-turn-events.md](seed-state-run-snapshot-turn-events.md) — scope boundaries and legacy vs target table names
