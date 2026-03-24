---
description: Verification notes for turn-table v2 schema spine slice
tags: [verification, plan, database, turns]
---

# Turn schema spine — verification

- `SIM_DB_PATH=/tmp/turn_tables_v2.sqlite uv run python -m alembic -c pyproject.toml upgrade head` — exit 0, single head `f3c9a1e7b2d4`.
- `uv run pytest tests/db/test_turn_table_v2_schema_migration.py -q` — pass.
- `uv run pytest tests/db -k "turn or migration" -q` — pass.
- `uv run pytest tests/lint/test_lint_schema_conventions.py -q` — pass.
- `uv run python scripts/generate_db_schema_docs.py --check` — pass after updating `docs/db/LATEST.txt` to `2026_03_22-192628-feat__turn-table-v2-schema-spine`.
