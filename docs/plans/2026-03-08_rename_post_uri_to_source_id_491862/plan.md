---
description: "Implement issue #200: rename Post schema/model/db field `uri` to `source_id` (breaking API change) while keeping `uris` query params and `post_uris` lists unchanged."
tags:
  - backend
  - database
  - migration
  - api
  - ui
  - breaking-change
  - issue-200
---

# Rename Post `uri` → `source_id` (Issue #200)

## Overview

Rename the post identifier field currently called `uri` to `source_id` across:

- Domain model (`BlueskyFeedPost`)
- SQLite schema + Alembic migration (`bluesky_feed_posts` primary key column)
- API schema (`PostSchema`)
- UI types/mapping (API `source_id` → UI `sourceId`)

Scope decision (“Post-only”): keep naming for *collections of post identifiers* unchanged:

- `post_uris` fields remain `post_uris` (values now represent post source IDs).
- `GET /v1/simulations/posts?uris=...` keeps the query param name `uris`.

Hard breaking change: `PostSchema` responses no longer include `uri`.

## Happy Flow (end-to-end)

1. Backend loads persisted feed posts from SQLite table `bluesky_feed_posts` keyed by `source_id` and materializes `BlueskyFeedPost.source_id`.
2. Feed generation continues to persist feeds containing `post_uris` (unchanged naming), but the values represent post source IDs; hydration resolves those values via DB queries keyed by `source_id`.
3. `GET /v1/simulations/posts?uris=...` returns `PostSchema` objects containing `source_id` (no `uri`).
4. UI calls `getPosts(uris)` (name unchanged) and maps `source_id` → `sourceId`; UI indexes posts by `sourceId` and resolves `feed.postUris[]` against that map.

## Assets (UI screenshots)

Baseline (before):

- `/Users/mark/.codex/worktrees/9186/agent_simulation_platform/docs/plans/2026-03-08_rename_post_uri_to_source_id_491862/images/before/ui_run_turn_feed.png`

After change:

- `/Users/mark/.codex/worktrees/9186/agent_simulation_platform/docs/plans/2026-03-08_rename_post_uri_to_source_id_491862/images/after/ui_run_turn_feed.png`

## Manual Verification

From repo root:

- Python deps: `uv sync --extra test`
- Tests: `uv run pytest`
- Lint: `uv run ruff check .`
- Typecheck: `uv run pyright .`
- Migrations (SQLite): `uv run alembic -c pyproject.toml upgrade head`
- Pre-commit: `uv run pre-commit run --all-files`

UI:

- Regenerate API client/types: `cd ui && npm run generate:api`
- Lint/typecheck: `cd ui && npm run lint:all`

