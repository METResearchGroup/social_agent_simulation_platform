"""Tests for POST /v1/simulations/run endpoint."""

from unittest.mock import MagicMock, patch

from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.actions import Comment, Follow, Like, TurnAction
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata
from simulation.core.utils.exceptions import SimulationRunFailure
from tests.factories import (
    EngineFactory,
    GeneratedFeedFactory,
    RunConfigFactory,
    RunFactory,
    TurnMetadataFactory,
    TurnMetricsFactory,
)


def _make_mock_engine_for_completed_run(
    *,
    fastapi_app,
    run_id: str,
    total_turns: int,
    total_agents: int,
) -> MagicMock:
    created_at = get_current_timestamp()
    run = Run(
        run_id=run_id,
        created_at=created_at,
        total_turns=total_turns,
        total_agents=total_agents,
        feed_algorithm="chronological",
        metric_keys=[
            "run.actions.total",
            "run.actions.total_by_type",
            "turn.actions.counts_by_type",
            "turn.actions.total",
        ],
        started_at=created_at,
        status=RunStatus.COMPLETED,
        completed_at=created_at,
    )
    metadata_list = [
        TurnMetadata(
            run_id=run.run_id,
            turn_number=i,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=run.created_at,
        )
        for i in range(total_turns)
    ]
    turn_metrics_list = [
        TurnMetrics(
            run_id=run.run_id,
            turn_number=i,
            metrics={"turn.actions.total": 0},
            created_at=run.created_at,
        )
        for i in range(total_turns)
    ]
    run_metrics = RunMetrics(
        run_id=run.run_id,
        metrics={"run.actions.total": 0},
        created_at=run.created_at,
    )
    mock_engine = MagicMock()
    mock_engine.execute_run.return_value = run
    mock_engine.list_turn_metadata.return_value = metadata_list
    mock_engine.list_turn_metrics.return_value = turn_metrics_list
    mock_engine.get_run_metrics.return_value = run_metrics
    fastapi_app.state.engine = mock_engine
    return mock_engine


def test_post_simulations_run_success_returns_completed_and_metrics(simulation_client):
    """Success run returns 200 with status completed and per-turn metrics."""
    client, fastapi_app = simulation_client
    mock_engine = EngineFactory.create_completed_run_engine(
        run_id="run-success-1",
        total_turns=1,
        total_agents=1,
    )
    fastapi_app.state.engine = mock_engine
    run = mock_engine.execute_run.return_value
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1, "num_turns": 1},
    )
    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result = {
        "status": "completed",
        "num_agents": 1,
        "num_turns": 1,
        "error": None,
        "turns": [
            {
                "turn_number": 0,
                "created_at": run.created_at,
                "total_actions": {"like": 0, "comment": 0, "follow": 0},
                "metrics": {"turn.actions.total": 0},
            }
        ],
        "run_metrics": {"run.actions.total": 0},
    }
    assert data["status"] == expected_result["status"]
    assert data["num_agents"] == expected_result["num_agents"]
    assert data["num_turns"] == expected_result["num_turns"]
    assert data["error"] is expected_result["error"]
    assert data["run_id"] == run.run_id
    assert data["created_at"] == run.created_at
    assert data["turns"] == expected_result["turns"]
    assert data["run_metrics"] == expected_result["run_metrics"]


def test_post_simulations_run_defaults_num_turns_and_feed_algorithm(simulation_client):
    """Request with only num_agents uses default num_turns=10 and feed_algorithm=chronological."""
    client, fastapi_app = simulation_client
    mock_engine = EngineFactory.create_completed_run_engine(
        run_id="run-defaults-1",
        total_turns=10,
        total_agents=1,
    )
    fastapi_app.state.engine = mock_engine
    run = mock_engine.execute_run.return_value
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1},
    )
    expected_result = {
        "status_code": 200,
        "num_turns": 10,
        "status": "completed",
        "turn_count": 10,
    }
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert data["created_at"] == run.created_at
    assert data["num_turns"] == expected_result["num_turns"]
    assert data["status"] == expected_result["status"]
    assert len(data["turns"]) == expected_result["turn_count"]


def test_post_simulations_run_passes_feed_algorithm_config_to_engine(simulation_client):
    """Request with feed_algorithm_config passes config into RunConfig used by engine."""
    client, fastapi_app = simulation_client
    mock_engine = EngineFactory.create_completed_run_engine(
        run_id="run-config-1",
        total_turns=10,
        total_agents=1,
    )
    fastapi_app.state.engine = mock_engine

    feed_algorithm_config = {"order": "oldest_first"}
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1, "feed_algorithm_config": feed_algorithm_config},
    )
    expected_result = {
        "status_code": 200,
        "feed_algorithm": "chronological",
        "feed_algorithm_config": feed_algorithm_config,
    }
    assert response.status_code == expected_result["status_code"]

    _, kwargs = mock_engine.execute_run.call_args
    run_config = kwargs["run_config"]
    assert run_config.feed_algorithm == expected_result["feed_algorithm"]
    assert run_config.feed_algorithm_config == expected_result["feed_algorithm_config"]


