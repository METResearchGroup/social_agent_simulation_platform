---
name: Log Route Completion Decorator
overview: Refactor the repetitive `log_route_completion` calls in simulation routes into a parameterized decorator that logs route completion after each handler returns, keeping routes thin and consolidating the logging pattern per docs/RULES.md.
todos:
  - id: add-error-extractor
    content: Move _error_code_from_json_response to lib/request_logging.py
    status: completed
  - id: add-decorator
    content: Implement log_route_completion_decorator in lib/request_logging.py
    status: completed
  - id: refactor-routes
    content: Apply decorator to all 5 routes and remove inline logging in simulation.py
    status: completed
  - id: verify-tests
    content: Run pytest and pre-commit, verify structured logs
    status: completed
isProject: false
---

# Log Route Completion Decorator

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

The five simulation route handlers in [simulation/api/routes/simulation.py](simulation/api/routes/simulation.py) each contained 15–20 lines of branching logic that extracted `request_id`, `latency_ms`, and response metadata, then called `log_route_completion` for success vs error paths. This cluttered the routes and violated the "Keep HTTP routes thin" guideline in [docs/RULES.md](docs/RULES.md). We introduced a parameterized decorator `@log_route_completion_decorator` in [lib/request_logging.py](lib/request_logging.py) that wraps route handlers and performs the logging in one place, aligning with docs/RULES.md's preference for "decorators for removing boilerplate code shared across multiple callers."

---

## Happy Flow

1. Client issues a request (e.g. `GET /v1/simulations/runs`). [RequestIdMiddleware](simulation/api/main.py) assigns `request.state.request_id` and logs request start.
2. FastAPI invokes the route handler. The decorator wraps the handler; the inner logic calls the underlying handler (e.g. `_execute_get_simulation_runs`), which is already wrapped by `@timed` and attaches `request.state.duration_ms`.
3. Handler returns either a success type (`list`, `RunResponse`, `RunDetailsResponse`, `dict`) or a `JSONResponse` error. The decorator receives the return value.
4. Decorator inspects the return value: `isinstance(result, success_type)`. It extracts `request_id` and `latency_ms` from `request.state`, and derives `run_id`, `status`, and `error_code` from the result (success path) or from `_error_code_from_json_response` (error path).
5. Decorator calls [log_route_completion](../../lib/request_logging.py) and returns the original result. FastAPI serializes the response.

---

## Implementation Summary

### lib/request_logging.py

- **`_error_code_from_json_response(response)`** — Moved from simulation.py. Extracts `error.code` from JSONResponse content (dict or serialized body).
- **`log_route_completion_decorator(route, success_type, run_id_from)`** — Parameterized decorator:
  - `route`: Route identifier string (e.g. `SIMULATION_RUNS_ROUTE`)
  - `success_type`: Type(s) that indicate success
  - `run_id_from`: `"response"` | `"path"` | `"none"`

### simulation/api/routes/simulation.py

| Route | success_type | run_id_from |
|-------|--------------|-------------|
| get_simulation_runs | `list` | `"none"` |
| post_simulations_run | `RunResponse` | `"response"` |
| get_simulation_run | `RunDetailsResponse` | `"response"` |
| get_simulation_posts | `list` | `"none"` |
| get_simulation_run_turns | `dict` | `"path"` |

Decorator order: `@log_route_completion_decorator(...)` below `@router.get/post`.

---

## Manual Verification

- **Run tests**
  - `cd /Users/mark/Documents/work/agent_simulation_platform`
  - `uv run pytest tests/api/test_simulation_run.py tests/api/test_simulation_posts.py -v`
  - Expected: all tests pass.
- **Start server and verify logs**
  - `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
  - In another terminal: `curl -s http://localhost:8000/v1/simulations/runs | head -c 200`
  - Check server logs for structured `request_completed` lines with `event`, `request_id`, `route`, `latency_ms`, `status`.
- **Verify error path**
  - `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/simulations/runs/nonexistent`
  - Expected: 404. Check logs for `request_completed` with `error_code=RUN_NOT_FOUND`.
- **Linting and typecheck**
  - `uv run pre-commit run --all-files`
  - Expected: ruff, format, pyright pass.

---

## Alternative Approaches

- **Middleware**: Could log after `call_next` returns. Middleware only sees the final Starlette `Response`, not the route's return value. Would need to parse the response body for `run_id`/`error_code`, which duplicates logic and is brittle. Rejected.
- **Keep inline**: Keeps behavior explicit but clutters routes with 15+ lines of logging per handler. Violates DRY and "Keep HTTP routes thin." Rejected.
- **Decorator with extractors**: A decorator that accepts custom `run_id_extractor(result, kwargs)` and `status_extractor(result)` would be more flexible but adds complexity. The three `run_id_from` modes cover all current routes. Chosen approach is simpler and sufficient (YAGNI).
