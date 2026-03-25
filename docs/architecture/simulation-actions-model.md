---
description: Maps simulation action types across domain payloads, Generated* wrappers, Persisted* row models, turn_* event tables, and agent_* seed vs run_* snapshot tables—so catalog state is not confused with per-turn simulation output.
tags: [architecture, data-model, simulation, actions, generated, turns]
---

# Simulation actions model

Simulation “actions” (likes, comments, follows, posts, feeds) appear in **multiple related shapes** in the codebase. The important extra distinction is that the codebase has both:

- **`Generated*` models** for freshly produced turn outputs in memory, and
- **`Persisted*` / persisted-row models** for turn artifacts that have already been written to SQLite and read back.

Mixing these up causes confusing bugs—especially when a UI shows “likes” that came from **seed catalog** tables instead of **per-turn simulation** rows (or the reverse), or when code assumes a query-layer `PersistedLike` is interchangeable with a generator-layer `GeneratedLike`.

This document names the mapping **per action family**. For the global lifecycle rules (`agent_*` vs `run_*` vs `turn_*`), see [seed-state-run-snapshot-turn-events.md](seed-state-run-snapshot-turn-events.md) and [agents-turns-runs-data-model.md](agents-turns-runs-data-model.md). For post IDs used in feeds and actions (`run_post_id` vs `turn_post_id`), see [turn-feed-post-id-contract.md](turn-feed-post-id-contract.md).

## Where the same distinction shows up

| Area | What to read |
|------|----------------|
| **Persistence scopes** (seed vs snapshot vs turn) | [seed-state-run-snapshot-turn-events.md](seed-state-run-snapshot-turn-events.md) |
| **Taxonomy** (`Agent*` / `Run*` / `Turn*` lists) | [agents-turns-runs-data-model.md](agents-turns-runs-data-model.md) |
| **Run-start snapshots** (what gets copied when a run is created) | [run-snapshots.md](run-snapshots.md) |
| **UI vs data source** (e.g. run detail “Liked Posts” should follow turn actions, not only catalog) | `PROPOSED_APP_UPDATES.md` at repo root (product note) |
| **Normative table names** | `db/schema.py` (steady-state names use `turn_*`, not legacy `likes` / `comments` / `follows` from older migrations) |
| **Domain action payloads** (IDs + core fields before “generation” wrapping) | `simulation/core/models/actions.py` (`Like`, `Comment`, `Follow`) |
| **Pre-persistence turn outputs** | `simulation/core/models/generated/` (`GeneratedLike`, `GeneratedComment`, `GeneratedFollow`, `GeneratedPost`) and `simulation/core/models/feeds.py` (`GeneratedFeed`) |
| **Replay / query joining** turn artifacts | `simulation/core/services/query_service.py`, `simulation/core/utils/turn_data_hydration.py` |

**Related interaction types:** Likes and comments on posts use the same **seed → snapshot → turn** split. **Follows** use **follow edges** (`agent_follow_edges` → `run_follow_edges`) instead of `agent_post_*` tables—there is no `agent_post_follows`. **Posts** use **`agent_posts` → `run_posts`** for catalog/snapshot material; **new authorship during a run** goes to **`turn_posts`**. **Feeds** persist as **`turn_generated_feeds`** (ordered post IDs per agent per turn); there is no parallel `agent_generated_feeds` table—the feed is derived from run-scoped posts and ranking for that turn.

**Out of scope here:** `GeneratedBio` (`simulation/core/models/generated/bio.py`) is for Bluesky profile text generation, not the simulation turn-action pipeline.

## The layers (mental model)

1. **Domain action / domain payload (Python)** — The minimal action content independent of storage concerns: `Like`, `Comment`, `Follow`, plus post/feed payload models such as `TurnPostSnapshot` or `GeneratedFeed` inputs. These carry the core IDs and fields.
2. **`Generated*` (Python, in-memory)** — Output of generators **for a turn** before persistence. These wrap a domain action (or post snapshot / feed payload) with `explanation` and `GenerationMetadata` where applicable. These are what `SimulationAgent` accumulates and what `command_service` passes to the persistence layer.
3. **`Persisted*` / persisted-row models (Python, query/repository boundary)** — Typed Python representations of rows that already exist in `turn_*` tables. For likes/comments/follows this layer lives in `simulation/core/models/persisted_actions.py` as `PersistedLike`, `PersistedComment`, and `PersistedFollow`. It is the bridge shape used by adapters/repositories/query hydration after SQLite rows are loaded. For posts, `TurnPostSnapshot` itself serves this role; there is no separate `PersistedPost`. For feeds, the code currently uses the persisted table shape directly rather than a `PersistedFeed` model.
4. **`turn_*` (SQLite, append-only)** — **What actually happened in turn *N*** of run *R*: durable simulation history. Rows include `run_id` and `turn_number` (and reference `turns` where the schema enforces it). This is the authoritative source for **replay** and for UI sections that mean “actions taken during the simulation.”
5. **`agent_*` → `run_*` (SQLite, seed vs snapshot)** — **Catalog facts before the run** (`agent_*`, editable) and their **frozen copy at run creation** (`run_*`). Used for baseline feeds, counts, and hydration—**not** a substitute for `turn_likes` / `turn_comments` / `turn_follows` when the question is “what did the simulation do each turn?”

### Practical rule of thumb

- Use **`Generated*`** while the turn is being produced.
- Use **`Persisted*`** when reading already-written turn history from repositories/adapters.
- Use **`turn_*` tables** as the durable source of truth.
- Use **`agent_*` / `run_*`** only for seed catalog and run-start snapshot state.

---

## Likes

