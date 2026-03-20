---
description: Alembic data migration rewrites legacy agent.agent_id and all dependent FKs to canonical 16-char hex IDs using deterministic stable-source rules (DID > handle > legacy id), with collision detection and integration tests.
tags:
  - agent-id
  - alembic
  - sqlite
  - migrations
  - data-backfill
---

# Agent FK/PK canonical ID migration (persisted)

See `strategy_planning/2026-03-20_agent_id_migration/proposal.md` for background and precedence rules.

## Delivered in this unit

- `lib/agent_id_migration.py` — `stable_source_for_agent_row`, `build_old_to_new_map`, collision error.
- `db/migrations/versions/c3d5e7f9a0b2_rewrite_agent_primary_keys_and_fks.py` — one-way data migration after `b2c4d6e8f0a1`.
- `tests/lib/test_agent_id_migration.py` — mapping unit tests.
- `tests/db/test_agent_id_pk_migration.py` — upgrade tests on temp SQLite.
- Regenerated `docs/db/` snapshot for current branch.

## Manual verification (short)

- `uv run pytest tests/db/test_agent_id_pk_migration.py -v`
- `uv run python scripts/generate_db_schema_docs.py --check`
- `SIM_DB_PATH=/tmp/migrate.sqlite uv run python -m alembic -c pyproject.toml upgrade head` then `sqlite3 /tmp/migrate.sqlite "PRAGMA foreign_key_check;"`
