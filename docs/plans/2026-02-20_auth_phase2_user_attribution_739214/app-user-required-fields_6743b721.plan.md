---
name: app-user-required-fields
overview: Ensure app user identity data is treated as a strict contract by requiring email/display_name at the core, persistence, and dependency layers.
todos:
  - id: tighten-model
    content: Harden `AppUser`/repo signatures so `email`/`display_name` are `str`, update `[db/adapters/base.py](db/adapters/base.py)` and `[db/adapters/sqlite/app_user_adapter.py](db/adapters/sqlite/app_user_adapter.py)` to drop nullable params, and ensure `simulation/api/dependencies/app_user.py` always supplies those strings.
    status: completed
  - id: enforce-schema
    content: Add an Alembic migration and `db/schema.py` update that make `app_users.email` and `display_name` `NOT NULL`, including any data-backfill/cleansing logic and documentation in `AUTH_MIGRATION.md` so the schema matches the new contract.
    status: completed
  - id: audit-call-sites
    content: Audit the remaining callers (tests, services, docs) for optional metadata, update `tests/api/test_app_user_attribution.py` with the new expectations, and document the tighter guarantees in `AUTH_MIGRATION.md`/plan assets under `docs/plans/2026-02-26_required_app_user_identity_734215/`.
    status: completed
isProject: false
description: Require app user email/display_name everywhere so persistence matches the identity contract.
tags: [plan, backend, auth, database]
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview

Tighten the app_user identity contract so `email` and `display_name` are treated as required strings from model to persistence, avoiding nullable columns and optional adapter params. All assets for this work (plan write-up, documentation updates, and any supporting diagrams/memos) will live under `docs/plans/2026-02-26_required_app_user_identity_734215/` so CI docs metadata checks keep running.

## Happy Flow

1. `simulation/api/dependencies/app_user.py` pulls Supabase claims, defaults `display_name` to `email`, and calls `[db/repositories/app_user_repository.py](db/repositories/app_user_repository.py)::SQLiteAppUserRepository.upsert_from_auth` with non-optional `email`/`display_name` so the domain sees the complete identity.
2. The repository constructs `[simulation/core/models/app_user.py](simulation/core/models/app_user.py)::AppUser` whose `email` and `display_name` are now `str` fields validated as non-empty, then writes through `[db/adapters/base.py](db/adapters/base.py)::AppUserDatabaseAdapter` and `[db/adapters/sqlite/app_user_adapter.py](db/adapters/sqlite/app_user_adapter.py)` that no longer accept `None` and always bind concrete strings in `INSERT`/`UPDATE` statements.
3. `[db/schema.py](db/schema.py)` (and the new Alembic migration) makes `app_users.email` and `app_users.display_name` `nullable=False`, and migration logic backfills/alerts if existing rows lack those values so `SQLiteAppUserAdapter` can rely on NOT NULL constraints without silently persisting `NULL`.
4. Update `tests/api/test_app_user_attribution.py` (and any other regression suites or docs like `AUTH_MIGRATION.md`) to exercise both the happy path and the new failure path when claims omit required metadata, proving the stricter persistence contract.

## Manual Verification

- `uv run pytest tests/api/test_app_user_attribution.py` (verifies the upsert route still works and fails when claims omit required identity fields).
- `uv run ruff check db/adapters/sqlite/app_user_adapter.py db/adapters/base.py db/repositories/app_user_repository.py simulation/core/models/app_user.py db/schema.py` (ensure profiling/lint picks up the signature and schema changes without complaints).
- `uv run python scripts/check_docs_metadata.py docs/plans/2026-02-26_required_app_user_identity_734215/` (validate that any new plan or doc files added for this change carry the required metadata).

## Alternative approaches

- Keeping `email`/`display_name` nullable at the persistence layer and forcing non-null defaults everywhere else would preserve backward compatibility but would violate the rule that downstream services should not add fallbacks; requiring the fields directly is clearer, forces migration verification, and keeps the schema aligned with the contract.