| Layer | Type / table | Role |
|--------|----------------|------|
| Domain action | `Like` in `simulation/core/models/actions.py` | `like_id`, `agent_id`, `post_id`, `created_at` |
| Generated wrapper | `GeneratedLike` | `like` + `explanation` + `metadata` |
| Persisted row model | `PersistedLike` in `simulation/core/models/persisted_actions.py` | Typed Python row returned from `turn_likes`; includes `run_id`, `turn_number`, and optional generation columns |
| Turn persistence | `turn_likes` | Append-only per-turn like events; optional LLM columns (`explanation`, `model_used`, …) |
| Seed / snapshot | `agent_post_likes` → `run_post_likes` | Pre-run “who already liked which catalog post”; snapshotted at run start for stable counts and hydration |

**Historical names:** Older docs or migrations may say `likes` instead of `turn_likes`; at HEAD the normative name is `turn_likes`.

---

## Comments

| Layer | Type / table | Role |
|--------|----------------|------|
| Domain action | `Comment` in `simulation/core/models/actions.py` | `comment_id`, `agent_id`, `post_id`, `text`, `created_at` |
| Generated wrapper | `GeneratedComment` | `comment` + `explanation` + `metadata` |
| Persisted row model | `PersistedComment` in `simulation/core/models/persisted_actions.py` | Typed Python row returned from `turn_comments`; includes `run_id`, `turn_number`, and optional generation columns |
| Turn persistence | `turn_comments` | Append-only per-turn comment events |
| Seed / snapshot | `agent_post_comments` → `run_post_comments` | Pre-run comments on catalog posts; snapshotted at run start (e.g. duplicate suppression and reply counts from baseline) |

Same structural split as likes; only the post anchor and text payload differ.

---

## Follows

| Layer | Type / table | Role |
|--------|----------------|------|
| Domain action | `Follow` in `simulation/core/models/actions.py` | `follow_id`, `agent_id`, `target_agent_id`, `created_at` |
| Generated wrapper | `GeneratedFollow` | `follow` + `explanation` + `metadata` |
| Persisted row model | `PersistedFollow` in `simulation/core/models/persisted_actions.py` | Typed Python row returned from `turn_follows`; includes `run_id`, `turn_number`, and optional generation columns |
| Turn persistence | `turn_follows` | Append-only per-turn follow events |
| Seed / snapshot | `agent_follow_edges` → `run_follow_edges` | Pre-run follow graph between agents (not post-anchored) |

There are no `agent_post_follows` / `run_post_follows` tables; follows are **graph edges**, not per-post interaction rows.

---

## Posts

| Layer | Type / table | Role |
|--------|----------------|------|
| Turn-authored content | `TurnPostSnapshot` + `GeneratedPost` | `GeneratedPost` wraps `snapshot` + `explanation` + `metadata`; persists to `turn_posts` |
| Persisted row model | `TurnPostSnapshot` | The same model is used as the typed Python row shape for `turn_posts`; there is no separate `PersistedPost` class today |
| Turn persistence | `turn_posts` | Posts **authored during** the run (see feed visibility rules in [turn-feed-post-id-contract.md](turn-feed-post-id-contract.md)) |
| Catalog / snapshot | `agent_posts` → `run_posts` | Posts that exist in the **seed catalog** and their **run-scoped** frozen copies (`run_post_id`) |

Likes and comments in `turn_*` tables target **feed-visible post IDs** that resolve to either `run_posts` or `turn_posts`; see [turn-feed-post-id-contract.md](turn-feed-post-id-contract.md).

---

## Feeds

| Layer | Type / table | Role |
|--------|----------------|------|
| Per-turn feed record | `GeneratedFeed` in `simulation/core/models/feeds.py` | `feed_id`, `run_id`, `turn_number`, `agent_id`, ordered `post_ids`, … |
| Turn persistence | `turn_generated_feeds` | One row per agent per turn listing ordered post IDs seen in that turn’s feed |

Feeds are **not** seeded as `agent_*` rows. They are **computed per turn** from run-scoped post material and ranking, then **persisted** as `turn_generated_feeds`. The same `post_ids` vocabulary is shared with `turn_likes` and `turn_comments` (see [turn-feed-post-id-contract.md](turn-feed-post-id-contract.md)). Unlike likes/comments/follows, there is no dedicated `PersistedFeed` model called out in `simulation/core/models/`; the persisted table row is handled more directly.

---

## Quick reference matrix

| Concern | Likes | Comments | Follows | Posts | Feeds |
|---------|-------|----------|---------|-------|-------|
| **Domain / payload** | `Like` | `Comment` | `Follow` | `TurnPostSnapshot` | `GeneratedFeed` payload |
| **`Generated*`** | `GeneratedLike` | `GeneratedComment` | `GeneratedFollow` | `GeneratedPost` | `GeneratedFeed` |
| **Persisted row model** | `PersistedLike` | `PersistedComment` | `PersistedFollow` | `TurnPostSnapshot` | *(no dedicated `PersistedFeed` model)* |
| **`turn_*`** | `turn_likes` | `turn_comments` | `turn_follows` | `turn_posts` | `turn_generated_feeds` |
| **Seed → snapshot** | `agent_post_likes` → `run_post_likes` | `agent_post_comments` → `run_post_comments` | `agent_follow_edges` → `run_follow_edges` | `agent_posts` → `run_posts` | *(derived; no `agent_feed` table)* |

---

## Related docs

- [seed-state-run-snapshot-turn-events.md](seed-state-run-snapshot-turn-events.md) — scope boundaries and naming
- [agents-turns-runs-data-model.md](agents-turns-runs-data-model.md) — `Agent*` / `Run*` / `Turn*` taxonomy
- [turn-feed-post-id-contract.md](turn-feed-post-id-contract.md) — ID resolution for feeds and actions
