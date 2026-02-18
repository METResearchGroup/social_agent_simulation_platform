"""Simulation persistence: turn and run metrics in transactions or single writes."""

from db.adapters.sqlite.sqlite import run_transaction
from db.repositories.interfaces import MetricsRepository, RunRepository
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import RunStatus
from simulation.core.models.turns import TurnMetadata


def create_simulation_persistence_service(
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
) -> "SimulationPersistenceService":
    """Create a SimulationPersistenceService with the given repositories."""
    return SimulationPersistenceService(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
    )


class SimulationPersistenceService:
    """Persists turn data (metadata + metrics in one transaction) and run completion (metrics + status in one transaction)."""

    def __init__(
        self,
        *,
        run_repo: RunRepository,
        metrics_repo: MetricsRepository,
    ):
        self._run_repo = run_repo
        self._metrics_repo = metrics_repo

    def write_turn(
        self,
        turn_metadata: TurnMetadata,
        turn_metrics: TurnMetrics,
    ) -> None:
        """Persist one turn: metadata and metrics in a single transaction.

        On any exception (duplicate, DB error, etc.) the transaction is rolled back;
        no partial turn is persisted.
        """
        with run_transaction() as conn:
            self._run_repo.write_turn_metadata(turn_metadata, conn=conn)
            self._metrics_repo.write_turn_metrics(turn_metrics, conn=conn)

    def write_run(self, run_id: str, run_metrics: RunMetrics) -> None:
        """Persist run metrics and set run status to COMPLETED in a single transaction.

        On any exception the transaction is rolled back; no partial run completion.
        """
        with run_transaction() as conn:
            self._metrics_repo.write_run_metrics(run_metrics, conn=conn)
            self._run_repo.update_run_status(run_id, RunStatus.COMPLETED, conn=conn)
