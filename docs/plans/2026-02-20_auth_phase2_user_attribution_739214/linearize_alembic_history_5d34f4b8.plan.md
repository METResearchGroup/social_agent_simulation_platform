---
name: Linearize Alembic History
overview: Remove this branch’s Alembic heads, rebase on main, and regenerate the migration so the history stays linear and the schema doc/drift scripts succeed again.
description: "Outline the steps required to collapse the diverging Alembic heads and regenerate a linear migration history."
tags:
  - alembic
  - migration
  - docs
  - plan
todos:
  - id: identify-conflict-migs
    content: List the current Alembic heads and diff `db/migrations/versions/` against `main` to capture the diverging files.
    status: completed
  - id: drop-pr-migs
    content: Remove the branch-specific migration files so only `main`’s history remains before regenerating a new revision.
    status: completed
  - id: recreate-linear-mig
    content: Run `alembic revision --autogenerate` on top of `main`, review the generated migration, and ensure the docs/drift scripts pass.
    status: completed
isProject: false
---

## Step 1: Survey the current migration landscape

- Run `uv run alembic heads` and `uv run alembic history --verbose` to see which migration files drive the “multiple heads” warning.
- Inspect the branch-specific files in `db/migrations/versions/` (e.g., `[db/migrations/versions/d8e4f2a0b1c5_add_app_users_and_run_app_user_id.py](db/migrations/versions/d8e4f2a0b1c5_add_app_users_and_run_app_user_id.py)` and `[db/migrations/versions/4ea9cc982076_add_generated_feeds_run_id_foreign_key.py](db/migrations/versions/4ea9cc982076_add_generated_feeds_run_id_foreign_key.py)`) to understand which heads they introduce and whether their dependencies point to different parents.

## Step 2: Resync with `main` and drop the divergent heads

- Fetch/merge the latest `main` branch so we know the current canonical head SHA and files under `db/migrations/versions/`.
- Delete (or move aside) the branch-specific migration modules above so the working tree only reflects the migrations already present on `main`.

## Step 3: Generate a new, linear migration

- With the working tree reset to `main` + schema changes from this PR, run `uv run alembic revision --autogenerate` so the new migration has the current `main` head as its `down_revision` and captures only the net schema delta.
- Update the new migration file as needed to reflect manual adjustments that previously lived in the deleted files; ensure its `down_revision` points to the latest `main` migration and that no other heads are declared.

## Step 4: Regenerate schema docs/drift artifacts

- Run `scripts/generate_db_schema_docs.py` and `scripts/check_db_schema_drift.py` to verify the new linear history satisfies the hooks, and check the updated schema docs referenced in `docs/db/LATEST.txt` if they change.
- Commit the new migration and regenerated docs once everything passes.

## Verification/Follow-up

- Re-run `uv run alembic heads` to confirm only a single head exists and double-check `scripts/check_db_schema_drift.py` exits cleanly.
- Optionally run the project’s test suite or smoke tests mentioned in `docs/runbooks/SMOKE_TEST.md` if the schema changes touch runtime behavior.

