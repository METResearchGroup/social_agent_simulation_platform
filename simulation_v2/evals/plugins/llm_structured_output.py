"""Report LLM generation outcomes by action type and status."""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from simulation_v2.db.models.evals import EvalScope
from simulation_v2.evals.interfaces import EvalContext, EvalMetricDraft, EvalResult
from simulation_v2.evals.query_helpers import load_generations


class LlmStructuredOutputPlugin:
    name: ClassVar[str] = "llm_structured_output"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn", "run"})

    def run(self, context: EvalContext) -> EvalResult:
        generations = load_generations(context)

        by_type_status: dict[tuple[str, str], int] = defaultdict(int)
        by_type_total: dict[str, int] = defaultdict(int)
        by_type_completed: dict[str, int] = defaultdict(int)

        for generation in generations:
            key = (generation.action_type, generation.status)
            by_type_status[key] += 1
            by_type_total[generation.action_type] += 1
            if generation.status == "completed":
                by_type_completed[generation.action_type] += 1

        metrics: list[EvalMetricDraft] = []
        for (action_type, status), count in sorted(by_type_status.items()):
            metrics.append(
                EvalMetricDraft(
                    metric_name="generation_count",
                    metric_value=float(count),
                    metadata_json={
                        "action_type": action_type,
                        "status": status,
                    },
                )
            )

        for action_type in sorted(by_type_total):
            total = by_type_total[action_type]
            completed = by_type_completed[action_type]
            success_rate = completed / total if total > 0 else 0.0
            metrics.append(
                EvalMetricDraft(
                    metric_name="success_rate",
                    metric_value=success_rate,
                    metadata_json={"action_type": action_type},
                )
            )

        return EvalResult(
            plugin_name=self.name,
            status="passed",
            metrics=metrics,
        )