def test_post_simulations_run_validation_num_agents_zero(simulation_client):
    """Invalid num_agents returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 0},
    )
    expected_result = {"status_code": 422}
    assert response.status_code == expected_result["status_code"]


def test_post_simulations_run_validation_num_agents_missing(simulation_client):
    """Missing num_agents returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/run",
        json={},
    )
    expected_result = {"status_code": 422}
    assert response.status_code == expected_result["status_code"]


def test_post_simulations_run_validation_invalid_feed_algorithm(simulation_client):
    """Invalid feed_algorithm returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1, "feed_algorithm": "invalid_algo"},
    )
    expected_result = {"status_code": 422}
    assert response.status_code == expected_result["status_code"]


def test_post_simulations_run_pre_create_failure_returns_500(simulation_client):
    """Failure before run creation returns 500 with error payload."""
    client, fastapi_app = simulation_client
    mock_engine = MagicMock()
    mock_engine.execute_run.side_effect = SimulationRunFailure(
        message="Run creation or status update failed",
        run_id=None,
        cause=RuntimeError("db error"),
    )
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 2, "num_turns": 2},
    )
    expected_result = {
        "status_code": 500,
        "error_code": "RUN_CREATION_FAILED",
        "error_message": "Run creation or status update failed",
        "error_detail": None,
    }
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == expected_result["error_code"]
    assert data["error"]["message"] == expected_result["error_message"]
    assert data["error"]["detail"] is expected_result["error_detail"]


def test_post_simulations_run_partial_failure_returns_200_with_partial_metrics(
    simulation_client,
):
    """Mid-run failure returns 200 with status failed and partial per-turn metrics."""
    client, fastapi_app = simulation_client
    partial_metadata = [
        TurnMetadataFactory.create(
            run_id="run-partial-1",
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 3,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2026-01-01T00:00:00",
        ),
    ]
    partial_turn_metrics = [
        TurnMetricsFactory.create(
            run_id="run-partial-1",
            turn_number=0,
            metrics={"turn.actions.total": 3},
            created_at="2026-01-01T00:00:00",
        )
    ]
    failed_run = RunFactory.create(
        run_id="run-partial-1",
        created_at="2026-01-01T00:00:00",
        total_turns=2,
        total_agents=2,
        feed_algorithm="chronological",
        metric_keys=[
            "run.actions.total",
            "run.actions.total_by_type",
            "turn.actions.counts_by_type",
            "turn.actions.total",
        ],
        started_at="2026-01-01T00:00:00",
        status=RunStatus.FAILED,
        completed_at=None,
    )
    mock_engine = MagicMock()
    mock_engine.execute_run.side_effect = SimulationRunFailure(
        message="Run failed during execution",
        run_id="run-partial-1",
        cause=RuntimeError("turn 1 failed"),
    )
    mock_engine.list_turn_metadata.return_value = partial_metadata
    mock_engine.list_turn_metrics.return_value = partial_turn_metrics
    mock_engine.get_run_metrics.return_value = None
    mock_engine.get_run.return_value = failed_run
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 2, "num_turns": 2},
    )
    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result = {
        "run_id": "run-partial-1",
        "created_at": "2026-01-01T00:00:00",
        "status": "failed",
        "num_agents": 2,
        "num_turns": 2,
        "turns": [
            {
                "turn_number": 0,
                "created_at": "2026-01-01T00:00:00",
                "total_actions": {"like": 3, "comment": 0, "follow": 0},
                "metrics": {"turn.actions.total": 3},
            }
        ],
        "run_metrics": None,
    }
    assert data["run_id"] == expected_result["run_id"]
    assert data["created_at"] == expected_result["created_at"]
    assert data["status"] == expected_result["status"]
    assert data["num_agents"] == expected_result["num_agents"]
    assert data["num_turns"] == expected_result["num_turns"]
    assert data["turns"] == expected_result["turns"]
    assert data["run_metrics"] is expected_result["run_metrics"]
    assert data["error"] is not None
    expected_result = {
        "error_code": "SIMULATION_FAILED",
        "error_message": "Run failed during execution",
        "error_detail": None,
    }
    assert data["error"]["code"] == expected_result["error_code"]
    assert data["error"]["message"] == expected_result["error_message"]
    assert data["error"]["detail"] is expected_result["error_detail"]


def test_get_simulations_runs_returns_persisted_runs_newest_first(
    simulation_client,
    run_repo,
):
    """GET /v1/simulations/runs returns persisted run summaries, newest first."""
    import db.repositories.run_repository as run_repository_module

    with patch.object(
        run_repository_module,
        "get_current_timestamp",
        side_effect=["2026_01_01-00:00:00", "2026_01_02-00:00:00"],
    ):
        older_run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1, num_turns=1, feed_algorithm="chronological"
            )
        )
        newer_run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1, num_turns=1, feed_algorithm="chronological"
            )
        )

    client, _ = simulation_client
    response = client.get("/v1/simulations/runs")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert len(data) == 2
    assert data[0]["run_id"] == newer_run.run_id
    assert data[1]["run_id"] == older_run.run_id
    assert "total_turns" in data[0]
    assert "total_agents" in data[0]


def test_get_simulations_run_turns_returns_turn_map(
    simulation_client,
    run_repo,
    generated_feed_repo,
):
    """GET /v1/simulations/runs/{run_id}/turns returns turn payload map."""
    run = run_repo.create_run(
        RunConfigFactory.create(
            num_agents=1, num_turns=2, feed_algorithm="chronological"
        )
    )
    run_repo.write_turn_metadata(
        TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 1,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2026-01-01T00:00:00.000Z",
        )
    )
    run_repo.write_turn_metadata(
        TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=1,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2026-01-01T00:01:00.000Z",
        )
    )
    generated_feed_repo.write_generated_feed(
        GeneratedFeedFactory.create(
            feed_id="feed-1",
            run_id=run.run_id,
            turn_number=0,
            agent_handle="test.agent",
            post_uris=["at://did:plc:example1/post1"],
            created_at="2026-01-01T00:00:00.000Z",
        )
    )

    client, _ = simulation_client
    response = client.get(f"/v1/simulations/runs/{run.run_id}/turns")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result = {
        "turn_count": 2,
        "first_turn_key": "0",
    }
    assert len(data) == expected_result["turn_count"]
    assert expected_result["first_turn_key"] in data
    assert "turn_number" in data[expected_result["first_turn_key"]]
    assert "agent_feeds" in data[expected_result["first_turn_key"]]
    assert "agent_actions" in data[expected_result["first_turn_key"]]


def test_get_simulations_run_turns_hydrates_agent_actions(
    simulation_client,
    run_repo,
    generated_feed_repo,
    like_repo,
    comment_repo,
    follow_repo,
):
    """GET /v1/simulations/runs/{run_id}/turns returns hydrated agent_actions."""
    run = run_repo.create_run(
        RunConfig(num_agents=1, num_turns=1, feed_algorithm="chronological")
    )
    run_repo.write_turn_metadata(
        TurnMetadata(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 1,
                TurnAction.COMMENT: 1,
                TurnAction.FOLLOW: 1,
            },
            created_at="2026-01-01T00:00:00.000Z",
        )
    )
    agent_handle = "@agent1.bsky.social"
    post_uri = "at://did:plc:example1/post1"
    generated_feed_repo.write_generated_feed(
        GeneratedFeed(
            feed_id="feed-1",
            run_id=run.run_id,
            turn_number=0,
            agent_handle=agent_handle,
            post_uris=[post_uri],
            created_at="2026-01-01T00:00:00.000Z",
        )
    )
    created_at = "2026-01-01T00:00:00.000Z"
    meta = GenerationMetadata(
        model_used=None,
        generation_metadata={"test": True},
        created_at=created_at,
    )
    like_repo.write_likes(
        run.run_id,
        0,
        [
            GeneratedLike(
                like=Like(
                    like_id="like-1",
                    agent_id=agent_handle,
                    post_id=post_uri,
                    created_at=created_at,
                ),
                explanation="because",
                metadata=meta,
            )
        ],
    )
    comment_repo.write_comments(
        run.run_id,
        0,
        [
            GeneratedComment(
                comment=Comment(
                    comment_id="comment-1",
                    agent_id=agent_handle,
                    post_id=post_uri,
                    text="hello",
                    created_at=created_at,
                ),
                explanation="because",
                metadata=meta,
            )
        ],
    )
    follow_repo.write_follows(
        run.run_id,
        0,
        [
            GeneratedFollow(
                follow=Follow(
                    follow_id="follow-1",
                    agent_id=agent_handle,
                    user_id="@target.bsky.social",
                    created_at=created_at,
                ),
                explanation="because",
                metadata=meta,
            )
        ],
    )

    client, _ = simulation_client
    response = client.get(f"/v1/simulations/runs/{run.run_id}/turns")
    assert response.status_code == 200
    data = response.json()
    actions = data["0"]["agent_actions"][agent_handle]
    types = {a["type"] for a in actions}
    assert types == {"like", "comment", "follow"}
    like_action = next(a for a in actions if a["type"] == "like")
    assert like_action["post_uri"] == post_uri
    assert like_action["user_id"] is None
    follow_action = next(a for a in actions if a["type"] == "follow")
    assert follow_action["post_uri"] is None
    assert follow_action["user_id"] == "@target.bsky.social"


def test_get_simulations_run_turns_missing_run_returns_404(simulation_client):
    """Unknown run_id for turns endpoint returns stable RUN_NOT_FOUND payload."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/runs/missing-run-id/turns")

    expected_result = {"status_code": 404}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result = {
        "code": "RUN_NOT_FOUND",
        "message": "Run not found",
    }
    assert data["error"]["code"] == expected_result["code"]
    assert data["error"]["message"] == expected_result["message"]
