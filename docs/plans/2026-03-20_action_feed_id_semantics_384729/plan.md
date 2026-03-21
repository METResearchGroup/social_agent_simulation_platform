---
name: Action feed ID semantics
overview: Align SQLite DDL (Alembic), declarative schema, and core models so run-scoped likes/comments/follows and generated_feeds use canonical agent_id / target_agent_id with explicit naming; backfill legacy rows; update adapters, services, seeds, and tests. Downgrade unsupported.
description: Single migration after c3d5e7f9a0b2 renames action columns, adds FKs to agent, rebuilds generated_feeds PK on agent_id, backfills from agent join; core models and mechanical ripple; seed JSON + loader; schema docs and tests.
tags:
  - agent-id
  - alembic
  - sqlite
  - migrations
  - actions
  - generated-feeds
todos:
  - id: contract-freeze
    content: DDL/backfill contract documented in this plan (YAML + Interface freeze section)
    status: completed
  - id: alembic-migration
    content: Revision d4f8a1c3e5b7 — likes/comments/follows renames + FKs; generated_feeds rebuild; downgrade NotImplementedError
    status: completed
  - id: schema-and-docs
    content: db/schema.py + scripts/generate_db_schema_docs.py --update/--check
    status: completed
  - id: core-models
    content: Persisted actions, Follow.target_agent_id, GeneratedFeed.agent_id, SimulationAgent.get_feed
    status: completed
  - id: mechanical-ripple
    content: Adapters/repos/services/hydration/tests/seeds including candidate_filter + preload_follow canonical keys
    status: completed
  - id: verify
    content: pytest, ruff, pyright scoped paths, alembic upgrade + PRAGMA foreign_key_check
    status: completed
isProject: false
---

# Action and feed ID-first schema and models

## Interface or contract freeze

- Table/column names after migration: `likes.agent_id`, `comments.agent_id`, `follows.agent_id`, `follows.target_agent_id`, `generated_feeds` primary key `(agent_id, run_id, turn_number)`, not handle.
- Runtime `Follow` field: `target_agent_id` (not `user_id`).
- `GeneratedFeed` carries required canonical `agent_id`; optional `agent_handle` for display.
- `SimulationAgent.get_feed` requires `self.agent_id` when building a feed.
- Follow history keys for duplicate suppression: preload records `canonical_agent_id(handle_at_start)` for follow targets; feed candidate filter uses canonical target keys when `author_agent_id` is not already 16-char hex.

## Happy Flow

1. **Alembic** — New revision `d4f8a1c3e5b7` after `c3d5e7f9a0b2`: rename columns, backfill via `agent` join, add FKs, rebuild `generated_feeds` with new PK and backfill.
2. **Declarative schema** — `db/schema.py` matches migrated SQLite.
3. **Core models** — `PersistedLike` / `PersistedComment` / `PersistedFollow`, `Follow`, `GeneratedFeed`, `SimulationAgent.get_feed` aligned with contract.
4. **Mechanical ripple** — SQLite adapters, repositories, `turn_data_hydration`, command/query services, generators, factories, seeds.
5. **Behavior** — `HistoryAwareActionFeedFilter` and `preload_follow_history_from_snapshots` use canonical follow target keys consistent with generated follows.

## Data Flow

Migration reads legacy handle-like values in action tables and resolves to `agent.agent_id` (normalized handle match). `generated_feeds` rows get `agent_id` from `agent` join; `generated_feeds.agent_handle` retained where needed for display. Runtime writes resolve actor/target via `resolve_agent_id_sqlite` where needed.

## Manual Verification

- `uv run pytest` — full suite green (736+ tests).
- `uv run ruff check` on touched paths — clean.
- `uv run pyright` on touched modules — no new errors.
- `SIM_DB_PATH=/tmp/action_feed_semantics.sqlite uv run python -m alembic -c pyproject.toml upgrade head` — exit 0; `sqlite3 ... "PRAGMA foreign_key_check;"` — empty.
- `uv run python scripts/generate_db_schema_docs.py --update` then `--check` — pass.
