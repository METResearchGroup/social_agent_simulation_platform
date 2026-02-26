---
description: How to run the backend and frontend locally (LOCAL mode) with seeded dummy data and bypassed auth.
tags: [local, development, api, uvicorn, auth]
---


# Local Development Runbook

This runbook covers setup and running the API locally.

## Recommended: Local dev mode

Local dev mode makes local development “just work”:

- Backend auth bypass is enabled automatically.
- Frontend auth bypass is enabled automatically.
- Backend uses a dedicated dummy DB: `db/dev_dummy_data_db.sqlite` and seeds it from fixtures.

Start backend:

```bash
LOCAL=true PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000
```

Start frontend:

```bash
cd ui && LOCAL=true npm run dev
```

Reset and reseed the dummy DB:

```bash
LOCAL=true LOCAL_RESET_DB=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000
```

## Setup

- Python ≥3.10. Install dependencies with [uv](https://docs.astral.sh/uv/):

  ```bash
  uv sync --extra test
  ```

## Running the API

From the repository root (with `uv sync` already run):

```bash
PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
```

Then open `http://localhost:8000/health` for a health check. API docs are at `http://localhost:8000/docs`.

## See Also

- [API_REFERENCE.md](./API_REFERENCE.md) — endpoint details, error codes, curl examples
- [PRE_COMMIT_AND_LINTING.md](./PRE_COMMIT_AND_LINTING.md) — pre-commit, Ruff, Pyright, complexipy
- [UPDATE_SEED_DATA.md](./UPDATE_SEED_DATA.md) — updating LOCAL=true seed fixtures
