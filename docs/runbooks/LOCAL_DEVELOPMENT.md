---
description: Setup and running the simulation API locally with uv and uvicorn.
tags: [local, development, setup, api, uvicorn]
---

# Local Development Runbook

This runbook covers setup and running the API locally.

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
