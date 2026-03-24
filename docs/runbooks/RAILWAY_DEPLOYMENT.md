---
description: Deploy the FastAPI backend to Railway with Docker and persistent SQLite.
tags: [deployment, railway, docker, fastapi, sqlite]
---

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
2. Set environment variables:

```bash
railway variables --set "SIM_DB_PATH=/data/db.sqlite"
railway variables --set "FORWARDED_ALLOW_IPS=*"
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
uv run uvicorn simulation.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
```

**Proxy headers (FASTAPI-PROXY-001):** Set `FORWARDED_ALLOW_IPS=*` in Railway variables. The container is only reachable through Railway's proxy, so trusting forwarded headers from all connections is safe. This ensures `X-Forwarded-For` and other proxy headers are applied for rate limiting and client IP detection. See [plan Security section](../plans/2026-02-19_rate_limiting_post_paths_847291/plan.md#security-proxy-trust-fastapi-proxy-001).

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

Replace `<APP_URL>` with your output domain and verify endpoints.

**Public health:**

```bash
curl -sS "<APP_URL>/health"
```

**Authenticated simulation routes** (use a valid bearer token; same requirement as the UI):

```bash
curl -sS -X POST "<APP_URL>/v1/simulations/run" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"num_agents": 1, "num_turns": 1}'
curl -sS -H "Authorization: Bearer <TOKEN>" "<APP_URL>/v1/simulations/metrics"
curl -sS -H "Authorization: Bearer <TOKEN>" "<APP_URL>/v1/simulations/feed-algorithms"
```

Expected behavior:

- `GET /health` returns `{"status":"ok"}` with HTTP 200 (no auth).
- `POST /v1/simulations/run` returns HTTP 200 with a `RunResponse`-shaped body: `run_id`, `created_at`, `status`, `num_agents`, `num_turns`, `turns` (list of turn summaries), optional `run_metrics`, and `error` when `status` is `failed`.
- `GET /v1/simulations/metrics` and `GET /v1/simulations/feed-algorithms` return HTTP **200** with JSON arrays (metadata for the UI). A **404** on these paths usually means API/UI release skew or a wrong base URL.

## Run Smoke Tests Against Deployed URL

With a bearer token (production-style):

```bash
SIMULATION_API_URL=<APP_URL> SIMULATION_API_BEARER_TOKEN=<TOKEN> uv run pytest -m smoke tests/api/test_simulation_smoke.py
```

For local smoke against an API with `DISABLE_AUTH=1`, `SIMULATION_API_BEARER_TOKEN` may be omitted. See [SMOKE_TEST.md](./SMOKE_TEST.md).

## Operational Notes

- Keep worker count conservative with SQLite to reduce lock contention.
- Sync run requests can take time; configure client and platform timeouts accordingly.
- For higher production concurrency, plan migration to a server database (for example Postgres) in a later phase.
