---
description: Run the simulation API smoke suite against a local or deployed server via pytest.
tags: [smoke-test, testing, api, pytest]
---

# Smoke Test Runbook

This runbook describes how to run the simulation API smoke suite against a running server (local or deployed).

## Prerequisites

- `SIMULATION_API_URL` must be set to the base URL of a running simulation API (no trailing slash).
- The target server must be reachable (e.g. local uvicorn or a deployed Railway app).
- **Protected routes** (`/v1/...`) require authentication unless the API is running with auth bypass (local only).

## Authentication for smoke tests

Simulation routes under `/v1` use the normal app auth dependency.

- **Local (recommended for smoke):** start the API with `DISABLE_AUTH=1` so smoke tests do not need a token:

  ```bash
  DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --port 8000
  ```

  Then run the suite with only `SIMULATION_API_URL` set (no bearer token).

- **Deployed / real auth:** set `SIMULATION_API_BEARER_TOKEN` to a valid JWT (or other bearer token the API accepts). The smoke tests send `Authorization: Bearer <token>` on `POST /v1/simulations/run`, `GET /v1/simulations/metrics`, and `GET /v1/simulations/feed-algorithms`.

  Example (replace `<TOKEN>`):

  ```bash
  SIMULATION_API_URL=https://agent-simulation-platform-production.up.railway.app \
    SIMULATION_API_BEARER_TOKEN=<TOKEN> \
    uv run pytest -m smoke tests/api/test_simulation_smoke.py
  ```

If auth is required but neither bypass nor `SIMULATION_API_BEARER_TOKEN` is available, those tests fail with HTTP 401/403 and an explicit message—this is distinct from a **404**, which indicates a missing route (contract skew).

## Running the Smoke Suite

From the repo root:

```bash
SIMULATION_API_URL=<APP_URL> uv run pytest -m smoke tests/api/test_simulation_smoke.py
```

**Examples:**

- Local server with auth bypass (see above):

  ```bash
  SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py
  ```

- Deployed Railway app with bearer token:

  ```bash
  SIMULATION_API_URL=https://agent-simulation-platform-production.up.railway.app \
    SIMULATION_API_BEARER_TOKEN=<TOKEN> \
    uv run pytest -m smoke tests/api/test_simulation_smoke.py
  ```

If `SIMULATION_API_URL` is not set, the smoke tests are **skipped** (they only run when explicitly pointed at a live server).

## What the suite checks

- `GET /health` — anonymous; expects `{"status": "ok"}`.
- `POST /v1/simulations/run` — response matches the current `RunResponse` contract (including `turns`, not legacy aggregate-like fields).
- `GET /v1/simulations/metrics` and `GET /v1/simulations/feed-algorithms` — **200** with non-empty JSON lists (metadata routes present on the deployed backend).

## See Also

- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) — coordinated same-ref release and post-deploy checks
- [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) — API deploy and verification with cURL
- [UI_DEPLOYMENT.md](./UI_DEPLOYMENT.md) — Vercel UI and `NEXT_PUBLIC_SIMULATION_API_URL`
