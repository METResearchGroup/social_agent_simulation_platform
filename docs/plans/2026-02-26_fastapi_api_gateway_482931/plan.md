## Overview

Add a bare-bones FastAPI API gateway that proxies `/v1/*` requests to the existing FastAPI backend, and wire it for local development (Docker Compose) and Railway deployment (two services using the same Dockerfile selected by `APP_MODULE`).

## Happy Flow

1. **UI request via env** – `ui/lib/api/simulation.ts` points to `NEXT_PUBLIC_SIMULATION_API_URL` so the browser hits `https://<gateway-domain>/v1/...`.
2. **Gateway entry** – `gateway/api/main.py` adds `X-Request-ID`, logs start, and routes through `gateway/api/proxy.py`.
3. **Proxy forward** – `gateway/api/proxy.py` builds `${GATEWAY_UPSTREAM_BASE_URL}/v1/...`, filters hop-by-hop headers, and uses `httpx.AsyncClient`.
4. **Backend handling** – `simulation/api/main.py` processes the request and returns the response.
5. **Gateway response** – The proxy filters hop-by-hop headers, returns the payload, and `GatewayRequestLoggingMiddleware` logs completion + latency/status.
6. **Structured logs** – Logs include `event`, `request_id`, `route`, `method`, `latency_ms`, `status` for future observability.
7. **UI receives same payload** – Browser gets the proxied response with the `X-Request-ID`.

## Data Flow

- Browser request → `gateway/api/main.py` → `gateway/api/proxy.py` (formed URL using `GATEWAY_UPSTREAM_BASE_URL` + `/v1/{full_path}`).
- Proxy → upstream backend (`simulation/api/main.py`) and receives response.
- Gateway middleware filters headers, logs completion, and returns response → computer/UI.

## Key changes

- New gateway service code in `gateway/` (FastAPI app + httpx proxy).
- Root `Dockerfile` supports `APP_MODULE` to select which ASGI app to run.
- `docker-compose.yml` runs `api` + `gateway` locally.
- Tests validate proxying behavior using `httpx.MockTransport`.
- New runbook: `docs/runbooks/API_GATEWAY_FASTAPI.md`.

## Manual verification

- `uv sync --extra test`
- Backend: `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000`
- Gateway: `PYTHONPATH=. GATEWAY_UPSTREAM_BASE_URL=http://127.0.0.1:8000 uv run uvicorn gateway.api.main:app --reload --port 8001`
- `curl -sS http://127.0.0.1:8001/health`
- `curl -sS http://127.0.0.1:8001/v1/simulations/metrics`
- Tests: `uv run --extra test pytest`
