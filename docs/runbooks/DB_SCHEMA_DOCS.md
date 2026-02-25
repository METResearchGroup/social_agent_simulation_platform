---
description: Generate and verify versioned database schema documentation (Mermaid + Markdown) from Alembic migrations at head.
tags: [database, schema, docs, mermaid, alembic, migrations, sqlite, pre-commit, ci]
---

# DB Schema Docs Runbook

This repo stores **versioned** database schema documentation under:

`docs/db/YYYY_MM_DD-HHMMSS-{branch_token}/`

Where:

- `YYYY_MM_DD-HHMMSS` is the local timestamp when docs were generated.
- `branch_token` is the current git branch name, sanitized.
  - Detached HEAD becomes `detached-<shortsha>`.

Each version folder contains:

- `schema.md` — human-readable table/field/relationship reference (includes a Mermaid diagram at the top)
- `schema.snapshot.json` — machine-readable, stable snapshot used for drift checks

## Source of truth

Docs are generated from a **fresh SQLite database** after applying Alembic migrations
to `head` (see `db/migrations/`).

## “Latest” folder

The “latest” folder is the lexicographically greatest version folder name under
`docs/db/`. This is safe because the name begins with a sortable timestamp.

## Update docs

From repo root:

```bash
uv run python scripts/generate_db_schema_docs.py --update
```

This creates a new version folder and updates `docs/db/LATEST.txt` for convenience.

## Verify docs are up to date (pre-commit/CI)

From repo root:

```bash
uv run python scripts/generate_db_schema_docs.py --check
```

This compares the schema produced by migrations at `head` to the latest committed
`docs/db/*/schema.snapshot.json`. If it fails, it prints the exact baseline files
and a single command to regenerate.

## Verify Alembic metadata does not drift

Alembic autogenerate metadata lives in `db/schema.py`.

Check drift (from repo root):

```bash
uv run python scripts/check_db_schema_drift.py
```
