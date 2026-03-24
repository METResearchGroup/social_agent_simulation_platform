---
description: "Verification commands and expected outcomes for turn-table steady-state closeout (lint, docs metadata, rg sweeps, schema-doc check)."
tags: [plan, verification, persistence, turns]
---

# Turn-table steady-state closeout — verification

## 1. Schema linter tests

```bash
uv run pytest tests/lint/test_lint_schema_conventions.py -q
```

**Expected:** All tests pass, including `test_rejects_legacy_turn_event_table_names` (SCHEMA-4).

## 2. Docs metadata

```bash
uv run python scripts/check_docs_metadata.py \
  docs/architecture/agents-turns-runs-data-model.md \
  docs/architecture/seed-state-run-snapshot-turn-events.md \
  docs/architecture/turn-feed-post-id-contract.md \
  docs/plans/2026-03-24_turn_table_steady_state_closeout_584731/
```

**Expected:** `Docs metadata validation succeeded.`

## 3. Runtime-path search (legacy **table** tokens)

```bash
rg "\b(turn_metadata|generated_feeds|likes|comments|follows)\b" \
  db/adapters db/repositories db/services simulation/api simulation/core scripts
```

**How to interpret hits (allowed residual categories):**

- **Python/domain identifiers:** Parameter names like `turn_metadata: TurnMetadata`, variables `likes`, `comments`, `follows`, `generated_feeds` collections — these are **not** SQL table names; they are expected unless a hit is a string literal SQL identifier for a dropped table.
- **API routes / English copy:** e.g. `/follows`, “list follows”, docstrings mentioning likes/comments — allowed.
- **Schema linter allowlist:** `scripts/lint_schema_conventions.py` lists legacy names intentionally as **forbidden table names** — expected.
- **Red flags:** ORM `Table("likes", …)`, raw SQL `FROM likes` / `INSERT INTO generated_feeds`, or new code introducing those as physical table names. At steady state, physical tables are `turns`, `turn_generated_feeds`, `turn_likes`, etc.

## 4. Docs / plans / lint tests search

```bash
rg "\b(turn_metadata|generated_feeds|likes|comments|follows)\b" \
  docs/architecture docs/plans tests/lint
```

**How to interpret hits:**

- **Historical / explanatory:** Architecture docs may name old table names when stating they are **not** acceptable at HEAD, or in pointers to strategy proposals — allowed.
- **Test fixtures:** Negative tests that model bad metadata (e.g. legacy table names) — allowed.
- **Red flags:** Normative “current schema uses `generated_feeds`” style statements — should be absent after closeout.

## 5. Generated schema docs check

```bash
uv run python scripts/generate_db_schema_docs.py --check
```

**Expected:** Check passes (generated docs match migrations/schema).

## 6. Ruff (repo-wide Python)

```bash
uv run ruff check .
```

**Expected:** Pass.

## 7. Optional: schema linter CLI on real metadata

```bash
uv run python scripts/lint_schema_conventions.py
```

**Expected:** `OK (N tables checked)` with exit code 0.
