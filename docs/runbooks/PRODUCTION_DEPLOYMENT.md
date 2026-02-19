---
description: General production and deployment guidance for the simulation API (workers, timeouts, run command).
tags: [production, deployment, uvicorn, workers, timeouts]
---

# Production Deployment Runbook

General production and deployment guidance for the simulation API.

## Run Command (no reload)

```bash
PYTHONPATH=. uv run uvicorn simulation.api.main:app --host 0.0.0.0 --port 8000
```

Override port via `$PORT` (e.g. on Railway).

## Workers

With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

## Timeouts

`POST /v1/simulations/run` can be long-running. Set a server timeout (e.g. uvicorn/gunicorn `--timeout 120`) and a client timeout (e.g. 60–120 seconds) so runs are not cut off.

## Platform-Specific Runbooks

- [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) — Railway deployment with Docker and persistent SQLite
- [UI_DEPLOYMENT.md](./UI_DEPLOYMENT.md) — Next.js UI deployment to Vercel
