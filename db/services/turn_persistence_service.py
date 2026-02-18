"""Turn persistence: write turn metadata and turn metrics in a single transaction."""

from db.adapters.sqlite.sqlite import run_transaction
from db.repositories.interfaces import MetricsRepository, RunRepository
from simulation.core.models.metrics import TurnMetrics
from simulation.core.models.turns import TurnMetadata


def create_turn_persistence_service(
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
) -> "TurnPersistenceService":
    """Create a TurnPersistenceService with the given repositories."""
    return TurnPersistenceService(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
    )


class TurnPersistenceService:
    """Writes turn metadata and turn metrics in one transaction (all-or-nothing per turn)."""

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
