---
description: Add and operate the FastAPI API Gateway (proxy) locally and on Railway.
tags: [gateway, fastapi, proxy, railway, docker]
---

# FastAPI API Gateway (Proxy)

This runbook describes how to run and deploy the FastAPI-based API gateway service that proxies `/v1/*` requests to the existing backend API.

## What it does (MVP)

- Exposes `GET /health`.
- Proxies `/{...}` under `/v1/{full_path:path}` to a single upstream `GATEWAY_UPSTREAM_BASE_URL`.
- Adds/propagates `X-Request-ID` and emits structured JSON logs (request start + completion).

## Local development (no Docker)

### 1) Install deps

From repo root:

```bash
uv sync --extra test
```

### 2) Start the backend API (upstream)

```bash
PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000
```

Expected: backend serves `http://127.0.0.1:8000/health`.

### 3) Start the gateway

```bash
PYTHONPATH=. \
GATEWAY_UPSTREAM_BASE_URL=http://127.0.0.1:8000 \
uv run uvicorn gateway.api.main:app --reload --port 8001
```

Expected: gateway serves `http://127.0.0.1:8001/health`.

### 4) Verify proxying

```bash
curl -sS http://127.0.0.1:8001/health
curl -sS http://127.0.0.1:8001/v1/simulations/metrics
```

Expected:

- Health returns `{"status":"ok"}`.
- The `/v1/...` call returns the same payload as the backend upstream.

## Local development (Docker Compose)

From repo root:

```bash
docker compose up --build
```

Verify:

```bash
curl -sS http://127.0.0.1:8001/health
curl -sS http://127.0.0.1:8001/v1/simulations/metrics
```

## Railway deployment (two services, one repo, one Dockerfile)

This repo uses a single root `Dockerfile` and selects which FastAPI app to run via `APP_MODULE`.

### Service 1: `api` (existing backend)

Variables:

- `APP_MODULE=simulation.api.main:app`
- `FORWARDED_ALLOW_IPS=*`
- If using persistent SQLite: `SIM_DB_PATH=/data/db.sqlite` (and mount a volume at `/data`)

Networking:

- Recommended after gateway is live: remove the public domain for `api` so it is only reachable on the private network.

### Service 2: `gateway` (public entrypoint)

Variables:

- `APP_MODULE=gateway.api.main:app`
- `FORWARDED_ALLOW_IPS=*`
- `ALLOWED_ORIGINS=<comma-separated UI origin(s)>`
- `GATEWAY_UPSTREAM_BASE_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}`
- `GATEWAY_TIMEOUT_SECONDS=60`

### UI (Vercel) configuration

Set Vercel env var:

- `NEXT_PUBLIC_SIMULATION_API_URL=https://<gateway-public-domain>/v1`

Redeploy the UI.

### Verify

```bash
curl -sS https://<gateway-public-domain>/health
curl -sS https://<gateway-public-domain>/v1/simulations/metrics
```

Optional smoke test:

```bash
SIMULATION_API_URL=https://<gateway-public-domain> uv run pytest -m smoke tests/api/test_simulation_smoke.py
```
