from __future__ import annotations

import json
from pathlib import Path

from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnMetadata


def read_json_list(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"Fixture must be a JSON array: {path}")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"Fixture array must contain objects: {path}")
    return data  # type: ignore[return-value]


def parse_runs_and_turn_metadata(
    fixtures_dir: Path,
) -> tuple[list[Run], list[TurnMetadata]]:
    runs_raw = read_json_list(fixtures_dir / "runs.json")
    turn_md_raw = read_json_list(fixtures_dir / "turn_metadata.json")

    runs = [Run.model_validate(item) for item in runs_raw]
    turn_metadata: list[TurnMetadata] = []
    for item in turn_md_raw:
        raw_total_actions = item.get("total_actions", {})
        if not isinstance(raw_total_actions, dict):
            raise ValueError("turn_metadata.total_actions must be an object")
        total_actions = {TurnAction(k): int(v) for k, v in raw_total_actions.items()}
        turn_metadata.append(
            TurnMetadata(
                run_id=str(item["run_id"]),
                turn_number=int(item["turn_number"]),
                total_actions=total_actions,
                created_at=str(item["created_at"]),
            )
        )
    return runs, turn_metadata


def read_seed_metrics(fixtures_dir: Path) -> tuple[list[TurnMetrics], list[RunMetrics]]:
    turn_metrics_raw = read_json_list(fixtures_dir / "turn_metrics.json")
    run_metrics_raw = read_json_list(fixtures_dir / "run_metrics.json")
    return (
        [TurnMetrics.model_validate(item) for item in turn_metrics_raw],
        [RunMetrics.model_validate(item) for item in run_metrics_raw],
    )


def _stable_turn_metrics(turn_metrics: list[TurnMetrics]) -> list[TurnMetrics]:
    return sorted(turn_metrics, key=lambda tm: (tm.run_id, tm.turn_number))


def _stable_run_metrics(run_metrics: list[RunMetrics]) -> list[RunMetrics]:
    return sorted(run_metrics, key=lambda rm: rm.run_id)


def metrics_payloads(
    turn_metrics: list[TurnMetrics], run_metrics: list[RunMetrics]
) -> tuple[list[dict], list[dict]]:
    return (
        [tm.model_dump(mode="json") for tm in _stable_turn_metrics(turn_metrics)],
        [rm.model_dump(mode="json") for rm in _stable_run_metrics(run_metrics)],
    )
