# How to Create a New Metric

This runbook describes how to add a new metric to the simulation metrics framework, including **where code goes**, how to **define a metric contract** via `output_adapter`, and how to **register + test** it.

## Overview (what a “metric” is here)

- A metric is a small unit of computation that returns a **JSON value** (`JsonValue`) and is stored/returned in a **JSON object** (`JsonObject`) keyed by metric key.
- Metrics are computed by `MetricsCollector`, which:
  - computes metrics in dependency order
  - validates each metric’s output against a per-metric Pydantic adapter
  - stores **only validated** values

## Where to put code

- **Interface**: `simulation/core/metrics/interfaces.py`
  - `Metric` is the abstract base class.
  - `MetricContext` and `MetricDeps` define runtime inputs.
- **Built-in metrics**: `simulation/core/metrics/builtins/`
  - Example: `simulation/core/metrics/builtins/actions.py`
- **Registry wiring / defaults**:
  - `simulation/core/metrics/registry.py` (registry container)
  - `simulation/core/metrics/defaults.py` (default metric keys + default registry builder)
- **Collector**: `simulation/core/metrics/collector.py`
  - Validates your metric output and wraps failures as `MetricsComputationError`.
- **Tests**: `tests/simulation/core/test_metrics_collector.py` (collector behavior + schema validation)

## Step-by-step: implement a metric

### 1) Choose a metric key and scope

Metric keys are strings (examples: `turn.actions.total`, `run.actions.total_by_type`).

- Use `MetricScope.TURN` when the metric is per-turn and requires `turn_number`.
- Use `MetricScope.RUN` when the metric is aggregated across the whole run.

### 2) Define an output schema (`output_adapter`)

Every metric must declare an `output_adapter` describing the metric’s output shape.
In practice, this should be a file-level `pydantic.TypeAdapter(...)` constant.

Example output shapes:

- `TypeAdapter(int)`
- `TypeAdapter(dict[str, int])`
- `TypeAdapter(list[float])`

Notes:

- The collector validates with `strict=True`, so you should return the *correct* types (don’t rely on coercion).
- The collector also enforces that the post-validation value is a valid `JsonValue` (JSON-serializable).

### 3) Implement `compute(...)`

Your `compute(...)` must return a `JsonValue`.

Inputs:

- `ctx: MetricContext`
  - `ctx.run_id` is always set
  - `ctx.turn_number` is only set for turn metrics (run metrics will have `None`)
- `deps: MetricDeps`
  - `deps.run_repo` and `deps.metrics_repo` are always available
  - `deps.sql_executor` may be `None` (only use it when you explicitly build a collector with one)
- `prior: JsonObject`
  - a dict of already-computed metric outputs keyed by metric key
  - **important**: `prior` contains *validated* outputs from dependencies

### 4) Declare dependencies via `requires`

If your metric depends on other metrics, declare them:

- `requires` returns a tuple of metric keys
- The collector will compute dependencies first and provide them in `prior`

### 5) Use file-level constants

Follow repo convention (`docs/RULES.md`): keep adapters and constants as file-level constants under imports, not inline inside methods.

## Example template (copy/paste)

```python
from __future__ import annotations

from pydantic import TypeAdapter

from simulation.core.metrics.interfaces import (
    Metric,
    MetricContext,
    MetricDeps,
    MetricScope,
)
from simulation.core.models.json_types import JsonObject, JsonValue

MY_METRIC_OUTPUT_ADAPTER = TypeAdapter(dict[str, int])


class MyMetric(Metric):
    @property
    def key(self) -> str:
        return "turn.my_metric.example"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.TURN

    @property
    def output_adapter(self):
        return MY_METRIC_OUTPUT_ADAPTER

    @property
    def requires(self) -> tuple[str, ...]:
        return ("turn.some_dependency",)

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        if ctx.turn_number is None:
            raise ValueError("turn_number is required for turn metrics")

        dep_value = prior["turn.some_dependency"]
        # dep_value has already been validated by its metric adapter
        # (you may still narrow/cast locally for static type-checkers if needed)

        return {"foo": 1}
```

## What the output looks like (turn vs run)

The collector returns a single `JsonObject` where:

- keys are **metric keys** (e.g. `"turn.my_metric.example"`)
- values are the metric outputs (validated by `output_adapter`)

### Turn metric output (per turn)

If you register `MyMetric` from the template above and it runs for turn 0, the computed metrics dict for that turn will look like:

```json
{
  "turn.some_dependency": 123,
  "turn.my_metric.example": { "foo": 1 }
}
```

Notes:

- Your metric’s output is **nested under its key**; the output itself is the value (`{ "foo": 1 }`).
- Dependency metrics appear in the same dict because the collector computes the dependency closure.

This dict is what ends up as `TurnMetrics.metrics` for that turn.

### Run metric output (once per run)

Run metrics use the same shape: a `JsonObject` keyed by metric key, computed once per run.

Example run metrics dict:

```json
{
  "run.some_metric.example": 42
}
```

This dict is what ends up as `RunMetrics.metrics` for the run.

## Register the metric so it runs

### 1) Add it to the default registry

Update `simulation/core/metrics/defaults.py`:

- Add a builder mapping in `create_default_metrics_registry()`
- Decide whether it belongs in:
  - `DEFAULT_TURN_METRIC_KEYS`
  - `DEFAULT_RUN_METRIC_KEYS`

Rules of thumb:

- If a metric should be present in all runs by default, add it to the appropriate `DEFAULT_*_METRIC_KEYS`.
- If it’s experimental / optional, wire it into the registry mapping but don’t add to defaults until you’re ready.

### 2) (Optional) Integrate with SQL-backed metrics

If your metric needs SQL, prefer providing parameterized SQL and params through `deps.sql_executor` (if available).

- If `deps.sql_executor` is `None`, raise a clear error (don’t silently skip).

## Testing requirements

At minimum:

- **Unit tests** for:
  - correct dependency ordering (if you use `requires`)
  - schema validation failures (wrong type/shape)
  - happy path output is JSON-serializable

Suggested place:

- `tests/simulation/core/test_metrics_collector.py`

## Running checks locally

From repo root:

```bash
uv run pytest
uv run --extra test pre-commit run --all-files
```

If you only want to run the collector tests:

```bash
uv run pytest tests/simulation/core/test_metrics_collector.py
```

## Common pitfalls

- **Forgetting `output_adapter`**: the metric won’t satisfy the `Metric` ABC and will fail at import/instantiation time.
- **Returning non-JSON values**: e.g. `set(...)`, custom objects, bytes → collector will reject.
- **Implicit coercion**: collector validation uses `strict=True`, so return the right types.
- **Scope mismatches**: a RUN metric can’t depend on a TURN metric (and vice versa) unless you split the computation or change the data source.
