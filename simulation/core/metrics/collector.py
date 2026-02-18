from __future__ import annotations

from collections import defaultdict, deque

from simulation.core.exceptions import MetricsComputationError
from simulation.core.metrics.interfaces import MetricContext, MetricDeps, MetricScope
from simulation.core.metrics.registry import MetricsRegistry
from simulation.core.models.json_types import JsonObject, JsonValue


class MetricsCollector:
    def __init__(
        self,
        *,
        registry: MetricsRegistry,
        turn_metric_keys: list[str],
        run_metric_keys: list[str],
        deps: MetricDeps,
    ):
        self._registry = registry
        self._turn_metric_keys = list(turn_metric_keys)
        self._run_metric_keys = list(run_metric_keys)
        self._deps = deps

    def collect_turn_metrics(self, *, run_id: str, turn_number: int) -> JsonObject:
        ctx = MetricContext(run_id=run_id, turn_number=turn_number)
        metric_keys = self._turn_metric_keys
        return self._collect(scope=MetricScope.TURN, metric_keys=metric_keys, ctx=ctx)

    def collect_run_metrics(self, *, run_id: str) -> JsonObject:
        ctx = MetricContext(run_id=run_id, turn_number=None)
        metric_keys = self._run_metric_keys
        return self._collect(scope=MetricScope.RUN, metric_keys=metric_keys, ctx=ctx)

    def _collect(
        self,
        *,
        scope: MetricScope,
        metric_keys: list[str],
        ctx: MetricContext,
    ) -> JsonObject:
        ordered_keys = self._resolve_order(scope=scope, metric_keys=metric_keys)

        results: JsonObject = {}
        for key in ordered_keys:
            metric = self._registry.get(metric_key=key)
            try:
                value: JsonValue = metric.compute(
                    ctx=ctx, deps=self._deps, prior=results
                )
            except Exception as e:
                raise MetricsComputationError(
                    metric_key=key,
                    run_id=ctx.run_id,
                    turn_number=ctx.turn_number,
                    message=f"Failed to compute metric '{key}': {e}",
                    cause=e,
                ) from e
            results[key] = value
        return results

    def _resolve_order(
        self, *, scope: MetricScope, metric_keys: list[str]
    ) -> list[str]:
        # Compute closure over dependencies, then stable topological order.
        requested_keys = list(metric_keys)
        all_keys: set[str] = set()
        required_by: dict[str, set[str]] = defaultdict(set)
        requires_of: dict[str, set[str]] = defaultdict(set)

        queue = deque(sorted(set(requested_keys)))
        while queue:
            key = queue.popleft()
            if key in all_keys:
                continue

            metric = self._registry.get(metric_key=key)
            if metric.scope != scope:
                raise ValueError(
                    f"Metric '{key}' has scope '{metric.scope.value}', expected '{scope.value}'"
                )

            all_keys.add(key)
            for dep in metric.requires:
                required_by[dep].add(key)
                requires_of[key].add(dep)
                if dep not in all_keys:
                    queue.append(dep)

        indegree: dict[str, int] = {k: len(requires_of[k]) for k in all_keys}
        ready = [k for k, d in indegree.items() if d == 0]
        ready.sort()

        ordered: list[str] = []
        while ready:
            key = ready.pop(0)
            ordered.append(key)
            for dependent in sorted(required_by.get(key, set())):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()

        if len(ordered) != len(all_keys):
            missing = sorted(all_keys - set(ordered))
            raise ValueError(f"Metric dependency cycle or missing node: {missing}")

        # Return only metrics requested explicitly or needed as dependencies, but in order.
        return ordered
