"""Compute rejected/proposed rates by action type and filter."""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from simulation_v2.db.models.evals import EvalScope
from simulation_v2.evals.interfaces import EvalContext, EvalMetricDraft, EvalResult
from simulation_v2.evals.query_helpers import load_proposed_actions


class InvalidActionRatePlugin:
    name: ClassVar[str] = "invalid_action_rate"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn", "run"})

    def run(self, context: EvalContext) -> EvalResult:
        proposed = load_proposed_actions(context)

        proposed_by_type: dict[str, int] = defaultdict(int)
        rejected_groups: dict[tuple[str, str | None, str | None], int] = defaultdict(
            int
        )

        for action in proposed:
            proposed_by_type[action.action_type] += 1
            if action.record_kind != "rejected":
                continue
            key = (
                action.action_type,
                action.filter_id,
                action.filter_reason,
            )
            rejected_groups[key] += 1

        metrics: list[EvalMetricDraft] = []
        for (action_type, filter_id, filter_reason), rejected_count in sorted(
            rejected_groups.items()
        ):
            proposed_count = proposed_by_type[action_type]
            rate = rejected_count / proposed_count if proposed_count > 0 else 0.0
            metadata = {
                "action_type": action_type,
                "filter_id": filter_id,
                "filter_reason": filter_reason,
            }
            for metric_name, value in (
                ("rate", rate),
                ("rejected_count", float(rejected_count)),
                ("proposed_count", float(proposed_count)),
            ):
                metrics.append(
                    EvalMetricDraft(
                        metric_name=metric_name,
                        metric_value=value,
                        metadata_json=metadata,
                    )
                )

        return EvalResult(
            plugin_name=self.name,
            status="passed",
            metrics=metrics,
        )
