# Rules for the repo

1. Interfaces live next to implementations, in a "(path to folder)/interfaces.py" (e.g., feeds/interfaces.py).
2. Prefer ABC to Protocol, for strict inheritance and enforcement at runtime.

Dependency Injection over concrete instantiation

- Services should not instantiate concrete infra/state dependencies internally (e.g., no InMemory...() inside business methods).
- Inject dependencies via constructor or builder functions.

Keep orchestration thin

- Facades like SimulationEngine should delegate; avoid embedding dependency-construction logic in orchestration classes when possible.

APIs should accept explicit parameters, not implicit behavior

- The old update_run_status(run) always set RUNNING.
- The new update_run_status(run, status) makes the status explicit.
- Prefer parameters that describe what to do, not hidden, fixed behavior.

Prefer single or minimal public APIs. Default to private APIs that perform the implementation and expose one or two public API functions that do the composite task.

Organization:

- Public APIs should appear first among all functions or classes
- Follow with private APIs in descending order of callers:
  1. Public API first
  2. Immediate private APIs called by the public API
  3. Private APIs called only by other private APIs

Don't hardcode defaults or constants into functions inline. Define as file-level constants, underneath the imports, and then use them. This helps us keep track of hardcoded behaviors. Give file-level constants clear names and explicit types.

- Example: `feeds/feed_generator.py` exposes one public function, `generate_feeds`, which is the only function used by external callers. The actual functionality is largely managed by internal private functions.

Prefer keyword args.

Domain purity

- Domain models (simulation.core.models) depend only on stdlib, pydantic, and same-layer models. No imports from lib, db, feeds, or ai. Time and I/O are supplied by callers (e.g. created_at parameter) or live in the application layer.

Imports:

- Use absolute imports (e.g., import path.to.module) instead of relative imports (e.g., import .module)

Type annotations:

- Use | instead of "Optional" or "Union" for typing.
- When creating a variable as the result of a function, always include the type annotation in the variable definition. However, do this only on the happy path definition and instantiation of the function, not when it is defined in alternative branch or exception paths (so as to avoid pyright errors like "Declaration "metadata_list" is obscured by a declaration of the same name").
- Prefer generic Iterable over list or set, unless it truly needs to be a list or set (e.g., type as a list if we need order preserved). Err on the side of more generic annotation.
- Avoid using the "Any" type annotation, unless absolutely needed. If you ever use it, flag to the user and get explicit approval.

API design and rollout

- Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.

Per-commit:

- Run all pre-commit hooks.
- Follow ci.yml and run those commands (e.g., "ruff", "uv run pytest") and fix errors as needed.
- ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.

Testing:

- Add throwaway end-to-end tests to verify functionality
- Before finalizing tests, decide:
  - Should these end-to-end tests be persisted or removed after verification?
  - Should I/O operations be mocked or use real I/O?
- Use explicit expected-result variables in tests (e.g. expected_result = {...} then assert against it) to keep assertions readable.
- Make use of fixtures to systematize resource setup/teardown across tests.

Docstrings:

- Avoid hardcoding implementation details (e.g., "runs XYZ function, calls XYZ database"). Keep docstrings related to (1) inputs/outputs, (2) expected exceptions, (3) core algorithmic details (including branching logic), and (4) known edge cases or gotchas or tricky situations.

API routes

- Keep HTTP routes thin. Routes should validate input, get dependencies (e.g. from request.app.state), call a service (or asyncio.to_thread(service, ...) for sync code), and return the response. Put orchestration (building config, calling engine, mapping to response DTOs) in a dedicated service module, not in the route.

Error and failure semantics:

- Use a stable error payload shape (e.g. code, message, detail) and sanitize detail; avoid exposing stack traces or internal paths.
- Partial results on mid-run failure: return 200 with status="failed", partial data (e.g. likes_per_turn), and an error object—reserve 500 for pre-creation or infrastructure failures so clients can rely on partial results when a run exists.

API layer vs core

