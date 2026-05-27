"""Compare validated proposed actions against golden fixture labels."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ValidationError

from simulation_v2.db.models.actions import ProposedActionRecord
from simulation_v2.db.models.evals import EvalScope
from simulation_v2.evals.fixtures.models import GoldenCase, load_golden_fixture
from simulation_v2.evals.interfaces import EvalContext, EvalMetricDraft, EvalResult
from simulation_v2.evals.query_helpers import load_proposed_actions


class PrecisionRecallF1Metrics(BaseModel):
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def compute_precision_recall_f1(
    predicted: set[str], expected: set[str]
) -> PrecisionRecallF1Metrics:
    """Compute precision, recall, and F1 from predicted and expected string sets.

    Treats set membership as binary classification: true positives are items in
    both sets; false positives are predicted-only; false negatives are expected-only.
    """
    true_positives = len(predicted & expected)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PrecisionRecallF1Metrics(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def _normalize_topic(value: str) -> str:
    """Normalize a write topic for case-insensitive golden-label comparison."""
    return value.strip().lower()


class GoldenDatasetPlugin:
    name: ClassVar[str] = "golden_dataset"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn"})

    def __init__(self, fixture_path: Path | None = None) -> None:
        """Optionally override the default golden fixture JSON path (for tests)."""
        self._fixture_path = fixture_path

    def run(self, context: EvalContext) -> EvalResult:
        """Load the golden fixture and score validated proposed actions per labeled case."""
        try:
            fixture = load_golden_fixture(self._fixture_path)
        except (OSError, ValidationError, ValueError) as exc:
            return EvalResult(
                plugin_name=self.name,
                status="failed",
                metrics=[],
                warnings=[f"failed to load golden fixture: {exc}"],
            )

        run_user_ids = {
            user.user_id
            for user in context.repos.list_users_for_run(context.run_id, context.conn)
        }
        proposed = load_proposed_actions(context)
        validated_by_user: dict[str, list[ProposedActionRecord]] = defaultdict(list)
        for action in proposed:
            if action.record_kind != "validated":
                continue
            validated_by_user[action.user_id].append(action)

        metrics: list[EvalMetricDraft] = []
        warnings: list[str] = []
        cases_evaluated = 0
        cases_skipped = 0
        labels_skipped = 0
        f1_by_label_type: dict[str, list[float]] = defaultdict(list)

        for case in fixture.cases:
            if case.user_id not in run_user_ids:
                cases_skipped += 1
                continue

            cases_evaluated += 1
            user_actions = validated_by_user.get(case.user_id, [])
            case_metrics, case_warnings, case_labels_skipped = _evaluate_case(
                case, user_actions
            )
            metrics.extend(case_metrics)
            warnings.extend(case_warnings)
            labels_skipped += case_labels_skipped

            for metric in case_metrics:
                if metric.metric_name != "f1":
                    continue
                label_type = (metric.metadata_json or {}).get("label_type")
                if label_type:
                    f1_by_label_type[str(label_type)].append(metric.metric_value)

        for label_type, f1_values in sorted(f1_by_label_type.items()):
            macro_f1 = sum(f1_values) / len(f1_values)
            metrics.append(
                EvalMetricDraft(
                    metric_name="f1",
                    metric_value=macro_f1,
                    metadata_json={"label_type": label_type, "aggregate": "macro"},
                )
            )

        for metric_name, value in (
            ("cases_evaluated", float(cases_evaluated)),
            ("cases_skipped", float(cases_skipped)),
            ("labels_skipped", float(labels_skipped)),
        ):
            metrics.append(EvalMetricDraft(metric_name=metric_name, metric_value=value))

        return EvalResult(
            plugin_name=self.name,
            status="passed",
            metrics=metrics,
            warnings=warnings,
        )


def _evaluate_case(
    case: GoldenCase, user_actions: list[ProposedActionRecord]
) -> tuple[list[EvalMetricDraft], list[str], int]:
    """Score one golden case against a user's validated actions for present label fields."""
    metrics: list[EvalMetricDraft] = []
    warnings: list[str] = []
    labels_skipped = 0
    fields_set = case.model_fields_set

    label_specs: list[tuple[str, str, set[str], set[str]]] = []

    if "expected_like_post_ids" in fields_set:
        predicted = {
            action.target_id
            for action in user_actions
            if action.action_type == "like_post" and action.target_id
        }
        expected = set(case.expected_like_post_ids or [])
        label_specs.append(("like", case.case_id, predicted, expected))
    else:
        labels_skipped += 1
        warnings.append(f"skipped label_type=like for case_id={case.case_id}")

    if "expected_follow_user_ids" in fields_set:
        predicted = {
            action.target_id
            for action in user_actions
            if action.action_type == "follow_user" and action.target_id
        }
        expected = set(case.expected_follow_user_ids or [])
        label_specs.append(("follow", case.case_id, predicted, expected))
    else:
        labels_skipped += 1
        warnings.append(f"skipped label_type=follow for case_id={case.case_id}")

    if "expected_write_topic" in fields_set:
        predicted_topic = next(
            (
                action.target_content or ""
                for action in user_actions
                if action.action_type == "write_post"
            ),
            "",
        )
        predicted = {_normalize_topic(predicted_topic)} if predicted_topic else set()
        expected_value = case.expected_write_topic or ""
        expected = {_normalize_topic(expected_value)} if expected_value else set()
        label_specs.append(("write_topic", case.case_id, predicted, expected))
    else:
        labels_skipped += 1
        warnings.append(f"skipped label_type=write_topic for case_id={case.case_id}")

    for label_type, case_id, predicted, expected in label_specs:
        scores = compute_precision_recall_f1(predicted, expected)
        metadata = {"label_type": label_type, "case_id": case_id}
        for metric_name, value in (
            ("precision", scores.precision),
            ("recall", scores.recall),
            ("f1", scores.f1),
            ("tp", float(scores.true_positives)),
            ("fp", float(scores.false_positives)),
            ("fn", float(scores.false_negatives)),
        ):
            metrics.append(
                EvalMetricDraft(
                    metric_name=metric_name,
                    metric_value=value,
                    metadata_json=metadata,
                )
            )

    return metrics, warnings, labels_skipped
