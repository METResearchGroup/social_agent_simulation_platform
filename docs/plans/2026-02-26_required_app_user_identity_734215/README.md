---
description: Notes for the required app_user identity contract change (schema, migration, tests).
tags: [auth, migration, docs]
---

## Why

- The API now treats `email` and `display_name` as required strings throughout `[simulation/api/dependencies/app_user.py](simulation/api/dependencies/app_user.py)` → `[db/repositories/app_user_repository.py](db/repositories/app_user_repository.py)` → `[db/adapters/base.py](db/adapters/base.py)` → `[db/adapters/sqlite/app_user_adapter.py](db/adapters/sqlite/app_user_adapter.py)` so downstream services can assume these fields are always present.
- `[simulation/core/models/app_user.py](simulation/core/models/app_user.py)` now validates those columns are non-empty, matching the tighter domain contract and avoiding `None` propagation.
- `[db/schema.py](db/schema.py)` and the new migration `[db/migrations/versions/f0e1d2c3b4a5_enforce_app_user_identity_not_null.py](db/migrations/versions/f0e1d2c3b4a5_enforce_app_user_identity_not_null.py)` enforce the NOT NULL constraint, and the migration guards against existing rows missing the required data before altering the columns.

## Verification

- Run `uv run pytest tests/api/test_app_user_attribution.py` to exercise the happy path plus the new 400 response when a JWT lacks an email.
- Run `uv run alembic upgrade head` (with `SIM_DB_PATH` or `SIM_DATABASE_URL` pointing to your instance) to ensure the new migration succeeds once all app_user rows have non-null identity data.
- Run `uv run python scripts/check_docs_metadata.py docs/plans/2026-02-26_required_app_user_identity_734215/` to keep the docs metadata bot happy.
