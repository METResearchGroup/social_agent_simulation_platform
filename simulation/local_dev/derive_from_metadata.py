"""Derive turn/run metrics from canonical `TurnMetadata` using the same registry as runtime.

Used by :mod:`simulation.local_dev.seed_loader` so metric rows are never hand-maintained
separately from ``turn_metadata`` fixtures.
"""

from __future__ import annotations

from collections import defaultdict

from db.repositories.interfaces import MetricsRepository, RunRepository
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import (
    create_default_metrics_registry,
    resolve_metric_keys_by_scope,
)
from simulation.core.metrics.interfaces import MetricDeps
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata


def _unexpected_metrics_repo_call(method: str) -> RuntimeError:
    return RuntimeError(
        f"metrics_repo.{method} must not be called during seed metric derivation "
        "(builtin metrics use run_repo only)"
    )


class _SeedDerivationMetricsRepositoryStub(MetricsRepository):
    """Explicit stub: builtin turn/run metrics here never read or write persisted metrics."""

    def write_turn_metrics(
        self,
        turn_metrics: TurnMetrics,
        conn: object | None = None,
    ) -> None:
        _ = (turn_metrics, conn)
        raise _unexpected_metrics_repo_call("write_turn_metrics")

    def get_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        _ = (run_id, turn_number)
        raise _unexpected_metrics_repo_call("get_turn_metrics")

    def list_turn_metrics(self, run_id: str) -> list[TurnMetrics]:
        _ = run_id
        raise _unexpected_metrics_repo_call("list_turn_metrics")

    def write_run_metrics(
        self,
        run_metrics: RunMetrics,
        conn: object | None = None,
    ) -> None:
        _ = (run_metrics, conn)
        raise _unexpected_metrics_repo_call("write_run_metrics")

    def get_run_metrics(self, run_id: str) -> RunMetrics | None:
        _ = run_id
        raise _unexpected_metrics_repo_call("get_run_metrics")


_METRICS_REPO_FOR_SEED_DERIVATION: MetricsRepository = (
    _SeedDerivationMetricsRepositoryStub()
)


class _FixtureRunRepository(RunRepository):
    """Minimal in-memory `RunRepository` for metric collection only."""

    def __init__(
        self,
        *,
        runs: dict[str, Run],
        turn_metadata_by_run: dict[str, list[TurnMetadata]],
    ) -> None:
        self._runs = runs
        self._turn_metadata_by_run = {
            rid: sorted(tms, key=lambda t: t.turn_number)
            for rid, tms in turn_metadata_by_run.items()
        }

    def create_run(
        self, config: RunConfig, created_by_app_user_id: str | None = None
    ) -> Run:
        raise NotImplementedError

    def get_run(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[Run]:
        return list(self._runs.values())

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        conn: object | None = None,
    ) -> None:
        raise NotImplementedError

    def get_turn_metadata(self, run_id: str, turn_number: int) -> TurnMetadata | None:
        for tm in self._turn_metadata_by_run.get(run_id, []):
            if tm.turn_number == turn_number:
                return tm
        return None

    def list_turn_metadata(self, run_id: str) -> list[TurnMetadata]:
        return list(self._turn_metadata_by_run.get(run_id, []))

    def write_turn_metadata(
        self,
        turn_metadata: TurnMetadata,
        conn: object | None = None,
    ) -> None:
        raise NotImplementedError


def derive_turn_and_run_metrics_from_fixtures(
    *,
    runs: list[Run],
    turn_metadata: list[TurnMetadata],
) -> tuple[list[TurnMetrics], list[RunMetrics]]:
    """Compute `TurnMetrics` / `RunMetrics` from `runs` + `turn_metadata` via the default registry."""
    runs_by_id = {r.run_id: r for r in runs}
    by_run: dict[str, list[TurnMetadata]] = defaultdict(list)
    for tm in turn_metadata:
        by_run[tm.run_id].append(tm)

    run_repo = _FixtureRunRepository(runs=runs_by_id, turn_metadata_by_run=dict(by_run))
    deps = MetricDeps(
        run_repo=run_repo,
        metrics_repo=_METRICS_REPO_FOR_SEED_DERIVATION,
        sql_executor=None,
        pending_turn_metadata=None,
    )
    registry = create_default_metrics_registry()
    collector = MetricsCollector(
        registry=registry,
        turn_metric_keys=[],
        run_metric_keys=[],
        deps=deps,
    )

    turn_out: list[TurnMetrics] = []
    run_out: list[RunMetrics] = []

    for run in runs:
        turn_keys, run_keys = resolve_metric_keys_by_scope(run.metric_keys)
        for tm in sorted(by_run.get(run.run_id, []), key=lambda t: t.turn_number):
            computed = collector.collect_turn_metrics(
                run_id=run.run_id,
                turn_number=tm.turn_number,
                turn_metric_keys=turn_keys,
                turn_metadata=tm,
            )
            turn_out.append(
                TurnMetrics(
                    run_id=tm.run_id,
                    turn_number=tm.turn_number,
                    metrics=computed,
                    created_at=tm.created_at,
                )
            )

        if not by_run.get(run.run_id):
            continue

        run_computed = collector.collect_run_metrics(
            run_id=run.run_id,
            run_metric_keys=run_keys,
        )
        created_at = run.completed_at or run.started_at
        run_out.append(
            RunMetrics(
                run_id=run.run_id,
                metrics=run_computed,
                created_at=created_at,
            )
        )

    return turn_out, run_out
