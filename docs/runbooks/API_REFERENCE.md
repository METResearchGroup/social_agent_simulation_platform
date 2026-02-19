---
description: Endpoint reference and example requests for the simulation API (health, run simulation, fetch run details).
tags: [api, reference, endpoints, curl, simulation]
---

# API Reference Runbook

Endpoint reference and example requests for the simulation API.

## Endpoints

- **`GET /health`** — Health check. Returns `200` with `{"status": "ok"}`.

- **`POST /v1/simulations/run`** — Run a synchronous simulation.
  - **Request body:** `num_agents` (required, >0), `num_turns` (optional, default `10`), `feed_algorithm` (optional, default `"chronological"`).
  - **Response:** `run_id`, `status` (`completed` or `failed`), `num_agents`, `num_turns`, `likes_per_turn`, `total_likes`, `error` (present when `status` is `failed` or on server error). OpenAPI schema at `http://localhost:8000/docs`.

- **`GET /v1/simulations/runs/{run_id}`** — Fetch details for a persisted run.
  - **Response:** `run_id`, `status` (`running` | `completed` | `failed`), timestamps, `config` (`num_agents`, `num_turns`, `feed_algorithm`), and ordered turn history (`turns` with `turn_number`, `created_at`, `total_actions`).

## Error Payloads

Error responses use a stable shape `error: { "code", "message", "detail" }`:

| Code | HTTP | When |
|------|------|------|
| `SIMULATION_FAILED` | 200 | Run created but failed mid-execution; partial `likes_per_turn` returned. |
| `RUN_CREATION_FAILED` | 500 | Failure before run creation (e.g. DB error). |
| `RUN_NOT_FOUND` | 404 | Requested run ID does not exist. |
| `INTERNAL_ERROR` | 500 | Unexpected server error. |
| `VALIDATION_ERROR` | 422 | Invalid request body (e.g. `num_agents` ≤ 0); `detail` is an array of field errors. |

## Example Requests (curl)

```bash
# Health check
curl -s http://localhost:8000/health

# Minimal run (defaults: num_turns=10, feed_algorithm=chronological)
curl -s -X POST http://localhost:8000/v1/simulations/run \
  -H "Content-Type: application/json" \
  -d '{"num_agents": 5}'

# Full run
curl -s -X POST http://localhost:8000/v1/simulations/run \
  -H "Content-Type: application/json" \
  -d '{"num_agents": 10, "num_turns": 5, "feed_algorithm": "chronological"}'

# Fetch run details by run_id (replace with value from POST response)
curl -s http://localhost:8000/v1/simulations/runs/run_2026_01_01-00:00:00_abc123
```
