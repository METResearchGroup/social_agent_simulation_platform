---
name: Rate Limiting POST Paths
overview: Add per-IP rate limiting to all POST routes using slowapi, with a stricter limit on POST /v1/simulations/run. Deployment is Railway with a single uvicorn worker; in-memory backend is sufficient. No per-user/tenant limits.
todos:
  - id: add-slowapi-dep
    content: Add slowapi>=0.1.9 to pyproject.toml dependencies
    status: completed
  - id: configure-limiter-main
    content: Configure Limiter and custom RateLimitExceeded handler in simulation/api/main.py
    status: completed
  - id: apply-limit-post-route
    content: Add @limiter.limit("5/minute") to POST /simulations/run in simulation/api/routes/simulation.py
    status: completed
  - id: add-rate-limit-tests
    content: Add tests for 429 on rate limit and error shape in tests/api/
    status: completed
  - id: manual-verification
    content: Run Manual Verification checklist (pytest, server, curl, pre-commit)
    status: completed
isProject: false
---

# Rate Limiting for POST Paths

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Add rate limiting to protect the Agent Simulation Platform API from abuse. Per SECURITY_IMPROVEMENTS.md, expensive endpoints like `POST /v1/simulations/run` can be used for DoS or cost exhaustion. We use slowapi to apply per-IP limits on all POST routes. With a single uvicorn worker on Railway, the in-memory backend is sufficient; no Redis required.

---

## Happy Flow

1. Client sends a request to `POST /v1/simulations/run` (or any future POST route). Request passes through [RequestIdMiddleware](simulation/api/main.py) and CORS.
2. slowapi's `Limiter` checks the per-IP count for the route key. If under the limit (e.g. 5/minute for POST /simulations/run), the request proceeds to the route handler.
3. Route handler (e.g. `post_simulations_run`) runs; [log_route_completion_decorator](lib/request_logging.py) logs completion.
4. **If over limit:** slowapi raises `RateLimitExceeded` before the handler runs. Our custom exception handler returns a `JSONResponse` with status 429 and the standard error shape `{"error": {"code": "RATE_LIMITED", "message": "...", "detail": null}}`.
5. We use a custom key function `_get_rate_limit_key` in [lib/rate_limiting.py](lib/rate_limiting.py) (via `limiter = Limiter(key_func=_get_rate_limit_key)`). It reads `X-Forwarded-For` when present (Railway sets this), otherwise falls back to `request.client.host` or `127.0.0.1`, so clients behind the proxy are correctly identified by their real IP.

---

## Implementation

### 1. Add dependency

In [pyproject.toml](pyproject.toml), add to `dependencies`:

```toml
"slowapi>=0.1.9",
```

### 2. Configure Limiter and exception handler in main.py

In [simulation/api/main.py](simulation/api/main.py):

- Import `limiter` and `rate_limit_exceeded_handler` from [lib/rate_limiting](lib/rate_limiting.py)
- Import `RateLimitExceeded` from slowapi.errors
- Store `app.state.limiter = limiter` (the limiter is created in lib/rate_limiting.py with `limiter = Limiter(key_func=_get_rate_limit_key)`)
- Add exception handler for `RateLimitExceeded` that calls `rate_limit_exceeded_handler`; it returns a 429 `JSONResponse` matching the existing error shape: `{"error": {"code": "RATE_LIMITED", "message": "Rate limit exceeded", "detail": null}}`

The key function `_get_rate_limit_key` in lib/rate_limiting.py reads `request.headers.get("x-forwarded-for")` (HTTP headers are case-insensitive). On Railway the **rightmost** value is trustworthy (proxy appends real client); we use `split(",")[-1]`. Otherwise falls back to `request.client.host` or `FALLBACK_CLIENT_IP`.

### 3. Apply rate limit to POST route

In [simulation/api/routes/simulation.py](simulation/api/routes/simulation.py):

- Import `limiter` from [lib/rate_limiting](lib/rate_limiting.py). slowapi requires the limiter to be on `app.state.limiter`; the decorator resolves it from the request's app.
- Add `@limiter.limit("5/minute")` to `post_simulations_run`. Decorator order (top to bottom):
  1. `@router.post(...)`
  2. `@limiter.limit("5/minute")`
  3. `@log_route_completion_decorator(...)`
  4. `async def post_simulations_run(...)`
- The handler already receives `request: Request`, which slowapi requires.

Convention for future POST routes: add `@limiter.limit("5/minute")` (or an appropriate limit) below the route decorator and above the logging decorator.

### 4. Tests

