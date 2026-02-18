"""SQLite implementation of metrics repository."""

from __future__ import annotations

from db.adapters.base import MetricsDatabaseAdapter
from db.repositories.interfaces import MetricsRepository
from simulation.core.models.metrics import RunMetrics, TurnMetrics


class SQLiteMetricsRepository(MetricsRepository):
    """SQLite implementation of MetricsRepository."""

    def __init__(self, *, db_adapter: MetricsDatabaseAdapter):
        self._db_adapter = db_adapter

    def write_turn_metrics(
        self,
        turn_metrics: TurnMetrics,
        conn: object | None = None,
    ) -> None:
        self._db_adapter.write_turn_metrics(turn_metrics, conn=conn)

    def get_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        return self._db_adapter.read_turn_metrics(run_id, turn_number)

    def list_turn_metrics(self, run_id: str) -> list[TurnMetrics]:
        return self._db_adapter.read_turn_metrics_for_run(run_id)

    def write_run_metrics(
        self,
        run_metrics: RunMetrics,
        conn: object | None = None,
    ) -> None:
        self._db_adapter.write_run_metrics(run_metrics, conn=conn)

    def get_run_metrics(self, run_id: str) -> RunMetrics | None:
        return self._db_adapter.read_run_metrics(run_id)


def create_sqlite_metrics_repository() -> SQLiteMetricsRepository:
    from db.adapters.sqlite.metrics_adapter import SQLiteMetricsAdapter

    return SQLiteMetricsRepository(db_adapter=SQLiteMetricsAdapter())
