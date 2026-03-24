---
description: General production and deployment guidance for the simulation API (workers, timeouts, run command).
tags: [production, deployment, uvicorn, workers, timeouts]
---

# Production Deployment Runbook

General production and deployment guidance for the simulation API.

## Coordinated release (same ref on API and UI)

UI and API must be deployed from **one chosen git ref** (tag, branch SHA, or release) so the frontend calls match the backend contract. Drift (for example a newer UI expecting metadata routes against an older API) causes hard-to-debug production failures.

**Recommended order:**

1. Pick one ref (e.g. `main` at commit `abc123` or a release tag) and use it for both deploys.
2. Deploy the **API** first (Railway). See [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md).
3. Confirm the API base URL and contract (health + metadata routes). Use the commands in [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md#verify-deployment-with-railway-cli--http-checks) and [SMOKE_TEST.md](./SMOKE_TEST.md).
4. Deploy the **UI** (Vercel) from the **same ref**. See [UI_DEPLOYMENT.md](./UI_DEPLOYMENT.md).
5. In Vercel project settings, set `NEXT_PUBLIC_SIMULATION_API_URL` to the **canonical Railway production API URL** the UI should call (must match the API you just verified—often the stable `https://…up.railway.app` URL for the production service).
6. Run post-deploy checks: smoke suite with `SIMULATION_API_BEARER_TOKEN` against production, then open the production UI and sanity-check a seeded run.

Platform-specific details and copy-pastable checks live in the Railway and Vercel runbooks above.

## Run Command (no reload)

```bash
PYTHONPATH=. uv run uvicorn simulation.api.main:app --host 0.0.0.0 --port 8000 --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
```

Override port via `$PORT` (e.g. on Railway). When behind a reverse proxy (e.g. Railway), set `FORWARDED_ALLOW_IPS=*` so forwarded headers (`X-Forwarded-For`, etc.) are trusted for client IP detection and rate limiting (FASTAPI-PROXY-001).

## Workers

With SQLite, use 1–2 workers to avoid write contention. For higher concurrency, use a dedicated DB (e.g. Postgres) in a later phase.

## Timeouts

`POST /v1/simulations/run` can be long-running. Set a server timeout (e.g. uvicorn/gunicorn `--timeout 120`) and a client timeout (e.g. 60–120 seconds) so runs are not cut off.

## Platform-Specific Runbooks

- [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) — Railway deployment with Docker and persistent SQLite
- [UI_DEPLOYMENT.md](./UI_DEPLOYMENT.md) — Next.js UI deployment to Vercel
