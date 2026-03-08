---
description: Refactor Bluesky-specific feed posts into a generic Post model with canonical post_id and propagate post_ids through DB, API, and UI (Issue #163).
tags: [refactor, posts, feeds, migrations, sqlite, alembic, api, ui, bluesky]
---

# Issue #163 — Refactor `BlueskyFeedPost` into generic `Post` + `PostSource`

## Overview

Refactor the codebase to replace the Bluesky-specific `simulation.core.models.posts.BlueskyFeedPost` with a generic `simulation.core.models.posts.Post` that includes `source: PostSource`, and update persistence + feed plumbing to store and propagate a canonical `post_id` (string) everywhere. This includes DB migrations (rename `bluesky_feed_posts` → `feed_posts`, add `source`, migrate IDs), API schema changes (`post_uris` → `post_ids`, `uris` query param → `post_ids`), and corresponding UI contract regeneration + UI usage updates.

## Decisions (Decision-complete)

### Canonical post ID

- Canonical ID format: `"{source.value}:{uri}"` (split on the first `":"`).
- `Post` validation:
  - `source` must be a `PostSource` enum value.
  - `uri` must be non-empty.
  - If `post_id` is missing, it is computed as `f"{source.value}:{uri}"`.
  - If `post_id` is provided, it must match `f"{source.value}:{uri}"` (otherwise `ValueError`).

### Supported sources

- `PostSource.BLUESKY = "bluesky"`
- `PostSource.AI_GENERATED = "ai_generated"`

### API contract changes (breaking)

- Feeds: `post_uris` → `post_ids`
- Posts endpoint: `GET /v1/simulations/posts?uris=...` → `GET /v1/simulations/posts?post_ids=...`
- Actions: `post_uri` → `post_id`

## Happy Flow

1. Feed post ingestion creates `Post(source=BLUESKY, uri=..., post_id="bluesky:...")` and persists to `feed_posts`.
2. Feed algorithm ranks `candidate_posts: list[Post]` and returns `FeedAlgorithmResult.post_ids` (canonical IDs).
3. `GeneratedFeed(post_ids=[...])` is persisted to `generated_feeds.post_ids` as JSON.
4. UI requests turns for a run; receives feeds containing `post_ids`.
5. UI collects unique `post_ids` across feeds and actions and calls `GET /v1/simulations/posts?post_ids=...`.
6. Backend resolves posts via `FeedPostRepository.read_feed_posts_by_ids`, returns `PostSchema` including `post_id`, `source`, and `uri`.
7. UI maps and renders posts keyed by `postId`.

## Data Flow

- **DB**:
  - Rename `bluesky_feed_posts` → `feed_posts`.
  - Store canonical `post_id` as the primary key and persist `source` and `uri` alongside the content fields.
  - Rename `generated_feeds.post_uris` → `generated_feeds.post_ids` and migrate existing values by prefixing with `bluesky:`.
  - Prefix existing run-scoped action targets (`likes.post_id`, `comments.post_id`) with `bluesky:` (guarded so it is safe on partially migrated dev DBs).
- **API**:
  - `FeedSchema.post_ids` replaces `post_uris`.
  - `PostSchema` includes `post_id`, `source`, `uri` (keep `uri` for debugging/display and to avoid forcing the UI to parse `post_id`).
  - `/v1/simulations/posts` uses `post_ids` as the query parameter name.
- **UI**:
  - Regenerate OpenAPI artifacts and TS types.
  - Fetch posts by `postIds`, index posts by `postId`, and map actions by `postId`.

## Migration plan (SQLite + Alembic)

Add an Alembic revision that:

1. Creates `feed_posts` with `post_id TEXT PRIMARY KEY`, `source TEXT NOT NULL`, `uri TEXT NOT NULL`, and the existing content columns.
2. Copies rows from `bluesky_feed_posts`:
   - `post_id = 'bluesky:' || uri`
   - `source = 'bluesky'`
   - `uri = old.uri`
3. Drops `bluesky_feed_posts`.
4. Updates `generated_feeds`:
   - Renames `post_uris` → `post_ids`
   - Transforms existing JSON values: `"at://..."` → `"bluesky:at://..."`
5. Updates run-scoped actions:
   - In `likes.post_id` and `comments.post_id`, prefixes values that do not already start with `"bluesky:"`.

## Manual Verification

- Apply migrations on a fresh DB:
  - `uv run alembic -c pyproject.toml upgrade head`
  - Expected: completes with exit code 0.
- Start API (auth bypass if needed for local dev):
  - `PYTHONPATH=. DISABLE_AUTH=1 uv run uvicorn simulation.api.main:app --reload`
  - Expected: `GET http://localhost:8000/health` returns 200.
- Regenerate UI API artifacts:
  - `cd ui && npm run generate:api`
  - Expected: generated files updated and no type errors.
- Start UI:
  - `cd ui && npm run dev`
  - Expected: UI loads.
- UI smoke:
  - Select a run → select a turn → confirm posts load (no “Cannot load posts” error).
  - Confirm request is `GET /v1/simulations/posts?post_ids=...` and response items contain `post_id` + `source`.

## Screenshots

- Before: `docs/plans/2026-02-27_post_source_refactor_163163/images/before/run_turn1_feed.png`
- After: `docs/plans/2026-02-27_post_source_refactor_163163/images/after/run_turn1_feed.png`
