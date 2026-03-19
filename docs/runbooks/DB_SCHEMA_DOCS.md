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

The check also **compiles every Mermaid ER diagram** in `docs/db/**/schema.md` using
the Mermaid CLI (`mmdc` from `@mermaid-js/mermaid-cli`). A parse or render failure
fails the check and prints the CLI output.

- **CI** installs a pinned release (`@mermaid-js/mermaid-cli@11.12.0`) in the `schema` workflow job.
- **Locally**, install `mmdc` on your PATH (for example
  `npm install -g @mermaid-js/mermaid-cli@11.12.0`),
  or rely on the script’s fallback: if `mmdc` is missing but `npx` is available, it runs
  `npx --yes @mermaid-js/mermaid-cli@11.12.0 ...` (same major line as CI).
- Override the command with `MMDC` (or `MERMAID_CLI`) if you need a custom wrapper
  (space-separated argv prefix, e.g. `MMDC=/path/to/mmdc`).
- On **Linux CI** (including GitHub Actions), Chromium often requires disabling the
  sandbox; the repo passes `scripts/mermaid_cli_puppeteer.json` to `mmdc -p` by default.
  Set `MERMAID_CLI_NO_PUPPETEER_CONFIG=1` only if you must opt out.
- **Timeouts**: Alembic upgrade and Mermaid CLI compilation share
  `SCHEMA_DOCS_ALEMBIC_TIMEOUT_SECONDS` (default `120` seconds). Raise it if either step
  hits a timeout on slow machines.

## Verify Alembic metadata does not drift

Alembic autogenerate metadata lives in `db/schema.py`.

Check drift (from repo root):

```bash
uv run python scripts/check_db_schema_drift.py
```
