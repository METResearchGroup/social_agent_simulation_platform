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

- Example: `feeds/feed_generator.py` exposes one public function, `generate_feeds`, which is the only function used by external callers. The actual functionality is largely managed by internal private functions.

Prefer keyword args.

Domain purity

- Domain models (simulation.core.models) depend only on stdlib, pydantic, and same-layer models. No imports from lib, db, feeds, or ai. Time and I/O are supplied by callers (e.g. created_at parameter) or live in the application layer.

Imports:

- Use absolute imports (e.g., import path.to.module) instead of relative imports (e.g., import .module)

Type annotations:

- Use | instead of "Optional" for typing
