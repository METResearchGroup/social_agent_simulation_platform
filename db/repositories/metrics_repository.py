"""SQLite implementation of metrics repository."""

from __future__ import annotations

from db.adapters.base import MetricsDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import MetricsRepository
from simulation.core.models.metrics import RunMetrics, TurnMetrics


class SQLiteMetricsRepository(MetricsRepository):
    """SQLite implementation of MetricsRepository."""

    def __init__(
        self,
        *,
        db_adapter: MetricsDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_turn_metrics(
        self,
        turn_metrics: TurnMetrics,
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_turn_metrics(turn_metrics, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_turn_metrics(turn_metrics, conn=c)

    def get_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_turn_metrics(run_id, turn_number, conn=c)

    def list_turn_metrics(self, run_id: str) -> list[TurnMetrics]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_turn_metrics_for_run(run_id, conn=c)

    def write_run_metrics(
        self,
        run_metrics: RunMetrics,
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_run_metrics(run_metrics, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_run_metrics(run_metrics, conn=c)

    def get_run_metrics(self, run_id: str) -> RunMetrics | None:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_run_metrics(run_id, conn=c)


def create_sqlite_metrics_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteMetricsRepository:
    from db.adapters.sqlite.metrics_adapter import SQLiteMetricsAdapter

    return SQLiteMetricsRepository(
        db_adapter=SQLiteMetricsAdapter(),
        transaction_provider=transaction_provider,
    )
