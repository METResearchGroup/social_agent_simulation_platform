# Railway Deployment Guide

This guide deploys the FastAPI backend to Railway with Docker and persistent SQLite.
It uses the Railway CLI for both deployment and verification steps.

## Prerequisites

- Railway account and project
- Railway CLI installed: `npm i -g @railway/cli`
- Logged in: `railway login`
- Repository contains `Dockerfile` and `railway.json`

## Link The Project

From repo root:

```bash
railway link
```

If you need to create a new Railway project first:

```bash
railway init
```

## Persistent SQLite Setup

1. Add a volume in Railway and mount it at `/data`.
2. Set environment variable:

```bash
railway variables --set "SIM_DB_PATH=/data/db.sqlite"
```

Notes:
- `SIM_DB_PATH` is read by the app at runtime and is the recommended SQLite path override for Railway.
- If you use a different mount path, set `SIM_DB_PATH` accordingly.
- The Docker build uses `uv sync --frozen` only when `uv.lock` exists; otherwise it falls back to `uv sync --no-dev`.

## Deploy With Railway CLI

From repo root:

```bash
railway up
```

The runtime command is configured in `Dockerfile` (`CMD`):

```bash
uv run uvicorn simulation.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Verify Deployment With Railway CLI + HTTP Checks

Check service status and logs:

```bash
railway status
railway logs
```

Get the service URL:

```bash
railway domain
```

Replace `<APP_URL>` with your output domain and verify endpoints:

```bash
curl -sS "<APP_URL>/health"
curl -sS -X POST "<APP_URL>/v1/simulations/run" \
  -H "Content-Type: application/json" \
  -d '{"num_agents": 1, "num_turns": 1}'
```

Expected behavior:
- `GET /health` returns `{"status":"ok"}` with HTTP 200.
- `POST /v1/simulations/run` returns HTTP 200 with `run_id`, `status`, `likes_per_turn`, and `total_likes` (status may be `failed` if no agent fixture data is loaded).

## Run Smoke Tests Against Deployed URL

```bash
SIMULATION_API_URL=<APP_URL> uv run pytest -m smoke tests/api/test_simulation_smoke.py
```

## Operational Notes

- Keep worker count conservative with SQLite to reduce lock contention.
- Sync run requests can take time; configure client and platform timeouts accordingly.
- For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
