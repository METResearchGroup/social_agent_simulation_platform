---
description: How to update local-dev seed fixtures used by LOCAL=true mode.
tags: [local, development, seed, fixtures, sqlite]
---

# Update seed data (LOCAL=true)

When `LOCAL=true`, the backend forces its SQLite DB to:

- `db/dev_dummy_data_db.sqlite`

This dummy DB is populated from committed JSON fixtures under:

- `simulation/local_dev/seed_fixtures/*.json`

`LOCAL=true` **ignores** `SIM_DB_PATH` to avoid ambiguity about which database the app is using.

---

## When to update seed fixtures

Update seed fixtures whenever you introduce changes that affect local UI/API behavior, including:

- New API fields (request/response schema changes)
- New DB tables or columns that local UI routes depend on
- New UI surfaces that need representative data (e.g., runs with metrics)
- Changes to default metric keys / metric output shapes

If you add new features and the local UI feels “stuck” or missing data, it usually means the fixtures don’t include representative rows for the new flow.

---

## How to regenerate fixtures

Seed fixtures are **canonical JSON** files committed in:

- `simulation/local_dev/seed_fixtures/*.json`

To update seed data:

1. Edit the relevant JSON fixture(s) directly.
2. Review the diffs in git.
3. Reset and re-seed your local dummy DB (see below) to apply the new fixtures.

---

## How to apply new fixtures to your local DB

Local mode uses a **seed-once** policy. If your dummy DB is already seeded and fixtures change, the backend will log a warning and **refuse to overwrite**.

To force a fresh DB seeded with the new fixtures:

```bash
LOCAL=true LOCAL_RESET_DB=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000
```

This deletes `db/dev_dummy_data_db.sqlite`, re-runs migrations, then re-seeds from fixtures.

---

## Validate end-to-end

1. Start backend:

   ```bash
   LOCAL=true PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000
   ```

2. Confirm API returns seeded runs:

   ```bash
   curl -s http://localhost:8000/v1/simulations/runs | jq 'length'
   ```

3. Start UI:

   ```bash
   cd ui && LOCAL=true npm run dev
   ```

4. Visit `http://localhost:3000` and confirm:
   - No sign-in required
   - Runs list is populated
   - Selecting a run loads turns and posts without errors

5. Run tests:

   ```bash
   uv run pytest
   ```
