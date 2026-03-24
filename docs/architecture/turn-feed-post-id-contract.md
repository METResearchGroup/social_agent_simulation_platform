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
- **`turn_post_id`:** Identifies a post **authored during a turn** and stored in **`turn_posts`**. Same conceptual ID shape as other feed-visible IDs, but resolved against `turn_posts` rather than `run_posts`.

Readers (feed hydration, action display, replay) implement **one resolver** that accepts feed-visible IDs and loads from `run_posts`, `turn_posts`, or both as needed. Mixed `run_posts` + `turn_posts` hydration is required for the system to interpret feeds and actions; see the strategy proposal’s milestones on mixed post resolution.

### Resolution algorithm (application layer)

- **Lookup order:** For each feed-visible ID, resolve against `run_posts` first (run-scoped snapshot). Any ID not found there is then resolved against `turn_posts` scoped by the same `run_id` (keyed by `turn_post_id`).
- **Collisions:** If the same string appeared in both tables (unlikely if ID generation is disjoint), the **run** row wins; the turn row is not consulted for that ID.
- **Missing IDs:** If an ID exists in neither table, it is omitted from hydrated post lists (no error). Feed ordering is preserved; slots with missing posts are skipped.
- **Engagement counts:** Like/reply counts on hydrated `Post` objects come from run-scoped `run_post_likes` / `run_post_comments` for `run_post_id` rows only. Turn-authored posts use zero counts until turn-scoped engagement storage exists.

## Turn-authored posts: generation and feed visibility

- **`TurnAction.POST`** is emitted during turn simulation; snapshots persist to **`turn_posts`** in the same atomic `write_turn` transaction as other turn artifacts.
- **Feed candidate rule:** For feed generation at turn **N**, eligible `turn_posts` rows are those with **`turn_number` < N** (same-turn posts are not candidates—they are not inserted until after feed generation for that turn). Thus a post authored in turn **T** can appear in **`turn_generated_feeds`** starting turn **T+1**, never in turn **T**’s feed.
- **Per-author cap:** At most **`MAX_AUTHORED_POSTS_PER_TURN`** (5) persisted posts per `(run_id, turn_number, author_agent_id)` per turn; enforced in generation/validation before persistence.

## Non-goals

- Aggregate like/reply **counts** on hydrated `Post` cards for `turn_post_id` from `turn_likes` / `turn_comments` (beyond storing those actions) — optional follow-up.

## Related docs

- [agents-turns-runs-data-model.md](agents-turns-runs-data-model.md) — `Agent*`, `Run*`, and `Turn*` taxonomy
- [seed-state-run-snapshot-turn-events.md](seed-state-run-snapshot-turn-events.md) — scope boundaries and steady-state `turn_*` tables
