"""Simulation persistence: turn and run metrics in transactions or single writes."""

from __future__ import annotations

from db.adapters.base import TransactionProvider
from db.repositories.interfaces import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
    MetricsRepository,
    RunRepository,
)
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import RunStatus
from simulation.core.models.turns import TurnMetadata


def create_simulation_persistence_service(
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
    *,
    transaction_provider: TransactionProvider,
    like_repo: LikeRepository | None = None,
    comment_repo: CommentRepository | None = None,
    follow_repo: FollowRepository | None = None,
) -> SimulationPersistenceService:
    """Create a SimulationPersistenceService with the given repositories and transaction provider."""
    return SimulationPersistenceService(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        transaction_provider=transaction_provider,
        like_repo=like_repo,
        comment_repo=comment_repo,
        follow_repo=follow_repo,
    )


class SimulationPersistenceService:
    """Persists turn data (metadata + metrics + actions in one transaction) and run completion."""

    def __init__(
        self,
        *,
        run_repo: RunRepository,
        metrics_repo: MetricsRepository,
        transaction_provider: TransactionProvider,
        like_repo: LikeRepository | None = None,
        comment_repo: CommentRepository | None = None,
        follow_repo: FollowRepository | None = None,
    ):
        self._run_repo = run_repo
        self._metrics_repo = metrics_repo
        self._transaction_provider = transaction_provider
        self._like_repo = like_repo
        self._comment_repo = comment_repo
        self._follow_repo = follow_repo

    def write_turn(
        self,
        turn_metadata: TurnMetadata,
        turn_metrics: TurnMetrics,
        *,
        likes: list[GeneratedLike] | None = None,
        comments: list[GeneratedComment] | None = None,
        follows: list[GeneratedFollow] | None = None,
    ) -> None:
        """Persist one turn: metadata, metrics, and optional actions in a single transaction.

        On any exception (duplicate, DB error, etc.) the transaction is rolled back;
        no partial turn is persisted.
        """
        run_id = turn_metadata.run_id
        turn_number = turn_metadata.turn_number
        with self._transaction_provider.run_transaction() as conn:
            self._run_repo.write_turn_metadata(turn_metadata, conn=conn)
            self._metrics_repo.write_turn_metrics(turn_metrics, conn=conn)
            if self._like_repo is not None and likes:
                self._like_repo.write_likes(run_id, turn_number, likes, conn=conn)
            if self._comment_repo is not None and comments:
                self._comment_repo.write_comments(
                    run_id, turn_number, comments, conn=conn
                )
            if self._follow_repo is not None and follows:
                self._follow_repo.write_follows(run_id, turn_number, follows, conn=conn)

    def write_run(self, run_id: str, run_metrics: RunMetrics) -> None:
        """Persist run metrics and set run status to COMPLETED in a single transaction.

        On any exception the transaction is rolled back; no partial run completion.
        """
        with self._transaction_provider.run_transaction() as conn:
            self._metrics_repo.write_run_metrics(run_metrics, conn=conn)
            self._run_repo.update_run_status(run_id, RunStatus.COMPLETED, conn=conn)
