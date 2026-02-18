# How to Create a New Metric

To add a new metric, you only need to touch:

1. `simulation/core/metrics/builtins/<your_metric_file>.py` (create a new file or edit an existing one)
2. `simulation/core/metrics/defaults.py` (add the metric class to `BUILTIN_METRICS`)

Everything else (evaluation order, output validation, persistence) is handled by the framework.

## Step-by-step

### 1) Implement the metric (in `simulation/core/metrics/builtins/`)

Your metric class must define:

- `KEY = "turn.some.metric"` (or `"run.some.metric"`)
- `SCOPE = MetricScope.TURN` (or `MetricScope.RUN`)
- `output_adapter`: a `pydantic.TypeAdapter(...)` describing the output shape
- `compute(...) -> JsonValue`

Optional:

- `DEFAULT_ENABLED = False` to register the metric but keep it disabled by default.
- `requires = ("turn.some_dependency", ...)` if it depends on other metrics.

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
    KEY = "turn.my_metric.example"
    SCOPE = MetricScope.TURN
    DEFAULT_ENABLED = True

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

## Register the metric (in `simulation/core/metrics/defaults.py`)

Add your metric class to `BUILTIN_METRICS`.

## Running checks locally

From repo root:

```bash
uv run pytest
uv run --extra test pre-commit run --all-files
```

## Common pitfalls

- **Forgetting `KEY` / `SCOPE`**: metrics must declare these class constants; missing them fails fast at import time.
- **Forgetting `output_adapter`**: the metric won’t satisfy the `Metric` ABC and will fail at import/instantiation time.
- **Returning non-JSON values**: e.g. `set(...)`, custom objects, bytes → collector will reject.
- **Implicit coercion**: collector validation uses `strict=True`, so return the right types.
- **Scope mismatches**: a RUN metric can’t depend on a TURN metric (and vice versa) unless you split the computation or change the data source.
