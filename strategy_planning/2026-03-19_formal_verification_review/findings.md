---
date: 2026-03-19
scope: python-backend
repo: agent-simulation-platform
---

## Scope reviewed

- **API entrypoint and request lifecycle**: `simulation/api/main.py`, `simulation/api/routes/*`, `simulation/api/services/*`
- **Core orchestration**: `simulation/core/engine.py`, `simulation/core/command_service.py`, `simulation/core/query_service.py`
- **“Formal-ish” invariants**: action generation + filtering + validation (`simulation/core/action_generators/*`, `simulation/core/action_policy/*`, `simulation/core/action_history/*`)
- **Persistence + transactions**: `db/adapters/sqlite/sqlite.py`, `db/services/simulation_persistence_service.py`, adapter/repo interfaces (`db/adapters/base.py`)
- **Cross-cutting**: auth dependency (`simulation/api/dependencies/auth.py`), request logging (`lib/request_logging.py`), security headers (`lib/security_headers.py`), rate limiting (`lib/rate_limiting.py`), timestamps (`lib/timestamp_utils.py`)

## What’s strong (keep it)

- **Clear layering with guardrails**: you already enforce architectural boundaries (import-linter + your custom “dependency injection guard” in CI/pre-commit), and the route layer stays fairly thin (routes call service functions; service calls the engine).
- **Event-loop safety for “sync-heavy” work**: routes use `asyncio.to_thread(...)` for engine/service operations (e.g., `simulation/api/routes/runs.py`), which avoids blocking the FastAPI event loop during simulation runs.
- **Transactional “all-or-nothing” persistence for a turn**: `SimulationPersistenceService.write_turn(...)` writes metadata + metrics (+ actions) inside a single transaction, preventing partial turn persistence.
- **Action invariants are explicit and enforced**: `AgentActionRulesValidator` + `ActionHistoryStore` enforce “no duplicates this turn” and “no repeat actions across turns” at runtime before persisting.
- **Consistent API error envelope**: the API consistently returns `{ "error": { code, message, detail } }` via helpers and exception handlers (validation errors, rate-limit errors, auth errors).

## Key risks / friction points I found

- **Non-determinism is baked into “random_simple” policies**: several action generators use module-global `random.random()` with no run/turn seed control (e.g., `simulation/core/action_generators/*/algorithms/random_simple.py`). That makes results hard to reproduce/debug and makes regression testing noisier.
- **Timestamp format is custom and inconsistently interpreted**:
  - `lib/timestamp_utils.get_current_timestamp()` emits a local-time, custom string format: `"%Y_%m_%d-%H:%M:%S"`.
  - random-simple generators parse `Post.created_at` using that same custom format, and silently degrade to a score of `0.0` on parse failure.
  - `Post.created_at` is an unconstrained string at the model layer, so upstream ISO-8601 timestamps (likely for Bluesky) will degrade scoring unexpectedly.
- **Identifier semantics are confusing in action models**: generated actions populate `Like.agent_id` / `Follow.agent_id` with an **agent handle** (not the canonical `Agent.agent_id`). This is likely intentional for now, but it’s a sharp edge that will cause confusion and potential join bugs when you expand persistence/analytics.
- **Proxy/rate-limit identity is easy to get wrong**: rate limiting uses `X-Forwarded-For` and selects the **rightmost** value as “real client IP” (`lib/rate_limiting.py`). That may match Railway’s behavior in one deployment setup, but it’s brittle across other proxy chains and can be spoofable without an explicit “trusted proxy” model.
- **Security headers are minimal**: good baseline headers are present (nosniff, frame deny, optional HSTS), but you’re missing the next layer of headers that help harden browser-facing interactions even for APIs (CSP, referrer policy, permissions policy).
