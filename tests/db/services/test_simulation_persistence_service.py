"""Tests for SimulationPersistenceService."""

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from db.repositories.interfaces import FollowRepository
from db.services.simulation_persistence_service import (
    SimulationPersistenceService,
    create_simulation_persistence_service,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.persisted_actions import PersistedFollow
from simulation.core.models.runs import RunStatus
from tests.factories import (
    GeneratedCommentFactory,
    GeneratedFeedFactory,
    GeneratedFollowFactory,
    GeneratedLikeFactory,
    RunConfigFactory,
    RunMetricsFactory,
    TurnMetadataFactory,
    TurnMetricsFactory,
)


@pytest.fixture
def mock_run_repo():
    return Mock()


@pytest.fixture
def mock_metrics_repo():
    return Mock()


@pytest.fixture
def mock_transaction_provider():
    """TransactionProvider that yields a single mock conn so both repos receive the same conn."""

    class MockTransactionProvider:
        @contextmanager
        def run_transaction(self):
            conn = Mock()
            yield conn

    return MockTransactionProvider()


@pytest.fixture
def mock_like_repo():
    return Mock()


@pytest.fixture
def mock_comment_repo():
    return Mock()


@pytest.fixture
def mock_follow_repo():
    return Mock()


@pytest.fixture
def mock_generated_feed_repo():
    return Mock()


@pytest.fixture
def sample_turn_metadata():
    return TurnMetadataFactory.create(
        run_id="run_1",
        turn_number=0,
        total_actions={
            TurnAction.LIKE: 1,
            TurnAction.COMMENT: 0,
            TurnAction.FOLLOW: 0,
        },
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture
def sample_turn_metrics():
    return TurnMetricsFactory.create(
        run_id="run_1",
        turn_number=0,
        metrics={"turn.actions.total": 1},
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture
def sample_run_metrics():
    return RunMetricsFactory.create(
        run_id="run_1",
        metrics={"run.actions.total": 10},
        created_at="2026-01-01T00:00:00",
    )


class TestCreateSimulationPersistenceService:
    def test_returns_simulation_persistence_service(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
    ):
        service = create_simulation_persistence_service(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        assert isinstance(service, SimulationPersistenceService)


class TestSimulationPersistenceServiceWriteTurn:
    def test_calls_both_repos_with_same_conn(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        """When write_turn is called, both write_turn_metadata and write_turn_metrics receive the same conn."""
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_turn(
            turn_metadata=sample_turn_metadata,
            turn_metrics=sample_turn_metrics,
        )
        assert mock_run_repo.write_turn_metadata.called
        assert mock_metrics_repo.write_turn_metrics.called
        call_metadata = mock_run_repo.write_turn_metadata.call_args
        call_metrics = mock_metrics_repo.write_turn_metrics.call_args
        assert call_metadata.kwargs.get("conn") is not None
        assert call_metrics.kwargs.get("conn") is not None
        assert call_metadata.kwargs["conn"] is call_metrics.kwargs["conn"]

    def test_passes_metadata_and_metrics_to_repos(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_turn(
            turn_metadata=sample_turn_metadata,
            turn_metrics=sample_turn_metrics,
        )
        mock_run_repo.write_turn_metadata.assert_called_once()
        assert mock_run_repo.write_turn_metadata.call_args[0][0] == sample_turn_metadata
        mock_metrics_repo.write_turn_metrics.assert_called_once()
        assert (
            mock_metrics_repo.write_turn_metrics.call_args[0][0] == sample_turn_metrics
        )

    def test_exception_from_write_turn_metadata_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        from simulation.core.utils.exceptions import DuplicateTurnMetadataError

        mock_run_repo.write_turn_metadata.side_effect = DuplicateTurnMetadataError(
            "run_1", 0
        )
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        with pytest.raises(DuplicateTurnMetadataError):
            service.write_turn(
                turn_metadata=sample_turn_metadata,
                turn_metrics=sample_turn_metrics,
            )
        mock_metrics_repo.write_turn_metrics.assert_not_called()

    def test_exception_from_write_turn_metrics_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        mock_metrics_repo.write_turn_metrics.side_effect = RuntimeError("db error")
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        with pytest.raises(RuntimeError):
            service.write_turn(
                turn_metadata=sample_turn_metadata,
                turn_metrics=sample_turn_metrics,
            )
        mock_run_repo.write_turn_metadata.assert_called_once()


class TestSimulationPersistenceServiceWriteRun:
    def test_calls_write_run_metrics_and_update_run_status(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_run_metrics,
    ):
        """When write_run is called, write_run_metrics and update_run_status are invoked in one transaction."""
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_run(run_id="run_1", run_metrics=sample_run_metrics)
        mock_metrics_repo.write_run_metrics.assert_called_once()
        assert mock_metrics_repo.write_run_metrics.call_args[0][0] == sample_run_metrics
        mock_run_repo.update_run_status.assert_called_once_with(
            "run_1",
            RunStatus.COMPLETED,
            conn=mock_metrics_repo.write_run_metrics.call_args[1]["conn"],
        )
        # Both called with same conn (transaction)
        write_conn = mock_metrics_repo.write_run_metrics.call_args[1]["conn"]
        status_conn = mock_run_repo.update_run_status.call_args[1]["conn"]
        assert write_conn is status_conn

    def test_passes_run_id_and_run_metrics(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_run_metrics,
    ):
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_run(run_id="run_1", run_metrics=sample_run_metrics)
        mock_metrics_repo.write_run_metrics.assert_called_once()
        assert mock_metrics_repo.write_run_metrics.call_args[0][0] == sample_run_metrics
        assert mock_run_repo.update_run_status.call_count == 1
        assert mock_run_repo.update_run_status.call_args[0][:2] == (
            "run_1",
            RunStatus.COMPLETED,
        )
        assert "conn" in mock_run_repo.update_run_status.call_args[1]

    def test_exception_from_write_run_metrics_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_generated_feed_repo,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_run_metrics,
    ):
        mock_metrics_repo.write_run_metrics.side_effect = RuntimeError("db error")
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            generated_feed_repo=mock_generated_feed_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        with pytest.raises(RuntimeError):
            service.write_run(run_id="run_1", run_metrics=sample_run_metrics)
        mock_run_repo.update_run_status.assert_not_called()


class TestSimulationPersistenceServiceAtomicity:
    def test_mid_write_failure_rolls_back_all_turn_rows(
        self,
        run_repo,
        metrics_repo,
        generated_feed_repo,
        like_repo,
        comment_repo,
        follow_repo,
    ):
        from db.adapters.sqlite.sqlite import SqliteTransactionProvider, get_connection
        from lib.agent_id import canonical_agent_id

        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        run_repo.update_run_status(run.run_id, RunStatus.RUNNING)
        agent_id = canonical_agent_id("atomic-test-agent.bsky.social")
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO agent (
                    agent_id, handle, persona_source, display_name, created_at, updated_at
                ) VALUES (?, ?, 'test', ?, '2026-01-01', '2026-01-01')
                """,
                (
                    agent_id,
                    "atomic-test-agent.bsky.social",
                    "atomic-test-agent.bsky.social",
                ),
            )
            conn.commit()

        turn_metadata = TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 1,
                TurnAction.COMMENT: 1,
                TurnAction.FOLLOW: 1,
            },
            created_at="2026-01-01T00:00:00",
        )
        turn_metrics = TurnMetricsFactory.create(
            run_id=run.run_id,
            turn_number=0,
            metrics={"turn.actions.total": 3},
            created_at="2026-01-01T00:00:00",
        )
        generated_feed = GeneratedFeedFactory.create(
            run_id=run.run_id,
            turn_number=0,
            agent_handle="atomic-test-agent.bsky.social",
            post_ids=["bluesky:at://did:plc:atomic/app.bsky.feed.post/post1"],
            created_at="2026-01-01T00:00:00",
        )
        like = GeneratedLikeFactory.create(
            agent_id=agent_id,
            post_id="bluesky:at://did:plc:atomic/app.bsky.feed.post/post1",
        )
        comment = GeneratedCommentFactory.create(
            agent_id=agent_id,
            post_id="bluesky:at://did:plc:atomic/app.bsky.feed.post/post1",
        )
        follow = GeneratedFollowFactory.create(
            agent_id=agent_id,
            target_agent_id=canonical_agent_id("atomic-target.bsky.social"),
        )

        class FailingFollowRepo(FollowRepository):
            def write_follows(self, *args, **kwargs) -> None:
                raise RuntimeError("forced follow write failure")

            def read_follows_by_run_turn(
                self, run_id: str, turn_number: int
            ) -> list[PersistedFollow]:
                return follow_repo.read_follows_by_run_turn(run_id, turn_number)

        service = create_simulation_persistence_service(
            run_repo=run_repo,
            metrics_repo=metrics_repo,
            generated_feed_repo=generated_feed_repo,
            transaction_provider=SqliteTransactionProvider(),
            like_repo=like_repo,
            comment_repo=comment_repo,
            follow_repo=FailingFollowRepo(),
        )

        with pytest.raises(RuntimeError, match="forced follow write failure"):
            service.write_turn(
                turn_metadata=turn_metadata,
                turn_metrics=turn_metrics,
                generated_feeds=[generated_feed],
                likes=[like],
                comments=[comment],
                follows=[follow],
            )

        assert run_repo.get_turn_metadata(run.run_id, 0) is None
        assert metrics_repo.get_turn_metrics(run.run_id, 0) is None
        assert generated_feed_repo.read_feeds_for_turn(run.run_id, 0) == []
        assert like_repo.read_likes_by_run_turn(run.run_id, 0) == []
        assert comment_repo.read_comments_by_run_turn(run.run_id, 0) == []
        assert follow_repo.read_follows_by_run_turn(run.run_id, 0) == []
