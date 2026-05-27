"""Count proposed, accepted, rejected, and executed actions per action type."""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from simulation_v2.db.models.evals import EvalScope
from simulation_v2.evals.interfaces import EvalContext, EvalMetricDraft, EvalResult
from simulation_v2.evals.query_helpers import (
    count_executed_by_action_type,
    load_proposed_actions,
)


class ActionCountsPlugin:
    name: ClassVar[str] = "action_counts"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn", "run"})

    def run(self, context: EvalContext) -> EvalResult:
        proposed = load_proposed_actions(context)
        executed = count_executed_by_action_type(context)

        by_type_kind: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for action in proposed:
            by_type_kind[action.action_type][action.record_kind] += 1

        action_types = sorted(set(by_type_kind) | set(executed))
        metrics: list[EvalMetricDraft] = []
        warnings: list[str] = []

        for action_type in action_types:
            kinds = by_type_kind.get(action_type, {})
            proposed_count = sum(kinds.values())
            accepted = kinds.get("validated", 0)
            rejected = kinds.get("rejected", 0)
            executed_count = executed.get(action_type, 0)

            for metric_name, value in (
                ("proposed", proposed_count),
                ("accepted", accepted),
                ("rejected", rejected),
                ("executed", executed_count),
            ):
                metrics.append(
                    EvalMetricDraft(
                        metric_name=metric_name,
                        metric_value=float(value),
                        metadata_json={"action_type": action_type},
                    )
                )

            if accepted != executed_count:
                warnings.append(
                    f"{action_type}: accepted ({accepted}) != executed ({executed_count})"
                )

        status = "failed" if warnings else "passed"
        return EvalResult(
            plugin_name=self.name,
            status=status,
            metrics=metrics,
            warnings=warnings,
        )