Create or extend a test file under `tests/api/` to cover:

- **Rate limit enforced:** Send 6 requests to `POST /v1/simulations/run` within a short window from the same client; the 6th should return 429 with `error.code == "RATE_LIMITED"`.
- **Success under limit:** Send 1–2 requests; both return 200.
- **Error shape:** Assert 429 response has the standard structure `{"error": {"code": "RATE_LIMITED", "message": "...", "detail": ...}}`.

Testing approach: Use `TestClient` with the same app. Use `_trigger_rate_limit` helper to reset the limiter and make 6 requests; tests assert on responses. The in-memory limiter keys by IP; use `X-Forwarded-For` header to simulate different clients. Mock the engine to avoid running real simulations.

Note: slowapi resolves the limiter from `request.app.state.limiter`. Ensure the test app has the limiter configured before tests run.

---

## Security: Proxy trust (FASTAPI-PROXY-001)

**X-Forwarded-For** is trusted to identify the client when behind a reverse proxy (e.g. Railway). Per FASTAPI-PROXY-001, we must not blindly trust `X-Forwarded-*` from the open internet. In production:

1. **Dockerfile** — Uvicorn is started with `--forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"` so forwarded headers are applied only when the connection comes from a trusted proxy.
2. **Railway** — Set the env var: `railway variables --set "FORWARDED_ALLOW_IPS=*"`. On Railway the container is only reachable through the proxy, so `*` is safe.
3. **X-Forwarded-For parsing** — Railway appends the real client IP as the **rightmost** value. `_get_rate_limit_key` uses the rightmost value (`split(",")[-1]`) rather than the leftmost (which clients can spoof).

See [RAILWAY_DEPLOYMENT.md](../../runbooks/RAILWAY_DEPLOYMENT.md) for full setup.

---

## Manual Verification

- **Run tests**
  - `cd /Users/mark/.cursor/worktrees/v2_agent_simulation_platform_worktree/kxp`
  - `uv run pytest tests/api/test_simulation_run.py tests/api/test_simulation_rate_limit.py -v`
  - Expected: all tests pass.
- **Start server**
  - `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
  - Expected: server starts without errors.
- **Verify rate limit**
  - `for i in {1..7}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/v1/simulations/run -H "Content-Type: application/json" -d '{"num_agents":1,"num_turns":1}'; done`
  - Expected: first 5 return 200 (or 500 if engine not fully mocked), 6th and 7th return 429.
- **Verify 429 error shape**
  - `curl -s -X POST http://localhost:8000/v1/simulations/run -H "Content-Type: application/json" -d '{"num_agents":1,"num_turns":1}'` (after exceeding limit)
  - Expected: `{"error":{"code":"RATE_LIMITED","message":"Rate limit exceeded","detail":null}}`
- **Verify GET routes unaffected**
  - `curl -s http://localhost:8000/v1/simulations/runs | head -c 100`
  - Expected: 200, no rate limiting.
- **Lint and typecheck**
  - `uv run ruff check simulation/ lib/ tests/`
  - `uv run ruff format --check simulation/ lib/ tests/`
  - `uv run pyright simulation/ lib/`
  - Expected: no errors.
- **Pre-commit**
  - `uv run pre-commit run --all-files`
  - Expected: all hooks pass.

---

## Alternative Approaches

- **fastapi-limiter:** Uses `Depends(RateLimiter(...))`. DI-based, no Redis. Chosen slowapi because it is more widely used and has Redis support when we scale to multiple workers.
- **Custom middleware:** Full control but reinvents rate limiting logic; rejected for YAGNI.
- **Edge/proxy rate limiting (Railway/nginx):** Complements app-level limits; can add later. Not in scope for this change.

---

## Rule Compliance (review-rules)

| Rule                    | Status | Notes                                                                        |
| ----------------------- | ------ | ---------------------------------------------------------------------------- |
| PLANNING_RULES          | pass   | Overview, Happy Flow, Manual Verification, alternatives, specificity present |
| UNIT_TESTING_STANDARDS  | pass   | Tests for rate limit behavior, error shape; use pytest, arrange-act-assert   |
| CODING_REPO_CONVENTIONS | pass   | Use uv, Ruff; pre-commit verification in Manual Verification                 |
| CODING_RULES            | pass   | Implementation follows existing patterns (error shape, middleware)           |

---

## Plan Asset Storage

Save this plan and any related assets (e.g. verification notes) in:

```text
docs/plans/2026-02-19_rate_limiting_post_paths_847291/
```

No UI screenshots required (backend-only change).
