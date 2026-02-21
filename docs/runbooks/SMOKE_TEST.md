---
description: Run the simulation API smoke suite against a local or deployed server via pytest.
tags: [smoke-test, testing, api, pytest]
---

# Smoke Test Runbook

This runbook describes how to run the simulation API smoke suite against a running server (local or deployed).

## Prerequisites

- `SIMULATION_API_URL` must be set to the base URL of a running simulation API (no trailing slash).
- The target server must be reachable (e.g. local uvicorn or a deployed Railway app).

## Running the Smoke Suite

From the repo root:

```bash
SIMULATION_API_URL=<APP_URL> uv run pytest -m smoke tests/api/test_simulation_smoke.py
```

**Examples:**

- Local server (default port):

  ```bash
  SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py
  ```

- Deployed Railway app:

  ```bash
  SIMULATION_API_URL=https://agent-simulation-platform-production.up.railway.app uv run pytest -m smoke tests/api/test_simulation_smoke.py
  ```

If `SIMULATION_API_URL` is not set, the smoke tests are **skipped** (they only run when explicitly pointed at a live server).

## See Also

- [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) — deploy and verify with cURL; includes the same smoke command in "Run Smoke Tests Against Deployed URL".
