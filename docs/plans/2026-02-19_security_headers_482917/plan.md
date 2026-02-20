---
name: Security Headers Implementation
overview: Add security headers middleware to the FastAPI backend to mitigate XSS, clickjacking, and MIME sniffing risks by setting X-Content-Type-Options, X-Frame-Options, and Strict-Transport-Security (when HTTPS) on all API responses.
todos:
  - id: create-middleware
    content: Create lib/security_headers.py with SecurityHeadersMiddleware
    status: completed
  - id: register-middleware
    content: Register SecurityHeadersMiddleware in simulation/api/main.py
    status: completed
  - id: add-tests
    content: Add tests/api/test_security_headers.py with header assertions
    status: completed
  - id: verify
    content: Run pytest and manual curl verification
    status: completed
isProject: false
---

# Security Headers Implementation Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Implement item 8 from [SECURITY_IMPROVEMENTS.md](SECURITY_IMPROVEMENTS.md): add response headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` when HTTPS) via a Starlette middleware. This reduces risk of XSS, clickjacking, and MIME sniffing when the API or its docs (Swagger UI) are embedded or served in a broader context.

---

## Happy Flow

1. Request hits any API route (e.g. `GET /health` or `POST /v1/simulations/run`).
2. `RequestIdMiddleware` runs first (existing), then `SecurityHeadersMiddleware`.
3. `SecurityHeadersMiddleware` calls `call_next(request)`, obtains the response.
4. Middleware adds headers to the response:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (only when `ENABLE_HSTS` is set and truthy, for HTTPS deployments).
5. Response is returned to the client with all security headers present.

Files involved:

- [simulation/api/main.py](simulation/api/main.py) – add middleware registration
- [lib/security_headers.py](lib/security_headers.py) – new module containing `SecurityHeadersMiddleware` class

---

## Manual Verification

- **Run tests**
  - `cd /Users/mark/.cursor/worktrees/v2_agent_simulation_platform_worktree/kxp`
  - `uv run pytest tests/ -v`
  - Expected: all tests pass.
- **Verify headers on local API**
  - Start API: `PYTHONPATH=. uv run uvicorn simulation.api.main:app --host 127.0.0.1 --port 8000`
  - In another terminal: `curl -s -I http://127.0.0.1:8000/health`
  - Confirm presence of:
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options: DENY`
  - Confirm `Strict-Transport-Security` is **absent** when `ENABLE_HSTS` is unset (local HTTP).
- **Verify HSTS when enabled**
  - Set env: `ENABLE_HSTS=1`
  - Restart API and run: `curl -s -I http://127.0.0.1:8000/health`
  - Confirm `Strict-Transport-Security: max-age=31536000; includeSubDomains` is present.
- **Verify headers on API routes**
  - `curl -s -I http://127.0.0.1:8000/v1/simulations/run -X POST -H "Content-Type: application/json" -d '{}'`
  - Same headers should appear on all routes (including 422/500 responses).

---

## Implementation Steps

### 1. Create `lib/security_headers.py`

Define `SecurityHeadersMiddleware`:

- Extend `starlette.middleware.base.BaseHTTPMiddleware`.
- In `dispatch`, call `response = await call_next(request)`.
- Add headers to `response.headers`:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - If `os.environ.get("ENABLE_HSTS", "").lower() in ("1", "true", "yes")`: add `Strict-Transport-Security: max-age=31536000; includeSubDomains`.
- Return `response`.

Use immutable dict assignment (e.g. `response.headers["X-Content-Type-Options"] = "nosniff"`) to avoid mutating the shared headers object incorrectly. Starlette `Response` allows header assignment.

### 2. Register middleware in `simulation/api/main.py`

- Import `SecurityHeadersMiddleware` from `lib.security_headers`.
- Add `app.add_middleware(SecurityHeadersMiddleware)` **before** `RequestIdMiddleware` (middleware runs in reverse order of registration; SecurityHeaders should run after RequestId so it wraps the inner stack and adds headers to the final response).

Middleware execution order: last added runs first (outermost). Current order (as registered):

1. `RequestIdMiddleware` (added first)
2. `CORSMiddleware`

For SecurityHeaders to add headers to the final response, it should run as an outer layer. Add `SecurityHeadersMiddleware` **before** `RequestIdMiddleware` so it executes after RequestId (i.e. SecurityHeaders is outermost, adds headers last). Actually: in Starlette, the first middleware added is the outermost. So:

- `app.add_middleware(A)` → A is outermost
- `app.add_middleware(B)` → B is inside A

Request flow: A receives request → B receives request → route → B sends response → A sends response. So A can modify the response from B. If we want SecurityHeaders to add headers to the final response, SecurityHeaders should be the outermost (first added). Add `app.add_middleware(SecurityHeadersMiddleware)` **before** the existing `app.add_middleware(RequestIdMiddleware)`.

### 3. Add tests in `tests/api/test_security_headers.py`

- `test_security_headers_present_on_health`: `GET /health` returns 200 and response includes `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.
- `test_hsts_absent_when_disabled`: With `ENABLE_HSTS` unset or false, `Strict-Transport-Security` header is absent.
- `test_hsts_present_when_enabled`: With `ENABLE_HSTS=1`, `Strict-Transport-Security` is present with `max-age=31536000`.

Use `TestClient` from `starlette.testclient` (or `httpx`/`requests` via FastAPI's `TestClient`) and assert on `response.headers`.

---

## Alternative Approaches

- **Per-route decorator**: Would require decorating every route; middleware is DRY and applies to all responses.
- `**fastapi-security` or third-party package**: Adds a dependency for a simple middleware; custom middleware is minimal and matches existing patterns (e.g. `RequestIdMiddleware`).
- **CSP header**: Omitted for the API since responses are JSON; CSP is most useful for HTML (e.g. Swagger UI). Can be added later if needed.
- `**X-XSS-Protection`**: Deprecated in modern browsers; `X-Content-Type-Options: nosniff` and CSP provide better protection; not included.

---

## Plan Asset Storage

```
docs/plans/2026-02-19_security_headers_482917/
```

No UI changes; no before/after screenshots required.