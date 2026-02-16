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

Prefer single or minimal public APIs. Default to private APIs that perform the implementation and expose one or two public API functions that do the composite task. The public API should appear first out of all the functions or classes, to then be followed by the private API functions. It should be in descending order of callers; the public API first, then the immediate private APIs called by the public API, then the private APIs called by only other private APIs.

Don't hardcode defaults or constants into functions inline. Define as file-level constants and then use them. This helps us keep track of hardcoded behaviors.

- Example: `feeds/feed_generator.py` exposes one public function, `generate_feeds`, which is the only function used by external callers. The actual functionality is largely managed by internal private functions.

Prefer keyword args.

Domain purity

- Domain models (simulation.core.models) depend only on stdlib, pydantic, and same-layer models. No imports from lib, db, feeds, or ai. Time and I/O are supplied by callers (e.g. created_at parameter) or live in the application layer.

Imports:

- Use absolute imports (e.g., import path.to.module) instead of relative imports (e.g., import .module)

Type annotations:

- Use | instead of "Optional" or "Union" for typing.
- When creating a variable as the result of a function, always include the type annotation in the variable definition.

API design and rollout

- Prefer sync endpoints first to lock in behavior and contracts; add async/job-based APIs later for concurrency and scale.

Per-commit:

- Run all pre-commit hooks.
- Follow ci.yml and run those commands (e.g., "ruff", "uv run pytest") and fix errors as needed.
- ALWAYS run `uv run pre-commit run --all-files` after completing a batch of commitable work or after completing a TODO item.

Testing:

- In addition to unit tests, add throwaway end-to-end tests to verify functionality. Ask the user if they want these end-to-end tests to be persisted, and if they want to mock I/O or use real I/O.