- Apply defaults at the API boundary, not in shared models. Keep core/domain models (e.g. RunConfig) without default values; build them in the API layer (e.g. request DTO → service) and apply defaults there (e.g. DEFAULT_NUM_TURNS, DEFAULT_FEED_ALGORITHM) so core stays explicit and reusable. Core/domain models stay explicit: every field is required. No hidden defaults. Defaults are applied only when building those models, in the API layer (e.g. when turning a request DTO into a RunConfig). This means:
  - Core stays reusable: CLI, API, and tests can each choose their own defaults (or none)
  - Core stays obvious: reading RunConfig tells you exactly what must be provided.
  - Defaults live in one place: the API (or whatever layer builds the config).

Fixed sets of values (e.g. status, type, kind):

- Use a str-backed enum (e.g. class RunResponseStatus(str, Enum)) when the same set is used in more than one place (schemas, services, routes) or you want a single shared type and stable OpenAPI; JSON then stays string values.
- Use a Pydantic model or discriminated union when each value has different required fields.
- Prefer enum over Literal when the type is shared and reused; Literal is fine for a one-off field in a single schema.

Deterministic outputs:

- Principle: Functions and API responses should be deterministic and repeatable when given the same inputs and config; avoid order-dependent or undefined ordering in results.
- When a function returns a list (or list-derived result) and input order is not guaranteed, sort by a domain-natural key (e.g. turn_number, created_at, id) before building the result.
- For API and serialized data, treat ordering as part of the contract unless otherwise specified: document or enforce it (e.g. “ordered by turn_number ascending”) so clients get stable, repeatable results.

Response schema consistency:

- For response fields that depend on each other (e.g. status and error), use a shared enum for the discriminating field and a Pydantic @model_validator(mode="after") to enforce the invariant (e.g. when status is "failed", error must be set; when "completed", error must be None) so invalid combinations are rejected at the boundary.

Validation helpers

- Use shared validation helpers instead of inline checks. Put common validators
  (e.g. non-empty string) in a central module (e.g. lib/validation_utils.py) and
  reuse. Avoid duplicating patterns like `if not v or not v.strip(): raise ValueError(...)`.
- Before adding a one-off check: Look for the same pattern elsewhere and centralize (e.g. “value in allowed set” → validate_value_in_set).

Registries and swappable implementations

- For swappable implementations (e.g. behavior policies, algorithms), prefer a
  central registry as the single source of truth. Avoid per-component registries
  that duplicate mode/config logic.

Fields and parameters

- For fields that describe "why" or "how" something was chosen (e.g. reasoning
  for an action), use implementation-neutral names (e.g. `explanation` instead of
  `ai_reason`) so the field is accurate for deterministic, LLM, and other
  policies.
- Do not add fields or params that aren't explicitly used, unless told to explicitly by the user.

Logging and observability

- Prefer centralized logging infra (one format, request identity, shared helpers) and let each layer (API, engine) add its own middleware or decorators that call that infra.
- Use structured request logging with correlation (e.g. request_id, and where relevant run_id) so logs are parseable and traceable.
Put timing in a single, reusable decorator (e.g. in lib/decorators.py) used by both API and core; avoid duplicate timing logic in multiple places.
- Observability must not hide real failures: best-effort behavior (e.g. attaching duration to request.state) should be wrapped in a narrow try/except; log the error (e.g. with logger.warning and context like attach_attr, func.__qualname__) and continue, so the wrapped function’s exception is never replaced.

Consolidation over duplication

- Prefer one implementation per concern. When replacing an older pattern (e.g. a decorator), migrate existing callers to the new one and remove the old; avoid keeping two near-equivalents.
- When renaming or replacing: prefer the clearer, long-term name and update call sites (e.g. timed instead of extending record_runtime with more options).

Package management — Use uv for Python; don’t use pip.

Decorators

- Use decorators for (1) extending generic functionality across multiple callers (e.g., adding custom retry logic) or (2) removing boilerplate code shared across multiple callers (e.g., doing input validation).
