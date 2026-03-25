---
name: Feature Extraction API Health
description: "Add a minimal FastAPI app under ml_tooling/api with GET /health, tests, Dockerfile.feature-extraction, and Railway second-service runbook — without changing the simulation Dockerfile or railway.json."
tags: [plan, fastapi, railway, docker, ml-tooling, health]
overview: Ship the first slice of the Feature Extraction PRD — a standalone FastAPI service with GET /health for Railway health checks and future readiness fields — with pytest (TestClient), a dedicated Dockerfile, and documented Railway steps for a second service.
todos:
  - id: contract-freeze
    content: Freeze GET /health JSON shape and status codes (document in PR or plan section)
    status: completed
  - id: ptp-1-tests
    content: Add tests/ml_tooling/api/test_health.py with TestClient (TDD red)
    status: completed
  - id: ptp-2-api
    content: Implement ml_tooling/api/main.py + routes/health.py; wire router; green tests
    status: completed
  - id: ptp-3-docker-railway
    content: Add Dockerfile.feature-extraction + Railway runbook subsection; optional HEALTHCHECK
    status: completed
  - id: ptp-4-pyproject
    content: "Only if needed: extend pyproject hatch packages for ml_tooling"
    status: cancelled
  - id: docs-plan-file
    content: Write docs/plans/2026-03-25_feature_extraction_api_health_847291/plan.md with YAML front matter; run check_docs_metadata.py
    status: completed
  - id: final-verify
    content: Run pytest, ruff, pyright on touched paths; manual curl + optional Railway deploy check
    status: completed
isProject: false
---

# Feature Extraction API — health endpoint + Railway scaffold

## Overview

Ship the first slice of the [Feature Extraction PRD](strategy_planning/2026-03-13_feature_extraction_api/FEATURE_EXTRACTION_API_PRD.md): a standalone FastAPI service entrypoint under `ml_tooling/api/` with **GET /health** returning JSON suitable for Railway’s HTTP health checks and future readiness fields (models, version). Include **pytest coverage** using `TestClient`, and **deployment artifacts** (slim Dockerfile + documented Railway service settings) so a **second** Railway service can run this app without altering the existing `Dockerfile` / `railway.json` used by `simulation.api.main`.

## Interface or Contract Freeze

| Item                  | Value                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Path                  | `GET /health`                                                                                                            |
| Status                | `200` when process is up (no model loading yet — always ready for v1)                                                    |
| JSON fields (minimum) | `status`: `"ok"`; `service`: `"feature-extraction"`                                                                      |
| Optional fields       | `version`: string from env e.g. `FEATURE_EXTRACTION_VERSION` or `GIT_COMMIT` / Railway’s `RAILWAY_GIT_COMMIT_SHA` if set |
| Future                | `readiness` object reserved for Phase 2 — may be `{}` or omitted in v1                                                   |

## Happy Flow

1. Operator runs the service locally: `PYTHONPATH=. uv run uvicorn ml_tooling.api.main:app --reload --host 127.0.0.1 --port 8010`.
2. Client calls `GET http://127.0.0.1:8010/health`.
3. FastAPI resolves the health router in `ml_tooling/api/routes/health.py` (included from `ml_tooling/api/main.py`).
4. Response is **HTTP 200** with JSON body (`status`, `service`, optional `version`).
5. On Railway, the platform probes `/health` against the public URL; container binds `$PORT` with `--host 0.0.0.0`.

## Data Flow

Client or Railway health probe sends HTTP GET to Uvicorn; FastAPI dispatches to the health router; the handler returns a small JSON dict (status, service, optional version from environment) with no database or model loading.

## Manual Verification

- **Unit tests:** `uv run pytest tests/ml_tooling/api/test_health.py -v` — all passed.
- **Local server:** `PYTHONPATH=. uv run uvicorn ml_tooling.api.main:app --host 127.0.0.1 --port 8010` then `curl -sS http://127.0.0.1:8010/health` — HTTP 200 and JSON with `status` key.
- **OpenAPI:** `curl -sS http://127.0.0.1:8010/openapi.json` returns schema.
- **Docker (optional):** `docker build -f Dockerfile.feature-extraction -t fe-api:local .` then run with `-e PORT=8010` and curl `/health`.
- **Docs metadata:** `uv run python scripts/check_docs_metadata.py docs/runbooks/RAILWAY_DEPLOYMENT.md docs/plans/2026-03-25_feature_extraction_api_health_847291/plan.md`
